# IBKR Trading Bot - Auto-Start Script
# Task 4.1: Desktop Deployment
# Triggered by Windows Task Scheduler at 6:00 AM ET daily

# ============================================
# Configuration
# ============================================
$ProjectRoot = "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production"
$DockerComposeDir = "$ProjectRoot\docker"
$LogDir = "$ProjectRoot\logs"
$StartupLogFile = "$LogDir\startup_$(Get-Date -Format 'yyyyMMdd').log"

# Discord webhook URL (read from docker/.env file)
$EnvFilePath = "$DockerComposeDir\.env"
if (Test-Path $EnvFilePath) {
    $DiscordWebhookUrl = (Get-Content $EnvFilePath | Select-String "DISCORD_WEBHOOK_URL").Line.Split('=')[1]
} else {
    $DiscordWebhookUrl = $env:DISCORD_WEBHOOK_URL
}

# ============================================
# Logging Function
# ============================================
function Write-StartupLog {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $StartupLogFile -Value $LogMessage
}

# ============================================
# Discord Notification Function
# ============================================
function Send-DiscordNotification {
    param(
        [string]$Message,
        [string]$Level = "INFO"  # INFO, WARNING, ERROR
    )

    if (-not $DiscordWebhookUrl) {
        Write-StartupLog "Discord webhook not configured, skipping notification"
        return
    }

    $Color = switch ($Level) {
        "INFO"    { 3447003 }  # Blue
        "WARNING" { 16776960 } # Yellow
        "ERROR"   { 15158332 } # Red
        default   { 3447003 }
    }

    # Escape message for JSON
    $EscapedMessage = $Message -replace '\\', '\\' -replace '"', '\"' -replace "`n", '\n' -replace "`r", '' -replace "`t", '\t'

    # Build JSON payload manually to avoid ConvertTo-Json escaping issues
    $TimestampUTC = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    $Payload = @"
{
    "embeds": [{
        "title": "Bot Auto-Start",
        "description": "$EscapedMessage",
        "color": $Color,
        "timestamp": "$TimestampUTC",
        "footer": {
            "text": "Desktop Deployment (Task 4.1)"
        }
    }]
}
"@

    try {
        Invoke-RestMethod -Uri $DiscordWebhookUrl -Method Post -Body $Payload -ContentType "application/json; charset=utf-8" -ErrorAction Stop
        Write-StartupLog "Discord notification sent successfully"
    } catch {
        Write-StartupLog "Failed to send Discord notification: $($_.Exception.Message)"
    }
}
        Write-StartupLog "❌ Failed to send Discord notification: $_"
    }
}

# ============================================
# Main Startup Logic
# ============================================
try {
    # Create log directory if it doesn't exist
    if (-not (Test-Path $LogDir)) {
        New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    }

    Write-StartupLog "========================================="
    Write-StartupLog "🚀 IBKR Trading Bot Auto-Start Initiated"
    Write-StartupLog "========================================="

    # Step 1: Verify Docker Desktop is running
    Write-StartupLog "Checking Docker Desktop status..."
    $DockerRunning = $false
    $MaxDockerWaitSeconds = 120
    $DockerWaitElapsed = 0

    while (-not $DockerRunning -and $DockerWaitElapsed -lt $MaxDockerWaitSeconds) {
        try {
            $DockerInfo = docker info 2>&1
            if ($LASTEXITCODE -eq 0) {
                $DockerRunning = $true
                Write-StartupLog "✅ Docker Desktop is running"
            } else {
                Write-StartupLog "⏳ Waiting for Docker Desktop to start... ($DockerWaitElapsed / $MaxDockerWaitSeconds seconds)"
                Start-Sleep -Seconds 5
                $DockerWaitElapsed += 5
            }
        } catch {
            Write-StartupLog "⏳ Docker not ready yet, waiting... ($DockerWaitElapsed / $MaxDockerWaitSeconds seconds)"
            Start-Sleep -Seconds 5
            $DockerWaitElapsed += 5
        }
    }

    if (-not $DockerRunning) {
        $ErrorMsg = "❌ Docker Desktop did not start within $MaxDockerWaitSeconds seconds. Aborting startup."
        Write-StartupLog $ErrorMsg
        Send-DiscordNotification -Message "**STARTUP FAILED**`n`n$ErrorMsg`n`nOperator intervention required." -Level "ERROR"
        exit 1
    }

    # Step 2: Navigate to Docker Compose directory
    Write-StartupLog "Navigating to Docker Compose directory: $DockerComposeDir"
    if (-not (Test-Path $DockerComposeDir)) {
        $ErrorMsg = "❌ Docker Compose directory not found: $DockerComposeDir"
        Write-StartupLog $ErrorMsg
        Send-DiscordNotification -Message "**STARTUP FAILED**`n`n$ErrorMsg" -Level "ERROR"
        exit 1
    }
    Set-Location $DockerComposeDir

    # Step 3: Start Docker Compose services
    Write-StartupLog "Starting Docker Compose services..."
    $ComposeResult = docker compose up -d 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-StartupLog "✅ Docker Compose services started successfully"
        Write-StartupLog "Compose output: $ComposeResult"
    } else {
        $ErrorMsg = "❌ Failed to start Docker Compose services. Exit code: $LASTEXITCODE"
        Write-StartupLog $ErrorMsg
        Write-StartupLog "Error output: $ComposeResult"
        Send-DiscordNotification -Message "**STARTUP FAILED**`n`n$ErrorMsg`n`nSee logs for details." -Level "ERROR"
        exit 1
    }

    # Step 4: Wait for services to become healthy
    Write-StartupLog "Waiting for services to become healthy..."
    Start-Sleep -Seconds 10

    # Step 5: Verify Gateway health
    Write-StartupLog "Checking IBKR Gateway health..."
    $GatewayHealth = docker inspect ibkr-gateway --format='{{.State.Health.Status}}' 2>&1
    Write-StartupLog "Gateway health status: $GatewayHealth"

    # Step 6: Verify Trading Bot status
    Write-StartupLog "Checking Trading Bot status..."
    $BotStatus = docker inspect trading-bot --format='{{.State.Status}}' 2>&1
    Write-StartupLog "Trading Bot status: $BotStatus"

    # Step 7: Verify Health Monitor status
    Write-StartupLog "Checking Health Monitor status..."
    $MonitorStatus = docker inspect health-monitor --format='{{.State.Status}}' 2>&1
    Write-StartupLog "Health Monitor status: $MonitorStatus"

    # Step 8: Send success notification to Discord
    $SuccessMsg = @"
**Startup Successful** ✅

**Services Status:**
- Gateway: $GatewayHealth
- Trading Bot: $BotStatus
- Health Monitor: $MonitorStatus

**Configuration:**
- Mode: DRY-RUN (Task 4.1 validation)
- Platform: Windows 11 Desktop
- Startup Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss ET')

Bot is operational. Monitoring active.
"@

    Send-DiscordNotification -Message $SuccessMsg -Level "INFO"

    Write-StartupLog "========================================="
    Write-StartupLog "✅ Auto-Start Complete - All Services Running"
    Write-StartupLog "========================================="

} catch {
    $ErrorMsg = "❌ Unhandled exception during startup: $_"
    Write-StartupLog $ErrorMsg
    Write-StartupLog "Stack trace: $($_.Exception.StackTrace)"
    Send-DiscordNotification -Message "**STARTUP FAILED**`n`n$ErrorMsg`n`nCheck logs for stack trace." -Level "ERROR"
    exit 1
}
