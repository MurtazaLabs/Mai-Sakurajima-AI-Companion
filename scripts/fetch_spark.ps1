param(
    [string]$Url = "https://huggingface.co/qikuanz/Spark-X2.5-4B/resolve/main/Spark-X2.5-4B-Q4_K_M.gguf",
    [string]$Out = "E:\Mai_ai\models\Spark-X2.5-4B-Q4_K_M.gguf",
    [long]$Total = 2600224352,
    [int]$ChunkMB = 32,
    [int]$Workers = 6,
    [string]$Expect = "adfcfa19a4ed6a5985da8bf565fe15f8e1a7e131d79bae2d19d48d1c40109428"
)
# Chunks go to separate .part files: no shared-seek writer (that bug silently
# left 110 zero blocks last time) and each file's size is self-verifying.
# Rerunning resumes — complete .part files are skipped.
$ErrorActionPreference = "Stop"
$dir = Join-Path (Split-Path -Parent $Out) "spark_parts"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$chunk = [long]$ChunkMB * 1MB
$count = [int][math]::Ceiling($Total / $chunk)

function Part-Path([int]$i) { Join-Path $dir ("{0:d3}.part" -f $i) }
function Part-Want([int]$i) {
    $start = [long]$i * $chunk
    [math]::Min($chunk, $Total - $start)
}
function Part-Ok([int]$i) {
    $p = Part-Path $i
    (Test-Path $p) -and ((Get-Item $p).Length -eq (Part-Want $i))
}

$todo = @(0..($count - 1) | Where-Object { -not (Part-Ok $_) })
Write-Output ("chunks: {0} total, {1} to fetch (~{2} MB)" -f $count, $todo.Count, [math]::Round($todo.Count * $chunk / 1MB))

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$failed = @()
for ($b = 0; $b -lt $todo.Count; $b += $Workers) {
    $batch = $todo[$b..([math]::Min($b + $Workers - 1, $todo.Count - 1))]
    $procs = @()
    foreach ($i in $batch) {
        $start = [long]$i * $chunk
        $end = $start + (Part-Want $i) - 1
        $procs += Start-Process -FilePath "curl.exe" -PassThru -WindowStyle Hidden -ArgumentList @(
            "-s", "-L", "--fail", "--max-time", "1200", "-r", "$start-$end",
            "-o", (Part-Path $i), $Url
        )
    }
    $procs | Wait-Process -Timeout 1300 -ErrorAction SilentlyContinue
    # A timed-out curl still holds its .part file; killing it first keeps the
    # retry below from writing the same path from two processes.
    $procs | Where-Object { -not $_.HasExited } | Stop-Process -Force -ErrorAction SilentlyContinue

    foreach ($i in $batch) {
        for ($try = 1; $try -le 3 -and -not (Part-Ok $i); $try++) {
            $start = [long]$i * $chunk
            $end = $start + (Part-Want $i) - 1
            & curl.exe -s -L --fail --max-time 1200 -r "$start-$end" -o (Part-Path $i) $Url
            if (-not (Part-Ok $i)) { Start-Sleep -Seconds (3 * $try) }
        }
        if (-not (Part-Ok $i)) { $failed += $i }
    }

    $done = (Get-ChildItem $dir -Filter *.part | Measure-Object -Property Length -Sum).Sum
    Write-Output ("  {0:N0}/{1:N0} MB  ({2:N0}s)" -f ($done / 1MB), ($Total / 1MB), $sw.Elapsed.TotalSeconds)
}

if ($failed.Count) { Write-Output ("FAILED chunks: " + ($failed -join ",")); exit 1 }

Write-Output "assembling ..."
$fs = [System.IO.File]::Create($Out)
try {
    for ($i = 0; $i -lt $count; $i++) {
        $bytes = [System.IO.File]::ReadAllBytes((Part-Path $i))
        $fs.Write($bytes, 0, $bytes.Length)
    }
} finally { $fs.Dispose() }

$size = (Get-Item $Out).Length
$h = (Get-FileHash $Out -Algorithm SHA256).Hash.ToLower()
Write-Output ("assembled {0:N0} bytes (expected {1:N0})" -f $size, $Total)
Write-Output ("sha256: " + $h)
if ($size -eq $Total -and $h -eq $Expect) {
    Remove-Item $dir -Recurse -Force
    Write-Output "MATCH - download verified, parts cleaned up"
} else {
    Write-Output ("MISMATCH - parts kept in " + $dir)
    exit 1
}
