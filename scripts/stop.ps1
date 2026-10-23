$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot "tmp/server-pids.json"
if (!(Test-Path -LiteralPath $pidFile)) { Write-Output "기록된 서버가 없습니다."; exit }
$servers = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($serverId in @($servers.backend, $servers.frontend)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$serverId"
    if ($process -and $process.ExecutablePath -eq (Join-Path $projectRoot ".venv\Scripts\python.exe") -and
        ($process.CommandLine -match "uvicorn app.api:app|streamlit run frontend/app.py")) {
        Stop-Process -Id $serverId
    }
}
Write-Output "프로젝트 서버를 종료했습니다."
