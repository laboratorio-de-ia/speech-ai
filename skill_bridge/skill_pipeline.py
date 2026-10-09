"""
=========================================================
Skill Pipeline
---------------------------------------------------------
Sprint 10 - Integração com Skills de Jornais

Fluxo:

input/Jornais/*.pdf (identifica o jornal)
      │
      ▼
PDF do jornal
      │
      ▼
FastNewspaperPipeline (engine "fast": Python + IA em chamadas únicas)
  ou SkillRunner (engine "agent": Claude Code executa a skill inteira)
      │
      ▼
output/Jornais/<Jornal> - DD-MM-AAAA/script.txt
      │
      ▼
SpeechAIApp (lê o script.txt direto da pasta do jornal)
      │
      ▼
output/<nome do PDF>_AAAA-MM-DD_HH-MM-SS.mp3
      │
      ▼
input/Jornais/processados/AAAA-MM-DD/<pdf>

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app import SpeechAIApp

from newsroom.pipeline import FastNewspaperPipeline

from skill_bridge.newspaper_inbox import NewspaperInbox
from skill_bridge.skill_catalog import SkillCatalog, SkillDefinition
from skill_bridge.skill_runner import SkillRunner

logger = logging.getLogger(__name__)


class SkillPipeline:

    # -------------------------------------------------

    def __init__(self, app: SpeechAIApp = None):

        self.app = app or SpeechAIApp()

        self.cfg = self.app.config

        self.catalog = SkillCatalog(self.cfg)

        self.runner = SkillRunner(self.cfg)

        self.inbox = NewspaperInbox(self.cfg, self.catalog)

        # "fast" (padrão): processo rápido do newsroom/; "agent": skill completa via Claude Code.
        self.engine = self.cfg.skills.get("engine", "fast")

        self.fast = FastNewspaperPipeline(

            self.cfg.skills,

            self.runner.newspapers_dir,

            self.runner.script_name

        )

    # -------------------------------------------------

    def run_inbox(self) -> bool:

        """
        Processa todos os PDFs de input/Jornais, um jornal
        por vez. PDFs processados são arquivados; os que
        falham ficam na pasta para a próxima execução.

        Retorna True se tudo foi processado sem erro.
        """

        recognized, unknown = self.inbox.scan()

        print()
        print("=" * 60)
        print(" Newspaper Inbox")
        print("=" * 60)
        print(f"Folder............. {self.inbox.inbox}")
        print(f"PDFs recognized.... {len(recognized)}")
        print(f"PDFs unknown....... {len(unknown)}")
        print("=" * 60)

        for pdf in unknown:

            print(f"[IGNORED] Newspaper not identified: {pdf.name}")

            logger.warning("Newspaper not identified: %s", pdf)

        if not recognized:

            print()
            print("No newspapers to process.")

            return not unknown

        results = []

        for pdf, skill in recognized:

            try:

                audio = self.run(skill.name, pdf)

                archived = self.inbox.archive(pdf)

                results.append((pdf.name, skill, audio, None))

                logger.info("Processed %s -> %s (pdf archived at %s)", pdf, audio, archived)

            except Exception as error:

                logger.exception("Failed to process %s", pdf)

                results.append((pdf.name, skill, None, error))

        print()
        print("=" * 60)
        print(" Newspapers Summary")
        print("=" * 60)

        for name, skill, audio, error in results:

            if error is None:

                print(f"[OK]    {skill.newspaper}: {audio}")

            else:

                print(f"[ERROR] {skill.newspaper} ({name}): {error}")

        print("=" * 60)

        return not unknown and all(error is None for *_, error in results)

    # -------------------------------------------------

    def run(self, skill_name: str, pdf: Path = None) -> Path:

        """
        Executa a skill sobre o PDF e gera o áudio.

        Sem PDF, reaproveita o script.txt mais recente já
        gerado pela skill (por exemplo, no Cowork).
        """

        skill = self.catalog.get(skill_name)

        since = None

        pending = None

        if pdf is not None and self.engine == "fast":

            # Processo rápido: Python extrai e monta o HTML; a IA só escreve o conteúdo.
            pending = self.fast.run(skill.name, Path(pdf))

            script = pending.folder / self.runner.script_name

        else:

            if pdf is not None:

                # Processo completo: o Claude executa a skill inteira (SKILL.md).
                since = time.time()

                self.runner.run(skill, Path(pdf))

            script = self.find_script(skill, since)

        # O script fica na pasta do jornal (output/Jornais) e não é
        # copiado para input/, onde seria reprocessado pelo ScriptInbox.
        # O mp3 leva o nome do PDF (ou da pasta do jornal, sem PDF) e fica
        # na mesma pasta do jornal, junto do HTML e do script.txt.
        base_name = Path(pdf).stem if pdf is not None else script.parent.name

        audio = self.app.run(

            script_file=script,

            output_filename=self.app.audio_filename(base_name),

            output_dir=script.parent,

        )

        # O HTML do processo rápido termina em paralelo com o áudio.
        if pending is not None:

            pending.wait()

        return audio

    # -------------------------------------------------

    def find_script(self, skill: SkillDefinition, since: float = None) -> Path:

        """
        Localiza o script.txt mais recente nas pastas
        "<Jornal> - *" da pasta de jornais.
        """

        candidates = [

            folder / self.runner.script_name

            for folder in self.runner.newspapers_dir.glob(f"{skill.newspaper} - *")

            if (folder / self.runner.script_name).is_file()

        ]

        if since is not None:

            candidates = [

                script

                for script in candidates

                if script.stat().st_mtime >= since

            ]

        if not candidates:

            raise FileNotFoundError(

                f"No {self.runner.script_name} found for '{skill.newspaper}' "
                f"in {self.runner.newspapers_dir}"

            )

        return max(candidates, key=lambda script: script.stat().st_mtime)
