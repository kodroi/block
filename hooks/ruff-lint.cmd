: << 'CMDBLOCK'
@echo off
REM Run ruff linter on Python files

where ruff >nul 2>&1
if %errorlevel% neq 0 (
    echo ruff not installed. Install with: pip install ruff
    exit /b 1
)

ruff check hooks\ tests\
exit /b %errorlevel%
CMDBLOCK

# Unix
if ! command -v ruff &> /dev/null; then
    echo "ruff not installed. Install with: pip install ruff"
    exit 1
fi

ruff check hooks/ tests/
