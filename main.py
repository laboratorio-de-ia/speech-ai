"""
====================================================
 Speech AI - Main
----------------------------------------------------
Sprint 10

Ponto de entrada da aplicação.

Uso:

  python main.py
      Processa tudo, nesta ordem:
      1. Cada .txt em input/ vira output/<nome>_AAAA-MM-DD_HH-MM-SS.mp3
         e é arquivado em input/processados/AAAA-MM-DD/.
      2. Cada PDF em input/Jornais: identifica o jornal, executa a
         skill (HTML + script.txt em output/Jornais/), gera
         output/<nome do PDF>_AAAA-MM-DD_HH-MM-SS.mp3 e arquiva o PDF
         em input/Jornais/processados/AAAA-MM-DD/.

  python main.py --txt
      Processa somente os .txt de input/.

  python main.py --jornais
      Processa somente os PDFs de input/Jornais.

  python main.py --txt --jornais
      Mesmo que sem parâmetros: os dois, .txt primeiro.

  python main.py --skill valor-economico --pdf "Valor.pdf"
      Executa uma skill sobre um PDF específico.

  python main.py --skill estado-de-sp
      Sem --pdf: usa o script.txt mais recente já gerado
      pela skill na pasta de jornais.

  python main.py --list-skills

Toda a orquestração fica em SpeechAIApp e SkillPipeline.
====================================================
"""

import argparse
import sys

from app import ScriptInbox, SpeechAIApp


def parse_args():

    parser = argparse.ArgumentParser(description="Speech AI Pipeline")

    parser.add_argument(
        "--txt", "--script",
        dest="txt",
        action="store_true",
        help="Processa os arquivos .txt de input/"
    )

    parser.add_argument(
        "--jornais",
        action="store_true",
        help="Processa os PDFs de jornais de input/Jornais"
    )

    parser.add_argument(
        "--skill",
        help="Skill de jornal a executar (ex.: valor-economico, estado-de-sp)"
    )

    parser.add_argument(
        "--pdf",
        help="PDF do jornal. Sem ele, usa o último script.txt gerado pela skill."
    )

    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="Lista as skills disponíveis"
    )

    return parser.parse_args()


def main():

    for stream in (sys.stdout, sys.stderr):

        stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

    args = parse_args()

    if args.list_skills:

        from config.config_manager import ConfigManager
        from skill_bridge import SkillCatalog

        for skill in SkillCatalog(ConfigManager()).all():

            aliases = ", ".join(skill.aliases)

            print(f"{skill.name:<18} {skill.newspaper}  (aliases: {aliases})")

        return

    if args.pdf and not args.skill:

        raise SystemExit("--pdf requires --skill")

    if args.skill and (args.txt or args.jornais):

        raise SystemExit("--skill cannot be combined with --txt/--jornais")

    app = SpeechAIApp()

    if args.skill:

        from skill_bridge import SkillPipeline

        SkillPipeline(app).run(args.skill, args.pdf)

        return

    # Sem --txt nem --jornais: processa os dois.
    process_all = not (args.txt or args.jornais)

    ok = True

    # Os .txt de input/ sempre vêm antes dos jornais.
    if args.txt or process_all:

        ok = ScriptInbox(app).run() and ok

    if args.jornais or process_all:

        from skill_bridge import SkillPipeline

        ok = SkillPipeline(app).run_inbox() and ok

    if not ok:

        sys.exit(1)


if __name__ == "__main__":
    main()
