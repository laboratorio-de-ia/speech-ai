"""
=========================================================
Skill Runner
---------------------------------------------------------
Sprint 10 - Integração com Skills de Jornais

Executa uma skill de jornal através do Claude Code em
modo não interativo (claude -p).

O HTML e o script.txt são gravados em
output/Jornais/<Jornal> - DD-MM-AAAA/.

O andamento é exibido no console (stream-json) e o log
completo de cada execução fica em logs/skills/.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config.config_manager import ConfigManager

from newsroom.pdf_tools import find_pdftotext
from skill_bridge.skill_catalog import SkillDefinition

logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """\
Execute a skill "{name}". Leia o arquivo {skill_file} por inteiro e siga todas as instruções dele.

PDF do jornal: {pdf}
Data de processamento (hoje): {today}

Ambiente de execução (Speech AI, execução automática pelo main.py):
- Você está rodando localmente no Windows via Claude Code, sem interação com o usuário.
- Não existem /mnt/user-data, device_commit_files nem SendUserFile: ignore esses passos.
- Grave os arquivos diretamente em "{output_dir}".
  Se essa pasta já existir, crie uma nova com sufixo, por exemplo "{output_dir_alt}".
- A pasta final deve conter "{newspaper} - {today}.html" e "{script_name}".
- NÃO execute a etapa "Gerar o áudio" da skill: o Speech AI gera o áudio logo depois.
- Leia o PDF de fato, página a página. Ferramentas disponíveis:
  - pdftotext: "{pdftotext}"
  - Python: "{python}" (pdfplumber e playwright instalados).
- Os resumos anteriores (em "{newspapers_dir}" ou em pastas de referência) servem SOMENTE como base visual
  (<head>, <style> e <script>). Nunca copie textos, números ou o script.txt deles, mesmo que seja a mesma edição.
- Se npm/node não estiverem disponíveis, pule o download das fontes e verifique com as fontes do sistema.
- Use scripts temporários fora da pasta do projeto (por exemplo, em %TEMP%).
- Não publique artefatos.

