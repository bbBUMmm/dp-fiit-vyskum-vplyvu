# build-school-kit.ps1 -- assemble everything a Slovak school needs, in one folder.
#
# The thesis assignment requires the solution to be verified BY USING IT in a
# school. That is not a claim a repository can make about itself: a school
# receives a folder, not a git clone, and whatever is missing from that folder
# is missing on the day.
#
# So the kit is built, checked, and the check is what fails -- not the teacher.
#
#   .\build-school-kit.ps1                 build into .\school-kit
#   .\build-school-kit.ps1 -Verify         check the sources only, copy nothing
#   .\build-school-kit.ps1 -Force          rebuild even if school-kit\data has files
#
# What the school gets:
#   RUN.cmd                 one double-click to start a lesson (whole class or one PC)
#   TEST.cmd                one double-click to administer a test or questionnaire
#   KODY.cmd                issue the pupil codes -- run by the SCHOOL, once
#   client\                 the exercise client + teacher dashboard + activities
#   test\                   the assessment module: banks, runner, scoring
#   tlac\                   everything that must be printed
#   kontrola\               the same-afternoon data check (standard library only)
#   PRECITAJ-MA.txt         what to do, in order, in Slovak
#
# KODY.cmd is in the kit and not in the researcher's hands on purpose. The
# code-to-pupil mapping is the one thing that must never leave the school, so
# the school generates it.
#
# Two defects of the first version, fixed here:
#   * every text file of the kit was written from strings inside THIS script.
#     Windows PowerShell 5.1 reads a script without a byte-order mark as ANSI,
#     so the Slovak letters in those strings arrived as mojibake ("n with caron"
#     became two Latin-1 characters in PRECITAJ-MA.txt),
#     and Set-Content -Encoding UTF8 then put a BOM in front of every .cmd,
#     which cmd.exe reads as part of the first command. The texts now live in
#     kit\ as files and are copied byte for byte; this script is pure ASCII.
#   * the data check shipped analysis\ingest.py, which needs numpy, pandas and a
#     console module the kit did not contain, and checks files the kit does not
#     produce. It now ships assessment\datacheck.py, standard library only.

param([switch]$Verify, [switch]$Force)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit  = Join-Path $root "school-kit"

# ---------------------------------------------------------------- required
# Every entry is checked before anything is copied. A kit that is 90 % built
# is worse than no kit: it looks ready.
$required = @(
    @{ From = "exercise-client\server.py";      To = "client\server.py" },
    @{ From = "exercise-client\pedagogy.py";    To = "client\pedagogy.py" },
    @{ From = "exercise-client\providers.py";   To = "client\providers.py" },
    @{ From = "exercise-client\events.py";      To = "client\events.py" },
    @{ From = "exercise-client\activities.py";  To = "client\activities.py" },
    @{ From = "exercise-client\metrics.py";     To = "client\metrics.py" },
    @{ From = "exercise-client\peqi_live.py";   To = "client\peqi_live.py" },
    @{ From = "exercise-client\qr.py";          To = "client\qr.py" },
    @{ From = "exercise-client\README.md";      To = "client\README.md" },
    @{ From = "assessment\linkage.py";          To = "client\linkage.py" },
    @{ From = "assessment\consent.py";          To = "client\consent.py" },
    # --- the assessment module: without it the kit can teach but not measure
    @{ From = "assessment\bank.py";        To = "test\bank.py" },
    @{ From = "assessment\sessions.py";    To = "test\sessions.py" },
    @{ From = "assessment\linkage.py";     To = "test\linkage.py" },
    @{ From = "assessment\consent.py";     To = "test\consent.py" },
    @{ From = "assessment\runner.py";      To = "test\runner.py" },
    @{ From = "assessment\scoring.py";     To = "test\scoring.py" },
    @{ From = "assessment\effort.py";      To = "test\effort.py" },
    @{ From = "assessment\integrity.py";   To = "test\integrity.py" },
    @{ From = "assessment\profiles.py";    To = "test\profiles.py" },
    @{ From = "assessment\report.py";      To = "test\report.py" },
    @{ From = "assessment\calibration.py"; To = "test\calibration.py" },
    @{ From = "assessment\results.py";     To = "test\results.py" },
    @{ From = "assessment\testy.py";       To = "test\testy.py" },
    @{ From = "assessment\datacheck.py";   To = "kontrola\datacheck.py" },
    # --- launchers and texts, copied byte for byte
    @{ From = "kit\RUN.cmd";          To = "RUN.cmd" },
    @{ From = "kit\TEST.cmd";         To = "TEST.cmd" },
    @{ From = "kit\KODY.cmd";         To = "KODY.cmd" },
    @{ From = "kit\SKONTROLUJ.cmd";   To = "kontrola\SKONTROLUJ.cmd" },
    @{ From = "kit\PRECITAJ-MA.txt";  To = "PRECITAJ-MA.txt" },
    @{ From = "kit\CO-VYTLACIT.txt";  To = "tlac\CO-VYTLACIT.txt" }
)
$requiredDirs = @(
    @{ From = "exercise-client\static";     To = "client\static" },
    @{ From = "exercise-client\tasks";      To = "client\tasks" },
    @{ From = "exercise-client\activities"; To = "client\activities" },
    @{ From = "assessment\banks";           To = "test\banks" },
    @{ From = "assessment\static";          To = "test\static" },
    # the test section: the tests are the plain-text files the commission reads
    @{ From = "testy";                      To = "test\testy" }
)

