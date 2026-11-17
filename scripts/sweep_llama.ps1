param(
    [string]$ModelPath,
    [string]$Alias = "spark",
    [string]$Configs = "99,8192,2;99,4096,1",
    [int]$TimeOut = 240
)
# Config string: ngl,ctx,parallel  ;  runs each, prints TTFT / tok/s / VRAM.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "mai_env\Scripts\python.exe"
$bench = Join-Path $env:TEMP "opencode\llm_bench.py"
$srv = Join-Path $root "tools\llama\llama-server.exe"

function Stop-Server {
    Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3
}

foreach ($cfg in $Configs.Split(";")) {
    $p = $cfg.Split(",")
    $ngl = [int]$p[0]; $ctx = [int]$p[1]; $par = [int]$p[2]
    Stop-Server
    Write-Output "=== ngl=$ngl ctx=$ctx parallel=$par ==="
    # Start-Process joins array elements without quoting, so a path with spaces
    # ("E:\rika documentation agent\...") arrives as three arguments.
    $argLine = "--model `"$ModelPath`" --alias $Alias --host 127.0.0.1 --port 8082 " +
               "--ctx-size $ctx --parallel $par --n-gpu-layers $ngl --flash-attn on " +
               "--no-webui --jinja --reasoning off"
    $proc = Start-Process -FilePath $srv -ArgumentList $argLine -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput "$env:TEMP\opencode\srv_$ngl`_$ctx`_$par.log" `
        -RedirectStandardError "$env:TEMP\opencode\srv_$ngl`_$ctx`_$par.err.log"
    try {
        # First request after load pays one-time CUDA warmup (measured 35.9s TTFT
        # vs 0.5s warm). Discard it, report the second run.
        & $py $bench --wait 2>&1 | ForEach-Object { $_.Trim() } | Out-Null
        & $py $bench 2>&1 | ForEach-Object { $_.Trim() }
    }
    catch {
        Write-Output "FAILED: $_"
    }
    finally {
        Stop-Server
    }
}
Stop-Server
Write-Output "=== sweep done ==="
