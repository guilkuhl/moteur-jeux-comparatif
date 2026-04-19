@echo off
setlocal

set "REG_KEY=HKCU\Software\Google\Chrome\NativeMessagingHosts\com.anthropic.claude_code_browser_extension"
set "BACKUP_FILE=%TEMP%\claude_desktop_chrome_manifest.txt"

echo ============================================
echo  Claude Code CLI - Chrome Bridge (Windows)
echo ============================================
echo.

REM 1. Sauvegarder la valeur actuelle (celle de Desktop)
for /f "tokens=2,*" %%a in ('reg query "%REG_KEY%" /ve 2^>nul ^| findstr /i "REG_SZ"') do (
    set "DESKTOP_MANIFEST=%%b"
)

if defined DESKTOP_MANIFEST (
    echo [1/3] Sauvegarde du manifest Desktop : %DESKTOP_MANIFEST%
    echo %DESKTOP_MANIFEST% > "%BACKUP_FILE%"

    REM 2. Supprimer la cle pour que le CLI puisse s'enregistrer
    reg delete "%REG_KEY%" /f >nul 2>&1
    echo [2/3] Cle de registre liberee pour le CLI.
) else (
    echo [info] Aucun manifest Desktop detecte, la cle est deja libre.
)

echo [3/3] Redemarrer Chrome maintenant, puis lancer : claude --chrome
echo.
echo Appuie sur une touche quand tu as fini avec le CLI...
pause >nul

REM 3. Restaurer la valeur Desktop
if exist "%BACKUP_FILE%" (
    set /p RESTORE_VAL=<"%BACKUP_FILE%"
    call set "RESTORE_VAL=%%RESTORE_VAL%%"
)

if defined RESTORE_VAL (
    reg add "%REG_KEY%" /ve /t REG_SZ /d "%RESTORE_VAL%" /f >nul 2>&1
    del "%BACKUP_FILE%" >nul 2>&1
    echo.
    echo [OK] Manifest Desktop restaure. Redemarrer Chrome pour retrouver Cowork.
) else (
    echo.
    echo [info] Rien a restaurer.
)

echo Termine.
endlocal
