# `srccode/`: experiment runners

Part of the replication package for *An Empirical Evaluation of LLM Prompting Strategies for Multi-Language Code Smell Detection* (anonymous submission).

One thin entry point per prompting strategy; all share `common/runner.py`.

```
run_p1_zero_shot.py      P1 zero-shot
run_p2_few_shot.py       P2 few-shot (2 smelly + 1 clean train file, seed 42)
run_p3_taxonomy_tree.py  P3 taxonomy-guided reasoning (ordered 23-check procedure)
run_p4_self_verify.py    P4 self-verification (<analysis>/<answer> protocol)
run_p5_rag.py            P5 retrieval-augmented: --rag-mode dense|random, --rag-k N
build_rag_index.py       Builds the dense index over prepared_data/datasets/annotated/train.json
common/
  config.py         Settings (env-derived) and Paths
  taxonomy.py       The 23 smells and their Fowler categories (shared with prepared_data/build_dataset.py)
  llm_client.py     LLMClient (abstract), Usage, Provider resolution, create_client factory
  bedrock_client.py BedrockClient: AWS Bedrock converse API (used for all paper runs)
  ollama_client.py  OllamaClient: optional local / Ollama Cloud provider
  dataset.py        DatasetRepository: dataset splits, train pool, gold keys
  rag_index.py      Retriever (abstract), EmbeddingIndex (dense, all-MiniLM-L6-v2, cosine,
                    same-language, sample_id self-exclusion), RandomRetriever (control)
  prompt_loader.py  PromptBuilder and ExemplarFormatter: renders prompts/<language>/<prompt>.md
  evaluator.py      SmellVocabulary, ResponseParser, ScoredRecord, MetricsCalculator
                    (span/key matching, micro/macro/weighted P/R/F1, bootstrap CIs)
  runner.py         RunConfig (CLI), ExperimentRunner, ResultWriter, SummaryPrinter
```

Paper runs used `--provider bedrock --dataset annotated --split <language>`.
Each run writes `<prompt>__<model>__<dataset>__<language>__all[__<rag_mode>_k<k>]__<timestamp>`
`.metrics.json`, `.per_record.csv`, and `.predictions.json` under `--output-dir`.
Unparseable responses are scored as empty predictions and counted in
`parse_errors`.
