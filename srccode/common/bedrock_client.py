from __future__ import annotations

import threading
from typing import Optional

from .config import Settings
from .llm_client import LLMClient, Usage


class BedrockClient(LLMClient):
    name = "bedrock"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = self._build()
        return self._client

    def _build(self):
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError("boto3 is required for --provider=bedrock. Install with: pip install boto3") from e
        kwargs = {"region_name": self._settings.aws_region} if self._settings.aws_region else {}
        if self._settings.bedrock_profile:
            return boto3.Session(profile_name=self._settings.bedrock_profile).client("bedrock-runtime", **kwargs)
        return boto3.client("bedrock-runtime", **kwargs)

    def chat(
        self,
        model: str,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        seed: int = 42,
        num_ctx: Optional[int] = None,
        num_predict: Optional[int] = 4096,
    ) -> tuple[str, Usage]:
        inference_config = {"temperature": float(temperature)}
        if num_predict is not None:
            inference_config["maxTokens"] = int(num_predict)
        resp = self.client.converse(
            modelId=model,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig=inference_config,
        )
        parts = resp.get("output", {}).get("message", {}).get("content", []) or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        raw = resp.get("usage", {}) or {}
        in_tok = int(raw.get("inputTokens", 0) or 0)
        out_tok = int(raw.get("outputTokens", 0) or 0)
        return text, Usage.of(in_tok, out_tok, int(raw.get("totalTokens", in_tok + out_tok) or 0))

    def health_check(self) -> str:
        try:
            client = self.client
        except Exception as e:
            raise RuntimeError(f"Cannot initialise AWS Bedrock client: {e}") from e
        profile = f"  profile={self._settings.bedrock_profile}" if self._settings.bedrock_profile else ""
        region = client.meta.region_name or "<unset>"
        if self._settings.bedrock_api_key:
            auth = "  auth=api-key"
        elif self._settings.bedrock_profile:
            auth = ""
        else:
            auth = "  auth=aws-cli-chain"
        return f"OK: AWS Bedrock  region={region}{profile}{auth}"
