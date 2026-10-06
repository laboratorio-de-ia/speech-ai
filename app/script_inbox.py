"""
=========================================================
Script Inbox
---------------------------------------------------------
Sprint 10

Processa os arquivos .txt da pasta de entrada (input/),
um por vez, antes dos jornais.

Para cada arquivo:
  input/<nome>.txt
        │
        ▼
  output/<nome>_AAAA-MM-DD_HH-MM-SS.mp3
        │
        ▼
  input/processados/AAAA-MM-DD/<nome>.txt

Arquivos que falham ficam em input/ para a próxima
execução.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ScriptInbox:

    # -------------------------------------------------

    def __init__(self, app):

        self.app = app

        cfg = app.config

        self.inbox = self._resolve(
            cfg.get("input", "scripts_directory") or "input"
        )

        self.processed = self._resolve(
            cfg.get("input", "processed_directory") or "input/processados"
        )

    # -------------------------------------------------

    def _resolve(self, directory) -> Path:

        path = Path(directory)

        return path if path.is_absolute() else self.app.project_root / path

    # -------------------------------------------------

    def scan(self):

        self.inbox.mkdir(parents=True, exist_ok=True)

        return sorted(self.inbox.glob("*.txt"))

    # -------------------------------------------------

    def run(self) -> bool:

        """
        Retorna True se todos os .txt foram processados.
        """

        scripts = self.scan()

        print()
        print("=" * 60)
        print(" Script Inbox")
        print("=" * 60)
        print(f"Folder............. {self.inbox}")
        print(f"Scripts found...... {len(scripts)}")
        print("=" * 60)

        if not scripts:

            print("No scripts to process.")

            return True

        results = []

        for script in scripts:

            try:

                audio = self.app.run(script_file=script)

                archived = self.archive(script)

                results.append((script.name, audio, None))

                logger.info("Processed %s -> %s (archived at %s)", script, audio, archived)

            except Exception as error:

                logger.exception("Failed to process %s", script)

                results.append((script.name, None, error))

        print()
        print("=" * 60)
        print(" Scripts Summary")
        print("=" * 60)

        for name, audio, error in results:

            if error is None:

                print(f"[OK]    {name}: {audio}")

            else:

                print(f"[ERROR] {name}: {error}")

        print("=" * 60)

        return all(error is None for *_, error in results)

    # -------------------------------------------------

    def archive(self, script: Path) -> Path:

        target_dir = self.processed / datetime.now().strftime("%Y-%m-%d")

        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / script.name

        if target.exists():

            target = target_dir / f"{script.stem}_{datetime.now():%H-%M-%S}{script.suffix}"

        shutil.move(str(script), target)

        return target
