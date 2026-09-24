from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Settings
from .dataset import DatasetRepository
from .evaluator import MetricsCalculator, ScoredRecord
from .llm_client import LLMClient, Provider, Usage, create_client
from .prompt_loader import PromptBuilder

LANGUAGES = ["java", "python", "javascript", "cpp"]
LONG_CONTEXT_PROMPTS = ("p2_few_shot", "p5_rag")


@dataclass
class RunConfig:
    prompt_name: str
    provider: str
    model: str | None
    language: str | None
    dataset: str
    split: str
    limit: int | None
    temperature: float
    seed: int
    num_ctx: int | None
    num_predict: int
    workers: int
    bootstrap: int
    no_csv: bool
    rag_mode: str
    rag_k: int
    output_dir: str
    verbose: bool

    @property
    def is_rag(self) -> bool:
        return self.prompt_name == "p5_rag"

    @classmethod
    def parser(cls, prompt_name: str, settings: Settings) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(description=f"Run {prompt_name}")
        p.add_argument("--provider", choices=["auto", "local", "cloud", "bedrock"], default="auto",
                       help="LLM backend: 'auto' detects from OLLAMA_HOST; 'local' = Ollama at localhost:11434; "
                            "'cloud' = Ollama Cloud (needs OLLAMA_API_KEY); 'bedrock' = AWS Bedrock converse API.")
        p.add_argument("--model", default=None, help="Model id (Ollama tag or Bedrock model id). Default depends on --provider.")
        p.add_argument("--language", choices=LANGUAGES, default=None, help="Filter to one language")
        p.add_argument("--dataset", choices=list(DatasetRepository.DATASETS)[::-1], default="unannotated",
                       help="Which annotation flavour to evaluate against")
        p.add_argument("--split", choices=list(DatasetRepository.SPLITS), default="test",
                       help="File under prepared_data/datasets/<dataset>/ to load: all=34, train=20, val=6, test=8, "
                            "or a language name for that language's full set.")
        p.add_argument("--limit", type=int, default=None, help="Cap number of records (debug)")
        p.add_argument("--temperature", type=float, default=0.0)
        p.add_argument("--seed", type=int, default=42)
        p.add_argument("--num-ctx", type=int, default=None,
                       help="Input context window (Ollama only). Default 8192, or 16384 for p2/p5. Ignored on Bedrock.")
        p.add_argument("--num-predict", type=int, default=8000, help="Max output tokens (Ollama num_predict / Bedrock maxTokens).")
        p.add_argument("--workers", type=int, default=8, help="Records processed concurrently (1 = sequential).")
        p.add_argument("--bootstrap", type=int, default=1000, help="Bootstrap resamples for micro P/R/F1 95%% CIs (0 disables).")
        p.add_argument("--no-csv", action="store_true", help="Skip per-record CSV export.")
        p.add_argument("--rag-mode", choices=["dense", "random"], default="dense",
                       help="P5 retrieval: 'dense' = all-MiniLM-L6-v2 cosine over the train split; 'random' = null-retriever ablation.")
        p.add_argument("--rag-k", type=int, default=2, help="Number of exemplars retrieved for P5.")
        p.add_argument("--output-dir", default=str(settings.paths.results))
        p.add_argument("--verbose", action="store_true", help="Log full prompts and responses.")
        return p

    @classmethod
    def from_cli(cls, prompt_name: str, settings: Settings, argv: list[str] | None = None) -> "RunConfig":
        args = cls.parser(prompt_name, settings).parse_args(argv)
        return cls(prompt_name=prompt_name, **vars(args))


