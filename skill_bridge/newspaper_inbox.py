"""
=========================================================
Newspaper Inbox
---------------------------------------------------------
Sprint 10 - Integração com Skills de Jornais

Varre a pasta de entrada (input/Jornais), identifica o
jornal de cada PDF e arquiva os PDFs já processados.

Identificação:
  1. pelo nome do arquivo (nome da skill, aliases e
     palavras-chave do settings.json);
  2. pelo texto da capa (pdftotext), usando apenas as
     palavras-chave (nomes completos dos jornais).

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

from config.config_manager import ConfigManager

from newsroom.pdf_tools import find_pdftotext
from skill_bridge.skill_catalog import SkillCatalog, SkillDefinition

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:

    text = unicodedata.normalize("NFKD", text)

    text = "".join(c for c in text if not unicodedata.combining(c))

    text = re.sub(r"[_\-]+", " ", text.lower())

    return re.sub(r"\s+", " ", text)


class NewspaperInbox:

    # -------------------------------------------------

    def __init__(self, cfg: ConfigManager, catalog: SkillCatalog):

        self.cfg = cfg

        self.catalog = catalog

        settings = cfg.skills

        self.inbox = cfg.project_root / settings.get("inbox_directory", "input/Jornais")

        self.processed = cfg.project_root / settings.get(
            "processed_directory",
            "input/Jornais/processados"
        )

    # -------------------------------------------------

    def scan(self):

        """
        Retorna [(pdf, skill)] para os PDFs reconhecidos e
        a lista de PDFs que não puderam ser identificados.
        """

        self.inbox.mkdir(parents=True, exist_ok=True)

        recognized = []

        unknown = []

        for pdf in sorted(self.inbox.glob("*.pdf")):

            skill = self.identify(pdf)

            if skill is None:

                unknown.append(pdf)

            else:

                recognized.append((pdf, skill))

        return recognized, unknown

    # -------------------------------------------------

    def identify(self, pdf: Path) -> SkillDefinition | None:

        name = normalize(pdf.stem)

        for skill in self.catalog.all():

            terms = (skill.name, *skill.aliases, *skill.keywords)

            if any(normalize(term) in name for term in terms):

                return skill

        cover = normalize(self.read_cover(pdf))

        scores = {

            skill: sum(cover.count(normalize(k)) for k in skill.keywords)

            for skill in self.catalog.all()

        }

        best = max(scores, key=scores.get, default=None)

        if best is None or scores[best] == 0:

            return None

        return best

    # -------------------------------------------------

    def read_cover(self, pdf: Path) -> str:

        executable = find_pdftotext(self.cfg.skills.get("pdftotext"))

        if executable is None:

            logger.warning("pdftotext not found; cannot read cover of %s", pdf)

            return ""

        with tempfile.TemporaryDirectory() as tmp:

            # Nome sem acentos: o pdftotext do Git não abre caminhos Unicode.
            source = Path(tmp) / "jornal.pdf"

            shutil.copyfile(pdf, source)

            result = subprocess.run(

                [str(executable), "-f", "1", "-l", "1", "-enc", "UTF-8", str(source), "-"],

                capture_output=True

            )

        return result.stdout.decode("utf-8", errors="ignore")

    # -------------------------------------------------

    def archive(self, pdf: Path) -> Path:

        target_dir = self.processed / datetime.now().strftime("%Y-%m-%d")

        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / pdf.name

        shutil.move(str(pdf), target)

        logger.info("PDF archived: %s", target)

        return target
