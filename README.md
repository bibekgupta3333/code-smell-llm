# An Empirical Evaluation of LLM Prompting Strategies for Multi-Language Code Smell Detection

Replication artifact for the anonymous submission of the same title. It contains the prompt
templates, experiment runners, the harmonized benchmark, every raw model
response and per-record score, and the analysis notebook that regenerates all
tables and figures reported in the paper.

## Study at a glance

- **Benchmark:** Smelly Code Dataset (Zenodo, doi:10.5281/zenodo.14989674),
  harmonized into one JSON schema: 34 files, 473 line-level labels, 21 of 23
  Fowler smells, Java / Python / JavaScript / C++. Language-stratified split
  20 / 6 / 8 train / val / test (seed 42).
- **Models:** nine instruction-tuned LLMs served through AWS Bedrock
  (region ap-southeast-2), greedy decoding (temperature 0, top_p 1, seed 42).
- **Prompting strategies:** P1 zero-shot, P2 few-shot, P3 taxonomy-guided
  reasoning, P4 self-verification, P5 dense RAG (k=3), plus a random-retrieval
  control (k=2). 54 configurations, 216 (model, prompt, language) cells,
  1,836 scored responses.
- **Statistics:** paired bootstrap on per-record outcomes (1,000 resamples,
  seed 42) with Holm–Bonferroni correction within each test family, and a
  held-out-only (val+test) re-test of the RAG contrast.

| Bedrock model ID | Results folder |
|---|---|
| `deepseek.v3.2` | `results/llm_runs/deepseekv3_2` |
| `mistral.devstral-2-123b` | `results/llm_runs/mistral_devstral_2_123b` |
| `openai.gpt-oss-120b-1:0` | `results/llm_runs/openai.gpt-oss-120b-1` |
| `google.gemma-3-27b-it` | `results/llm_runs/gemma_3_27b_it` |
| `qwen.qwen3-coder-30b-a3b-v1:0` | `results/llm_runs/qwen.qwen3-coder-30b-a3b-v1` |
| `nvidia.nemotron-nano-3-30b` | `results/llm_runs/nvidia.nemotron-nano-3-30b` |
| `google.gemma-3-4b-it` | `results/llm_runs/google.gemma-3-4b-it` |
| `mistral.voxtral-mini-3b-2507` | `results/llm_runs/mistral.voxtral-mini-3b-2507` |
| `nvidia.nemotron-nano-9b-v2` | `results/llm_runs/nvidia.nemotron-nano-9b-v2` |

Output cap (`--num-predict`) was 8,000 tokens, except 4,096 for the DeepSeek,
Gemma 3 27B, and Devstral runs. Each run's exact settings are recorded in the
`meta` block of its `*.metrics.json` and summarized in
`results/tables/final_comparative/12_run_config_audit.csv`.

## Repository layout

```
prompts/                     Prompt templates: _system.md, _taxonomy.md,
                             _output_schema.md, and <language>/p1..p5 .md
srccode/                     Runners (one per strategy) and shared code
  common/                    runner, prompt loader, Bedrock/Ollama clients,
                             dataset loader, evaluator, RAG index
prepared_data/
  build_dataset.py           Harmonizes the raw dataset into prepared_data/datasets
  datasets/annotated/        Line-level labels and train/val/test splits (used)
  datasets/unannotated/      Class-level variant (runner default; not used in the paper)
results/
  llm_runs/<model>/<prompt>/ One run per (model, prompt, language[, RAG arm]):
                             *.metrics.json, *.per_record.csv, *.predictions.json
  tables/final_comparative/  CSVs behind every table in the paper
  figures/final_comparative/ Figures used in the paper
  _archive/superseded_k2_pilot/ An earlier run of Nemotron 9B v2's random arm,
                             used only for the repeat-run noise estimate
notebook/
  final_comparative_analysis.ipynb   Regenerates all tables and figures
requirements.txt, package.json
```

## Reproduce the tables and figures (no API access needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute \
  notebook/final_comparative_analysis.ipynb --output-dir /tmp
```

The notebook reads `results/llm_runs/` and rewrites
`results/tables/final_comparative/` (files `01_`–`13_`) and
`results/figures/final_comparative/`. Key files:

| File | Paper element |
|---|---|
| `01_headline_micro_macro.csv` | Table III (micro and macro F1) |
| `06_paired_bootstrap_within_model.csv`, `09_holm_bonferroni.csv` | Table V, correction tiers for all three families |
| `07_paired_bootstrap_cross_model.csv` | Table VI |
| `08_paired_bootstrap_rag.csv`, `10_rag_ablation_heldout.csv` | Table IV (all files and held-out) |
| `11_p4_failure_breakdown.csv` | RQ2 failure analysis |
| `13_repeat_run_noise.csv` | Run-to-run noise estimate |

## Re-run the experiments (requires AWS Bedrock access)

Create a `.env` in the repository root with `AWS_REGION`, and either
`AWS_PROFILE` or `BEDROCK_API_KEY`. Then:

```bash
python -m srccode.build_rag_index          # once, builds the dense index from train.json

python -m srccode.run_p5_rag --provider bedrock \
  --model mistral.devstral-2-123b --output-dir results/llm_runs/mistral_devstral_2_123b \
  --dataset annotated --split python --rag-mode dense --rag-k 3
```

All five runners (`run_p1_zero_shot`, `run_p2_few_shot`, `run_p3_taxonomy_tree`,
`run_p4_self_verify`, `run_p5_rag`) share the same flags. Use
`--split {java,python,javascript,cpp}` and `--dataset annotated` to match the
paper; the random-retrieval control is `--rag-mode random --rag-k 2`. Set
`PYTHONHASHSEED=0` for a reproducible random-arm exemplar draw. Shortcuts for
every (prompt, language) pair are in `package.json` (`npm run p2:bedrock:py`, ...).

Rebuilding `prepared_data/datasets/` from scratch requires the upstream
dataset at `data/datasets/SmellyCodeDataset/` (download from the Zenodo DOI
above), then `python prepared_data/build_dataset.py`.

## License

Code: MIT. Dataset: see the upstream Smelly Code Dataset license.
