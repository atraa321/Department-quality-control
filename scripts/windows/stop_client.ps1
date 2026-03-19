param(
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $scriptDir)
$runtimeDir = Join-Path $root ".runtime"
$logDir = Join-Path $runtimeDir "logs"
$null = New-Item -ItemType Directory -Force -Path $logDir
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "stop_client_$ts.log"
$pidFile = Join-Path $runtimeDir "client.pid"

function Write-LogLine {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy/MM/dd HH:mm:ss"), $Message
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function Finish-Script {
    Write-Host ""
    Write-Host "处理完成。"
    Write-Host "日志文件：$logFile"
    Write-LogLine "处理完成。"
    Write-LogLine "日志文件：$logFile"
    if (-not $NoPause) {
        Read-Host "按 Enter 继续"
    }
    exit 0
}

Write-Host "================================================"
Write-Host "  科室质控平台 - 停止客户端后台运行"
Write-Host "================================================"
Write-Host ""

if (-not (Test-Path $pidFile)) {
    Write-Host "[状态] 客户端当前没有后台运行记录。"
    Write-Host "客户端未记录 PID，跳过。"
    Write-LogLine "[状态] 客户端当前没有后台运行记录。"
    Write-LogLine "客户端未记录 PID，跳过。"
    Finish-Script
}

$pidText = (Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim()
if ([string]::IsNullOrWhiteSpace($pidText)) {
    Write-Host "[状态] 客户端 PID 标记为空，已清理。"
    Write-Host "客户端 PID 为空，跳过。"
    Write-LogLine "[状态] 客户端 PID 标记为空，已清理。"
    Write-LogLine "客户端 PID 为空，跳过。"
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Finish-Script
}

$pid = 0
if (-not [int]::TryParse($pidText, [ref]$pid)) {
    Write-Host "[状态] 客户端 PID 标记无效，已清理。"
    Write-Host "客户端 PID 不是有效数字，跳过。"
    Write-LogLine "[状态] 客户端 PID 标记无效，已清理。"
    Write-LogLine "客户端 PID 不是有效数字，跳过。"
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Finish-Script
}

$process = Get-Process -Id $pid -ErrorAction SilentlyContinue
if ($null -eq $process) {
    Write-Host "[状态] 客户端进程已不存在，已清理旧标记。"
    Write-Host "客户端进程不存在，清理标记。"
    Write-LogLine "[状态] 客户端进程已不存在，已清理旧标记。"
    Write-LogLine "客户端进程不存在，清理标记。"
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Finish-Script
}

try {
    Stop-Process -Id $pid -Force -ErrorAction Stop
    Write-Host "客户端已停止，PID=$pid"
    Write-LogLine "客户端已停止，PID=$pid"
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
} catch {
    Write-Host "[错误] 客户端停止失败，PID=$pid"
    Write-Host $_.Exception.Message
    Write-LogLine "[错误] 客户端停止失败，PID=$pid"
    Write-LogLine $_.Exception.Message
    if (-not $NoPause) {
        Read-Host "按 Enter 继续"
    }
    exit 1
}

Finish-Script
