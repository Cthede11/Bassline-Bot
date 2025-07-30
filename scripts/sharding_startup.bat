@echo off
setlocal enabledelayedexpansion

REM BasslineBot Sharding Startup Script for Windows
REM This script helps you deploy your bot with different sharding configurations

title BasslineBot Sharding Manager

REM Colors for output (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "NC=[0m"

REM Check if .env file exists
if not exist ".env" (
    echo %RED%❌ .env file not found!%NC%
    echo.
    echo Please create a .env file with your configuration.
    echo You can use one of these templates:
    echo   - .env.example ^(basic setup^)
    echo   - .env.sharding ^(sharding template^)
    echo.
    pause
    exit /b 1
)

REM Load environment variables from .env
for /f "usebackq tokens=1,2 delims==" %%i in (".env") do (
    if not "%%i"=="" if not "%%i"=="REM" if not "%%i"=="#" (
        set "%%i=%%j"
    )
)

REM Check Discord token
if "%DISCORD_TOKEN%"=="" (
    echo %RED%❌ DISCORD_TOKEN not set in .env file!%NC%
    pause
    exit /b 1
)

REM Display deployment options menu
:show_menu
cls
echo.
echo %BLUE%BasslineBot Sharding Deployment Options%NC%
echo ==========================================
echo.
echo 1. Single Instance ^(No Sharding^) - Simple setup
echo 2. Automatic Sharding - Recommended for most users
echo 3. Manual Sharding ^(2 shards^) - Advanced users
echo 4. Manual Sharding ^(Custom^) - Expert configuration
echo 5. Docker Automatic Sharding - Production ready
echo 6. Docker Manual Sharding - Full control
echo 7. Monitor Existing Deployment
echo 8. Stop All Services
echo 9. Help ^& Information
echo.
set /p choice="Select deployment option (1-9): "
echo.

if "%choice%"=="1" goto deploy_single
if "%choice%"=="2" goto deploy_auto_sharding
if "%choice%"=="3" goto deploy_manual_2
if "%choice%"=="4" goto deploy_manual_custom
if "%choice%"=="5" goto deploy_docker_auto
if "%choice%"=="6" goto deploy_docker_manual
if "%choice%"=="7" goto monitor_deployment
if "%choice%"=="8" goto stop_services
if "%choice%"=="9" goto show_help
echo %RED%Invalid option selected%NC%
pause
goto show_menu

REM Single instance deployment
:deploy_single
echo %BLUE%ℹ️  Deploying single instance ^(no sharding^)...%NC%

REM Create backup of .env
copy .env .env.backup >nul

REM Create temporary .env for single instance
powershell -Command "(gc .env) -replace 'AUTO_SHARD=.*', 'AUTO_SHARD=false' | Out-File -encoding ASCII .env.tmp"
powershell -Command "(gc .env.tmp) -replace 'SHARD_ID=.*', 'SHARD_ID=' | Out-File -encoding ASCII .env.tmp2"
powershell -Command "(gc .env.tmp2) -replace 'SHARD_COUNT=.*', 'SHARD_COUNT=' | Out-File -encoding ASCII .env"
del .env.tmp .env.tmp2 >nul 2>&1

echo %GREEN%✅ Starting bot in single instance mode...%NC%
python -m src.bot
goto cleanup

REM Automatic sharding deployment
:deploy_auto_sharding
echo %BLUE%ℹ️  Deploying with automatic sharding...%NC%

REM Check for Redis/PostgreSQL recommendation
if "%REDIS_URL%"=="" (
    echo %YELLOW%⚠️  Warning: Redis not configured - recommended for sharding%NC%
)
if "%DATABASE_URL%"=="sqlite:///./data/basslinebot.db" (
    echo %YELLOW%⚠️  Warning: Using SQLite - consider PostgreSQL for production%NC%
)

REM Create backup and configure for auto sharding
copy .env .env.backup >nul
powershell -Command "(gc .env) -replace 'AUTO_SHARD=.*', 'AUTO_SHARD=true' | Out-File -encoding ASCII .env.tmp"
powershell -Command "(gc .env.tmp) -replace 'SHARD_ID=.*', 'SHARD_ID=' | Out-File -encoding ASCII .env.tmp2"
powershell -Command "(gc .env.tmp2) -replace 'SHARD_COUNT=.*', 'SHARD_COUNT=' | Out-File -encoding ASCII .env"
del .env.tmp .env.tmp2 >nul 2>&1

echo %GREEN%✅ Starting bot with automatic sharding...%NC%
python -m src.bot
goto cleanup

REM Manual sharding - 2 shards
:deploy_manual_2
set shard_count=2
goto deploy_manual_sharding

REM Manual sharding - custom count
:deploy_manual_custom
set /p shard_count="Enter number of shards: "
goto deploy_manual_sharding

REM Manual sharding deployment
:deploy_manual_sharding
echo %BLUE%Deploying with manual sharding ^(%shard_count% shards^)...%NC%

REM Create batch files for each shard
for /l %%i in (0,1,%shard_count%) do (
    if %%i lss %shard_count% (
        echo %BLUE%Creating shard %%i batch file...%NC%
        
        REM Create shard-specific batch file
        echo @echo off > start_shard_%%i.bat
        echo title BasslineBot Shard %%i >> start_shard_%%i.bat
        echo set SHARD_ID=%%i >> start_shard_%%i.bat
        echo set SHARD_COUNT=%shard_count% >> start_shard_%%i.bat
        echo set AUTO_SHARD=false >> start_shard_%%i.bat
        
        if %%i==0 (
            echo set DASHBOARD_ENABLED=true >> start_shard_%%i.bat
        ) else (
            echo set DASHBOARD_ENABLED=false >> start_shard_%%i.bat
        )
        
        echo echo Starting Shard %%i/%shard_count%... >> start_shard_%%i.bat
        echo python -m src.bot >> start_shard_%%i.bat
        echo pause >> start_shard_%%i.bat
    )
)

echo %GREEN%Created shard batch files!%NC%
echo.
echo %BLUE%Starting all shards...%NC%
echo Dashboard will be available at: http://localhost:%DASHBOARD_PORT%

REM Start each shard in a new window
for /l %%i in (0,1,%shard_count%) do (
    if %%i lss %shard_count% (
        echo %BLUE%▶️  Starting shard %%i...%NC%
        start "Shard %%i" start_shard_%%i.bat
        timeout /t 5 >nul
    )
)

echo %GREEN%✅ All %shard_count% shards started!%NC%
echo %BLUE%ℹ️  Check individual shard windows for status%NC%
pause
goto end

REM Docker automatic sharding
:deploy_docker_auto
echo %BLUE%Deploying with Docker automatic sharding...%NC%

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo %RED%docker-compose not found! Please install Docker Compose.%NC%
    pause
    goto show_menu
)

