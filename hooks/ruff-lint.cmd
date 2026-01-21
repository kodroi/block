: << 'CMDBLOCK'
@echo off
REM Run ruff linter on Python files

where ruff >nul 2>&1
if %errorlevel% neq 0 exit /b 0

ruff check hooks\ tests\ 2>nul
exit /b 0
CMDBLOCK

# Unix
command -v ruff &> /dev/null || exit 0
ruff check hooks/ tests/ 2>/dev/null || true
exit 0
