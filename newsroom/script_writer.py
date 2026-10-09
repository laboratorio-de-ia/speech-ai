"""
=========================================================
Script Writer
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais

Monta o script.txt (roteiro para áudio) na ordem das
skills, a partir dos parágrafos escritos pela IA, e
valida as regras de escrita para voz em Python:

  título falado · abertura · 1º, 2º e 3º destaques
  (um parágrafo por slide) · o que acompanhar · encerramento

Símbolos que escaparem (%, R$, US$, ×, →...) são
convertidos para a forma falada.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import re

from newsroom.profiles import NewspaperProfile


# Abreviações só em minúsculas: "PP" (partido) não é "pp" (pontos percentuais).
FORBIDDEN = re.compile(r"[%×→•*#$<>]|R\$|US\$|\spp\b|\sbi\b|\smi\b|https?://")

MAGNITUDE = {

    "tri": "trilhões", "trilhão": "trilhões", "trilhao": "trilhões", "trilhões": "trilhões", "trilhoes": "trilhões",
    "bi": "bilhões", "bilhão": "bilhões", "bilhao": "bilhões", "bilhões": "bilhões", "bilhoes": "bilhões",
    "mi": "milhões", "milhão": "milhões", "milhao": "milhões", "milhões": "milhões", "milhoes": "milhões",
    "mil": "mil",

}

SINGULAR = {"trilhões": "trilhão", "bilhões": "bilhão", "milhões": "milhão", "mil": "mil"}

# A IA às vezes escreve a magnitude por extenso ("bilhões", "bilhão") em vez da
# abreviação ("bi"). As duas formas (com ou sem acento) precisam ser reconhecidas,
# senão a palavra por extenso fica sem casar com a regex e sobra solta no texto
# (ex.: "3,2 reaisbilhões").
SCALE = r"(?:tri|trilh(?:[ãa]o|[õo]es)|bi|bilh(?:[ãa]o|[õo]es)|mi|milh(?:[ãa]o|[õo]es)|mil)"


def magnitude(value: str, abbreviation: str) -> str:

    """'1,4' + 'tri' -> 'trilhão' (singular abaixo de 2), '30' + 'bi' -> 'bilhões'."""

    word = MAGNITUDE[abbreviation.lower()]

    try:

        number = float(value.replace(".", "").replace(",", "."))

    except ValueError:

        return word

    return SINGULAR[word] if number < 2 else word


CURRENCY = {"R$": "reais", "US$": "dólares", "€": "euros"}


def speak(text: str) -> str:

    """Converte para a forma falada o que escapou das regras."""

    def money(match):

        currency, value, scale = match.group(1), match.group(2), (match.group(3) or "").lower()

        unit = CURRENCY[currency]

        if scale:

            return f"{value} {magnitude(value, scale)} de {unit}"

        return f"{value} {unit}"

    text = re.sub(rf"(R\$|US\$|€)\s?(\d[\d.,]*)\s?({SCALE})?\b\.?", money, text)

    text = re.sub(rf"(\d[\d.,]*)\s?({SCALE})\b\.?", lambda m: f"{m.group(1)} {magnitude(m.group(1), m.group(2))}", text)

    text = re.sub(r"([+-−]?\d[\d.,]*)\s?%", lambda m: f"{m.group(1)} por cento", text)

    text = re.sub(r"(\d[\d.,]*)\s?pp\b", r"\1 pontos percentuais", text)

    text = re.sub(r"(\d[\d.,]*)\s?pb\b", r"\1 pontos-base", text)

    text = text.replace("×", " contra ").replace("→", " para ")

    text = re.sub(r"[•*#<>]", "", text)

    text = re.sub(r"https?://\S+", "", text)

    text = text.replace("−", "menos ")

    return re.sub(r"[ \t]{2,}", " ", text).strip()


class ScriptWriter:

    # -------------------------------------------------

    def __init__(self, profile: NewspaperProfile):

        self.profile = profile

    # -------------------------------------------------

    def build(self, tiers: list[dict], cover: dict) -> str:

        name = self.profile.spoken_name

        paragraphs = [

            f"Resumo do jornal {name}. Edição de {cover['spoken_date']}.",

            cover["script_opening"],

        ]

        for tier, block in zip(self.profile.tiers, tiers):

            paragraphs.append(tier.spoken)

            paragraphs.extend(slide["script"] for slide in block["slides"] if slide["script"].strip())

        paragraphs.append("O que acompanhar nos próximos dias.")

        paragraphs.append(" ".join(block["watch_sentence"] for block in tiers))

        paragraphs.append(f"Este foi o resumo do {name}. Até a próxima edição.")

        return "\n\n".join(speak(p) for p in paragraphs) + "\n"

    # -------------------------------------------------

    def validate(self, script: str) -> dict:

        words = len(script.split())

        order = [script.find(t.spoken) for t in self.profile.tiers]

        issues = []

        if not 700 <= words <= 1100:

            issues.append(f"{words} palavras (meta: 700 a 1.100)")

        found = sorted(set(m.group(0).strip() for m in FORBIDDEN.finditer(script)))

        if found:

            issues.append("símbolos proibidos: " + ", ".join(found))

        if -1 in order or order != sorted(order):

            issues.append("destaques fora de ordem")

        return {"words": words, "issues": issues}
