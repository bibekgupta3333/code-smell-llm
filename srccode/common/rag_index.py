from __future__ import annotations

import random
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from .config import Settings
from .dataset import DatasetRepository


class Retriever(ABC):
    def __init__(self, datasets: DatasetRepository):
        self._datasets = datasets

    def _pool(self, language: str) -> list[dict]:
        return [r for r in self._datasets.train_pool(language) if r.get("annotations")]

    @abstractmethod
    def retrieve(self, language: str, target: dict, k: int) -> list[dict]:
        ...


class RandomRetriever(Retriever):
    def retrieve(self, language: str, target: dict, k: int) -> list[dict]:
        pool = [r for r in self._pool(language) if r["sample_id"] != target.get("sample_id")]
        rng = random.Random(hash(target.get("sample_id", "x")) & 0xFFFFFFFF)
        return rng.sample(pool, min(k, len(pool))) if pool else []


class EmbeddingIndex(Retriever):
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIM = 384
    MAX_CHARS = 4000

    _model = None
    _model_lock = threading.Lock()
    _cache: dict[str, dict] = {}

    def __init__(self, settings: Settings, datasets: DatasetRepository):
        super().__init__(datasets)
        self._cache_dir = settings.paths.embedding_cache

    @classmethod
    def _encoder(cls):
        if cls._model is None:
            with cls._model_lock:
                if cls._model is None:
                    from sentence_transformers import SentenceTransformer
                    cls._model = SentenceTransformer(cls.MODEL_NAME)
        return cls._model

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._encoder().encode(
            [t[: self.MAX_CHARS] for t in texts],
            batch_size=8,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs.astype(np.float32)

    def cache_path(self, language: str) -> Path:
        return self._cache_dir / f"rag_train_{language}.npz"

    def build(self, language: str, *, force: bool = False) -> dict:
        if not force and language in self._cache:
            return self._cache[language]
        pool = self._pool(language)
        entry = self._load_cached(language, pool) if not force else None
        if entry is None:
            entry = self._embed_pool(language, pool)
        self._cache[language] = entry
        return entry

    def _load_cached(self, language: str, pool: list[dict]) -> dict | None:
        path = self.cache_path(language)
        if not path.exists():
            return None
        npz = np.load(path, allow_pickle=False)
        if list(npz["sample_ids"]) != [r["sample_id"] for r in pool]:
            return None
        return {"vecs": npz["vecs"], "records": pool}

    def _embed_pool(self, language: str, pool: list[dict]) -> dict:
        if not pool:
            return {"vecs": np.zeros((0, self.DIM), dtype=np.float32), "records": []}
        vecs = self.embed([r["source_code"] for r in pool])
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez(self.cache_path(language), vecs=vecs, sample_ids=np.array([r["sample_id"] for r in pool], dtype="U128"))
        return {"vecs": vecs, "records": pool}

    def retrieve(self, language: str, target: dict, k: int) -> list[dict]:
        idx = self.build(language)
        if idx["vecs"].shape[0] == 0:
            return []
        sims = idx["vecs"] @ self.embed([target["source_code"]])[0]
        out: list[dict] = []
        for i in np.argsort(-sims):
            rec = idx["records"][int(i)]
            if rec["sample_id"] == target.get("sample_id"):
                continue
            out.append({**rec, "_rag_score": float(sims[int(i)])})
            if len(out) >= k:
                break
        return out

    def build_all(self, verbose: bool = True) -> None:
        for lang in sorted({r["language"] for r in self._datasets.train_annotated}):
            idx = self.build(lang, force=True)
            if verbose:
                print(f"[rag-index] {lang:12s}  n={idx['vecs'].shape[0]:4d}  "
                      f"dim={idx['vecs'].shape[1] if idx['vecs'].size else 0}  "
                      f"cache={self.cache_path(lang).name}")

    @classmethod
    def metadata(cls) -> dict:
        return {
            "encoder": cls.MODEL_NAME,
            "dim": cls.DIM,
            "similarity": "cosine (L2-normalised dot product)",
            "truncation_chars": cls.MAX_CHARS,
        }
