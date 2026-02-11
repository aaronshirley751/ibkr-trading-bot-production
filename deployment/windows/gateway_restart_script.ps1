# IBKR Gateway - Daily Restart Script
# Task 4.1: Desktop Deployment
# Triggered by Windows Task Scheduler at 4:30 PM ET daily
# Purpose: Mitigate Gateway memory leak, ensure clean state for next trading day

# ============================================
# Configuration
# ============================================
$ProjectRoot = "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production"
$LogDir = "$ProjectRoot\logs"
$RestartLogFile = "$LogDir\gateway_restart_$(Get-Date -Format 'yyyyMMdd').log"

# Discord webhook URL
$DiscordWebhookUrl = $env:DISCORD_WEBHOOK_URL

# ============================================
# Logging Function
# ============================================
function Write-RestartLog {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $RestartLogFile -Value $LogMessage
}

# ============================================
# Discord Notification Function
# ============================================
function Send-DiscordNotification {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    if (-not $DiscordWebhookUrl) {
        Write-RestartLog "⚠️ Discord webhook not configured, skipping notification"
        return
    }

    $Color = switch ($Level) {
        "INFO"    { 3447003 }  # Blue
        "WARNING" { 16776960 } # Yellow
        "ERROR"   { 15158332 } # Red
        default   { 3447003 }
    }

    $Payload = @{
        embeds = @(
            @{
                title = "🔄 IBKR Gateway - Daily Restart"
                description = $Message
                color = $Color
                timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
                footer = @{
                    text = "Desktop Deployment (Task 4.1)"
                }
            }
        )
    } | ConvertTo-Json -Depth 4

    try {
        Invoke-RestMethod -Uri $DiscordWebhookUrl -Method Post -Body $Payload -ContentType "application/json" -ErrorAction Stop
        Write-RestartLog "✅ Discord notification sent successfully"
    } catch {
        Write-RestartLog "❌ Failed to send Discord notification: $_"
    }
}

# ============================================
# Main Restart Logic
# ============================================
try {
    # Create log directory if it doesn't exist
    if (-not (Test-Path $LogDir)) {
        New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    }

    Write-RestartLog "========================================="
    Write-RestartLog "🔄 IBKR Gateway Daily Restart Initiated"
    Write-RestartLog "========================================="

    # Step 1: Check if Gateway is currently running
    Write-RestartLog "Checking Gateway container status..."
    $GatewayStatus = docker inspect ibkr-gateway --format='{{.State.Status}}' 2>&1
    Write-RestartLog "Current Gateway status: $GatewayStatus"

    if ($LASTEXITCODE -ne 0) {
        $ErrorMsg = "❌ Gateway container not found or Docker not accessible"
        Write-RestartLog $ErrorMsg
        Send-DiscordNotification -Message "**RESTART FAILED**`n`n$ErrorMsg`n`nGateway may not be running." -Level "ERROR"
        exit 1
    }

    # Step 2: Capture current uptime before restart
    $UptimeSeconds = docker inspect ibkr-gateway --format='{{.State.StartedAt}}' 2>&1
    Write-RestartLog "Gateway started at: $UptimeSeconds"

    # Step 3: Send pre-restart notification
    Send-DiscordNotification -Message "**Daily Gateway Restart Starting**`n`nCurrent status: $GatewayStatus`n`nBot will automatically reconnect after restart." -Level "INFO"

    # Step 4: Restart Gateway container
    Write-RestartLog "Executing Gateway restart..."
    $RestartOutput = docker restart ibkr-gateway 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-RestartLog "✅ Gateway restart command completed successfully"
        Write-RestartLog "Restart output: $RestartOutput"
    } else {
        $ErrorMsg = "❌ Gateway restart command failed. Exit code: $LASTEXITCODE"
        Write-RestartLog $ErrorMsg
        Write-RestartLog "Error output: $RestartOutput"
        Send-DiscordNotification -Message "**RESTART FAILED**`n`n$ErrorMsg`n`nManual intervention may be required." -Level "ERROR"
        exit 1
    }

    # Step 5: Wait for Gateway to restart and become healthy
    Write-RestartLog "Waiting for Gateway to restart..."
    $MaxWaitSeconds = 120
    $WaitElapsed = 0
    $GatewayHealthy = $false

    while (-not $GatewayHealthy -and $WaitElapsed -lt $MaxWaitSeconds) {
        Start-Sleep -Seconds 5
        $WaitElapsed += 5

        $CurrentHealth = docker inspect ibkr-gateway --format='{{.State.Health.Status}}' 2>&1
        Write-RestartLog "Gateway health check ($WaitElapsed / $MaxWaitSeconds seconds): $CurrentHealth"

        if ($CurrentHealth -eq "healthy") {
            $GatewayHealthy = $true
        }
    }

    if (-not $GatewayHealthy) {
        $WarningMsg = "⚠️ Gateway did not become healthy within $MaxWaitSeconds seconds. Current status: $CurrentHealth"
        Write-RestartLog $WarningMsg
        Send-DiscordNotification -Message "**RESTART WARNING**`n`n$WarningMsg`n`nGateway may require 2FA approval or manual intervention." -Level "WARNING"
    } else {
        Write-RestartLog "✅ Gateway is healthy and ready"
    }

    # Step 6: Verify Trading Bot reconnected
    Write-RestartLog "Checking Trading Bot status..."
    Start-Sleep -Seconds 10  # Give bot time to reconnect

    $BotStatus = docker inspect trading-bot --format='{{.State.Status}}' 2>&1
    Write-RestartLog "Trading Bot status after Gateway restart: $BotStatus"

    # Step 7: Check bot logs for reconnection
    Write-RestartLog "Checking bot logs for reconnection activity..."
    $BotLogs = docker logs trading-bot --tail 20 2>&1
    Write-RestartLog "Recent bot log entries:`n$BotLogs"

    # Step 8: Send success notification
    $SuccessMsg = @"
**Gateway Restart Complete** ✅

**Post-Restart Status:**
- Gateway: $CurrentHealth
- Trading Bot: $BotStatus

**Restart Time:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss ET')

Bot reconnection verified. System operational for next trading day.
"@

    Send-DiscordNotification -Message $SuccessMsg -Level "INFO"

    Write-RestartLog "========================================="
    Write-RestartLog "✅ Gateway Daily Restart Complete"
    Write-RestartLog "========================================="

} catch {
    $ErrorMsg = "❌ Unhandled exception during Gateway restart: $_"
    Write-RestartLog $ErrorMsg
    Write-RestartLog "Stack trace: $($_.Exception.StackTrace)"
    Send-DiscordNotification -Message "**RESTART FAILED**`n`n$ErrorMsg`n`nCheck logs for stack trace." -Level "ERROR"
    exit 1
}
