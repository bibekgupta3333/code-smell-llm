from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from srccode.common.taxonomy import CATEGORY_OF, ENTIRE_CLASS

LABEL_ALIASES: dict[str, str] = {
    "Message Chain": "Message Chains",
    "Switch Statement": "Switch Statements",
    "Temporary Fields": "Temporary Field",
    "Long Parameters List": "Long Parameter List",
    "Long Parameters": "Long Parameter List",
    "Parallel Inheritance Hierarchy": "Parallel Inheritance Hierarchies",
    "Parallel Inheritance": "Parallel Inheritance Hierarchies",
    "Middleman": "Middle Man",
    "Inappropriate Intimacies": "Inappropriate Intimacy",
    "Unnecessary Comments": "Comments",
    "Useless Comments": "Comments",
}


class CommentAnnotationExtractor:
    COMMENT_PREFIXES = {
        "java": ("//", "/*", "*"),
        "javascript": ("//", "/*", "*"),
        "cpp": ("//", "/*", "*"),
        "python": ("#",),
    }
    CONTROL_KEYWORDS = {"if", "for", "while", "switch", "return", "catch"}
    _NAMES = sorted(set(CATEGORY_OF) | set(LABEL_ALIASES), key=lambda s: (-len(s), s))
    SMELL_RE = re.compile(r"\b(" + "|".join(re.escape(n) for n in _NAMES) + r")\b")
    METHOD_PATTERNS = {
        "python": re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\("),
        "java": re.compile(r"^\s*(?:public|private|protected|static|async|function|constructor|\w[\w<>\[\]]*\s+)*"
                           r"([A-Za-z_]\w*)\s*\([^;]*\)\s*\{?\s*$"),
        "cpp": re.compile(r"^\s*[\w:~<>*&\s]+?\s+([A-Za-z_]\w*)::([A-Za-z_]\w*)\s*\("),
    }
    METHOD_PATTERNS["javascript"] = METHOD_PATTERNS["java"]

    def __init__(self, lang: str):
        self.lang = lang

    @staticmethod
    def canonical_smell(raw: str) -> str | None:
        raw = raw.strip()
        return LABEL_ALIASES.get(raw, raw if raw in CATEGORY_OF else None)

    def is_comment_line(self, line: str) -> bool:
        return line.lstrip().startswith(self.COMMENT_PREFIXES[self.lang])

    def comment_payload(self, line: str) -> str:
        if self.lang == "python":
            i = line.find("#")
            return line[i + 1 :] if i >= 0 else ""
        i = line.find("//")
        if i >= 0:
            return line[i + 2 :]
        i = line.find("/*")
        if i >= 0:
            return line[i + 2 :].rstrip("*/").strip()
        s = line.lstrip()
        return s[1:] if s.startswith("*") else ""

    def method_for_line(self, lines: list[str], lineno: int) -> str:
        pat = self.METHOD_PATTERNS[self.lang]
        for i in range(lineno - 1, -1, -1):
            m = pat.match(lines[i])
            if m:
                name = m.group(2) if (self.lang == "cpp" and m.lastindex and m.lastindex >= 2) else m.group(1)
                if name and name not in self.CONTROL_KEYWORDS:
                    return name
        return ENTIRE_CLASS

    def block_extent(self, lines: list[str], lineno: int) -> int:
        end = lineno
        for i in range(lineno, len(lines)):
            if not lines[i].strip() or self.is_comment_line(lines[i]):
                break
            end = i + 1
        return max(end, lineno)

    @staticmethod
    def brace_end(lines: list[str], header_lineno: int) -> int:
        depth, started = 0, False
        for i in range(header_lineno - 1, len(lines)):
            for ch in lines[i]:
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1
                    if started and depth == 0:
                        return i + 1
        return header_lineno

    @staticmethod
    def indent_end(lines: list[str], header_idx: int) -> int:
        header = lines[header_idx]
        header_indent = len(header) - len(header.lstrip())
        end = header_idx + 1
        for k in range(header_idx + 1, len(lines)):
            s = lines[k]
            if s.strip() == "":
                continue
            if len(s) - len(s.lstrip()) <= header_indent:
                break
            end = k + 1
        return end

    def method_end(self, lines: list[str], header_idx: int) -> int:
        return self.indent_end(lines, header_idx) if self.lang == "python" else self.brace_end(lines, header_idx + 1)

    def looks_like_method_header(self, line: str) -> bool:
        if self.lang == "python":
            i = line.find("#")
            return bool(re.match(r"^\s*def\s+\w+\s*\(", line[:i] if i >= 0 else line))
        i = line.find("//")
        s = (line[:i] if i >= 0 else line).strip()
        if not s or ";" in s:
            return False
        return bool(re.search(r"\)\s*\{?\s*$", s)) and "(" in s

    def _span(self, lines: list[str], i: int, raw: str) -> tuple[int, str, str]:
        line_start = i + 1
        if raw.lstrip().startswith(("//", "#", "/*", "*")):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or self.is_comment_line(lines[j])):
                j += 1
            if j < len(lines) and self.looks_like_method_header(lines[j]):
                return self.method_end(lines, j), "method-scope", self.method_for_line(lines, j + 1)
            return self.block_extent(lines, line_start), "block", self.method_for_line(lines, line_start)
        if self.looks_like_method_header(raw):
            return self.method_end(lines, i), "method-scope", self.method_for_line(lines, line_start)
        return line_start, "inline", self.method_for_line(lines, line_start)

    def extract(self, text: str) -> list[dict]:
        lines = text.splitlines()
        seen: set[tuple] = set()
        out: list[dict] = []
        for i, raw in enumerate(lines):
            payload = self.comment_payload(raw)
            if not payload:
                continue
            for m in self.SMELL_RE.finditer(payload):
                canon = self.canonical_smell(m.group(1))
                if not canon:
                    continue
                line_end, kind, method = self._span(lines, i, raw)
                key = (canon, i + 1, line_end)
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "smell_type": canon,
                    "category": CATEGORY_OF[canon],
                    "method": method,
                    "line_start": i + 1,
                    "line_end": line_end,
                    "evidence": raw.rstrip(),
                    "annotation_kind": kind,
                })
        return out


