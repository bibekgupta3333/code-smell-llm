from __future__ import annotations

import json
from functools import cached_property

from .config import Settings
from .taxonomy import ENTIRE_CLASS, LABEL_RE

SmellKey = tuple[str, str, str, str]


class LabelCommentScrubber:
    MARKERS = {"python": "#", "java": "//", "javascript": "//", "cpp": "//"}

    @classmethod
    def scrub_line(cls, line: str, language: str) -> str | None:
        i = line.find(cls.MARKERS[language])
        if i < 0 or not LABEL_RE.search(line[i:]):
            return line
        code = line[:i].rstrip()
        return code if code.strip() else None

    @classmethod
    def scrub(cls, source: str, language: str) -> str:
        kept = [cls.scrub_line(line, language) for line in source.splitlines()]
        return "\n".join(line for line in kept if line is not None)

    @classmethod
    def clean_record(cls, record: dict) -> dict:
        lang = record["language"]
        annotations = [
            {**a, "evidence": cls.scrub_line(a.get("evidence") or "", lang) or ""}
            for a in record.get("annotations") or []
        ]
        return {**record, "source_code": cls.scrub(record["source_code"], lang), "annotations": annotations}


class DatasetRepository:
    DATASETS = ("annotated", "unannotated")
    SPLITS = ("all", "train", "val", "test", "java", "python", "javascript", "cpp")

    def __init__(self, settings: Settings):
        self._paths = settings.paths
        self._clean = settings.strip_label_comments

    def _prepare(self, records: list[dict]) -> list[dict]:
        return [LabelCommentScrubber.clean_record(r) for r in records] if self._clean else records

    def load(self, language: str | None = None, dataset: str = "unannotated", split: str = "test") -> list[dict]:
        if dataset not in self.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset!r}")
        if split not in self.SPLITS:
            raise ValueError(f"Unknown split: {split!r}")
        records = self._prepare(json.loads((self._paths.prepared / dataset / f"{split}.json").read_text(encoding="utf-8")))
        return [r for r in records if r["language"] == language] if language else records

    @cached_property
    def train_annotated(self) -> list[dict]:
        return self._prepare(json.loads(self._paths.train_annotated.read_text(encoding="utf-8")))

    def train_pool(self, language: str) -> list[dict]:
        return [r for r in self.train_annotated if r["language"] == language]

    @staticmethod
    def ground_truth_keys(record: dict) -> set[SmellKey]:
        items = record.get("ground_truth") or record.get("annotations") or []
        return {
            (record["file_path"], record["class_name"], (g.get("method") or ENTIRE_CLASS).strip(), g["smell_type"].strip())
            for g in items
        }