Write-Output "=== kontrola zdrojov ==="
$missing = @()
foreach ($f in $required) {
    $p = Join-Path $root $f.From
    if (-not (Test-Path $p)) { $missing += $f.From } else { Write-Output "  ok   $($f.From)" }
}
foreach ($d in $requiredDirs) {
    $p = Join-Path $root $d.From
    if (-not (Test-Path $p)) { $missing += $d.From } else { Write-Output "  ok   $($d.From)\" }
}
# a .cmd with a byte-order mark or bare LF line endings misbehaves in cmd.exe
foreach ($f in $required | Where-Object { $_.From -like "*.cmd" }) {
    $p = Join-Path $root $f.From
    if (Test-Path $p) {
        $bytes = [System.IO.File]::ReadAllBytes($p)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $missing += "$($f.From) (byte-order mark)"
        }
        $text = [System.Text.Encoding]::ASCII.GetString($bytes)
        if ($text -match "[^\r]\n") { $missing += "$($f.From) (LF line endings; needs CRLF)" }
    }
}
if ($missing.Count -gt 0) {
    Write-Output ""
    Write-Output "CHYBA: zdroje nie su v poriadku, kit sa nestavia:"
    $missing | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
if ($Verify) { Write-Output "`nvsetky zdroje pritomne"; exit 0 }

# ---------------------------------------------------------------- assemble
# A kit that has been used holds data in data\. Rebuilding would delete it, so
# the build refuses unless told explicitly.
$dataDir = Join-Path $kit "data"
if ((Test-Path $dataDir) -and -not $Force) {
    $used = @(Get-ChildItem $dataDir -File -Recurse -ErrorAction SilentlyContinue)
    if ($used.Count -gt 0) {
        Write-Output ""
        Write-Output "CHYBA: school-kit\data obsahuje $($used.Count) suborov (zozbierane data?)."
        Write-Output "Presunte ich inam, alebo spustite s -Force, ak ich naozaj chcete zmazat."
        exit 1
    }
}
if (Test-Path $kit) { Remove-Item $kit -Recurse -Force }
New-Item -ItemType Directory $kit | Out-Null
foreach ($sub in @("client", "test", "tlac", "kontrola", "data")) {
    New-Item -ItemType Directory (Join-Path $kit $sub) | Out-Null
}
foreach ($f in $required) {
    $dst = Join-Path $kit $f.To
    New-Item -ItemType Directory (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item (Join-Path $root $f.From) $dst
}
foreach ($d in $requiredDirs) {
    Copy-Item (Join-Path $root $d.From) (Join-Path $kit $d.To) -Recurse
}
Get-ChildItem $kit -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
# the superseded first versions of the tests stay in the repository, not in the kit
$archive = Join-Path $kit "test\testy\archiv-v1"
if (Test-Path $archive) { Remove-Item $archive -Recurse -Force }
# paper backup: every pupil sheet without the key, ready to print
Push-Location (Join-Path $kit "test")
$env:PYTHONIOENCODING = "utf-8"
$sheets = & python testy.py --tlac-vsetko "..\tlac\testy" 2>&1 | Out-String
$sheetsCode = $LASTEXITCODE
Pop-Location
Get-ChildItem $kit -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
if ($sheetsCode -ne 0) { Write-Output "CHYBA: harky testov sa nepodarilo vytvorit"; Write-Output $sheets; exit 1 }

# ---------------------------------------------------------------- verify
Write-Output ""
Write-Output "=== kontrola zostaveneho kitu ==="
$expect = @("RUN.cmd", "TEST.cmd", "KODY.cmd", "PRECITAJ-MA.txt",
            "client\server.py", "client\linkage.py", "client\consent.py",
            "client\static\index.html", "client\static\consent.js",
            "client\static\teacher.html", "client\static\widgets.js", "client\tasks",
            "client\activities", "test\runner.py", "test\bank.py", "test\linkage.py", "test\consent.py",
            "test\banks", "test\static\test.html", "test\testy.py", "test\testy",
            "tlac\testy", "kontrola\datacheck.py",
            "kontrola\SKONTROLUJ.cmd", "tlac\CO-VYTLACIT.txt", "data")
$bad = @()
foreach ($e in $expect) {
    if (Test-Path (Join-Path $kit $e)) { Write-Output "  ok   $e" } else { $bad += $e }
}
if ($bad.Count -gt 0) {
    Write-Output ""
    $bad | ForEach-Object { Write-Output "  CHYBA $_" }
    exit 1
}

# The kit must also WORK, not merely contain the files. A folder whose Python
# cannot import is a folder that fails in the classroom, and the import graph is
# the part that breaks when a file is copied to a flatter directory than the one
# it was written in. So each part is imported and exercised from inside the kit,
# with nothing from the repository on the path.
Write-Output ""
Write-Output "=== kontrola funkcnosti kitu ==="
$env:PYTHONIOENCODING = "utf-8"
$probes = @(
    @{ Dir = "test"; Code = @'
import json, sys
sys.path.insert(0, ".")
import bank, linkage, sessions, scoring, profiles, report, effort, integrity, calibration, results
import consent, runner
assert runner.CONSENT_JS, "the test cannot find the consent screen (client\\static\\consent.js)"
assert consent.view("test", consent.PENDING)["version"]
banks = bank.load_all()
b = sessions.budget()
code = linkage.issue("GY", 1, seed=1)[0]
assert linkage.verify(code, "GY")
try:
    linkage.verify(code[:-1] + ("4" if code[-1] != "4" else "7"), "GY")
    raise SystemExit("a mistyped code was accepted")
except linkage.CodeError:
    pass
import testy
cat = testy.load_catalog()
forms = [f for f in cat.values() if f.is_test]
sit = testy.compose("F1-T3", cat, "K")
assert all(not i.conditions for i in sit.items), "condition filter"
print(json.dumps({"banks": len(banks), "items": sum(x.n_items for x in banks.values()),
                  "sessions_fit": b["all_fit"], "tests": len(forms),
                  "questionnaires": len(cat) - len(forms),
                  "test_items": sum(len(f.knowledge) for f in forms)}))
'@ },
    @{ Dir = "client"; Code = @'
import json, sys
sys.path.insert(0, ".")
import server, activities, pedagogy, metrics, peqi_live, qr
packs = activities.load_packs("activities")
lessons = [pedagogy.load_lesson("tasks/" + f) for f in ("t1_search.json", "m1_interest.json", "f1_circuits.json")]
assert qr.svg("http://192.168.0.1:5173/").startswith("<svg")
print(json.dumps({"activities": sum(len(p["activities"]) for p in packs.values()),
                  "lessons": [l.lesson_id for l in lessons]}))
'@ },
    @{ Dir = "kontrola"; Code = @'
import sys
sys.path.insert(0, ".")
import datacheck
assert not datacheck.self_test(), "datacheck self-test failed"
print("datacheck ok")
'@ }
)
foreach ($pr in $probes) {
    $probePath = Join-Path $kit "$($pr.Dir)\_probe.py"
    [System.IO.File]::WriteAllText($probePath, $pr.Code, (New-Object System.Text.UTF8Encoding $false))
    Push-Location (Join-Path $kit $pr.Dir)
    $out = & python -I _probe.py 2>&1 | Out-String
    $code = $LASTEXITCODE
    Pop-Location
    Remove-Item $probePath -Force
    Get-ChildItem (Join-Path $kit $pr.Dir) -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    if ($code -ne 0) {
        Write-Output "  CHYBA: $($pr.Dir)\ sa neda spustit z vlastneho priecinka"
        ($out -split "`n" | Select-Object -Last 12) | ForEach-Object { Write-Output "  ! $_" }
        exit 1
    }
    Write-Output ("  ok   {0,-9} {1}" -f "$($pr.Dir)\", $out.Trim())
}

$n = (Get-ChildItem $kit -Recurse -File | Measure-Object).Count
$mb = [math]::Round((Get-ChildItem $kit -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 2)
Write-Output ""
Write-Output "kit zostaveny: $kit"
Write-Output "$n suborov, $mb MB"
Write-Output ""
Write-Output "ZOSTAVA DOPLNIT RUCNE: vytlacene materialy do  school-kit\tlac\"
Write-Output "  (zoznam je v  school-kit\tlac\CO-VYTLACIT.txt)"
