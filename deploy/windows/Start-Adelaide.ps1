Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$logDirectory = Join-Path $repoRoot 'deploy\logs'
$logFile = Join-Path $logDirectory 'adelaide-startup.log'

function Write-Log {
    param([string]$Message)

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $logFile -Value "$timestamp $Message"
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Set-Location $repoRoot

Write-Log 'Startup task triggered.'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI was not found in PATH.'
}

if (-not (Test-Path '.env')) {
    throw 'Missing .env file. Copy .env.example to .env and provide BOT_TOKEN and DB_TOKEN.'
}

foreach ($path in @('images', 'images\calendar', 'images\event_thumbnail')) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$dockerService = Get-Service -Name 'com.docker.service' -ErrorAction SilentlyContinue
if ($dockerService -and $dockerService.Status -ne 'Running') {
    Write-Log 'Starting com.docker.service.'
    try {
        Start-Service -Name 'com.docker.service'
    }
    catch {
        Write-Log "Could not start com.docker.service: $($_.Exception.Message)"
    }
}

$dockerReady = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
        break
    }

    Write-Log "Docker daemon not ready yet (attempt $attempt of 30)."
    Start-Sleep -Seconds 10
}

if (-not $dockerReady) {
    throw 'Docker daemon did not become ready within the retry window.'
}

Write-Log 'Running docker compose up -d --remove-orphans.'
& docker compose up -d --remove-orphans *>> $logFile

if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed with exit code $LASTEXITCODE."
}

Write-Log 'Adelaide container is up.'