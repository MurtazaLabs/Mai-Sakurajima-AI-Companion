<#
  Mai-owned llama.cpp server (OpenAI-compatible /v1).

  Port 8082: 8080/8081 belong to another project on this machine, and Mai must
  not depend on that instance restarting on someone else's schedule.

  --parallel 2: Mai also calls the LLM from background threads (dream tasks,
  relationship, cognition, extractors). With --parallel 1 a dream task queues in
  front of a voice reply. llama.cpp divides --ctx-size across slots, so 8192
  total = 4096 per slot.

  -NGpuLayers is the VRAM/CPU split. Measured here with a 4B Q4_K_M (Spark, then
  Qwen3-4B-Instruct-2507): ngl 99 (full offload) = 3,135-3,673 MiB, 0.27-0.40 s
  TTFT, 22.1-28.5 tok/s; ngl 20 = 1,864 MiB, 0.92 s, 4.4 tok/s. Full offload wins
  5x on a 4B, so 99 is the default.
  Plan: docs/Mai_documentation/03-Features/llamacpp-local-llm-plan.md

  Usage:
    .\scripts\run_llama_server.ps1 -DryRun
    .\scripts\run_llama_server.ps1                 # foreground, logs on stdout
    .\scripts\run_llama_server.ps1 -Detach         # background, logs/llama-server.log
#>
param(
    [string]$ModelPath = "",
    [int]$Port = 8082,
    [int]$Ctx = 8192,
    [int]$Parallel = 2,
    [int]$NGpuLayers = 99,
    [string]$Alias = "qwen3-4b",
    [string]$BinDir = "",
    [switch]$DryRun,
    # Foreground dies with its terminal. Mai needs this server for every reply,
    # so -Detach is what you want for daily use.
    [switch]$Detach
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $BinDir) { $BinDir = Join-Path $root "tools\llama" }
if (-not $ModelPath) { $ModelPath = Join-Path $root "models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf" }

$exe = Join-Path $BinDir "llama-server.exe"
$serverArgs = @(
    "--model", $ModelPath,
    "--alias", $Alias,
    "--host", "127.0.0.1",
    "--port", "$Port",
    "--ctx-size", "$Ctx",
    "--parallel", "$Parallel",
    "--n-gpu-layers", "$NGpuLayers",
    "--flash-attn", "on",
    "--no-webui",
    "--jinja",
    # Qwen3-4B-Instruct-2507 has no thinking mode, but --reasoning off costs
    # nothing and keeps a thinking template from adding seconds per voice turn.
    "--reasoning", "off"
)

if ($DryRun) {
    "exe:  $exe"
    "args: " + ($serverArgs -join " ")
    if (-not (Test-Path $exe)) { "MISSING: llama-server.exe (install a llama.cpp release into $BinDir)" }
    if (-not (Test-Path $ModelPath)) { "MISSING: model ($ModelPath)" }
    return
}

if (-not (Test-Path $exe)) { throw "llama-server.exe not found at $exe" }
if (-not (Test-Path $ModelPath)) { throw "model not found at $ModelPath" }

Write-Host "Starting llama-server on http://127.0.0.1:$Port (ctx $Ctx, parallel $Parallel, ngl $NGpuLayers)"

if ($Detach) {
    $logDir = Join-Path $root "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $log = Join-Path $logDir "llama-server.log"
    # Start-Process joins array elements without quoting, so a path with spaces
    # would arrive as several arguments.
    $argLine = ($serverArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
    Start-Process -FilePath $exe -ArgumentList $argLine -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" | Out-Null
    for ($i = 0; $i -lt 90; $i++) {
        try {
            Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
            Write-Host "healthy on :$Port (pid(s): $((Get-Process llama-server -ErrorAction SilentlyContinue).Id -join ',')) - log: $log"
            return
        } catch { Start-Sleep -Seconds 1 }
    }
    throw "llama-server did not become healthy on :$Port within 90s - see $log"
}

& $exe @serverArgs
