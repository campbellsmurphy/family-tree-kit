#!/bin/sh
# Run every tool against the synthetic fixture. Exit non-zero on a structural problem.
set -e
cd "$(dirname "$0")"
F=fixtures/sample.ged
mkdir -p data
python3 tools/gedcheck.py $F
echo; python3 tools/gedlint.py $F || true
echo; python3 tools/rings.py $F --root @I5@ --json data/rings-fixture.json
echo; FTK_DATA=data python3 tools/gapranker.py $F --root @I5@ --top 10
echo; python3 tools/side_balance.py $F --root @I1@ --cut @I5@ --side paternal=@I2@ --side maternal=@I3@ --side partner=@I4@
