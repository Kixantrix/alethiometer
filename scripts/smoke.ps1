#!/usr/bin/env pwsh
# Read-only repo health check. Exits 0 on success, 1 on failure. Mirror: scripts/smoke.sh
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0

function Step($name, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -eq 0) { Write-Host "PASS $name" } else { Write-Host "FAIL $name"; $script:fail++ }
}

Step 'agent profiles + skills' { python tools/validators/agents_md.py }
Step 'assembly ledger' { python tools/validators/check_assembly_ledger.py }
Step 'website + api JS parse' {
    $files = @(Get-ChildItem js, api/src -Recurse -Filter *.js -File | Where-Object FullName -notmatch 'node_modules')
    $bad = 0
    foreach ($f in $files) { node --check $f.FullName; if ($LASTEXITCODE -ne 0) { $bad++ } }
    $global:LASTEXITCODE = [int]($bad -gt 0)
}
if (Test-Path hardware/cad) {
    Step 'hardware python compiles' {
        python -m py_compile (Get-ChildItem hardware/cad, hardware/pcb, hardware/dial, hardware/viewer -Filter *.py -File -ErrorAction SilentlyContinue).FullName
    }
}

if ($fail -gt 0) { Write-Host "smoke: $fail check(s) failed"; exit 1 }
Write-Host 'smoke: OK'
exit 0
