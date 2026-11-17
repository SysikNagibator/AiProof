@echo off
REM Build a single-file AiProof binary with PyInstaller on Windows.
REM Usage: tools\build_exe.bat [--onedir]
REM Produces dist\AiProof_Win_<arch>_<version>.exe, embeds tools\version_info.txt and the icon.
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set MODE=--onefile
if "%~1"=="--onedir" set MODE=--onedir

for /f "delims=" %%v in ('python -c "import aiproof; print(aiproof.__version__)"') do set VERSION=%%v

REM PROCESSOR_ARCHITEW6432 is the real architecture when running under WOW64.
set ARCH=x64
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set ARCH=arm64
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set ARCH=arm64

if exist assets\AiProof.ico (set ICON=--icon assets\AiProof.ico) else (set ICON=)

set NAME=AiProof_Win_%ARCH%_%VERSION%

echo Building AiProof %VERSION% for Windows/%ARCH% (%MODE%)

pyinstaller ^
  --name %NAME% ^
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

certutil -hashfile "dist\%NAME%.exe" SHA256 > "dist\%NAME%.exe.sha256" 2>nul

echo done: dist\%NAME%.exe
endlocal