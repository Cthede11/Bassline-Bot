@echo off
echo BasslineBot Windows Setup
echo ========================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version') do set python_version=%%i
echo Found Python %python_version%

REM Check if Python version is 3.8 or higher
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"
if %errorlevel% neq 0 (
    echo Error: Python 3.8+ required. Found Python %python_version%
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install requirements
    pause
    exit /b 1
)

REM Check FFmpeg installation
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: FFmpeg not found in PATH.
    echo.
    echo Please install FFmpeg:
    echo 1. Download from https://ffmpeg.org/download.html#build-windows
    echo 2. Extract to a folder (e.g., C:\ffmpeg)
    echo 3. Add C:\ffmpeg\bin to your system PATH
    echo 4. Restart this script after installation
    echo.
    echo Would you like to continue without FFmpeg? (y/N)
    set /p continue_without_ffmpeg=
    if /i not "%continue_without_ffmpeg%"=="y" (
        echo Please install FFmpeg and re-run this script.
        pause
        exit /b 1
    )
) else (
    echo FFmpeg found
)

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo Please edit .env file and add your Discord bot token!
) else (
    echo .env file already exists
)

REM Create necessary directories
echo Creating directories...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "downloads" mkdir downloads
if not exist "static" mkdir static

REM Initialize database
echo Initializing database...
python scripts\migrate.py
if %errorlevel% neq 0 (
    echo Database initialization had issues, but continuing...
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env file and add your Discord bot token
echo 2. Run the bot: python -m src.bot
echo 3. View dashboard: http://localhost:8080
echo.
echo For Docker setup: docker-compose up -d
echo.
echo Happy music botting!
echo.
pause