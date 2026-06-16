@echo off
echo Finance Dashboard - Iniciando...
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Ambiente virtual ativado.
) else (
    echo AVISO: .venv nao encontrado, usando Python global.
)

echo.
echo Iniciando Streamlit em http://localhost:8501
echo Pressione Ctrl+C para parar.
echo.

python -m streamlit run dashboards\streamlit\app.py ^
    --server.port 8501 ^
    --server.headless false ^
    --browser.gatherUsageStats false

pause
