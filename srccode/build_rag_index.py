from __future__ import annotations

from .common.config import Settings
from .common.dataset import DatasetRepository
from .common.rag_index import EmbeddingIndex


def main() -> None:
    settings = Settings.from_env()
    index = EmbeddingIndex(settings, DatasetRepository(settings))
    meta = index.metadata()
    print(f"[rag-index] encoder={meta['encoder']}  dim={meta['dim']}  sim={meta['similarity']}")
    index.build_all(verbose=True)
    print("[rag-index] done")


if __name__ == "__main__":
    main()
