@echo off
chcp 65001 > nul
echo ==========================================
echo BACKUP DIARIO - Documentos Privados
echo ==========================================
echo.

set "ORIGEM=%USERPROFILE%\Documents\Documentos_Privados"
set "DESTINO=%USERPROFILE%\OneDrive\Backup_Privado"
set "DATA=%date:~6,4%-%date:~3,2%-%date:~0,2%"
set "HORA=%time:~0,2%-%time:~3,2%"

REM Criar pasta de destino se não existir
if not exist "%DESTINO%" (
    echo Criando pasta de backup...
    mkdir "%DESTINO%"
)

echo Iniciando backup: %DATA% %HORA%
echo Origem: %ORIGEM%
echo Destino: %DESTINO%
echo.

REM Criar pasta com data
set "BACKUP_DIR=%DESTINO%\Backup_%DATA%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Copiar arquivos com log
xcopy "%ORIGEM%\*" "%BACKUP_DIR%\" /E /I /Y > "%BACKUP_DIR%\log_%HORA%.txt" 2>&1

echo.
echo ==========================================
echo Backup concluido!
echo Local: %BACKUP_DIR%
echo Log: log_%HORA%.txt
echo ==========================================
echo.
pause
