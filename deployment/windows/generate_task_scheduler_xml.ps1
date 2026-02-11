# Generate Task Scheduler XML Files with Correct User Credentials
# This script creates task_scheduler_startup.xml and task_scheduler_gateway_restart.xml
# with the current user's SID for Microsoft account compatibility
#
# Usage: Run this script before importing tasks into Task Scheduler
#        PowerShell.exe -ExecutionPolicy Bypass -File generate_task_scheduler_xml.ps1

# Get current user information
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$UserSID = $CurrentUser.User.Value
$UserName = $CurrentUser.Name
$ComputerName = $env:COMPUTERNAME

# Check if running as Administrator
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Task Scheduler XML Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Current User: $UserName" -ForegroundColor Green
Write-Host "User SID: $UserSID" -ForegroundColor Green
Write-Host "Computer: $ComputerName" -ForegroundColor Green
Write-Host "Running as Admin: $IsAdmin" -ForegroundColor $(if ($IsAdmin) {"Green"} else {"Yellow"})
Write-Host ""

if (-not $IsAdmin) {
    Write-Host "[WARNING] Not running as Administrator. Task import may fail." -ForegroundColor Yellow
    Write-Host "   Recommended: Right-click PowerShell -> 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
}

# Get project root directory (assuming script is in deployment/windows/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Green
Write-Host ""

# Check if Microsoft account
$LocalUser = Get-LocalUser -Name $env:USERNAME -ErrorAction SilentlyContinue
if ($LocalUser -and $LocalUser.PrincipalSource -eq "MicrosoftAccount") {
    Write-Host "[OK] Microsoft Account detected - using SID format for compatibility" -ForegroundColor Green
    $UserIdentifier = $UserSID
    # Microsoft accounts work better with InteractiveToken (Run only when user is logged on)
    $LogonType = "InteractiveToken"
    Write-Host "     Using LogonType: InteractiveToken (no password required)" -ForegroundColor Gray
} else {
    Write-Host "[OK] Local Account detected - using username format" -ForegroundColor Green
    $UserIdentifier = $UserName
    # Local accounts can use Password (Run whether user is logged on or not)
    $LogonType = "Password"
    Write-Host "     Using LogonType: Password (will prompt for credentials)" -ForegroundColor Gray
}
Write-Host ""

# Template for Auto-Start task
$AutoStartXML = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>$((Get-Date).ToString("yyyy-MM-ddTHH:mm:ss"))</Date>
    <Author>$UserName</Author>
    <Description>Launches IBKR Trading Bot Docker Compose stack at 6:00 AM ET daily for automated trading operations.</Description>
    <URI>\IBKR Trading Bot - Auto-Start</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$((Get-Date).AddDays(1).ToString("yyyy-MM-dd"))T06:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$UserIdentifier</UserId>
      <LogonType>$LogonType</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>4</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>PowerShell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -File "$ProjectRoot\deployment\windows\startup_script.ps1"</Arguments>
      <WorkingDirectory>$ProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Template for Gateway Restart task
$GatewayRestartXML = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>$((Get-Date).ToString("yyyy-MM-ddTHH:mm:ss"))</Date>
    <Author>$UserName</Author>
    <Description>Restarts IBKR Gateway container at 4:30 PM ET daily to mitigate memory leaks and ensure clean state for next trading day.</Description>
    <URI>\IBKR Gateway - Daily Restart</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$((Get-Date).ToString("yyyy-MM-dd"))T16:30:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$UserIdentifier</UserId>
      <LogonType>$LogonType</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>4</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>PowerShell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -File "$ProjectRoot\deployment\windows\gateway_restart_script.ps1"</Arguments>
      <WorkingDirectory>$ProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Save XML files
$AutoStartPath = Join-Path $ScriptDir "task_scheduler_startup.xml"
$GatewayRestartPath = Join-Path $ScriptDir "task_scheduler_gateway_restart.xml"

try {
    $AutoStartXML | Out-File -FilePath $AutoStartPath -Encoding unicode -Force
    Write-Host "[OK] Created: task_scheduler_startup.xml" -ForegroundColor Green

    $GatewayRestartXML | Out-File -FilePath $GatewayRestartPath -Encoding unicode -Force
    Write-Host "[OK] Created: task_scheduler_gateway_restart.xml" -ForegroundColor Green

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[SUCCESS] XML files generated successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Open Task Scheduler: taskschd.msc" -ForegroundColor White
    Write-Host "2. Import task_scheduler_startup.xml" -ForegroundColor White
    Write-Host "3. Import task_scheduler_gateway_restart.xml" -ForegroundColor White
    Write-Host "4. Enter your Windows password when prompted" -ForegroundColor White
    Write-Host ""
    Write-Host "Files saved to: $ScriptDir" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "[ERROR] Error creating XML files: $_" -ForegroundColor Red
    exit 1
}
