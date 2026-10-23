param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop")]
    [string]$Action,
    [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$mutex = New-Object System.Threading.Mutex($false, "Local\StockProjectDockerLauncher")
$locked = $false

function Invoke-Docker {
    param([string[]]$DockerArguments, [int]$TimeoutSeconds = 15)
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $script:dockerExe
    $info.Arguments = ($DockerArguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }) -join ' '
    $info.WorkingDirectory = $projectRoot
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (!$process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            throw "Docker 응답 시간이 초과되었습니다. Docker Desktop 상태를 확인하고 다시 실행해 주세요."
        }
        return @{ Code = $process.ExitCode; Output = $stdout.Result; Error = $stderr.Result }
    } finally { $process.Dispose() }
}

function Test-Engine {
    try { return (Invoke-Docker -DockerArguments @("info", "--format", "{{.ServerVersion}}") -TimeoutSeconds 5).Code -eq 0 }
    catch { return $false }
}

try {
    $locked = $mutex.WaitOne(0)
    if (!$locked) { throw "앱 시작 또는 종료가 이미 진행 중입니다. 잠시 뒤 다시 실행해 주세요." }
    $script:dockerExe = (Get-Command docker.exe -ErrorAction Stop).Source
    $ready = Test-Engine
    if ($Action -eq "stop") {
        if (!$ready) {
            Write-Host "Docker 엔진에 연결할 수 없습니다. Docker Desktop이 종료되어 있다면 앱도 꺼져 있습니다."
            exit 0
        }
        Write-Host "주식 앱을 종료하고 있습니다. 저장된 데이터는 유지됩니다."
        $result = Invoke-Docker -DockerArguments @("compose", "-p", "stockproject", "-f", "$projectRoot\compose.yaml", "stop") -TimeoutSeconds 60
        if ($result.Code -ne 0) { throw $result.Error }
        Write-Host "주식 앱을 종료했습니다."
    } else {
        if (!$ready) {
            $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
            if (!(Test-Path -LiteralPath $desktop)) { throw "Docker Desktop 설치를 찾지 못했습니다." }
            Write-Host "Docker Desktop을 시작하고 있습니다. 잠시 기다려 주세요."
            Start-Process -FilePath $desktop -WindowStyle Hidden
            $deadline = (Get-Date).AddSeconds(120)
            do {
                Start-Sleep -Seconds 3
                $ready = Test-Engine
            } while (!$ready -and (Get-Date) -lt $deadline)
            if (!$ready) { throw "Docker가 시작되지 않았습니다. Docker Desktop 오류 화면을 확인해 주세요. 초기화 버튼은 누르지 마세요." }
        }
        # Stop only this project's recorded local servers, avoiding port conflicts.
        if (Test-Path -LiteralPath (Join-Path $projectRoot "tmp\server-pids.json")) { & (Join-Path $PSScriptRoot "stop.ps1") }
        Write-Host "주식 앱을 시작하고 있습니다."
        $result = Invoke-Docker -DockerArguments @("compose", "-p", "stockproject", "-f", "$projectRoot\compose.yaml",
            "up", "-d", "--no-build", "--wait", "--wait-timeout", "120") -TimeoutSeconds 150
        if ($result.Code -ne 0) { throw $result.Error }
        $deadline = (Get-Date).AddSeconds(30)
        $healthy = $false
        do {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8501/_stcore/health" -TimeoutSec 3
                $healthy = $response.StatusCode -eq 200
            } catch { $healthy = $false }
            if (!$healthy) { Start-Sleep -Seconds 2 }
        } while (!$healthy -and (Get-Date) -lt $deadline)
        if (!$healthy) { throw "앱 화면이 아직 응답하지 않습니다. 잠시 뒤 다시 실행해 주세요." }
        Write-Host "주식 앱이 준비되었습니다: http://127.0.0.1:8501/"
        if (!$NoBrowser) { Start-Process "http://127.0.0.1:8501/" }
    }
} catch {
    Write-Host ("실행하지 못했습니다: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
