"""
=========================================================
Fast Newspaper Pipeline
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais

PDF -> output/Jornais/<Jornal> - DD-MM-AAAA/
         <Jornal> - DD-MM-AAAA.html
         script.txt
         editorial.json   (conteúdo da IA, para auditoria)
         relatorio.json   (tempos, custos e verificações)

Etapas:
  1. Extração do PDF ............ Python (segundos)
  2. Três destaques em paralelo .. IA (chamadas únicas)
  3. Capa e abertura do áudio .... IA (chamada curta)
  4. Roteiro + validação ......... Python
  5. HTML + verificação visual ... Python + Playwright (em paralelo com o áudio)

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from newsroom.editor import AIEditor
from newsroom.extractor import NewspaperExtractor
from newsroom.profiles import get_profile
from newsroom.renderer import DeckRenderer
from newsroom.script_writer import ScriptWriter

logger = logging.getLogger(__name__)


class FastResult:

    """
    Resultado do processo rápido. O roteiro já está gravado quando
    run() retorna; o HTML termina numa thread (em paralelo com o
    áudio). Chame wait() antes de considerar o jornal concluído.
    """

    def __init__(self, folder: Path):

        self.folder = folder

        self._thread = None

        self._error = None

    def start(self, target) -> None:

        def runner():

            try:

                target()

            except Exception as error:  # repassado em wait()

                self._error = error

        self._thread = threading.Thread(target=runner, daemon=True)

        self._thread.start()

    def wait(self) -> Path:

        if self._thread:

            self._thread.join()

        if self._error:

            raise self._error

        return self.folder


class FastNewspaperPipeline:

    # -------------------------------------------------

    def __init__(self, settings: dict, newspapers_dir: Path, script_name: str = "script.txt"):

        self.settings = settings

        self.newspapers_dir = Path(newspapers_dir)

        self.script_name = script_name

    # -------------------------------------------------

    def run(self, skill_name: str, pdf: Path) -> FastResult:

        profile = get_profile(skill_name)

        timings = {}

        started = time.time()

        def step(name, since):

            timings[name] = round(time.time() - since, 1)

            print(f"  [ok] {name:<34} {timings[name]:>6.1f}s")

        print()
        print("=" * 60)
        print(f" Fast newspaper pipeline: {profile.newspaper}")
        print("=" * 60)
        print(f"PDF................ {pdf}")
        print()

        # 1. Extração ------------------------------------------------
        t = time.time()

        extractor = NewspaperExtractor(self.settings.get("pdftotext"))

        pages = extractor.extract(Path(pdf))

        if len(pages) < 3:

            raise RuntimeError("Texto do PDF não pôde ser extraído (PDF escaneado ou protegido?).")

        step(f"Extração ({len(pages)} páginas)", t)

        # 2 e 3. IA ------------------------------------------------------
        editor = AIEditor(profile, self.settings)

        t = time.time()

        print("  ...  IA escrevendo os 3 destaques em paralelo")

        tiers = editor.write_tiers(pages)

        step("IA: 3 destaques (paralelo)", t)

        t = time.time()

        cover = editor.write_cover(tiers, pages[0].text)

        step("IA: capa e abertura", t)

        # 4. Roteiro (antes do HTML: o áudio já pode começar) --------------
        t = time.time()

        folder = self._new_folder(profile.newspaper)

        writer = ScriptWriter(profile)

        script = writer.build(tiers, cover)

        validation = writer.validate(script)

        (folder / self.script_name).write_text(script, encoding="utf-8")

        step(f"Roteiro ({validation['words']} palavras)", t)

        for issue in validation["issues"]:

            print(f"  [aviso] roteiro: {issue}")

        # 5. HTML + verificação, em paralelo com o áudio ---------------------
        html_path = folder / f"{folder.name.split(' (')[0]}.html"

        result = FastResult(folder)

        def build_html():

            t = time.time()

            layout = DeckRenderer(profile).render_checked(tiers, cover, html_path)

            final_tiers = layout.pop("tiers", tiers)

            step("HTML + verificação de layout", t)

            if layout.get("overflow"):

                print(f"  [aviso] slides ainda apertados: {layout['overflow']}")

            total = round(time.time() - started, 1)

            cost = sum(s["cost_usd"] or 0 for s in editor.stats)

            (folder / "editorial.json").write_text(

                json.dumps({"cover": cover, "tiers": final_tiers}, ensure_ascii=False, indent=1),

                encoding="utf-8"

            )

            (folder / "relatorio.json").write_text(

                json.dumps({

                    "jornal": profile.newspaper,

                    "pdf": str(pdf),

                    "processado_em": datetime.now().isoformat(timespec="seconds"),

                    "tempo_resumo_s": total,

                    "etapas_s": timings,

                    "chamadas_ia": editor.stats,

                    "custo_usd": round(cost, 2),

                    "layout": layout,

                    "roteiro": validation,

                }, ensure_ascii=False, indent=1),

                encoding="utf-8"

            )

            print(f"Skill finished..... {total / 60:.1f} min | US$ {cost:.2f}")

            logger.info("Fast pipeline %s finished in %.1fs (US$ %.2f)", profile.newspaper, total, cost)

        result.start(build_html)

        print(f"Folder............. {folder}")

        return result


    # -------------------------------------------------

    def _new_folder(self, newspaper: str) -> Path:

        base = f"{newspaper} - {datetime.now():%d-%m-%Y}"

        folder = self.newspapers_dir / base

        n = 2

        while folder.exists():

            folder = self.newspapers_dir / f"{base} ({n})"

            n += 1

        folder.mkdir(parents=True)

        return folder
