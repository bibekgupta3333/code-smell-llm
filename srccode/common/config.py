from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    root: Path = ROOT

    @property
    def raw_dataset(self) -> Path:
        return self.root / "data" / "datasets" / "SmellyCodeDataset"

    @property
    def prepared(self) -> Path:
        return self.root / "prepared_data" / "datasets"

    @property
    def train_annotated(self) -> Path:
        return self.prepared / "annotated" / "train.json"

    @property
    def prompts(self) -> Path:
        return self.root / "prompts"

    @property
    def system_block(self) -> Path:
        return self.prompts / "_system.md"

    @property
    def taxonomy_block(self) -> Path:
        return self.prompts / "_taxonomy.md"

    @property
    def schema_block(self) -> Path:
        return self.prompts / "_output_schema.md"

    @property
    def results(self) -> Path:
        return self.root / "results" / "llm_runs"

    @property
    def embedding_cache(self) -> Path:
        return self.root / "cache" / "embeddings"


@dataclass(frozen=True)
class Settings:
    paths: Paths = field(default_factory=Paths)
    ollama_host: str = "http://localhost:11434"
    ollama_api_key: str = ""
    aws_region: str = "ap-southeast-2"
    bedrock_profile: str | None = None
    bedrock_api_key: str = ""
    default_model_local: str = "qwen3:0.6b"
    default_model_cloud: str = "deepseek-v4-flash:cloud"
    default_model_bedrock: str = "mistral.devstral-2-123b"
    strip_label_comments: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        api_key = os.environ.get("BEDROCK_API_KEY") or os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
        if api_key and not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key
        return cls(
            ollama_host=os.environ.get("OLLAMA_HOST", cls.ollama_host),
            ollama_api_key=os.environ.get("OLLAMA_API_KEY", ""),
            aws_region=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or cls.aws_region,
            bedrock_profile=os.environ.get("AWS_PROFILE"),
            bedrock_api_key=api_key,
            default_model_bedrock=os.environ.get("BEDROCK_MODEL_ID", cls.default_model_bedrock),
        )
