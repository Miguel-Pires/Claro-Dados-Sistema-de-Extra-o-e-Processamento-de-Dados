@echo off
chcp 65001 > nul
echo.
echo ============================================================
echo   Gerando Analisador de Faturas  (onedir — rapido)
echo ============================================================
echo.

cd /d "%~dp0"

pyinstaller --noconfirm "Analisador de Faturas.spec"

echo.
if exist "dist\Analisador de Faturas\Analisador de Faturas.exe" (
    echo OK - Pasta gerada em:
    echo    dist\Analisador de Faturas\
    echo.
    echo Para compartilhar: compacte a pasta "Analisador de Faturas" em ZIP
    echo Quem receber: descompacta e abre "Analisador de Faturas.exe"
) else (
    echo ERRO - Build falhou. Verifique os logs acima.
)
echo.
pause
