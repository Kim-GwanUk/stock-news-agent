$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot ".venv/Scripts/python.exe"
if (!(Test-Path -LiteralPath $pythonPath)) { throw "먼저 README의 설치 절차를 실행해 주세요." }
New-Item -ItemType Directory -Force "tmp" | Out-Null
$backend = Start-Process -FilePath $pythonPath -ArgumentList "-m uvicorn app.api:app --host 127.0.0.1 --port 8000" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "tmp/backend.log" -RedirectStandardError "tmp/backend-error.log"
$frontend = Start-Process -FilePath $pythonPath -ArgumentList "-m streamlit run frontend/app.py --server.address 127.0.0.1" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "tmp/frontend.log" -RedirectStandardError "tmp/frontend-error.log"
@{backend=$backend.Id;frontend=$frontend.Id} | ConvertTo-Json | Set-Content "tmp/server-pids.json"
Write-Output "화면: http://127.0.0.1:8501"