class SummaryPrinter:
    def print(self, metrics: dict, verbose: bool = False) -> None:
        self._overall(metrics)
        self._languages(metrics)
        if verbose:
            self._per_language_smells(metrics)
            self._confusion(metrics)

    @staticmethod
    def _overall(metrics: dict) -> None:
        o = metrics["overall"]
        print(f"\n{'=' * 72}")
        print(f"Records: {o['n_records']}   Parse errors: {o['parse_errors']}")
        print(f"Pooled keys: TP={o['tp']}  FP={o['fp']}  FN={o['fn']}")
        tu = metrics.get("token_usage")
        if tu:
            print(f"Tokens   : in={tu['total_input_tokens']}  out={tu['total_output_tokens']}  "
                  f"total={tu['total_tokens']}   avg in/out={tu['avg_input_tokens']:.0f}/{tu['avg_output_tokens']:.0f}   "
                  f"max in/out={tu['max_input_tokens']}/{tu['max_output_tokens']}")
        print(f"\n{'Metric':22s} {'Precision':>10s} {'Recall':>10s} {'F1':>10s}")
        print(f"{'-' * 56}")
        for label, prefix in (("Micro (pooled keys)", "micro"), ("Macro (avg over smells)", "macro"),
                              ("Weighted (by support)", "weighted")):
            print(f"{label:22s} {o[f'{prefix}_precision']:>10.4f} {o[f'{prefix}_recall']:>10.4f} {o[f'{prefix}_f1']:>10.4f}")
        bs = metrics.get("bootstrap_ci")
        if bs:
            print(f"\nBootstrap {int((1 - bs['alpha']) * 100)}% CI  ({bs['n_resamples']} resamples, percentile method):")
            for k, label in (("micro_precision", "Micro Precision"), ("micro_recall", "Micro Recall   "),
                             ("micro_f1", "Micro F1       ")):
                s = bs[k]
                print(f"  {label}  {s['point']:.4f}  [{s['lo']:.4f}, {s['hi']:.4f}]   SE={s['stderr']:.4f}")

    @staticmethod
    def _languages(metrics: dict) -> None:
        print(f"\n{'=' * 72}\nPer-language summary (occurrence-level, micro/macro/weighted):")
        print(f"  {'lang':<10s} {'N':>3s} {'GT':>4s} {'Pred':>4s} | {'micP':>5s} {'micR':>5s} {'micF1':>6s} | "
              f"{'macP':>5s} {'macR':>5s} {'macF1':>6s} | {'wP':>5s} {'wR':>5s} {'wF1':>6s}")
        print("  " + "-" * 88)
        for lang, s in metrics.get("per_language_summary", {}).items():
            print(f"  {lang:<10s} {s['n_records']:>3d} {s['total_gt_occurrences']:>4d} {s['total_pred_occurrences']:>4d} | "
                  + " | ".join(f"{s[f'{p}_precision']:>5.2f} {s[f'{p}_recall']:>5.2f} {s[f'{p}_f1']:>6.3f}"
                               for p in ("micro", "macro", "weighted")))

    @staticmethod
    def _per_language_smells(metrics: dict) -> None:
        for lang, table in metrics.get("per_language_per_smell", {}).items():
            present = [(s, c) for s, c in table.items() if c["support"] > 0 or c["fp"] > 0]
            if not present:
                continue
            present.sort(key=lambda kv: (-kv[1]["support"], -kv[1]["fp"], kv[0]))
            gt_total = sum(c["support"] for _, c in present)
            pred_total = sum(c["tp"] + c["fp"] for _, c in present)
            print(f"\n{'-' * 84}\n[{lang}] per-smell — actual vs predicted (occurrence-level)   GT={gt_total}  Pred={pred_total}")
            print(f"  {'Smell':<42s} {'Act':>4s} {'Pred':>5s} {'TP':>3s} {'FP':>3s} {'FN':>3s} {'P':>5s} {'R':>5s} {'F1':>5s}")
            print("  " + "-" * 82)
            for smell, c in present:
                print(f"  {smell:<42s} {c['support']:>4d} {c['tp']+c['fp']:>5d} {c['tp']:>3d} {c['fp']:>3d} {c['fn']:>3d} "
                      f"{c['precision']:>5.2f} {c['recall']:>5.2f} {c['f1']:>5.2f}")

    @staticmethod
    def _confusion(metrics: dict) -> None:
        print(f"\n{'=' * 100}\nConfusion matrix per smell (ALL languages combined) — occurrence-level + record-level:")
        print(f"{'Smell':<48s} | {'oTP':>4s} {'oFP':>4s} {'oFN':>4s} {'oP':>5s} {'oR':>5s} {'oF1':>5s} {'oSup':>4s} | "
              f"{'rTP':>3s} {'rFP':>3s} {'rFN':>3s} {'rTN':>3s} {'rF1':>5s} {'rSup':>4s}")
        print("-" * 120)
        for smell, c in sorted(metrics["confusion_matrix"].items(), key=lambda kv: (-kv[1]["occ_support"], kv[0])):
            print(f"{smell:<48s} | {c['occ_tp']:>4d} {c['occ_fp']:>4d} {c['occ_fn']:>4d} {c['occ_precision']:>5.2f} "
                  f"{c['occ_recall']:>5.2f} {c['occ_f1']:>5.2f} {c['occ_support']:>4d} | {c['rec_tp']:>3d} {c['rec_fp']:>3d} "
                  f"{c['rec_fn']:>3d} {c['rec_tn']:>3d} {c['rec_f1']:>5.2f} {c['rec_support']:>4d}")
        print("\nLegend: Act = actual GT occurrences, Pred = total predicted, o* = occurrence-level, "
              "r* = record-level binary (per file)")


