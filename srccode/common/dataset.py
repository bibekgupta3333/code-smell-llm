from __future__ import annotations

import json
from functools import cached_property

from .config import Settings
from .taxonomy import ENTIRE_CLASS

SmellKey = tuple[str, str, str, str]


class DatasetRepository:
    DATASETS = ("annotated", "unannotated")
    SPLITS = ("all", "train", "val", "test", "java", "python", "javascript", "cpp")

    def __init__(self, settings: Settings):
        self._paths = settings.paths

    def load(self, language: str | None = None, dataset: str = "unannotated", split: str = "test") -> list[dict]:
        if dataset not in self.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset!r}")
        if split not in self.SPLITS:
            raise ValueError(f"Unknown split: {split!r}")
        records = json.loads((self._paths.prepared / dataset / f"{split}.json").read_text(encoding="utf-8"))
        return [r for r in records if r["language"] == language] if language else records

    @cached_property
    def train_annotated(self) -> list[dict]:
        return json.loads(self._paths.train_annotated.read_text(encoding="utf-8"))

    def train_pool(self, language: str) -> list[dict]:
        return [r for r in self.train_annotated if r["language"] == language]

    @staticmethod
    def ground_truth_keys(record: dict) -> set[SmellKey]:
        items = record.get("ground_truth") or record.get("annotations") or []
        return {
            (record["file_path"], record["class_name"], (g.get("method") or ENTIRE_CLASS).strip(), g["smell_type"].strip())
            for g in items
        }
