from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Optional

from .config import Settings


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def of(cls, input_tokens: int, output_tokens: int, total_tokens: int | None = None) -> "Usage":
        return cls(input_tokens, output_tokens, input_tokens + output_tokens if total_tokens is None else total_tokens)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Provider:
    name: str
    ollama_host: str
    settings: Settings

    LOCAL_HOST = "http://localhost:11434"
    CLOUD_HOST = "https://ollama.com"

    @classmethod
    def resolve(cls, requested: str, settings: Settings) -> "Provider":
        host = settings.ollama_host
        if requested == "local":
            return cls("local", cls.LOCAL_HOST, settings)
        if requested == "cloud":
            return cls("cloud", cls.CLOUD_HOST, settings)
        if requested == "bedrock":
            return cls("bedrock", host, settings)
        return cls("cloud" if "ollama.com" in host else "local", host, settings)

    @property
    def is_bedrock(self) -> bool:
        return self.name == "bedrock"

    @property
    def is_cloud(self) -> bool:
        return self.name == "cloud" or "ollama.com" in self.ollama_host

    @property
    def host_label(self) -> str:
        if self.is_bedrock:
            return f"AWS Bedrock {self.settings.aws_region or 'cli-default'}"
        return self.ollama_host

    @property
    def default_model(self) -> str:
        if self.is_bedrock:
            return self.settings.default_model_bedrock
        return self.settings.default_model_cloud if self.is_cloud else self.settings.default_model_local


class LLMClient(ABC):
    name: str = ""

    @abstractmethod
    def chat(
        self,
        model: str,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        seed: int = 42,
        num_ctx: Optional[int] = 8192,
        num_predict: Optional[int] = 4096,
    ) -> tuple[str, Usage]:
        ...

    @abstractmethod
    def health_check(self) -> str:
        ...


def create_client(provider: Provider, settings: Settings) -> LLMClient:
    if provider.is_bedrock:
        from .bedrock_client import BedrockClient
        return BedrockClient(settings)
    from .ollama_client import OllamaClient
    return OllamaClient(provider.ollama_host, settings.ollama_api_key, cloud=provider.is_cloud)