if not exist "docker-compose.yml" (
    echo %RED%docker-compose.yml not found!%NC%
    echo %BLUE%Please ensure you have the Docker Compose configuration file.%NC%
    pause
    goto show_menu
)

echo %BLUE%Starting infrastructure services...%NC%
docker-compose up -d db redis

echo %BLUE%Waiting for database and Redis to be ready...%NC%
timeout /t 15 >nul

echo %BLUE%Starting bot with automatic sharding...%NC%
docker-compose up -d bot-auto

echo %GREEN%Docker deployment complete!%NC%
echo %BLUE%Dashboard: http://localhost:8080%NC%
echo %BLUE%Monitor with: docker-compose logs -f bot-auto%NC%
pause
goto end

REM Docker manual sharding
:deploy_docker_manual
echo %BLUE%Deploying with Docker manual sharding...%NC%

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo %RED%docker-compose not found! Please install Docker Compose.%NC%
    pause
    goto show_menu
)

echo %BLUE%Starting infrastructure services...%NC%
docker-compose up -d db redis

echo %BLUE%Waiting for services to be ready...%NC%
timeout /t 20 >nul

echo %BLUE%Starting shard containers...%NC%
docker-compose up -d bot-shard-0 bot-shard-1

echo %GREEN%Docker manual sharding deployment complete!%NC%
echo %BLUE%Dashboard: http://localhost:8080%NC%
echo %BLUE%Monitor with: docker-compose logs -f%NC%
pause
goto end

REM Monitor deployment
:monitor_deployment
cls
echo %BLUE%Monitoring BasslineBot deployment...%NC%
echo.

