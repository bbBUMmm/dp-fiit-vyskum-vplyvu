# run-all-tests.ps1 -- every automated check in the project, in one command.
#
# Four components, four suites. They are independent, so a failure in one does
# not stop the others: the point of running them together is to see the whole
# picture, not to stop at the first problem.
#
#   .\run-all-tests.ps1

$ErrorActionPreference = "Continue"
# Exported so the suites' own Slovak output is readable in a narrow console.
# It used to MASK the bug it should have found: server.py crashed on a non-UTF-8
# console and the suite never saw it, because every subprocess inherited this.
# Both suites that can hit that now strip the variable explicitly in the test
# itself (test_server.py and test_analysis.py), so setting it here is safe again.
$env:PYTHONIOENCODING = "utf-8"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Order matters in one place: the Python analysis layer regenerates
# cross_impl_corpus.json, and the Java suite checks itself against it. Running
# Java first would test against a stale fixture.
$suites = @(
    @{ Name = "analysis layer";      Dir = "mastersLaTeX\analysis"; Cmd = "python"; Args = @("test_analysis.py") },
    @{ Name = "thesis consistency";  Dir = "mastersLaTeX\analysis"; Cmd = "python"; Args = @("verify_thesis.py") },
    @{ Name = "capture layer";       Dir = "ai-prompt-monitor";     Cmd = "python"; Args = @("mitm\test_capture.py") },
    @{ Name = "PEQI analysis (Java)"; Dir = "ai-prompt-monitor";    Cmd = "mvn";    Args = @("-B", "test") },
    @{ Name = "pedagogy";            Dir = "exercise-client";       Cmd = "python"; Args = @("test_pedagogy.py") },
    @{ Name = "interaction features"; Dir = "exercise-client";      Cmd = "python"; Args = @("test_features.py") },
    @{ Name = "exercise client e2e"; Dir = "exercise-client";       Cmd = "python"; Args = @("test_server.py") },
    @{ Name = "assessment layer";    Dir = "assessment";            Cmd = "python"; Args = @("test_assessment.py") }
)

$results = @()
foreach ($s in $suites) {
    Write-Output ""
    Write-Output ("=== {0} " -f $s.Name)
    Push-Location (Join-Path $root $s.Dir)
    $out = & $s.Cmd @($s.Args) 2>&1 | Out-String
    $code = $LASTEXITCODE
    Pop-Location

    # Reset first: a null match would otherwise leave the previous suite's
    # summary in place and report one suite's result under another's name.
    $summary = "(no summary line)"
    $match = $out -split "`n" |
        Select-String -Pattern "\d+ passed|Tests run:.*Failures|claims verified" |
        Select-Object -Last 1
    if ($null -ne $match) { $summary = $match.ToString().Trim() }

    $status = if ($code -eq 0) { "PASS" } else { "FAIL" }
    Write-Output ("   {0}  {1}" -f $status, $summary)
    if ($code -ne 0) {
        ($out -split "`n" | Select-Object -Last 15) | ForEach-Object { Write-Output "   ! $_" }
    }
    $results += [pscustomobject]@{ Suite = $s.Name; Status = $status; Summary = $summary }
}

Write-Output ""
Write-Output ("=" * 62)
# Rendered to a string rather than emitted as objects: mixing formatted output
# with the plain strings written below puts the formatter out of sequence.
Write-Output (($results | Format-Table -AutoSize | Out-String).TrimEnd())

# The thesis reports these counts, and a thesis must not contain a number that
# someone remembered to update. The counts are written here, read by
# analysis/export_macros.py, and checked by analysis/verify_thesis.py.
$counts = @{}
foreach ($r in $results) {
    $n = 0
    if ($r.Summary -match "(\d+)\s+passed") { $n = [int]$Matches[1] }
    elseif ($r.Summary -match "Tests run:\s*(\d+)") { $n = [int]$Matches[1] }
    elseif ($r.Summary -match "(\d+)\s*/\s*\d+\s+claims") { $n = [int]$Matches[1] }
    $counts[$r.Suite] = @{ passed = $n; status = $r.Status }
}
$total = ($counts.Values | ForEach-Object { $_.passed } | Measure-Object -Sum).Sum
$summary = [ordered]@{
    generated_by = "run-all-tests.ps1"
    generated_at = (Get-Date -Format "yyyy-MM-dd")
    suites       = $counts
    n_suites     = $results.Count
    total_passed = $total
}
$docDir = Join-Path $root "ai-doc"
if (-not (Test-Path $docDir)) { New-Item -ItemType Directory -Path $docDir | Out-Null }
# Written without a byte-order mark: Windows PowerShell's -Encoding utf8 adds
# one, and Python's json.load rejects it.
[System.IO.File]::WriteAllText(
    (Join-Path $docDir "test-summary.json"),
    ($summary | ConvertTo-Json -Depth 4),
    (New-Object System.Text.UTF8Encoding $false))
Write-Output ("{0} tests across {1} suites -> ai-doc\test-summary.json" -f $total, $results.Count)

# The thesis prints these counts, so the macros are refreshed here. The loop is
# genuinely self-referential -- the consistency checker is one of the suites, so
# its own check count is part of the total it then verifies -- which means a run
# that CHANGES the number of checks or tests needs one more pass to settle.
# Saying so is cheaper than pretending it converges in one.
$prevTotal = $null
$macroFile = Join-Path $root "mastersLaTeX\analysis\out\thesis_numbers.tex"
if (Test-Path $macroFile) {
    $m = Select-String -Path $macroFile -Pattern '\\newcommand\{\\repoTests\}\{(\d+)\}'
    if ($m) { $prevTotal = [int]$m.Matches[0].Groups[1].Value }
}
# The instrument macros carry the assessment suite's own test count, so they are
# regenerated AFTER the suites have run. Without this the count lags one run
# behind and verify_thesis.py reports the generated files as stale -- which is
# correct, and confusing, and avoidable.
Push-Location (Join-Path $root "assessment")
& python tex_export.py | Out-Null
Pop-Location
Push-Location (Join-Path $root "mastersLaTeX\analysis")
& python export_macros.py | Out-Null
Pop-Location
if ($null -ne $prevTotal -and $prevTotal -ne $total) {
    Write-Output ("   counts moved ({0} -> {1}); run once more to settle" -f $prevTotal, $total)
}

$failed = @($results | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
    Write-Output ("{0} suite(s) failed." -f $failed.Count)
    exit 1
}
Write-Output "all suites passed"
exit 0
