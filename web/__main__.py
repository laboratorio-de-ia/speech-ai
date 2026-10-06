"""
Inicia o frontend do Speech AI.

    python -m web            ->  http://127.0.0.1:8000
    python -m web --port 8080
"""

import argparse
import os
import sys
import webbrowser
from pathlib import Path

import uvicorn


def main():

    parser = argparse.ArgumentParser(description="Speech AI - Frontend")

    parser.add_argument("--host", default="127.0.0.1")

    parser.add_argument("--port", type=int, default=8000)

    parser.add_argument("--no-browser", action="store_true")

    args = parser.parse_args()

    # O servidor roda a partir da raiz do projeto (mesma base do main.py).
    os.chdir(Path(__file__).resolve().parent.parent)

    sys.path.insert(0, os.getcwd())

    url = f"http://{args.host}:{args.port}"

    print(f"Speech AI Frontend: {url}")

    if not args.no_browser:

        webbrowser.open(url)

    uvicorn.run("web.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
