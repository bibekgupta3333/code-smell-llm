# Prompts — Code-Smell Detection (research-grade)

20 prompt files for the **prompt × model × language** experimental matrix
(RQ1–RQ4). Output schema matches the columns of
[`prepared_data/datasets/*/occurrences/*.csv`](../prepared_data/datasets/README.md)
so grading is a direct join.

## Layout

```
prompts/
├── _system.md             # shared system role (Fowler 2018, evidence-first, abstention)
├── _taxonomy.md           # 23 canonical smells with detection rules + alias table
├── _output_schema.md      # strict JSON schema, naming conventions, line-range rules
├── _generate.py           # regenerator (run after editing templates)
├── _verify.py             # structural validator
├── README.md
├── java/        # 5 prompts
├── python/      # 5 prompts
├── javascript/  # 5 prompts
└── cpp/         # 5 prompts
```

Each generated prompt file is split with two delimiters that the runner
parses:

```
<!-- SYSTEM -->     ← becomes the `system` role
... taxonomy + schema + role + per-language guidance ...
<!-- USER -->       ← becomes the `user` role
... task + input file ...
```

This split is essential: it works identically across OpenAI, Anthropic,
local llama.cpp, and vLLM chat templates without re-engineering.

## Placeholders

| Placeholder | Filled by | When |
|---|---|---|
| `{SYSTEM_BLOCK}` | runner — text of `_system.md` | once per request |
| `{TAXONOMY}` | runner — text of `_taxonomy.md` | once per request |
| `{OUTPUT_SCHEMA}` | runner — text of `_output_schema.md` | once per request |
| `{FILE_PATH}`, `{CLASS_NAME}`, `{SOURCE_CODE}` | per record from `prepared_data/datasets/unannotated/*.json` | every request |
| `{FEW_SHOT_EXAMPLES}` | retriever (P2 only) — 2–3 worked examples from `train.json` (incl. one negative) | every P2 request |
| `{RETRIEVED_SNIPPETS}` | retriever (P5 only) — top-k similar snippets + their canonical findings | every P5 request |

The runner is responsible for prefixing every line of `{SOURCE_CODE}` with
`%4d| ` (4-space-padded, 1-indexed) so the model can cite line numbers
exactly.

## The 5 strategies

| ID | Strategy | Core mechanism | Token cost | Novel? |
|---|---|---|---|---|
| **P1** | Zero-shot | Taxonomy + schema + role only | low | baseline |
| **P2** | Few-shot | P1 + 2–3 worked examples (incl. **one negative**) | medium | baseline |
| **P3** | Taxonomy-Guided Decision Tree | 23-step ordered procedure with anchored thresholds (Sharma & Spinellis 2018, DesigniteJava) | high | ★ |
| **P4** | Self-Verification (Critique-Refine) | Two-pass with `<analysis>` / `<answer>` sentinel tags; runner discards `<analysis>` | very high | ★ |
| **P5** | Retrieval-Augmented (RAG) | P1 + retrieved exemplars with explicit anti-leakage rules | medium-high | baseline |

Both novel strategies were chosen for *2026-publishability*: plain CoT and
plain few-shot are no longer interesting, but **taxonomy-anchored decision
procedures** (P3) and **structured self-verification with parseable
scratchpads** (P4) are open research questions for multi-label code
analysis.

## Calibration & abstention (research-critical)

Every prompt enforces three pieces of discipline that distinguish this set
from typical LLM-as-judge work:

1. **Evidence-first.** Each finding must cite specific lines that
   demonstrate the smell. The schema rejects evidence that is reasoning
   ("this looks complex") rather than observation ("35-LOC body, 4
   `println` blocks at lines 63–97").
2. **Precision over recall.** When uncertain, models are told to **omit**.
   `findings: []` is a valid, expected answer.
3. **Bounded output.** Cap of 50 findings per file prevents runaway on
   small/under-trained models.

These rules are stated in `_system.md` and enforced by the schema in
`_output_schema.md`.

## Per-language adaptations

`_generate.py` injects a **Language-specific guidance** section into every
prompt covering issues unique to that language:

- **Python** — dunder methods, decorators, module-level `def`.
- **JavaScript** — arrow functions, prototype methods, anonymous callbacks.
- **C++** — `.h` / `.cpp` split, `friend` declarations, templates.
- **Java** — inner/nested classes, generated `equals`/`hashCode`/`toString`.

This avoids a common reviewer complaint: "your prompt assumes Java."

## Experimental matrix

| Axis | Levels |
|---|---|
| Prompt | P1, P2, P3, P4, P5 |
| Model tier | low (~3 B), medium (~14 B), high (32 B / reasoning-tuned) |
| Language | java, python, javascript, cpp |
| **Total** | **5 × 3 × 4 = 60 conditions** |

Run each condition on `prepared_data/datasets/unannotated/test.json`. Grade
the JSON output against:

- the line-level annotations in `prepared_data/datasets/annotated/test.json`
  (where they exist), or
- the method-level `ground_truth` in the unannotated record.

Reported metrics (per RQ):

- **RQ1** — overall P/R/F1 vs static baselines (PMD, SonarQube, DesigniteJava).
- **RQ2** — Δ F1 of P5 over P1 with the same model.
- **RQ3** — per-smell × per-language breakdown (which strategy helps which smell).
- **RQ4** — token-cost / latency × F1 Pareto frontier.

## Regenerating

After editing any of `_system.md`, `_taxonomy.md`, `_output_schema.md`, or
`_generate.py`:

```bash
python3 prompts/_generate.py    # writes the 20 per-language files
python3 prompts/_verify.py      # structural check; non-zero exit on any failure
```

CI should fail if `_verify.py` exits non-zero.

## What is *not* in these files (by design)

- **No model-specific tweaks** (no "Claude:" / "GPT-4:" headers). Tiering is
  the runner's responsibility.
- **No temperature / sampling parameters**. Set those in the runner; record
  them in the result file metadata.
- **No prompt-injection defences beyond format discipline**. Inputs are
  trusted research code; threat model is benign.
