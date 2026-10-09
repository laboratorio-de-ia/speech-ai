"""
=========================================================
Speech AI - Web Server
---------------------------------------------------------
Sprint 11 - Frontend

API local (FastAPI) usada pelo frontend:

  Envio de arquivos
    POST   /api/upload/txt          -> input/
    POST   /api/upload/jornais      -> input/Jornais/
    DELETE /api/files/{tipo}/{nome}

  Rotinas (main.py)
    POST   /api/run/txt             -> python main.py --txt
    POST   /api/run/jornais         -> python main.py --jornais
    POST   /api/job/cancel
    GET    /api/job?since=N

  Consulta
    GET    /api/files               -> pendentes + resultados
    GET    /media/audio/{nome}
    GET    /media/resumos/{pasta}/{arquivo}

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.config_manager import ConfigManager
from skill_bridge import NewspaperInbox, SkillCatalog

from web.job_runner import JobBusyError, JobRunner


cfg = ConfigManager()

ROOT = cfg.project_root

STATIC = Path(__file__).resolve().parent / "static"


def _resolve(directory) -> Path:

    path = Path(directory)

    return path if path.is_absolute() else ROOT / path


TXT_DIR = _resolve(cfg.get("input", "scripts_directory") or "input")

PDF_DIR = _resolve(cfg.skills.get("inbox_directory", "input/Jornais"))

OUTPUT_DIR = _resolve(cfg.output_directory)

RESUMOS_DIR = _resolve(cfg.skills.get("newspapers_directory", "output/Jornais"))

inbox = NewspaperInbox(cfg, SkillCatalog(cfg))

runner = JobRunner(ROOT)

app = FastAPI(title="Speech AI")

app.mount("/static", StaticFiles(directory=STATIC), name="static")


# =====================================================
# Helpers
# =====================================================

def _safe_name(name: str, suffix: str) -> str:

    """Mantém só o nome do arquivo (sem pastas) e valida a extensão."""

    clean = Path(name or "").name.strip()

    if not clean or clean.startswith("."):

        raise HTTPException(400, "Nome de arquivo inválido.")

    if Path(clean).suffix.lower() != suffix:

        raise HTTPException(400, f"'{clean}': envie apenas arquivos {suffix}.")

    return clean


def _inside(base: Path, *parts: str) -> Path:

    """Resolve o caminho e garante que ele está dentro de base."""

    path = base.joinpath(*parts).resolve()

    if base.resolve() not in path.parents or not path.is_file():

        raise HTTPException(404, "Arquivo não encontrado.")

    return path


def _info(path: Path) -> dict:

    stat = path.stat()

    return {

        "name": path.name,

        "size": stat.st_size,

        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),

    }


def _decode_text(raw: bytes) -> str:

    """Aceita UTF-8 e, como alternativa, ANSI (cp1252) do Bloco de Notas."""

    for encoding in ("utf-8-sig", "cp1252"):

        try:

            return raw.decode(encoding)

        except UnicodeDecodeError:

            continue

    raise HTTPException(400, "Não foi possível ler o texto (codificação desconhecida).")


def _ensure_idle():

    if runner.running:

        raise HTTPException(409, "Aguarde: há uma rotina em execução.")


# =====================================================
# Página
# =====================================================

@app.get("/", include_in_schema=False)
def index():

    return FileResponse(STATIC / "index.html")


# =====================================================
# Arquivos
# =====================================================

@app.get("/api/files")
def list_files():

    TXT_DIR.mkdir(parents=True, exist_ok=True)

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    scripts = []

    for path in sorted(TXT_DIR.glob("*.txt")):

        item = _info(path)

        item["words"] = len(path.read_text(encoding="utf-8", errors="replace").split())

        scripts.append(item)

    jornais = []

    for path in sorted(PDF_DIR.glob("*.pdf")):

        item = _info(path)

        skill = inbox.identify(path)

        item["newspaper"] = skill.newspaper if skill else None

        jornais.append(item)

    audios = sorted(

        (_info(p) for p in OUTPUT_DIR.glob("*.mp3")),

        key=lambda a: a["modified"],

        reverse=True

    )[:60]

    resumos = []

    if RESUMOS_DIR.exists():

        for folder in RESUMOS_DIR.iterdir():

            if not folder.is_dir():

                continue

            html = next(iter(sorted(folder.glob("*.html"))), None)

            script = folder / "script.txt"

            audio = next(iter(sorted(folder.glob("*.mp3"))), None)

            resumos.append({

                "folder": folder.name,

                "html": html.name if html else None,

                "script": script.is_file(),

                "audio": audio.name if audio else None,

                "modified": datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds"),

            })

    resumos.sort(key=lambda r: r["modified"], reverse=True)

    return {

        "txt": scripts,

        "jornais": jornais,

        "audios": audios,

        "resumos": resumos,

        "folders": {

            "txt": str(TXT_DIR),

            "jornais": str(PDF_DIR),

            "audios": str(OUTPUT_DIR),

            "resumos": str(RESUMOS_DIR),

        },

    }


@app.post("/api/upload/txt")
async def upload_txt(files: list[UploadFile] = File(...)):

    TXT_DIR.mkdir(parents=True, exist_ok=True)

    saved = []

    for upload in files:

        name = _safe_name(upload.filename, ".txt")

        text = _decode_text(await upload.read())

        if not text.strip():

            raise HTTPException(400, f"'{name}' está vazio.")

        # Sempre gravado em UTF-8, formato que o pipeline lê.
        (TXT_DIR / name).write_text(text, encoding="utf-8")

        saved.append(name)

    return {"saved": saved}


@app.post("/api/upload/jornais")
async def upload_jornais(files: list[UploadFile] = File(...)):

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    saved = []

    for upload in files:

        name = _safe_name(upload.filename, ".pdf")

        raw = await upload.read()

        if not raw.startswith(b"%PDF"):

            raise HTTPException(400, f"'{name}' não é um PDF válido.")

        target = PDF_DIR / name

        target.write_bytes(raw)

        skill = inbox.identify(target)

        saved.append({

            "name": name,

            "newspaper": skill.newspaper if skill else None,

        })

    return {"saved": saved}


@app.delete("/api/files/{kind}/{name}")
def delete_file(kind: str, name: str):

    _ensure_idle()

    folders = {"txt": (TXT_DIR, ".txt"), "jornais": (PDF_DIR, ".pdf")}

    if kind not in folders:

        raise HTTPException(404, "Tipo inválido.")

    base, suffix = folders[kind]

    path = _inside(base, _safe_name(name, suffix))

    path.unlink()

    return {"deleted": path.name}


# =====================================================
# Rotinas
# =====================================================

@app.post("/api/run/{mode}")
def run(mode: str):

    if mode not in ("txt", "jornais"):

        raise HTTPException(404, "Rotina inválida.")

    try:

        return runner.start(mode)

    except JobBusyError as error:

        raise HTTPException(409, str(error))


@app.post("/api/job/cancel")
def cancel():

    try:

        return runner.cancel()

    except JobBusyError as error:

        raise HTTPException(409, str(error))


@app.get("/api/job")
def job(since: int = 0):

    return runner.snapshot(since)


# =====================================================
# Resultados
# =====================================================

@app.get("/media/audio/{name}")
def audio(name: str, download: bool = False):

    path = _inside(OUTPUT_DIR, _safe_name(name, ".mp3"))

    return FileResponse(

        path,

        media_type="audio/mpeg",

        filename=path.name if download else None

    )


@app.get("/media/resumos/{folder}/{name}")
def resumo(folder: str, name: str, download: bool = False):

    path = _inside(RESUMOS_DIR, Path(folder).name, Path(name).name)

    suffix = path.suffix.lower()

    if suffix not in (".html", ".txt", ".mp3"):

        raise HTTPException(404, "Arquivo não encontrado.")

    media = {

        ".html": "text/html; charset=utf-8",

        ".txt": "text/plain; charset=utf-8",

        ".mp3": "audio/mpeg",

    }[suffix]

    return FileResponse(path, media_type=media, filename=path.name if download else None)
