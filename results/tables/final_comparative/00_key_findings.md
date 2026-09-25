
# Key Findings (auto-generated)

## Headline result
- **Best system:** *Mistral Devstral 2 123B* with **P5 RAG random (k=2)** → micro F1 = **0.961**
  (pooled across Java, Python, JavaScript, C++).
- Per-model best prompts: **DeepSeek v3.2** → P2 few-shot; **Gemma 3 27B-IT** → P2 few-shot; **Mistral Devstral 2 123B** → P5 RAG random (k=2); **Qwen3 Coder 30B A3B** → P5 RAG dense (k=3); **GPT-OSS 120B** → P5 RAG dense (k=3); **Gemma 3 4B-IT** → P1 zero-shot; **Mistral Voxtral Mini 3B** → P1 zero-shot; **Nemotron Nano 3-30B** → P2 few-shot; **Nemotron Nano 9B v2** → P2 few-shot.

## RQ1 — Does few-shot beat zero-shot?
- Mean lift of P2 few-shot over P1 across 9 models: **+0.090** F1.
- Few-shot improves all models: mixed.

## RQ2 — Does structured / self-correction reasoning help?
- P3 taxonomy-tree mean lift: **-0.070** F1.
- P4 self-verify mean lift:    **-0.166** F1.
- Take-away: structured reasoning tends to hurt;
  self-verify is inconsistent across models.

## RQ3 — Does RAG content matter?
- Dense (k=3) − random (k=2) per model (random arm run for all nine models):
  - DeepSeek v3.2: -0.002
  - Gemma 3 27B-IT: +0.008
  - Mistral Devstral 2 123B: -0.004
  - Qwen3 Coder 30B A3B: +0.046
  - GPT-OSS 120B: +0.005
  - Gemma 3 4B-IT: -0.077
  - Mistral Voxtral Mini 3B: +0.000
  - Nemotron Nano 3-30B: -0.004
  - Nemotron Nano 9B v2: -0.026
- Models that benefit from real retrieval: **Qwen3 Coder 30B A3B**.
- Models where dense ≈ random: **DeepSeek v3.2, Gemma 3 27B-IT, Mistral Devstral 2 123B, GPT-OSS 120B, Mistral Voxtral Mini 3B, Nemotron Nano 3-30B** → suggests the smell taxonomy
  in the system prompt already supplies most of the signal these models can exploit; retrieval mainly
  acts as a "prompt expander".

## Per-smell — easiest vs hardest
- **Easiest (highest mean F1, support ≥10):** Inappropriate Intimacy (0.92), Duplicate Code (0.90), Long Method (0.88), Shotgun Surgery (0.88), Switch Statements (0.88)
- **Hardest (lowest mean F1, support ≥10):**  Parallel Inheritance Hierarchies (0.77), Middle Man (0.78), Divergent Change (0.78), Refused Bequest (0.79), Temporary Field (0.81)

## Language difficulty
- python: mean F1 = 0.743
- javascript: mean F1 = 0.719
- java: mean F1 = 0.680
- cpp: mean F1 = 0.604

## Cost / latency
- Best F1-per-second is achieved at *('Mistral Devstral 2 123B', 'p5_rag_random')* (F1=0.961,
  total elapsed 371 s across 4 langs).

## Recommended setup for production
- **Quality-first:** *Mistral Devstral 2 123B + P5 RAG random (k=2)*.
- **Latency-first:** the model with highest F1 in P1 zero-shot — `Qwen3 Coder 30B A3B`
  (F1 = 0.854); skips few-shot/RAG context overhead.
- **Open question for future work:** the long tail of low-support smells (Lazy Class, Comments,
  Data Class, Feature Envy) is unstable across runs — collect more annotations before drawing
  conclusions on those classes.
