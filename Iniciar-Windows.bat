@echo off
setlocal
cd /d "%~dp0"
title Free Live Translator

rem Primeira vez: instala tudo automaticamente (precisa de internet).
if not exist ".venv\Scripts\python.exe" (
  echo ============================================================
  echo  Free Live Translator - primeira instalacao
  echo  Isso pode levar de 10 a 30 minutos. Nao feche esta janela.
  echo ============================================================
  echo.
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1" -Auto
  if errorlevel 1 (
    echo.
    echo A instalacao nao terminou.
    echo Se o Windows bloqueou o arquivo: clique com o botao direito na pasta
    echo ou no ZIP, escolha Propriedades, marque "Desbloquear" e tente de novo.
    echo.
    pause
    exit /b 1
  )
)

echo.
echo Iniciando... o painel abre sozinho no navegador em alguns segundos.
echo Para encerrar, feche esta janela.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1"
if errorlevel 1 (
  echo.
  echo O programa nao iniciou. Veja as mensagens acima.
  pause
)