class ResultWriter:
    def __init__(self, config: RunConfig):
        self._config = config

    def base_name(self) -> str:
        c = self._config
        safe_model = c.model.replace("/", "_").replace(":", "_")
        rag_tag = f"__{c.rag_mode}_k{c.rag_k}" if c.is_rag else ""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{c.prompt_name}__{safe_model}__{c.dataset}__{c.split}__{c.language or 'all'}{rag_tag}__{stamp}"

    def write(self, metrics: dict, records: list[ScoredRecord]) -> Path:
        out_dir = Path(self._config.output_dir) / self._config.prompt_name
        out_dir.mkdir(parents=True, exist_ok=True)
        base = self.base_name()
        (out_dir / f"{base}.metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        (out_dir / f"{base}.predictions.json").write_text(
            json.dumps([r.prediction_json() for r in records], indent=2, default=str), encoding="utf-8")
        if not self._config.no_csv:
            csv_path = out_dir / f"{base}.per_record.csv"
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(ScoredRecord.CSV_HEADER)
                writer.writerows(r.csv_row() for r in records)
            print(f"Saved → {csv_path}")
        return out_dir / f"{base}.metrics.json"


class ExperimentRunner:
    def __init__(self, config: RunConfig, settings: Settings, provider: Provider, client: LLMClient):
        self.config = config
        self.provider = provider
        self.client = client
        self.datasets = DatasetRepository(settings)
        self.prompts = PromptBuilder(settings, self.datasets)
        self.metrics = MetricsCalculator()

    def _score(self, i: int, total: int, rec: dict) -> tuple[ScoredRecord, str]:
        c = self.config
        system, user = self.prompts.render(rec["language"], c.prompt_name, rec, rag_mode=c.rag_mode, rag_k=c.rag_k)
        logging.info(f"[{i}/{total}] Processing {rec['sample_id']} ({rec['language']}/{rec['class_name']}) — "
                     f"system_bytes={len(system)} user_bytes={len(user)}")
        if c.verbose:
            logging.info(f"SYSTEM PROMPT:\n{system}\n\nUSER PROMPT:\n{user}")
        try:
            response, usage = self.client.chat(c.model, system, user, temperature=c.temperature, seed=c.seed,
                                               num_ctx=c.num_ctx, num_predict=c.num_predict)
        except Exception as e:
            print(f"  [{i}/{total}] {rec['sample_id']}: REQUEST FAILED: {e}")
            response, usage = "", Usage()
        scored = ScoredRecord(rec, response, usage)
        if c.verbose:
            logging.info(f"LLM RESPONSE ({len(response)} chars):\n{response}")
            logging.info(f"PARSED FINDINGS: {scored.total_findings if scored.parsed else 'PARSE_ERROR'}  "
                         f"invalid={scored.invalid_findings}  truncated={scored.truncated}")
        line = (f"  [{i}/{total}] {rec['sample_id']:35s} {scored.status()}"
                f" tok={usage.input_tokens}→{usage.output_tokens}")
        return scored, line

    def _score_all(self, records: list[dict]) -> list[ScoredRecord]:
        total = len(records)
        workers = max(1, self.config.workers)
        if workers <= 1:
            results = []
            for i, rec in enumerate(records, 1):
                results.append(self._score(i, total, rec))
                print(results[-1][1])
            return [r for r, _ in results]
        n_workers = min(workers, total)
        print(f"Processing {total} records with {n_workers} worker threads...")
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            results = [f.result() for f in [ex.submit(self._score, i, total, rec) for i, rec in enumerate(records, 1)]]
        for _, line in results:
            print(line)
        return [r for r, _ in results]

    def _meta(self, elapsed: float) -> dict:
        c = self.config
        return {
            "prompt": c.prompt_name, "model": c.model, "provider": self.provider.name,
            "host": self.provider.host_label, "is_cloud": self.provider.is_cloud, "is_bedrock": self.provider.is_bedrock,
            "dataset": c.dataset, "split": c.split, "language": c.language or "all", "limit": c.limit,
            "temperature": c.temperature, "seed": c.seed, "num_ctx": c.num_ctx, "num_predict": c.num_predict,
            "workers": c.workers, "bootstrap": c.bootstrap,
            "rag_mode": c.rag_mode if c.is_rag else None, "rag_k": c.rag_k if c.is_rag else None,
            "elapsed_sec": round(elapsed, 1), "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def _token_usage(records: list[ScoredRecord]) -> dict:
        ins = [r.usage.input_tokens for r in records]
        outs = [r.usage.output_tokens for r in records]
        n = max(len(records), 1)
        return {
            "total_input_tokens": sum(ins), "total_output_tokens": sum(outs), "total_tokens": sum(ins) + sum(outs),
            "avg_input_tokens": round(sum(ins) / n, 1), "avg_output_tokens": round(sum(outs) / n, 1),
            "max_input_tokens": max(ins, default=0), "max_output_tokens": max(outs, default=0),
        }

    def run(self) -> int:
        c = self.config
        print(f"Provider: {self.provider.name}  (host={self.provider.host_label})")
        print(self.client.health_check())
        print(f"Model: {c.model}")
        print(f"Prompt: {c.prompt_name}  num_ctx={c.num_ctx}  num_predict={c.num_predict}")
        print(f"Dataset: {c.dataset}/{c.split}.json")
        records = self.datasets.load(c.language, dataset=c.dataset, split=c.split)
        if c.limit:
            records = records[: c.limit]
        if not records:
            print("No test records found.")
            return 1
        print(f"Records: {len(records)}\n")

        t0 = time.time()
        scored = self._score_all(records)
        elapsed = time.time() - t0
        metrics = self.metrics.evaluate(scored)
        if c.bootstrap > 0:
            metrics["bootstrap_ci"] = self.metrics.bootstrap_ci(scored, n_resamples=c.bootstrap, alpha=0.05, seed=c.seed)
        metrics["meta"] = self._meta(elapsed)
        metrics["token_usage"] = self._token_usage(scored)
        SummaryPrinter().print(metrics, verbose=c.verbose)
        print(f"\nSaved → {ResultWriter(c).write(metrics, scored)}")
        return 0


def run(prompt_name: str) -> int:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    settings = Settings.from_env()
    config = RunConfig.from_cli(prompt_name, settings)
    provider = Provider.resolve(config.provider, settings)
    if provider.name == "cloud" and config.provider == "cloud" and not settings.ollama_api_key:
        print("WARNING: --provider=cloud but OLLAMA_API_KEY is not set.")
    config.model = config.model or provider.default_model
    if config.num_ctx is None:
        config.num_ctx = 16384 if prompt_name in LONG_CONTEXT_PROMPTS else 8192
    return ExperimentRunner(config, settings, provider, create_client(provider, settings)).run()
