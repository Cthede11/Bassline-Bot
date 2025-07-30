# BasslineBot Sharding Startup Script for Windows PowerShell
# Run this script to deploy your bot with different sharding configurations

param(
    [string]$Action = "",
    [int]$ShardCount = 2
)

# Set console title
$Host.UI.RawUI.WindowTitle = "BasslineBot Sharding Manager"

# Color functions
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Warning { param($Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Blue }
function Write-Header { param($Message) Write-Host "`n[BASSLINEBOT] $Message" -ForegroundColor Magenta }

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check if .env file exists
    if (-not (Test-Path ".env")) {
        Write-Error ".env file not found!"
        Write-Host "`nPlease create a .env file with your configuration."
        Write-Host "You can use one of these templates:"
        Write-Host "  - .env.example (basic setup)"
        Write-Host "  - .env.sharding (sharding template)"
        exit 1
    }
    
    # Load environment variables
    Get-Content ".env" | ForEach-Object {
        if ($_ -and !$_.StartsWith('#') -and $_.Contains('=')) {
            $key, $value = $_.Split('=', 2)
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
    
    # Check Discord token
    $discordToken = [Environment]::GetEnvironmentVariable('DISCORD_TOKEN')
    if (-not $discordToken -or $discordToken.Length -lt 50) {
        Write-Error "DISCORD_TOKEN not set or invalid in .env file!"
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Show deployment menu
function Show-Menu {
    Clear-Host
    Write-Header "BasslineBot Sharding Deployment Options"
    Write-Host "==========================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "1. [SINGLE] Single Instance (No Sharding) - Simple setup"
    Write-Host "2. [AUTO] Automatic Sharding - Recommended for most users"
    Write-Host "3. [MANUAL] Manual Sharding (2 shards) - Advanced users"
    Write-Host "4. [CUSTOM] Manual Sharding (Custom) - Expert configuration"
    Write-Host "5. [DOCKER-AUTO] Docker Automatic Sharding - Production ready"
    Write-Host "6. [DOCKER-MANUAL] Docker Manual Sharding - Full control"
    Write-Host "7. [MONITOR] Monitor Existing Deployment"
    Write-Host "8. [STOP] Stop All Services"
    Write-Host "9. [HELP] Help & Information"
    Write-Host ""
    
    $choice = Read-Host "Select deployment option (1-9)"
    
    switch ($choice) {
        "1" { Deploy-Single }
        "2" { Deploy-AutoSharding }
        "3" { Deploy-ManualSharding -ShardCount 2 }
        "4" { 
            $customCount = Read-Host "Enter number of shards"
            Deploy-ManualSharding -ShardCount [int]$customCount
        }
        "5" { Deploy-DockerAuto }
        "6" { Deploy-DockerManual }
        "7" { Monitor-Deployment }
        "8" { Stop-Services }
        "9" { Show-Help }
        default { 
            Write-Error "Invalid option selected"
            Start-Sleep 2
            Show-Menu
        }
    }
}

# Single instance deployment
function Deploy-Single {
    Write-Info "Deploying single instance (no sharding)..."
    
    # Backup .env
    Copy-Item ".env" ".env.backup" -Force
    
    # Configure for single instance
    $envContent = Get-Content ".env"
    $envContent = $envContent -replace 'AUTO_SHARD=.*', 'AUTO_SHARD=false'
    $envContent = $envContent -replace 'SHARD_ID=.*', 'SHARD_ID='
    $envContent = $envContent -replace 'SHARD_COUNT=.*', 'SHARD_COUNT='
    $envContent | Set-Content ".env"
    
    Write-Success "Starting bot in single instance mode..."
    try {
        python -m src.bot
    }
    finally {
        Restore-EnvBackup
    }
}

# Automatic sharding deployment
function Deploy-AutoSharding {
    Write-Info "Deploying with automatic sharding..."
    
    # Check recommendations
    $redisUrl = [Environment]::GetEnvironmentVariable('REDIS_URL')
    $databaseUrl = [Environment]::GetEnvironmentVariable('DATABASE_URL')
    
    if (-not $redisUrl) {
        Write-Warning "Redis not configured - recommended for sharding performance"
    }
    
    if ($databaseUrl -like "*sqlite*") {
        Write-Warning "Using SQLite - consider PostgreSQL for production sharding"
    }
    
    # Backup and configure
    Copy-Item ".env" ".env.backup" -Force
    
    $envContent = Get-Content ".env"
    $envContent = $envContent -replace 'AUTO_SHARD=.*', 'AUTO_SHARD=true'
    $envContent = $envContent -replace 'SHARD_ID=.*', 'SHARD_ID='
    $envContent = $envContent -replace 'SHARD_COUNT=.*', 'SHARD_COUNT='
    $envContent | Set-Content ".env"
    
    Write-Success "Starting bot with automatic sharding..."
    try {
        python -m src.bot
    }
    finally {
        Restore-EnvBackup
    }
}

# Manual sharding deployment
function Deploy-ManualSharding {
    param([int]$ShardCount)
    
    Write-Info "Deploying with manual sharding ($ShardCount shards)..."
    
    # Create PowerShell scripts for each shard
    for ($i = 0; $i -lt $ShardCount; $i++) {
        $scriptName = "start_shard_$i.ps1"
        
        $dashboardEnabled = if ($i -eq 0) { "true" } else { "false" }
        $dashboardText = if ($i -eq 0) { "Enabled" } else { "Disabled" }
        
        $scriptContent = @"
# Shard $i Startup Script
`$Host.UI.RawUI.WindowTitle = "BasslineBot Shard $i"

Write-Host "[START] Starting Shard $i/$ShardCount..." -ForegroundColor Green

# Set shard environment variables
`$env:SHARD_ID = "$i"
`$env:SHARD_COUNT = "$ShardCount"
`$env:AUTO_SHARD = "false"
`$env:DASHBOARD_ENABLED = "$dashboardEnabled"

# Load additional environment variables from .env
Get-Content ".env" | ForEach-Object {
    if (`$_ -and !`$_.StartsWith('#') -and `$_.Contains('=')) {
        `$key, `$value = `$_.Split('=', 2)
        [Environment]::SetEnvironmentVariable(`$key, `$value, 'Process')
    }
}

Write-Host "[CONFIG] Shard $i configuration:" -ForegroundColor Blue
Write-Host "  SHARD_ID: $i"
Write-Host "  SHARD_COUNT: $ShardCount"
Write-Host "  DASHBOARD: $dashboardText"
Write-Host ""

# Start the bot
try {
    python -m src.bot
}
catch {
    Write-Host "[ERROR] Error starting shard $i`: `$_" -ForegroundColor Red
}
finally {
    Write-Host "[STOP] Shard $i stopped. Press any key to close..." -ForegroundColor Yellow
    `$null = `$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
"@
        
        $scriptContent | Set-Content $scriptName
        Write-Info "Created $scriptName"
    }
    
    Write-Success "Created all shard scripts!"
    Write-Info "Starting all shards..."
    
    # Start each shard in a new PowerShell window
    for ($i = 0; $i -lt $ShardCount; $i++) {
        $scriptName = "start_shard_$i.ps1"
        Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptName`""
        Write-Info "Started shard $i"
        Start-Sleep 3  # Delay between shard starts
    }
    
    $dashboardPort = [Environment]::GetEnvironmentVariable('DASHBOARD_PORT')
    if (-not $dashboardPort) { $dashboardPort = "8080" }
    
    Write-Success "All $ShardCount shards started!"
    Write-Info "Dashboard available at: http://localhost:$dashboardPort"
    Write-Host "Check individual shard windows for status"
    
    Read-Host "Press Enter to continue"
}

# Docker automatic sharding
function Deploy-DockerAuto {
    Write-Info "Deploying with Docker automatic sharding..."
    
    # Check if docker-compose is available
    try {
        docker-compose --version | Out-Null
    }
    catch {
        Write-Error "docker-compose not found! Please install Docker Compose."
        return
    }
    
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Error "docker-compose.yml not found!"
        Write-Info "Please ensure you have the Docker Compose configuration file."
        return
    }
    
    Write-Info "Starting infrastructure services..."
    docker-compose up -d db redis
    
    Write-Info "Waiting for database and Redis to be ready..."
    Start-Sleep 15
    
    Write-Info "Starting bot with automatic sharding..."
    docker-compose up -d bot-auto
    
    Write-Success "Docker deployment complete!"
    Write-Info "Dashboard: http://localhost:8080"
    Write-Info "Monitor with: docker-compose logs -f bot-auto"
    
    Read-Host "Press Enter to continue"
}

# Docker manual sharding
function Deploy-DockerManual {
    Write-Info "Deploying with Docker manual sharding..."
    
    try {
        docker-compose --version | Out-Null
    }
    catch {
        Write-Error "docker-compose not found! Please install Docker Compose."
        return
    }
    
    Write-Info "Starting infrastructure services..."
    docker-compose up -d db redis
    
    Write-Info "Waiting for services to be ready..."
    Start-Sleep 20
    
    Write-Info "Starting shard containers..."
    docker-compose up -d bot-shard-0 bot-shard-1
    
    Write-Success "Docker manual sharding deployment complete!"
    Write-Info "Dashboard: http://localhost:8080"
    Write-Info "Monitor with: docker-compose logs -f"
    
    Read-Host "Press Enter to continue"
}

# Monitor deployment
function Monitor-Deployment {
    Clear-Host
    Write-Header "BasslineBot Deployment Status"
    
    # Check Docker services
    try {
        $dockerServices = docker-compose ps 2>$null
        if ($dockerServices -match "basslinebot") {
            Write-Host "[DOCKER] Docker Services:" -ForegroundColor Blue
            docker-compose ps
            Write-Host ""
            Write-Host "[LOGS] Recent logs:" -ForegroundColor Blue
            docker-compose logs --tail=20
        }
    }
    catch {
        Write-Host "[MANUAL] Manual Deployment Status:" -ForegroundColor Blue
        
        # Check for Python processes
        $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
        if ($pythonProcesses) {
            Write-Host "  Python processes found - bot likely running"
            $pythonProcesses | Format-Table Id, ProcessName, WorkingSet -AutoSize
        }
        else {
            Write-Host "  No Python processes found"
        }
        
        # Check for shard scripts
        $shardScripts = Get-ChildItem "start_shard_*.ps1" -ErrorAction SilentlyContinue
        if ($shardScripts) {
            Write-Host ""
            Write-Host "[SHARDS] Shard scripts found:" -ForegroundColor Blue
            $shardScripts | ForEach-Object { Write-Host "  $($_.Name)" }
        }
    }
    
    Write-Host ""
    Write-Host "[DASHBOARD] Dashboard Status:" -ForegroundColor Blue
    $dashboardPort = [Environment]::GetEnvironmentVariable('DASHBOARD_PORT')
    if (-not $dashboardPort) { $dashboardPort = "8080" }
    
    try {
        $response = Invoke-WebRequest "http://localhost:$dashboardPort/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Success "Dashboard is accessible at http://localhost:$dashboardPort"
    }
    catch {
        Write-Warning "Dashboard is not accessible"
    }
    
    Write-Host ""
    Write-Host "[DATABASE] Database Status:" -ForegroundColor Blue
    $databaseUrl = [Environment]::GetEnvironmentVariable('DATABASE_URL')
    if ($databaseUrl) {
        if ($databaseUrl -like "*postgresql*") {
            Write-Host "  Using PostgreSQL (recommended for sharding)"
        }
        elseif ($databaseUrl -like "*sqlite*") {
            Write-Warning "Using SQLite (consider PostgreSQL for production)"
        }
    }
    else {
        Write-Host "  No database URL configured"
    }
    
    Write-Host ""
    Write-Host "[REDIS] Redis Status:" -ForegroundColor Blue
    $redisUrl = [Environment]::GetEnvironmentVariable('REDIS_URL')
    if ($redisUrl) {
        Write-Host "  Redis configured (good for sharding)"
    }
    else {
        Write-Warning "Redis not configured (recommended for sharding)"
    }
    
    Write-Host ""
    Read-Host "Press Enter to continue"
}

# Stop all services
function Stop-Services {
    Write-Info "Stopping all BasslineBot services..."
    
    # Stop Docker services
    try {
        $dockerServices = docker-compose ps 2>$null
        if ($dockerServices -match "basslinebot") {
            Write-Info "Stopping Docker services..."
            docker-compose down
        }
    }
    catch { }
    
    # Stop Python processes
    Write-Info "Stopping Python processes..."
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Clean up shard scripts
    $shardScripts = Get-ChildItem "start_shard_*.ps1" -ErrorAction SilentlyContinue
    if ($shardScripts) {
        Write-Info "Cleaning up shard scripts..."
        $shardScripts | Remove-Item -Force
    }
    
    Write-Success "All services stopped"
    Read-Host "Press Enter to continue"
}

# Show help
function Show-Help {
    Clear-Host
    Write-Header "BasslineBot Sharding Help"
    Write-Host "============================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "[CONFIG] Configuration:" -ForegroundColor Cyan
    Write-Host "  - Edit .env file with your Discord token and settings"
    Write-Host "  - Use .env.sharding as a template for sharded setups"
    Write-Host ""
    Write-Host "[DEPLOY] Deployment Options:" -ForegroundColor Cyan
    Write-Host "  1. Single Instance: Best for small bots (<100 servers)"
    Write-Host "  2. Auto Sharding: Discord automatically manages shards"
    Write-Host "  3. Manual Sharding: You control shard distribution"
    Write-Host "  4. Docker: Containerized deployment for production"
    Write-Host ""
    Write-Host "[WHEN] When to Use Sharding:" -ForegroundColor Cyan
    Write-Host "  - Bot is in 1000+ servers"
    Write-Host "  - Experiencing rate limits"
    Write-Host "  - Need better performance distribution"
    Write-Host ""
    Write-Host "[TIPS] Performance Tips:" -ForegroundColor Cyan
    Write-Host "  - Use PostgreSQL instead of SQLite"
    Write-Host "  - Enable Redis for caching"
    Write-Host "  - Monitor resource usage per shard"
    Write-Host ""
    Write-Host "[COMMANDS] Useful Commands:" -ForegroundColor Cyan
    Write-Host "  - View logs: docker-compose logs -f"
    Write-Host "  - Check status: docker-compose ps"
    Write-Host "  - Restart: docker-compose restart"
    Write-Host ""
    Write-Host "[CLI] Command Line Usage:" -ForegroundColor Cyan
    Write-Host "  .\scripts\sharding_startup.ps1 single          # Single instance"
    Write-Host "  .\scripts\sharding_startup.ps1 auto            # Automatic sharding"
    Write-Host "  .\scripts\sharding_startup.ps1 manual 4        # Manual with 4 shards"
    Write-Host "  .\scripts\sharding_startup.ps1 docker-auto     # Docker auto sharding"
    Write-Host "  .\scripts\sharding_startup.ps1 monitor         # Monitor deployment"
    Write-Host "  .\scripts\sharding_startup.ps1 stop            # Stop all services"
    Write-Host ""
    
    Read-Host "Press Enter to continue"
}

# Restore .env backup
function Restore-EnvBackup {
    if (Test-Path ".env.backup") {
        Write-Info "Restoring original .env file..."
        Move-Item ".env.backup" ".env" -Force
    }
}

# Main script logic
function Main {
    Write-Header "BasslineBot Sharding Manager"
    Write-Host "==============================" -ForegroundColor Magenta
    
    # Check prerequisites
    Test-Prerequisites
    
    # Handle command line arguments
    if ($Action) {
        switch ($Action.ToLower()) {
            "single" { Deploy-Single }
            "auto" { Deploy-AutoSharding }
            "manual" { Deploy-ManualSharding -ShardCount $ShardCount }
            "docker-auto" { Deploy-DockerAuto }
            "docker-manual" { Deploy-DockerManual }
            "monitor" { Monitor-Deployment }
            "stop" { Stop-Services }
            "help" { Show-Help }
            default {
                Write-Error "Unknown action: $Action"
                Write-Host "Usage: .\scripts\sharding_startup.ps1 [single|auto|manual|docker-auto|docker-manual|monitor|stop|help] [shard_count]"
                exit 1
            }
        }
    }
    else {
        # Show interactive menu
        do {
            Show-Menu
        } while ($true)
    }
}

# Set execution policy for this session if needed
try {
    if ((Get-ExecutionPolicy) -eq 'Restricted') {
        Write-Warning "PowerShell execution policy is restricted. Setting to RemoteSigned for this session..."
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
    }
}
catch {
    Write-Warning "Could not change execution policy. You may need to run as administrator."
}

# Run main function
try {
    Main
}
catch {
    Write-Error "An error occurred: $_"
    Read-Host "Press Enter to exit"
}
finally {
    Restore-EnvBackup
}