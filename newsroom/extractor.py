"""
=========================================================
Newspaper Extractor
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais

Extrai o texto do PDF em Python (segundos, sem IA):

  1. copia o PDF para um nome simples (o pdftotext não
     abre caminhos com acentos no Windows);
  2. extrai página a página;
  3. identifica o código da página (A2, B7...) e a seção;
  4. descarta páginas sem conteúdo editorial (anúncios,
     balanços, editais, classificados, fonte corrompida);
  5. limpa o texto (hifenização, marcas, linhas soltas).

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from newsroom.pdf_tools import find_pdftotext


CODE = re.compile(r"(?<![\w/])([A-H])\s?(\d{1,2})(?![\w/,.%])")

NOISE_LINES = re.compile(r"^(ines\s?2\s?o?4\s?p?9|ines249|\|+|[\d\s.,/|-]+)$", re.I)

LEGAL_MARKERS = (
    "demonstrações financeiras", "demonstração do resultado", "balanço patrimonial",
    "notas explicativas", "edital de", "editais", "ata da assembleia", "cnpj",
    "classificados", "publicidade legal", "fluxo de caixa", "convocação",
)

SKIP_SECTIONS = ("classificados", "publicidade legal", "editais", "falecimentos")


@dataclass
class Page:

    number: int

    code: str

    section: str

    text: str

    @property
    def words(self) -> int:

        return len(self.text.split())


class NewspaperExtractor:

    # -------------------------------------------------

    def __init__(self, pdftotext: str = None, min_words: int = 120):

        self.pdftotext = find_pdftotext(pdftotext)

        if self.pdftotext is None:

            raise FileNotFoundError("pdftotext não encontrado (instale o Git for Windows).")

        self.min_words = min_words

    # -------------------------------------------------

    def extract(self, pdf: Path) -> list[Page]:

        raw_pages = self._pdftotext(Path(pdf))

        readable = [

            (number, raw, *self._header(raw))

            for number, raw in enumerate(raw_pages, start=1)

            if self._readable(raw)

        ]

        codes = self._fill_codes([code for _, _, code, _ in readable])

        pages = []

        for (number, raw, _, section), code in zip(readable, codes):

            if number == 1:

                code, section = code or "A1", section if code else "Capa"

            page = Page(number=number, code=code, section=section, text=self._clean(raw))

            if self._editorial(page):

                pages.append(page)

        return pages

    # -------------------------------------------------

    @staticmethod
    def _fill_codes(codes: list[str]) -> list[str]:

        """
        Páginas sem código no cabeçalho: se as vizinhas são do mesmo
        caderno, segue a anterior (+1); se a próxima abre outro caderno,
        usa a próxima (-1). Ex.: B10, ?, C2 -> o ? vira C1.
        """

        parsed = [re.fullmatch(r"([A-H])(\d{1,2})", c or "") for c in codes]

        result = list(codes)

        for i, code in enumerate(codes):

            if code:

                continue

            prev = next((parsed[j] for j in range(i - 1, -1, -1) if parsed[j]), None)

            nxt = next((parsed[j] for j in range(i + 1, len(codes)) if parsed[j]), None)

            if prev and (not nxt or nxt.group(1) == prev.group(1)):

                result[i] = f"{prev.group(1)}{int(prev.group(2)) + 1}"

            elif nxt and int(nxt.group(2)) > 1:

                result[i] = f"{nxt.group(1)}{int(nxt.group(2)) - 1}"

            elif prev:

                result[i] = f"{prev.group(1)}{int(prev.group(2)) + 1}"

        return result

    # -------------------------------------------------

    def to_prompt_text(self, pages: list[Page]) -> str:

        """Texto do jornal com marcadores de página para a IA citar a fonte."""

        blocks = []

        for page in pages:

            label = " · ".join(x for x in (page.code, page.section) if x) or f"p.{page.number}"

            blocks.append(f"=== [{label}] ===\n{page.text}")

        return "\n\n".join(blocks)

    # -------------------------------------------------

    def _pdftotext(self, pdf: Path) -> list[str]:

        with tempfile.TemporaryDirectory() as tmp:

            # Nome sem acentos: o pdftotext do Git não abre caminhos Unicode.
            source = Path(tmp) / "jornal.pdf"

            shutil.copyfile(pdf, source)

            result = subprocess.run(

                [str(self.pdftotext), "-enc", "UTF-8", str(source), "-"],

                capture_output=True

            )

        if result.returncode != 0:

            raise RuntimeError(
                "pdftotext falhou: " + result.stderr.decode("utf-8", "ignore").strip()
            )

        return result.stdout.decode("utf-8", "ignore").split("\f")

    # -------------------------------------------------

    @staticmethod
    def _readable(raw: str) -> bool:

        """Descarta páginas vazias ou com fonte corrompida (caracteres de controle)."""

        if len(raw.strip()) < 200:

            return False

        control = sum(1 for c in raw if ord(c) < 32 and c not in "\n\r\t\f")

        visible = [c for c in raw if not c.isspace()]

        letters = sum(1 for c in visible if c.isalpha())

        return control / len(raw) < 0.02 and letters / max(len(visible), 1) > 0.45

    # -------------------------------------------------

    @staticmethod
    def _header(raw: str) -> tuple[str, str]:

        lines = [l.strip() for l in raw.splitlines() if l.strip()][:8]

        code = ""

        for line in lines:

            if len(line) > 120:

                continue

            match = CODE.search(line)

            if match and (

                "valor" in line.lower()
                or "estado" in line.lower()
                or "de 20" in line.lower()
                or line.isupper()
                or len(line) <= 12

            ):

                code = f"{match.group(1)}{match.group(2)}"

                break

        section = ""

        for line in lines:

            plain = CODE.sub("", line).strip(" |")

            low = plain.lower()

            if (

                2 < len(plain) <= 40
                and not any(k in low for k in ("ines", "valor", "estado de s", "-feira", "outubro", "de 20", "publicado", "@", ".com"))
                and not re.search(r"[\d/]", plain)
                and low not in ("por", "foto", "fotos")
                and len(plain.split()) <= 5

            ):

                section = plain.title() if plain.isupper() else plain

                break

        return code, section

    # -------------------------------------------------

    @staticmethod
    def _clean(raw: str) -> str:

        text = raw.replace("\r", "")

        # Junta palavras hifenizadas na quebra de linha.
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        lines = []

        for line in text.splitlines():

            line = re.sub(r"Ines\s?2?\s?O?4?p?9", "", line).strip()

            if not line or NOISE_LINES.match(line) or len(line) <= 2:

                continue

            # Linhas de editais e balanços misturadas às matérias.
            if any(m in line.lower() for m in LEGAL_MARKERS):

                continue

            if len(line) > 25 and sum(c.isdigit() for c in line) / len(line) > 0.6:

                continue

            lines.append(line)

        text = "\n".join(lines)

        return re.sub(r"[ \t]{2,}", " ", text)

    # -------------------------------------------------

    def _editorial(self, page: Page) -> bool:

        if page.words < self.min_words:

            return False

        if any(s in page.section.lower() for s in SKIP_SECTIONS):

            return False

        # Páginas inteiras de balanços e tabelas: o texto que sobra é quase só número.
        digits = sum(c.isdigit() for c in page.text) / max(len(page.text), 1)

        return digits <= 0.25
