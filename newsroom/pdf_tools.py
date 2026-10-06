"""
=========================================================
PDF Tools
---------------------------------------------------------
Sprint 10 - Integração com Skills de Jornais

Localiza o pdftotext. No Windows ele costuma vir junto
com o Git (Git\\mingw64\\bin), fora do PATH do PowerShell.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import shutil
from pathlib import Path


def find_pdftotext(configured: str = None) -> Path | None:

    if configured and Path(configured).is_file():

        return Path(configured)

    found = shutil.which("pdftotext")

    if found:

        return Path(found)

    git = shutil.which("git")

    if git:

        # ...\Git\cmd\git.exe  ->  ...\Git\mingw64\bin\pdftotext.exe
        candidate = Path(git).resolve().parent.parent / "mingw64" / "bin" / "pdftotext.exe"

        if candidate.is_file():

            return candidate

    return None
