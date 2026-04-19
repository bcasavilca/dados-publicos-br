@echo off
chcp 65001 > nul
echo ==========================================
echo CRIANDO ESTRUTURA DE PASTAS PRIVADAS
echo ==========================================
echo.

set "BASE=%USERPROFILE%\Documents\Documentos_Privados"

echo Criando pastas em: %BASE%
echo.

mkdir "%BASE%\01_Pessoal\Identidade" 2> nul
mkdir "%BASE%\01_Pessoal\Financeiro" 2> nul
mkdir "%BASE%\01_Pessoal\Saude" 2> nul

mkdir "%BASE%\02_Trading\Estrategias" 2> nul
mkdir "%BASE%\02_Trading\Backtests" 2> nul
mkdir "%BASE%\02_Trading\Analises" 2> nul

mkdir "%BASE%\03_Projetos\DadosPublicosBR" 2> nul
mkdir "%BASE%\03_Projetos\CerebroDigital" 2> nul
mkdir "%BASE%\03_Projetos\Outros" 2> nul

mkdir "%BASE%\04_Familia\Contatos" 2> nul
mkdir "%BASE%\04_Familia\Documentos" 2> nul

mkdir "%BASE%\05_Backups\Logs" 2> nul
mkdir "%BASE%\05_Backups\Scripts" 2> nul

echo ✓ Pastas criadas com sucesso!
echo.
echo Estrutura:
echo   01_Pessoal
echo     - Identidade
echo     - Financeiro
echo     - Saude
echo   02_Trading
echo     - Estrategias
echo     - Backtests
echo     - Analises
echo   03_Projetos
echo     - DadosPublicosBR
echo     - CerebroDigital
echo     - Outros
echo   04_Familia
echo     - Contatos
echo     - Documentos
echo   05_Backups
echo     - Logs
echo     - Scripts
echo.
echo ==========================================
pause
