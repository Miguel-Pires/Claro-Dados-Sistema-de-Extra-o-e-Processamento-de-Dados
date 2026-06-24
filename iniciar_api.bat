@echo off
title Claro Extractor API - Porta 8765
echo Iniciando Claro Extractor API...
echo.
echo Acesso local:  http://localhost:8765/health
echo Acesso Docker: http://host.docker.internal:8765/health
echo.
cd /d "%~dp0"
python api.py
pause