class SmellyCodeDatasetBuilder:
    LANG_DIR = {
        "java": ("Java", ".java"),
        "python": ("Python", ".py"),
        "javascript": ("JavaScript", ".js"),
        "cpp": ("C++", (".cpp", ".h")),
    }
    SOURCE_VARIANT = {"annotated": "SmellyAnnotated", "unannotated": "SmellyUnannotated"}
    SKIP_NAMES = {"Makefile"}
    CSV_LANG = {"Java": "java", "Python": "python", "JavaScript": "javascript", "C++": "cpp"}
    OCCURRENCE_HEADER = ["language", "file_path", "class_name", "smell_type", "category", "method",
                         "line_start", "line_end", "annotation_kind", "evidence"]

    def __init__(self, dataset_root: Path | None = None, out_root: Path | None = None):
        self.dataset_root = dataset_root or ROOT / "data" / "datasets" / "SmellyCodeDataset"
        self.out_root = out_root or ROOT / "prepared_data" / "datasets"

    def load_ground_truth_csv(self) -> dict[tuple[str, str], list[dict]]:
        path = self.dataset_root / "Analysis" / "GroundTruthLevel" / "Cleaned_GroundTruth.csv"
        out: dict[tuple[str, str], list[dict]] = defaultdict(list)
        with path.open() as f:
            for row in csv.DictReader(f):
                lang = self.CSV_LANG.get(row["Language"])
                if lang:
                    out[(lang, row["Class"])].append({
                        "smell_type": LABEL_ALIASES.get(row["Code Smell"], row["Code Smell"]),
                        "category": row["Category"],
                        "method": row["Method"],
                        "description": row.get("Type", ""),
                    })
        return out

    def collect_files(self, lang: str, variant: str) -> list[Path]:
        sub, ext = self.LANG_DIR[lang]
        folder = self.dataset_root / sub / variant
        exts = (ext,) if isinstance(ext, str) else ext
        files = sorted(p for e in exts for p in sorted(folder.glob(f"*{e}")))
        return [p for p in files if p.name not in self.SKIP_NAMES]

    def _base_record(self, p: Path, lang: str) -> dict:
        text = p.read_text(encoding="utf-8", errors="replace")
        cls = p.stem
        return {
            "sample_id": f"{lang}_{cls}_{p.suffix.lstrip('.')}",
            "language": lang,
            "class_name": cls,
            "file_path": str(p.relative_to(self.dataset_root)),
            "loc": len(text.splitlines()),
            "source_code": text,
            "annotations": [],
        }

    def build_record_annotated(self, p: Path, lang: str) -> dict:
        rec = self._base_record(p, lang)
        rec["annotations"] = CommentAnnotationExtractor(lang).extract(rec["source_code"])
        rec["metadata"] = {"variant": "annotated", "num_annotations": len(rec["annotations"]), "num_lines": rec["loc"]}
        return rec

    def build_record_unannotated(self, p: Path, lang: str, gt_index: dict) -> dict:
        rec = self._base_record(p, lang)
        rec["ground_truth"] = gt_index.get((lang, rec["class_name"]), [])
        rec["metadata"] = {"variant": "unannotated", "num_ground_truth": len(rec["ground_truth"]), "num_lines": rec["loc"]}
        return rec

    @staticmethod
    def stratified_split(samples: list[dict], ratios=(0.6, 0.2, 0.2), seed: int = 42):
        rng = random.Random(seed)
        by_lang: dict[str, list[dict]] = defaultdict(list)
        for s in samples:
            by_lang[s["language"]].append(s)
        train, val, test = [], [], []
        for group in by_lang.values():
            g = group[:]
            rng.shuffle(g)
            n = len(g)
            n_tr = max(1, int(round(n * ratios[0])))
            n_val = max(1, int(round(n * ratios[1])))
            if n_tr + n_val >= n:
                n_val = max(1, n - n_tr - 1)
            train += g[:n_tr]
            val += g[n_tr : n_tr + n_val]
            test += g[n_tr + n_val :]
        return train, val, test

    @staticmethod
    def labels(record: dict, variant: str) -> list[dict]:
        return record.get("annotations") if variant == "annotated" else record.get("ground_truth", [])

    @staticmethod
    def write_json(path: Path, obj) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

    def _write_csv(self, path: Path, rows: list[list]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(self.OCCURRENCE_HEADER)
            w.writerows(rows)

    def write_occurrence_csvs(self, out_dir: Path, variant: str, per_lang: dict[str, list[dict]]) -> None:
        occ_dir = out_dir / "occurrences"
        occ_dir.mkdir(parents=True, exist_ok=True)
        all_rows: list[list] = []
        for lang, recs in per_lang.items():
            rows = [
                [r["language"], r["file_path"], r["class_name"], a.get("smell_type", ""), a.get("category", ""),
                 a.get("method", ""), a.get("line_start", ""), a.get("line_end", ""), a.get("annotation_kind", ""),
                 a.get("evidence", a.get("description", ""))]
                for r in recs for a in self.labels(r, variant)
            ]
            self._write_csv(occ_dir / f"{lang}.csv", rows)
            all_rows.extend(rows)
        self._write_csv(occ_dir / "all.csv", all_rows)

    def build_variant(self, variant: str, gt_index) -> dict:
        out_dir = self.out_root / variant
        per_lang: dict[str, list[dict]] = {}
        all_samples: list[dict] = []
        for lang in self.LANG_DIR:
            files = self.collect_files(lang, self.SOURCE_VARIANT[variant])
            recs = [self.build_record_annotated(p, lang) if variant == "annotated"
                    else self.build_record_unannotated(p, lang, gt_index) for p in files]
            per_lang[lang] = recs
            all_samples.extend(recs)
            self.write_json(out_dir / f"{lang}.json", recs)
        self.write_json(out_dir / "all.json", all_samples)
        splits = dict(zip(("train", "val", "test"), self.stratified_split(all_samples)))
        for name, part in splits.items():
            self.write_json(out_dir / f"{name}.json", part)
        self.write_occurrence_csvs(out_dir, variant, per_lang)

        smell_counts: Counter = Counter()
        cat_counts: Counter = Counter()
        per_lang_smell: dict[str, Counter] = defaultdict(Counter)
        for s in all_samples:
            for a in self.labels(s, variant):
                smell_counts[a["smell_type"]] += 1
                cat_counts[a["category"]] += 1
                per_lang_smell[s["language"]][a["smell_type"]] += 1
        return {
            "variant": variant,
            "num_files": len(all_samples),
            "files_per_language": {k: len(v) for k, v in per_lang.items()},
            "split_sizes": {k: len(v) for k, v in splits.items()},
            "total_labels": sum(smell_counts.values()),
            "smell_counts": dict(smell_counts.most_common()),
            "category_counts": dict(cat_counts.most_common()),
            "per_language_smell_counts": {k: dict(v.most_common()) for k, v in per_lang_smell.items()},
        }

    def run(self) -> dict:
        self.out_root.mkdir(parents=True, exist_ok=True)
        gt_index = self.load_ground_truth_csv()
        summary = {
            "annotated": self.build_variant("annotated", gt_index),
            "unannotated": self.build_variant("unannotated", gt_index),
            "smell_taxonomy": {
                "categories": sorted(set(CATEGORY_OF.values())),
                "smells": sorted(CATEGORY_OF),
                "aliases": LABEL_ALIASES,
            },
        }
        self.write_json(self.out_root / "summary.json", summary)
        return summary


def main() -> None:
    print(json.dumps(SmellyCodeDatasetBuilder().run(), indent=2))


if __name__ == "__main__":
    main()
