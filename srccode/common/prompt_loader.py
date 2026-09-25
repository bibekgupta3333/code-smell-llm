from __future__ import annotations

import json
import random
from typing import Optional

from .config import Settings
from .dataset import DatasetRepository
from .rag_index import EmbeddingIndex, RandomRetriever
from .taxonomy import ENTIRE_CLASS


def number_lines(source: str) -> str:
    return "\n".join(f"{i:4d}| {line}" for i, line in enumerate(source.splitlines(), 1))


class ExemplarFormatter:
    @staticmethod
    def findings(record: dict, limit: int) -> list[dict]:
        return [
            {
                "smell_type": a["smell_type"],
                "category":   a["category"],
                "method":     a.get("method") or ENTIRE_CLASS,
                "line_start": a.get("line_start"),
                "line_end":   a.get("line_end"),
                "evidence":   a.get("evidence", ""),
            }
            for a in record["annotations"][:limit]
        ]

    @classmethod
    def few_shot(cls, i: int, r: dict) -> str:
        out = {"language": r["language"], "file_path": r["file_path"], "class_name": r["class_name"],
               "findings": cls.findings(r, 8)}
        return (
            f"### Example {i} — file_path = `{r['file_path']}`\n"
            f"```{r['language']}\n{number_lines(r['source_code'])}\n```\n\n"
            f"Expected output:\n```json\n{json.dumps(out, indent=2)}\n```\n"
        )

    @classmethod
    def retrieved(cls, i: int, r: dict) -> str:
        score = r.get("_rag_score")
        score_str = f" — cos={score:.3f}" if isinstance(score, float) else ""
        return (
            f"### Exemplar {i} — file_path={r['file_path']}{score_str}\n"
            f"<source>\n{number_lines(r['source_code'])}\n</source>\n"
            f"<findings>\n{json.dumps(cls.findings(r, 6), indent=2)}\n</findings>\n"
        )


class PromptBuilder:
    SYSTEM_MARKER = "<!-- SYSTEM -->"
    USER_MARKER = "<!-- USER -->"

    def __init__(self, settings: Settings, datasets: DatasetRepository | None = None):
        self._paths = settings.paths
        self._datasets = datasets or DatasetRepository(settings)
        self._dense = EmbeddingIndex(settings, self._datasets)
        self._random = RandomRetriever(self._datasets)

    @staticmethod
    def _read(path) -> str:
        return path.read_text(encoding="utf-8")

    @classmethod
    def split_roles(cls, template: str) -> tuple[str, str]:
        if cls.SYSTEM_MARKER not in template or cls.USER_MARKER not in template:
            raise ValueError(f"Template missing {cls.SYSTEM_MARKER} / {cls.USER_MARKER} markers")
        sys_text, user_text = template.split(cls.SYSTEM_MARKER, 1)[1].split(cls.USER_MARKER, 1)
        return sys_text.strip(), user_text.strip()

    def render(
        self,
        language: str,
        prompt_name: str,
        record: dict,
        *,
        few_shot_examples: Optional[str] = None,
        retrieved_snippets: Optional[str] = None,
        rag_mode: str = "dense",
        rag_k: int = 2,
    ) -> tuple[str, str]:
        template = self._read(self._paths.prompts / language / f"{prompt_name}.md")
        for placeholder, value in (
            ("{SYSTEM_BLOCK}", self._read(self._paths.system_block)),
            ("{TAXONOMY}", self._read(self._paths.taxonomy_block)),
            ("{OUTPUT_SCHEMA}", self._read(self._paths.schema_block)),
            ("{FILE_PATH}", record["file_path"]),
            ("{CLASS_NAME}", record["class_name"]),
            ("{SOURCE_CODE}", number_lines(record["source_code"])),
        ):
            template = template.replace(placeholder, value)
        if "{FEW_SHOT_EXAMPLES}" in template:
            template = template.replace("{FEW_SHOT_EXAMPLES}", few_shot_examples or self.few_shot(language, record))
        if "{RETRIEVED_SNIPPETS}" in template:
            template = template.replace(
                "{RETRIEVED_SNIPPETS}", retrieved_snippets or self.rag_context(language, record, k=rag_k, mode=rag_mode)
            )
        return self.split_roles(template)

    def few_shot(self, language: str, target: dict | None = None, n_pos: int = 2) -> str:
        target_id = (target or {}).get("sample_id")
        train = [r for r in self._datasets.train_pool(language) if r["sample_id"] != target_id]
        pos = [r for r in train if r["annotations"]]
        neg = [r for r in train if not r["annotations"]]
        rng = random.Random(42)
        chosen: list[dict] = rng.sample(pos, min(n_pos, len(pos))) if pos else []
        if neg:
            chosen.append(rng.choice(neg))
        return "\n".join(ExemplarFormatter.few_shot(i, r) for i, r in enumerate(chosen, 1))

    def rag_context(self, language: str, target: dict, k: int = 2, *, mode: str = "dense") -> str:
        chosen = self._dense.retrieve(language, target, k) if mode == "dense" else []
        if not chosen:
            chosen = self._random.retrieve(language, target, k)
        blocks = [ExemplarFormatter.retrieved(i, r) for i, r in enumerate(chosen, 1)]
        return "\n".join(blocks) if blocks else "(no exemplars retrieved)"
