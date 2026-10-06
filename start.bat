@echo off
REM ====================================================
REM  Speech AI - Inicia o frontend (Windows)
REM ----------------------------------------------------
REM  Duplo clique neste arquivo, ou no PowerShell/CMD:
REM    start.bat                 -> http://127.0.0.1:8000 (abre o navegador)
REM    start.bat --port 8080     -> outra porta
REM    start.bat --no-browser    -> nao abre o navegador
REM
REM  Para encerrar: Ctrl+C ou feche esta janela.
REM ====================================================

title Speech AI - Frontend
chcp 65001 >nul

REM Sempre roda a partir da raiz do projeto.
cd /d "%~dp0"

set PYTHONIOENCODING=utf-8

set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON where py >nul 2>&1 && set "PYTHON=py"

if not defined PYTHON (
    echo.
    echo [ERRO] Python nao encontrado no PATH.
    echo.
    pause
    exit /b 1
)

%PYTHON% -m web %*

if errorlevel 1 (
    echo.
    echo [ERRO] O frontend terminou com erro. Veja a mensagem acima.
    echo.
    pause
)
