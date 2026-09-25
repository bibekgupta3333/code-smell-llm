from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .dataset import DatasetRepository, SmellKey
from .llm_client import Usage
from .taxonomy import ENTIRE_CLASS, SMELL_VOCAB


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


class SmellVocabulary:
    ALIASES: dict[str, str] = {
        "message chain":                  "Message Chains",
        "switch statement":               "Switch Statements",
        "temporary fields":               "Temporary Field",
        "long parameters list":           "Long Parameter List",
        "long parameters":                "Long Parameter List",
        "parallel inheritance hierarchy": "Parallel Inheritance Hierarchies",
        "parallel inheritance":           "Parallel Inheritance Hierarchies",
        "middleman":                      "Middle Man",
        "middle-man":                     "Middle Man",
        "inappropriate intimacies":       "Inappropriate Intimacy",
        "unnecessary comments":           "Comments",
        "useless comments":               "Comments",
        "duplicated code":                "Duplicate Code",
        "god class":                      "Large Class",
        "feature envies":                 "Feature Envy",
    }
    CATEGORY_LEAKS = frozenset({
        "bloaters", "object-orientation abusers", "oo abusers",
        "change preventers", "dispensables", "couplers",
    })
    _BY_LOWER = {s.lower(): s for s in SMELL_VOCAB}
    _METHOD_PARENS = re.compile(r"\(.*?\)\s*$")

    @classmethod
    def smell(cls, name: str) -> str | None:
        key = (name or "").strip().lower()
        if not key or key in cls.CATEGORY_LEAKS:
            return None
        return cls._BY_LOWER.get(key) or cls.ALIASES.get(key)

    @classmethod
    def method(cls, name: str) -> str:
        if not name:
            return ENTIRE_CLASS
        m = cls._METHOD_PARENS.sub("", name.strip())
        if m.count(".") == 1:
            m = m.split(".", 1)[1]
        return m or ENTIRE_CLASS


