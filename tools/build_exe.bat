@echo off
REM Build a single-file AiProof binary with PyInstaller on Windows.
REM Usage: tools\build_exe.bat [--onedir]
REM Produces dist\AiProof_Win_<version>.exe, embeds tools\version_info.txt and the icon.
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set MODE=--onefile
if "%~1"=="--onedir" set MODE=--onedir

for /f "delims=" %%v in ('python -c "import aiproof; print(aiproof.__version__)"') do set VERSION=%%v

if exist assets\AiProof.ico (set ICON=--icon assets\AiProof.ico) else (set ICON=)

echo Building AiProof %VERSION% for Windows (%MODE%)

pyinstaller ^
  --name AiProof_Win_%VERSION% ^
  --clean --noconfirm ^
  %MODE% ^
  %ICON% ^
  --version-file tools\version_info.txt ^
  --collect-data aiproof ^
  --hidden-import rich ^
  --hidden-import wcwidth ^
  --hidden-import tomli_w ^
  --console ^
  src\aiproof\__main__.py

if errorlevel 1 (
  echo build failed
  exit /b 1
)

certutil -hashfile "dist\AiProof_Win_%VERSION%.exe" SHA256 > "dist\AiProof_Win_%VERSION%.exe.sha256" 2>nul

echo done: dist\AiProof_Win_%VERSION%.exe
endlocal
