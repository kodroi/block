: << 'CMDBLOCK'
@echo off
REM Polyglot entry point - works as both Windows batch and Unix shell
REM Calls protect_directories.py with Python

setlocal EnableDelayedExpansion
set "HOOK_DIR=%~dp0"

REM Quick check: if no .block files exist anywhere, skip Python entirely
dir /s /b ".block" ".block.local" 2>nul | findstr /r "." >nul 2>&1
if %errorlevel% neq 0 (
    exit /b 0
)

REM .block file exists, need Python to evaluate protection rules
where python >nul 2>&1
if %errorlevel% equ 0 (
    python "%HOOK_DIR%protect_directories.py"
    exit /b !errorlevel!
)

echo {"decision":"block","reason":"Python 3.8+ is required to use .block file protection. Install Python from https://python.org"}
exit /b 0
CMDBLOCK

# Unix: here-doc above discards batch code
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

# Quick check: if no .block files exist anywhere, skip Python entirely
if ! find . -name ".block" -o -name ".block.local" 2>/dev/null | head -1 | grep -q .; then
    exit 0
fi

# .block file exists, need Python to evaluate protection rules
if command -v python3 &> /dev/null; then
    python3 "$HOOK_DIR/protect_directories.py"
    exit $?
fi

if command -v python &> /dev/null; then
    python "$HOOK_DIR/protect_directories.py"
    exit $?
fi

echo '{"decision":"block","reason":"Python 3.8+ is required to use .block file protection. Install Python from https://python.org"}'
exit 0