class ResponseParser:
    _FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
    _ANSWER = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.DOTALL | re.IGNORECASE)

    @classmethod
    def extract_json(cls, text: str) -> dict | None:
        if not text:
            return None
        m = cls._ANSWER.search(text)
        if m:
            text = m.group(1)
        m = cls._FENCE.search(text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return cls._first_balanced_object(text, start)

    @staticmethod
    def _first_balanced_object(text: str, start: int) -> dict | None:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    @staticmethod
    def findings(parsed: dict | None) -> list:
        return (parsed.get("findings", []) or []) if parsed else []

    @classmethod
    def prediction_keys(cls, record: dict, parsed: dict | None) -> set[SmellKey]:
        keys: set[SmellKey] = set()
        for f in cls.findings(parsed):
            if not isinstance(f, dict):
                continue
            smell = SmellVocabulary.smell(f.get("smell_type") or "")
            if smell is not None:
                keys.add((record["file_path"], record["class_name"], SmellVocabulary.method(f.get("method") or ENTIRE_CLASS), smell))
        return keys

    @classmethod
    def invalid_count(cls, parsed: dict | None) -> tuple[int, int]:
        findings = cls.findings(parsed)
        invalid = sum(1 for f in findings if isinstance(f, dict) and SmellVocabulary.smell(f.get("smell_type") or "") is None)
        return invalid, len(findings)

    @staticmethod
    def looks_truncated(response: str, parse_error: bool) -> bool:
        return bool(response) and (
            parse_error or response.rstrip().endswith((",", '"', ":")) or response.count("{") > response.count("}")
        )


@dataclass
class ScoredRecord:
    record: dict
    response: str
    usage: Usage
    parsed: dict | None = field(init=False)
    gold: set[SmellKey] = field(init=False)
    pred: set[SmellKey] = field(init=False)
    invalid_findings: int = field(init=False)
    total_findings: int = field(init=False)

    def __post_init__(self):
        self.parsed = ResponseParser.extract_json(self.response)
        self.gold = DatasetRepository.ground_truth_keys(self.record)
        self.pred = ResponseParser.prediction_keys(self.record, self.parsed)
        self.invalid_findings, self.total_findings = ResponseParser.invalid_count(self.parsed)

    @property
    def parse_error(self) -> bool:
        return self.parsed is None

    @property
    def truncated(self) -> bool:
        return ResponseParser.looks_truncated(self.response, self.parse_error)

    @property
    def language(self) -> str:
        return self.record["language"]

    @property
    def tp(self) -> int:
        return len(self.gold & self.pred)

    @property
    def fp(self) -> int:
        return len(self.pred - self.gold)

    @property
    def fn(self) -> int:
        return len(self.gold - self.pred)

    def status(self) -> str:
        if self.parse_error:
            return "PARSE_ERR" + ("+TRUNC" if self.truncated else "")
        flag = f"tp={self.tp} fp={self.fp} fn={self.fn}"
        if self.invalid_findings:
            flag += f" inv={self.invalid_findings}"
        return flag + (" TRUNC" if self.truncated else "")

    def prediction_json(self) -> dict:
        r = self.record
        return {
            "sample_id":   r["sample_id"],
            "language":    r["language"],
            "file_path":   r["file_path"],
            "parsed":      self.parsed,
            "gold_keys":   sorted(self.gold),
            "pred_keys":   sorted(self.pred),
            "parse_error": self.parse_error,
            "truncated":   self.truncated,
            "invalid_findings": self.invalid_findings,
            "total_findings":   self.total_findings,
            **self.usage.as_dict(),
            "raw":         self.response,
        }

    CSV_HEADER = (
        "sample_id", "language", "file_path", "class_name", "gold_count", "pred_count",
        "tp", "fp", "fn", "precision", "recall", "f1", "parse_error", "truncated",
        "invalid_findings", "total_findings", "input_tokens", "output_tokens", "total_tokens",
    )

    def csv_row(self) -> list:
        r = self.record
        p, rc, f = prf(self.tp, self.fp, self.fn)
        return [
            r["sample_id"], r["language"], r["file_path"], r["class_name"],
            len(self.gold), len(self.pred), self.tp, self.fp, self.fn,
            f"{p:.4f}", f"{rc:.4f}", f"{f:.4f}",
            int(self.parse_error), int(self.truncated), self.invalid_findings, self.total_findings,
            self.usage.input_tokens, self.usage.output_tokens, self.usage.total_tokens,
        ]


class MetricsCalculator:
    @staticmethod
    def _prf_block(counts: Sequence[int]) -> dict:
        return dict(zip(("precision", "recall", "f1"), (round(x, 4) for x in prf(*counts))),
                    **{"tp": counts[0], "fp": counts[1], "fn": counts[2]})

    @staticmethod
    def _macro_weighted(rows: list[dict], p: str, r: str, f: str, s: str) -> tuple[float, ...]:
        if not rows:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
        n = len(rows)
        total = sum(c[s] for c in rows)
        return (
            sum(c[p] for c in rows) / n,
            sum(c[r] for c in rows) / n,
            sum(c[f] for c in rows) / n,
            sum(c[p] * c[s] for c in rows) / total,
            sum(c[r] * c[s] for c in rows) / total,
            sum(c[f] * c[s] for c in rows) / total,
            total,
        )

    @staticmethod
    def _record_confusion(items: list[ScoredRecord], smell: str) -> tuple[int, int, int, int]:
        tp = fp = fn = tn = 0
        for it in items:
            in_gold = any(k[3] == smell for k in it.gold)
            in_pred = any(k[3] == smell for k in it.pred)
            if in_gold and in_pred:
                tp += 1
            elif in_pred:
                fp += 1
            elif in_gold:
                fn += 1
            else:
                tn += 1
        return tp, fp, fn, tn

    def _confusion(self, items: list[ScoredRecord], by_smell: dict) -> dict:
        n = len(items)
        out: dict[str, dict] = {}
        for smell in SMELL_VOCAB:
            occ_tp, occ_fp, occ_fn = by_smell[smell]
            occ_p, occ_r, occ_f = prf(occ_tp, occ_fp, occ_fn)
            rec_tp, rec_fp, rec_fn, rec_tn = self._record_confusion(items, smell)
            rec_p, rec_r, rec_f = prf(rec_tp, rec_fp, rec_fn)
            rec_acc = (rec_tp + rec_tn) / n if n else 0.0
            rec_spec = rec_tn / (rec_tn + rec_fp) if (rec_tn + rec_fp) else 0.0
            record_level = {
                "precision":   round(rec_p, 4),
                "recall":      round(rec_r, 4),
                "f1":          round(rec_f, 4),
                "specificity": round(rec_spec, 4),
                "accuracy":    round(rec_acc, 4),
                "support":     rec_tp + rec_fn,
            }
            out[smell] = {
                "occ_tp": occ_tp, "occ_fp": occ_fp, "occ_fn": occ_fn,
                "occ_precision": round(occ_p, 4), "occ_recall": round(occ_r, 4), "occ_f1": round(occ_f, 4),
                "occ_support": occ_tp + occ_fn,
                "rec_tp": rec_tp, "rec_fp": rec_fp, "rec_fn": rec_fn, "rec_tn": rec_tn,
                **{f"rec_{k}": v for k, v in record_level.items()},
                "tp": rec_tp, "fp": rec_fp, "fn": rec_fn, "tn": rec_tn,
                **record_level,
            }
        return out

    def _language_tables(self, by_lang: dict, by_lang_smell: dict, lang_n: dict) -> tuple[dict, dict]:
        per_smell: dict[str, dict] = {}
        summary: dict[str, dict] = {}
        for lang in sorted(by_lang):
            table = {}
            for smell in SMELL_VOCAB:
                s_tp, s_fp, s_fn = by_lang_smell[lang].get(smell, [0, 0, 0])
                sp, sr, sf = prf(s_tp, s_fp, s_fn)
                table[smell] = {"tp": s_tp, "fp": s_fp, "fn": s_fn, "support": s_tp + s_fn,
                                "precision": round(sp, 4), "recall": round(sr, 4), "f1": round(sf, 4)}
            per_smell[lang] = table
            l_tp, l_fp, l_fn = by_lang[lang]
            lp, lr, lf = prf(l_tp, l_fp, l_fn)
            present = [c for c in table.values() if c["support"] > 0]
            mp, mr, mf, wp, wr, wf, _ = self._macro_weighted(present, "precision", "recall", "f1", "support")
            summary[lang] = {
                "n_records": lang_n[lang],
                "tp": l_tp, "fp": l_fp, "fn": l_fn,
                "total_gt_occurrences":   l_tp + l_fn,
                "total_pred_occurrences": l_tp + l_fp,
                "smells_present_in_gt":   len(present),
                "micro_precision": round(lp, 4), "micro_recall": round(lr, 4), "micro_f1": round(lf, 4),
                "macro_precision": round(mp, 4), "macro_recall": round(mr, 4), "macro_f1": round(mf, 4),
                "weighted_precision": round(wp, 4), "weighted_recall": round(wr, 4), "weighted_f1": round(wf, 4),
            }
        return per_smell, summary

    def evaluate(self, records: Iterable[ScoredRecord]) -> dict:
        items = list(records)
        tp = fp = fn = 0
        by_lang: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
        by_smell: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
        by_lang_smell: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
        lang_n: dict[str, int] = defaultdict(int)
        for it in items:
            tp += it.tp; fp += it.fp; fn += it.fn
            lang = it.language
            lang_n[lang] += 1
            for slot, value in enumerate((it.tp, it.fp, it.fn)):
                by_lang[lang][slot] += value
            for slot, keys in enumerate((it.gold & it.pred, it.pred - it.gold, it.gold - it.pred)):
                for k in keys:
                    by_smell[k[3]][slot] += 1
                    by_lang_smell[lang][k[3]][slot] += 1

        confusion = self._confusion(items, by_smell)
        present = [c for c in confusion.values() if c["occ_support"] > 0]
        macro_p, macro_r, macro_f, w_p, w_r, w_f, _ = self._macro_weighted(
            present, "occ_precision", "occ_recall", "occ_f1", "occ_support")
        micro_p, micro_r, micro_f = prf(tp, fp, fn)
        per_language_per_smell, per_language_summary = self._language_tables(by_lang, by_lang_smell, lang_n)
        micro = {"precision": round(micro_p, 4), "recall": round(micro_r, 4), "f1": round(micro_f, 4)}
        return {
            "overall": {
                **micro,
                **{f"micro_{k}": v for k, v in micro.items()},
                "macro_precision": round(macro_p, 4), "macro_recall": round(macro_r, 4), "macro_f1": round(macro_f, 4),
                "weighted_precision": round(w_p, 4), "weighted_recall": round(w_r, 4), "weighted_f1": round(w_f, 4),
                "tp": tp, "fp": fp, "fn": fn,
                "n_records":           len(items),
                "parse_errors":        sum(it.parse_error for it in items),
                "truncated_responses": sum(it.truncated for it in items),
                "invalid_findings":    sum(it.invalid_findings for it in items),
                "total_findings":      sum(it.total_findings for it in items),
            },
            "per_language": {lang: self._prf_block(c) for lang, c in sorted(by_lang.items())},
            "per_smell": {smell: self._prf_block(c) for smell, c in sorted(by_smell.items())},
            "per_language_per_smell": per_language_per_smell,
            "per_language_summary":   per_language_summary,
            "confusion_matrix": confusion,
        }

    @staticmethod
    def _micro(items: Sequence[ScoredRecord]) -> tuple[float, float, float]:
        return prf(sum(it.tp for it in items), sum(it.fp for it in items), sum(it.fn for it in items))

    def bootstrap_ci(self, records: Iterable[ScoredRecord], *, n_resamples: int = 1000,
                     alpha: float = 0.05, seed: int = 42) -> dict:
        items = list(records)
        n = len(items)
        if n == 0:
            empty = {"point": 0.0, "lo": 0.0, "hi": 0.0, "stderr": 0.0}
            return {"n_resamples": 0, "alpha": alpha,
                    "micro_precision": empty, "micro_recall": empty, "micro_f1": empty}
        rng = random.Random(seed)
        samples = [self._micro([items[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples)]
        point = self._micro(items)

        def summarise(values: list[float], pt: float) -> dict:
            s = sorted(values)
            mean = sum(s) / len(s)
            var = sum((x - mean) ** 2 for x in s) / max(1, len(s) - 1)
            return {
                "point":  round(pt, 4),
                "lo":     round(s[int(alpha / 2 * n_resamples)], 4),
                "hi":     round(s[min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))], 4),
                "stderr": round(var ** 0.5, 4),
            }

        names = ("micro_precision", "micro_recall", "micro_f1")
        return {"n_resamples": n_resamples, "alpha": alpha,
                **{name: summarise([s[j] for s in samples], point[j]) for j, name in enumerate(names)}}
