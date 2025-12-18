Param()

# Запуск dev-окружения на Windows (PowerShell): control-plane, node_service и frontend
# Использование (из корня проекта):
#   powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1

$ErrorActionPreference = 'Stop'

function Import-DotEnv {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) { return }

    Get-Content $Path |
        Where-Object { $_ -and -not ($_.TrimStart().StartsWith('#')) } |
        ForEach-Object {
            if ($_ -match '^(?<key>[^=]+)=(?<val>.*)$') {
                $key = $Matches['key'].Trim()
                $val = $Matches['val']
                [System.Environment]::SetEnvironmentVariable($key, $val)
            }
        }
}

# Путь до корня (папка выше scripts)
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Подхватываем .env и env для ноды
Import-DotEnv "$Root/.env"
Import-DotEnv "$Root/node_service/.env.node"

Write-Host "[dev] Стартуем control-plane (port 8000)..."
$cp = Start-Process python -ArgumentList '-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000' -WorkingDirectory $Root -PassThru -NoNewWindow

Write-Host "[dev] Стартуем node_service (port 9000)..."
$node = Start-Process python -ArgumentList '-m', 'uvicorn', 'node_service.app.main:app', '--reload', '--host', '0.0.0.0', '--port', '9000' -WorkingDirectory $Root -PassThru -NoNewWindow

Write-Host "[dev] Стартуем frontend (port 5173)..."
$fe = Start-Process npm -ArgumentList 'run','dev','--','--host','--port','5173' -WorkingDirectory "$Root/frontend" -PassThru -NoNewWindow

try {
    Write-Host "[dev] Все процессы запущены. Нажмите Ctrl+C для остановки."
    Wait-Process -Id $cp.Id, $node.Id, $fe.Id
}
finally {
    Write-Host "[dev] Завершаем процессы..."
    foreach ($p in @($fe, $node, $cp)) {
        if ($null -ne $p) {
            try { Stop-Process -Id $p.Id -ErrorAction SilentlyContinue } catch {}
        }
    }
}
