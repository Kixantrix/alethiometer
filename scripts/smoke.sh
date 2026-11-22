#!/usr/bin/env bash
# Read-only repo health check. Exits 0 on success, 1 on failure. Mirror: scripts/smoke.ps1
cd "$(dirname "$0")/.." || exit 1
fail=0
PY=python3; "$PY" -c "" 2>/dev/null || PY=python
step() { local name=$1; shift; if "$@"; then echo "PASS $name"; else echo "FAIL $name"; fail=$((fail + 1)); fi; }

step "agent profiles + skills" "$PY" tools/validators/agents_md.py
step "assembly ledger" "$PY" tools/validators/check_assembly_ledger.py
js_check() { find js api/src -name '*.js' -not -path '*/node_modules/*' -print0 | xargs -0 -n1 node --check; }
step "website + api JS parse" js_check
if [ -d hardware/cad ]; then
  py_check() { find hardware/cad hardware/pcb hardware/dial hardware/viewer -maxdepth 1 -name '*.py' -print0 2>/dev/null | xargs -0 "$PY" -m py_compile; }
  step "hardware python compiles" py_check
fi

if [ "$fail" -gt 0 ]; then echo "smoke: $fail check(s) failed"; exit 1; fi
echo "smoke: OK"
