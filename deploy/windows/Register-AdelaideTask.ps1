param(
    [string]$TaskName = 'Adelaide Docker Startup',
    [ValidateSet('Startup', 'Logon')]
    [string]$TriggerMode = 'Startup',
    [string]$User = "$env:COMPUTERNAME\$env:USERNAME"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalContext = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principalContext.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell session.'
}

$scriptPath = Join-Path $PSScriptRoot 'Start-Adelaide.ps1'
if (-not (Test-Path $scriptPath)) {
    throw "Startup script was not found at $scriptPath."
}

$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments

if ($TriggerMode -eq 'Startup') {
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
}
else {
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $User
    $principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Highest
}

$settings = New-ScheduledTaskSettingsSet \
    -AllowStartIfOnBatteries \
    -DontStopIfGoingOnBatteries \
    -MultipleInstances IgnoreNew \
    -StartWhenAvailable

Register-ScheduledTask \
    -TaskName $TaskName \
    -Action $action \
    -Trigger $trigger \
    -Principal $principal \
    -Settings $settings \
    -Force | Out-Null

Write-Host "Task '$TaskName' registered with trigger mode '$TriggerMode'."