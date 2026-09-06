#!/bin/sh
# Run every tool against the synthetic fixture. Exit non-zero on a structural problem.
set -e
cd "$(dirname "$0")"
F=fixtures/sample.ged
export FTK_DATA=data FTK_GED=$F FTK_REGISTER=data/register-fixture.jsonl
mkdir -p data; rm -f data/register-fixture.jsonl
python3 tools/gedcheck.py $F
echo; python3 tools/gedlint.py $F || true
echo; python3 tools/rings.py $F --root @I5@ --json data/rings-fixture.json
echo "--- register: a controlled absent, a coverage-unknown, a void, a hit"
python3 tools/register.py --add --person @I7@ --corpus "irishgenealogy.ie civil" --query "CASEY, Cork, births 1922-1926, also CASEY/CASY" --years 1922-1926 --place Cork --record-type birth --result nil --nil-class absent --control "CASEY Cork 1924 returns 41 rows" --by fixture
python3 tools/register.py --add --person @I22@ --corpus "India Office N series (FamilySearch)" --query "COLE, India, baptisms 1923-1927" --years 1923-1927 --place India --record-type baptism --result nil --nil-class coverage-unknown --why "family was Catholic; N series is Anglican plus some Catholic" --next "FMP India Select Catholic" --by fixture
python3 tools/register.py --add --person @I20@ --corpus "India Office N series (FamilySearch)" --query "SEN, Calcutta, 1958" --result void --note "HTTP 429 after 3 requests" --by fixture
python3 tools/register.py --add --person @I9@ --corpus "Trove newspapers" --query "Fenwright Bendigo 1943" --result hit --ref nla.news-article00000001 --by fixture
if python3 tools/register.py --add --person @I7@ --corpus X --query Y --result nil --nil-class absent --by fixture 2>/dev/null; then echo "FAIL: uncontrolled absent was accepted"; exit 1; else echo "ok: uncontrolled absent refused"; fi
echo; python3 tools/register.py --exhausted @I7@; python3 tools/register.py --exhausted @I22@; python3 tools/register.py --stats
echo; python3 tools/gapranker.py $F --root @I5@ --top 10 --register data/register-fixture.jsonl
echo; python3 tools/side_balance.py $F --root @I1@ --cut @I5@ --side paternal=@I2@ --side maternal=@I3@ --side partner=@I4@ | head -4
