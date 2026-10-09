"""
=========================================================
Ollama Client
---------------------------------------------------------
Sprint 13 - IA local (custo zero)

Chamada única à API local do Ollama (/api/generate), com
saída estruturada por JSON Schema, no lugar do Claude Code
CLI. Mesma ideia de antes (uma chamada, sem ferramentas,
JSON validado por schema), mas rodando na GPU da máquina
e sem custo por token.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import json

import requests


class OllamaError(RuntimeError):

    pass


class OllamaClient:

    # -------------------------------------------------

    def __init__(self, host: str, timeout: int, num_ctx: int, keep_alive: str):

        self.host = host.rstrip("/")

        self.timeout = timeout

        self.num_ctx = num_ctx

        self.keep_alive = keep_alive

    # -------------------------------------------------

    def ensure_model(self, model: str) -> None:

        """Falha rápido e com uma mensagem clara se o Ollama ou o modelo não estiverem prontos."""

        try:

            response = requests.get(f"{self.host}/api/tags", timeout=10)

            response.raise_for_status()

        except requests.RequestException as error:

            raise OllamaError(
                f"Não foi possível conectar ao Ollama em {self.host}. "
                f"Verifique se o serviço está rodando (abra o app Ollama ou execute 'ollama serve'). "
                f"Detalhe: {error}"
            ) from error

        names = {m.get("name") for m in response.json().get("models", [])}

        base_names = {n.split(":")[0] for n in names}

        if model not in names and model.split(":")[0] not in base_names:

            raise OllamaError(
                f"Modelo '{model}' não encontrado no Ollama. Baixe antes com: ollama pull {model}"
            )

    # -------------------------------------------------

    def generate(self, model: str, system: str, prompt: str, schema: dict) -> dict:

        payload = {

            "model": model,

            "system": system,

            "prompt": prompt,

            "format": schema,

            "stream": False,

            "keep_alive": self.keep_alive,

            "options": {"num_ctx": self.num_ctx},

        }

        try:

            response = requests.post(
                f"{self.host}/api/generate", json=payload, timeout=self.timeout
            )

            response.raise_for_status()

        except requests.RequestException as error:

            raise OllamaError(f"Falha na chamada ao Ollama ({model}): {error}") from error

        text = response.json().get("response", "")

        try:

            parsed = json.loads(text)

        except ValueError as error:

            raise OllamaError(f"Resposta do modelo não é um JSON válido: {text[:300]!r}") from error

        if not isinstance(parsed, dict):

            raise OllamaError("Resposta do modelo não é um objeto JSON.")

        missing = [key for key in schema.get("required", []) if key not in parsed]

        if missing:

            raise OllamaError(f"Resposta incompleta: faltam os campos {missing}.")

        return parsed