Ao terminar, responda com o caminho completo da pasta criada.
"""


class SkillRunner:

    # -------------------------------------------------

    def __init__(self, cfg: ConfigManager):

        self.cfg = cfg

        settings = cfg.skills

        self.newspapers_dir = self._resolve(
            settings.get("newspapers_directory", "output/Jornais")
        )

        self.reference_dirs = [

            self._resolve(directory)

            for directory in settings.get("reference_directories", [])

        ]

        self.logs_dir = cfg.project_root / "logs" / "skills"

        self.script_name = settings.get("script_name", "script.txt")

        self.claude_command = settings.get("claude_command", "claude")

        self.permission_mode = settings.get("permission_mode", "acceptEdits")

        self.allowed_tools = settings.get("allowed_tools")

        self.model = settings.get("model")

        self.timeout = int(settings.get("timeout_minutes", 120)) * 60

        self.pdftotext = find_pdftotext(settings.get("pdftotext"))

    # -------------------------------------------------

    def build_env(self) -> dict:

        """
        Ambiente do Claude: pdftotext e o Python do Speech AI
        no PATH, mesmo quando main.py roda fora do Git Bash.
        """

        env = os.environ.copy()

        extra = [str(Path(sys.executable).parent)]

        if self.pdftotext:

            extra.append(str(self.pdftotext.parent))

        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])

        return env

    # -------------------------------------------------

    def _resolve(self, directory) -> Path:

        path = Path(directory)

        return path if path.is_absolute() else self.cfg.project_root / path

    # -------------------------------------------------

    def build_prompt(self, skill: SkillDefinition, pdf: Path) -> str:

        today = datetime.now().strftime("%d-%m-%Y")

        folder = self.newspapers_dir / f"{skill.newspaper} - {today}"

        return PROMPT_TEMPLATE.format(

            name=skill.name,

            skill_file=skill.skill_file,

            pdf=pdf,

            today=today,

            output_dir=f"{folder}\\",

            output_dir_alt=f"{folder} (2)\\",

            newspaper=skill.newspaper,

            script_name=self.script_name,

            newspapers_dir=self.newspapers_dir,

            pdftotext=self.pdftotext or "não encontrado (use pdfplumber)",

            python=sys.executable

        )

    # -------------------------------------------------

    def build_command(self, skill: SkillDefinition, pdf: Path) -> list:

        executable = shutil.which(self.claude_command)

        if executable is None:

            raise FileNotFoundError(
                f"Claude Code CLI not found: '{self.claude_command}'"
            )

        command = [

            executable,

            "-p", self.build_prompt(skill, pdf),

            "--output-format", "stream-json",

            "--verbose",

            "--permission-mode", self.permission_mode,

        ]

        directories = [

            self.newspapers_dir,

            pdf.parent,

            skill.skill_file.parent,

            *[d for d in self.reference_dirs if d.exists()],

        ]

        for directory in directories:

            command += ["--add-dir", str(directory)]

        if self.allowed_tools:

            command += ["--allowedTools", self.allowed_tools]

        if self.model:

            command += ["--model", self.model]

        return command

    # -------------------------------------------------

    def run(self, skill: SkillDefinition, pdf: Path) -> None:

        pdf = Path(pdf).resolve()

        if not pdf.exists():

            raise FileNotFoundError(f"PDF not found:\n{pdf}")

        self.newspapers_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.logs_dir / (
            f"{skill.name}_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        )

        command = self.build_command(skill, pdf)

        print()
        print("=" * 60)
        print(f" Running skill: {skill.name}")
        print("=" * 60)
        print(f"Newspaper.......... {skill.newspaper}")
        print(f"PDF................ {pdf}")
        print(f"Output folder...... {self.newspapers_dir}")
        print(f"Log................ {log_file}")
        print("=" * 60)
        print("Claude is reading the newspaper. This may take several minutes...")
        print()

        logger.info("Running skill '%s' on %s (log: %s)", skill.name, pdf, log_file)

        result = None

        with open(log_file, "w", encoding="utf-8") as log:

            process = subprocess.Popen(

                command,

                cwd=self.cfg.project_root,

                env=self.build_env(),

                stdout=subprocess.PIPE,

                stderr=subprocess.STDOUT,

                encoding="utf-8",

                errors="replace"

            )

            try:

                for line in process.stdout:

                    log.write(line)

                    log.flush()

                    event = self._parse(line)

                    if event is None:

                        print(f"  {line.rstrip()}")

                        continue

                    if event.get("type") == "result":

                        result = event

                    self._show_progress(event)

                process.wait(timeout=self.timeout)

            except subprocess.TimeoutExpired:

                process.kill()

                raise RuntimeError(
                    f"Skill '{skill.name}' timed out after {self.timeout // 60} min."
                )

        if process.returncode != 0 or result is None or result.get("is_error"):

            raise RuntimeError(

                f"Skill '{skill.name}' failed (exit code {process.returncode}). "
                f"See {log_file}"

            )

        cost = result.get("total_cost_usd")

        minutes = result.get("duration_ms", 0) / 60000

        print()
        print(f"Skill finished..... {minutes:.1f} min"
              + (f" | US$ {cost:.2f}" if cost is not None else ""))

        logger.info("Skill '%s' finished in %.1f min", skill.name, minutes)

    # -------------------------------------------------

    @staticmethod
    def _parse(line: str):

        try:

            return json.loads(line)

        except ValueError:

            return None

    # -------------------------------------------------

    @staticmethod
    def _show_progress(event: dict) -> None:

        if event.get("type") != "assistant":

            return

        for block in event.get("message", {}).get("content", []):

            if block.get("type") == "text" and block.get("text", "").strip():

                text = " ".join(block["text"].split())

                print(f"  > {text[:160]}")

            elif block.get("type") == "tool_use":

                data = block.get("input", {})

                detail = (

                    data.get("description")

                    or data.get("file_path")

                    or data.get("pattern")

                    or str(data.get("command", ""))

                )

                detail = " ".join(str(detail).split())

                print(f"  [{block.get('name')}] {detail[:140]}")
