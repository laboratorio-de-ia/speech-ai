"""
=========================================================
Job Runner
---------------------------------------------------------
Sprint 11 - Frontend

Executa as rotinas do main.py em segundo plano, uma por
vez, e guarda o log para o frontend acompanhar.

  modo "txt"      ->  python main.py --txt
  modo "jornais"  ->  python main.py --jornais

O log de cada execução também fica em logs/web_jobs/.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path


MODES = {

    "txt": ["--txt"],

    "jornais": ["--jornais"],

}


class JobBusyError(RuntimeError):

    pass


class JobRunner:

    # -------------------------------------------------

    def __init__(self, project_root: Path):

        self.project_root = project_root

        self.logs_dir = project_root / "logs" / "web_jobs"

        self._lock = threading.Lock()

        self._process = None

        self.job = None

    # -------------------------------------------------

    @property
    def running(self) -> bool:

        return self.job is not None and self.job["status"] == "running"

    # -------------------------------------------------

    def start(self, mode: str) -> dict:

        if mode not in MODES:

            raise ValueError(f"Modo inválido: {mode}")

        with self._lock:

            if self.running:

                raise JobBusyError(
                    f"Já existe uma rotina em execução ({self.job['mode']})."
                )

            self.logs_dir.mkdir(parents=True, exist_ok=True)

            started = datetime.now()

            command = [sys.executable, "main.py", *MODES[mode]]

            self.job = {

                "id": started.strftime("%Y%m%d_%H%M%S"),

                "mode": mode,

                "command": "python main.py " + " ".join(MODES[mode]),

                "status": "running",

                "started": started.isoformat(timespec="seconds"),

                "finished": None,

                "returncode": None,

                "lines": [],

                "log_file": str(self.logs_dir / f"{started:%Y%m%d_%H%M%S}_{mode}.log"),

            }

            env = os.environ.copy()

            env["PYTHONIOENCODING"] = "utf-8"

            self._process = subprocess.Popen(

                command,

                cwd=self.project_root,

                env=env,

                stdout=subprocess.PIPE,

                stderr=subprocess.STDOUT,

                encoding="utf-8",

                errors="replace",

                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

            )

            threading.Thread(

                target=self._follow,

                args=(self.job, self._process),

                daemon=True

            ).start()

            return self.snapshot()

    # -------------------------------------------------

    def _follow(self, job: dict, process: subprocess.Popen) -> None:

        with open(job["log_file"], "w", encoding="utf-8") as log:

            for line in process.stdout:

                line = line.rstrip("\n")

                job["lines"].append(line)

                log.write(line + "\n")

                log.flush()

        process.wait()

        job["returncode"] = process.returncode

        job["finished"] = datetime.now().isoformat(timespec="seconds")

        if job["status"] == "running":

            job["status"] = "success" if process.returncode == 0 else "failed"

    # -------------------------------------------------

    def cancel(self) -> dict:

        if not self.running:

            raise JobBusyError("Nenhuma rotina em execução.")

        self.job["status"] = "cancelled"

        pid = self._process.pid

        if os.name == "nt":

            # Encerra também os processos filhos (Claude Code da skill).
            subprocess.run(

                ["taskkill", "/PID", str(pid), "/T", "/F"],

                capture_output=True

            )

        else:

            self._process.kill()

        self.job["lines"].append("*** Rotina cancelada pelo usuário ***")

        return self.snapshot()

    # -------------------------------------------------

    def snapshot(self, since: int = 0) -> dict:

        if self.job is None:

            return {"status": "idle"}

        job = {k: v for k, v in self.job.items() if k != "lines"}

        job["lines"] = self.job["lines"][since:]

        job["total_lines"] = len(self.job["lines"])

        started = datetime.fromisoformat(self.job["started"])

        end = (

            datetime.fromisoformat(self.job["finished"])

            if self.job["finished"] else datetime.now()

        )

        job["elapsed_seconds"] = int((end - started).total_seconds())

        return job