REM Check if running via Docker
docker-compose ps 2>nul | findstr "basslinebot" >nul
if not errorlevel 1 (
    echo %BLUE%Docker Services:%NC%
    docker-compose ps
    echo.
    echo %BLUE%Recent logs:%NC%
    docker-compose logs --tail=20
) else (
    echo %BLUE%Manual Deployment Status:%NC%
    
    REM Check for running Python processes
    tasklist /fi "imagename eq python.exe" /fo table 2>nul | findstr "python.exe" >nul
    if not errorlevel 1 (
        echo   Python processes found - bot likely running
        tasklist /fi "imagename eq python.exe" /fo table
    ) else (
        echo   No Python processes found
    )
    
    REM Check for shard batch files
    if exist "start_shard_*.bat" (
        echo.
        echo %BLUE%Shard batch files found:%NC%
        dir start_shard_*.bat /b
    )
)

echo.
echo %BLUE%Dashboard Status:%NC%
curl -s http://localhost:%DASHBOARD_PORT%/health >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%✅ Dashboard is accessible at http://localhost:%DASHBOARD_PORT%%NC%
) else (
    echo %YELLOW%⚠️  Dashboard is not accessible%NC%
)

echo.
echo %BLUE% Database Status:%NC%
if "%DATABASE_URL%"=="" (
    echo   No database URL configured
) else (
    echo "%DATABASE_URL%" | findstr "postgresql" >nul
    if not errorlevel 1 (
        echo   Using PostgreSQL ^(recommended for sharding^)
    ) else (
        echo "%DATABASE_URL%" | findstr "sqlite" >nul
        if not errorlevel 1 (
            echo %YELLOW%  Using SQLite ^(consider PostgreSQL for production^)%NC%
        )
    )
)

echo.
echo %BLUE%Redis Status:%NC%
if not "%REDIS_URL%"=="" (
    echo   Redis configured ^(good for sharding^)
) else (
    echo %YELLOW%  Redis not configured ^(recommended for sharding^)%NC%
)

echo.
pause
goto show_menu

REM Stop all services
:stop_services
echo %BLUE%Stopping all BasslineBot services...%NC%

REM Stop Docker services
docker-compose ps 2>nul | findstr "basslinebot" >nul
if not errorlevel 1 (
    echo %BLUE%Stopping Docker services...%NC%
    docker-compose down
)

REM Stop manual shard processes
echo %BLUE%Stopping Python processes...%NC%
taskkill /f /im python.exe 2>nul

REM Clean up shard batch files
if exist "start_shard_*.bat" (
    echo %BLUE%🧹 Cleaning up shard batch files...%NC%
    del start_shard_*.bat
)

echo %GREEN%✅ All services stopped%NC%
pause
goto show_menu

REM Help information
:show_help
cls
echo %BLUE%BasslineBot Sharding Help%NC%
echo ============================
echo.
echo %PURPLE%Configuration:%NC%
echo   - Edit .env file with your Discord token and settings
echo   - Use .env.sharding as a template for sharded setups
echo.
echo %PURPLE%Deployment Options:%NC%
echo   1. Single Instance: Best for small bots ^(^<100 servers^)
echo   2. Auto Sharding: Discord automatically manages shards
echo   3. Manual Sharding: You control shard distribution
echo   4. Docker: Containerized deployment for production
echo.
echo %PURPLE%When to Use Sharding:%NC%
echo   - Bot is in 1000+ servers
echo   - Experiencing rate limits
echo   - Need better performance distribution
echo.
echo %PURPLE%Performance Tips:%NC%
echo   - Use PostgreSQL instead of SQLite
echo   - Enable Redis for caching
echo   - Monitor resource usage per shard
echo.
echo %PURPLE%Useful Commands:%NC%
echo   - View logs: docker-compose logs -f
echo   - Check status: docker-compose ps
echo   - Restart: docker-compose restart
echo.
pause
goto show_menu

REM Cleanup function
:cleanup
if exist ".env.backup" (
    echo %BLUE%Restoring original .env file...%NC%
    move .env.backup .env >nul
)
goto end

REM End of script
:end
echo.
echo %BLUE%Thank you for using BasslineBot Sharding Manager!%NC%
pause
exit /b 0