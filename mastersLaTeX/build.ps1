# build.ps1 -- Perl-free build of the thesis (pdflatex + biber, MiKTeX on Windows).
#   .\build.ps1            full build (3 pdflatex passes + biber)
#   .\build.ps1 -Quick     single pdflatex pass, for fast iteration
param([switch]$Quick)

$ErrorActionPreference = "Continue"
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path out)) { New-Item -ItemType Directory out | Out-Null }

$flags = @("-interaction=nonstopmode", "-file-line-error", "-synctex=1",
           "-output-directory=out", "-aux-directory=out", "main.tex")

function Invoke-Pass([string]$label) {
    Write-Output "--- pdflatex ($label) ---"
    & pdflatex @flags | Out-Null
}

Invoke-Pass "1"
if (-not $Quick) {
    Write-Output "--- biber ---"
    & biber --input-directory=out --output-directory=out main | Select-Object -Last 6
    Invoke-Pass "2"
    Invoke-Pass "3"
}

Write-Output ""
Write-Output "=== ERRORS ==="
$log = "out\main.log"
if (Test-Path $log) {
    $errs = Select-String -Path $log -Pattern '^(.*):(\d+): |^! ' | Select-Object -First 30
    if ($errs) { $errs | ForEach-Object { $_.Line } } else { Write-Output "(none)" }
    Write-Output ""
    Write-Output "=== UNDEFINED REFS / CITATIONS ==="
    $w = Select-String -Path $log -Pattern 'Citation .* undefined|Reference .* undefined|There were undefined' |
         Select-Object -First 20
    if ($w) { $w | ForEach-Object { $_.Line.Trim() } } else { Write-Output "(none)" }
    Write-Output ""
    Select-String -Path $log -Pattern 'Output written' | ForEach-Object { $_.Line.Trim() }
    $ob = Select-String -Path $log -Pattern 'Overfull \\hbox' | Measure-Object
    Write-Output "Overfull hboxes: $($ob.Count)"
}
if (Test-Path out\main.pdf) {
    $f = Get-Item out\main.pdf
    Write-Output "PDF: $([math]::Round($f.Length/1KB)) KB  @ $($f.LastWriteTime)"
} else { Write-Output "NO PDF PRODUCED" }
