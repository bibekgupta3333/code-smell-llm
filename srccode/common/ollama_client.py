from __future__ import annotations

from typing import Optional

from .llm_client import LLMClient, Usage


class OllamaClient(LLMClient):
    name = "ollama"

    def __init__(self, host: str, api_key: str = "", *, cloud: bool = False):
        self._host = host
        self._api_key = api_key
        self._cloud = cloud

    def _client(self):
        import ollama
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        return ollama.Client(host=self._host, headers=headers)

    @staticmethod
    def _count(resp, key: str) -> int:
        value = getattr(resp, key, 0) or (resp.get(key, 0) if hasattr(resp, "get") else 0)
        return int(value or 0)

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
        options = {"temperature": temperature, "seed": seed}
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        if num_predict is not None:
            options["num_predict"] = num_predict
        resp = self._client().chat(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            options=options,
        )
        return resp["message"]["content"], Usage.of(self._count(resp, "prompt_eval_count"), self._count(resp, "eval_count"))

    @property
    def _label(self) -> str:
        return f"{self._host}{' (cloud)' if self._cloud else ' (local)'}"

    def health_check(self) -> str:
        try:
            self._client().list()
        except Exception as e:
            raise RuntimeError(f"Cannot reach Ollama at {self._label}: {e}") from e
        return f"OK: {self._label}"
