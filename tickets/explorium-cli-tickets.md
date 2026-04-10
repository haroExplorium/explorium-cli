# Explorium CLI — Enrichment & Usability Improvements

## Context

During a real workflow (finding founders at stealth-mode startups across US, Israel, and Western Europe), several CLI friction points caused multi-step manual workarounds that should have been single commands. This ticket captures 4 fixes to the CLI and 1 fix to the skill documentation.

---

## Ticket 1: `enrich-file` should reuse existing `prospect_id` / `business_id` columns

### Problem

`enrich-file` always re-matches every row from scratch using name/email/linkedin columns, even when the input CSV already contains valid `prospect_id` or `business_id` values (e.g., output from a previous `prospects search` or `businesses search`).

This re-matching is unreliable — in our workflow, 52 out of 102 rows failed to re-match, producing `None` IDs that crashed entire enrichment batches:

```
✗ Batch failed: 'none is not an allowed value'
```

The workaround required manually extracting the 52 failed IDs and running `bulk-enrich --ids` separately.

### Root Cause

In `explorium_cli/commands/prospects.py` (lines 563-681), the `enrich_file()` function calls `parse_csv_prospect_match_params()` which only extracts match parameters (`first_name`, `last_name`, `email`, `linkedin`, `company_name`). It never checks for an existing `prospect_id` column.

The same issue exists in `explorium_cli/commands/businesses.py` for `business_id`.

The matching logic in `match_utils.py` (`resolve_prospect_id`, line 188) already supports skipping the API call when a `prospect_id` is provided directly — it's just never passed from the CSV parser.

### Fix

**Files to modify:**
- `explorium_cli/batching.py` — `parse_csv_prospect_match_params()` (line ~210) and `parse_csv_business_match_params()`: check for `prospect_id` / `business_id` column and include it in the returned params when present
- `explorium_cli/commands/prospects.py` — `enrich_file()` (line ~640): if `prospect_id` exists in parsed params, use it directly instead of calling `resolve_prospect_id()`
- `explorium_cli/commands/businesses.py` — same change for `business_id`

**Behavior:**
- If `prospect_id` (or `business_id`) column exists and the value is non-empty for a row → skip matching, use the ID directly
- If the column exists but the value is empty for a row → fall back to matching as today
- If the column doesn't exist → match as today (no behavior change)

### Test Cases

#### Test 1.1: Prospect `enrich-file` skips matching when `prospect_id` column exists

```bash
# Setup: create input CSV with valid prospect_ids from a prior search
explorium prospects search --company-name "Salesforce" --job-level cxo --total 10 -o csv --output-file tc1_input.csv

# Verify setup: confirm prospect_id column exists and is populated
head -1 tc1_input.csv | tr ',' '\n' | grep prospect_id  # Must find "prospect_id"
awk -F',' 'NR>1 {print $NF}' tc1_input.csv | grep -c '^$'  # Must be 0 (no empty IDs)

# Action: enrich using the file that already has prospect_ids
explorium prospects enrich-file -f tc1_input.csv --types contacts --summary -o csv --output-file tc1_output.csv 2>tc1_stderr.txt

# Assertions:
# 1. No matching step in stderr — should go straight to enrichment
grep -c "Matching\|Resolving\|match" tc1_stderr.txt  # Must be 0
# 2. Zero failures
grep "failed" tc1_stderr.txt  # Must show 0 failed
# 3. All rows enriched
input_rows=$(wc -l < tc1_input.csv | tr -d ' ')
output_rows=$(wc -l < tc1_output.csv | tr -d ' ')
echo "Input: $input_rows, Output: $output_rows"  # Must be equal
```

#### Test 1.2: Business `enrich-file` skips matching when `business_id` column exists

```bash
# Setup
explorium businesses search --country US --industry "Software" --total 5 -o csv --output-file tc1b_input.csv

# Action
explorium businesses enrich-file -f tc1b_input.csv --types firmographics --summary -o csv --output-file tc1b_output.csv 2>tc1b_stderr.txt

# Assertions: same as 1.1 — no matching step, zero failures, same row count
grep -c "Matching\|Resolving\|match" tc1b_stderr.txt  # Must be 0
```

#### Test 1.3: Falls back to matching when `prospect_id` column is absent

```bash
# Setup: create a CSV without prospect_id
echo "full_name,company_name" > tc1c_input.csv
echo "Marc Benioff,Salesforce" >> tc1c_input.csv

# Action
explorium prospects enrich-file -f tc1c_input.csv --types contacts --summary -o csv --output-file tc1c_output.csv 2>tc1c_stderr.txt

# Assertion: matching SHOULD occur (backward compatibility)
grep -c "Matching\|Resolving\|match" tc1c_stderr.txt  # Must be >= 1
```

#### Test 1.4: Handles mixed rows — some with `prospect_id`, some without

```bash
# Setup: CSV where some rows have prospect_id and some don't
explorium prospects search --company-name "Salesforce" --job-level cxo --total 3 -o csv --output-file tc1d_base.csv
# Manually blank out one prospect_id to simulate a missing value
python3 -c "
import csv
rows = list(csv.DictReader(open('tc1d_base.csv')))
rows[1]['prospect_id'] = ''  # blank one row
w = csv.DictWriter(open('tc1d_input.csv','w',newline=''), fieldnames=rows[0].keys())
w.writeheader(); w.writerows(rows)
"

# Action
explorium prospects enrich-file -f tc1d_input.csv --types contacts --summary -o csv --output-file tc1d_output.csv 2>tc1d_stderr.txt

# Assertions:
# 1. Should match only 1 row (the blank one), not all 3
grep "Matching 1 " tc1d_stderr.txt  # Must match
# 2. All 3 rows should appear in output
output_rows=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc1d_output.csv')))))")
echo "$output_rows"  # Must be 3
```

---

## Ticket 2: Multi-type enrichment should produce one row per entity in CSV output

### Problem

When running `enrich-file --types all` (contacts + profile), the CSV output contains **two rows per prospect** — one with contact fields (emails, phones) and another with profile fields (name, experience, education, LinkedIn). Same issue for businesses with multiple enrichment types.

This silently breaks downstream CSV processing. A naive `csv.DictReader` loop overwrites the first row's data with the second, losing all contact information.

### Root Cause

In `explorium_cli/commands/prospects.py` (lines 547-555), when multiple enrichment types are requested, each type's results are appended to `all_data` via `extend()`. This creates separate entries for the same `prospect_id` — one per enrichment type.

```python
for label, api_method in methods:
    partial = batched_enrich(api_method, prospect_ids, ...)
    all_data.extend(partial.get("data", []))  # Adds duplicate prospect_id entries
```

The CSV formatter then outputs each entry as a separate row.

### Fix

**Files to modify:**
- `explorium_cli/commands/prospects.py` — multi-type enrichment section (lines ~547-555): merge results by `prospect_id` instead of extending
- `explorium_cli/commands/businesses.py` — same pattern for `business_id`
- `explorium_cli/formatters.py` — alternatively, add a merge-by-key step in `output_csv()` before writing

**Approach — merge in the command handler:**

```python
if len(methods) == 1:
    result = batched_enrich(methods[0][1], prospect_ids, ...)
else:
    merged = {}  # prospect_id -> combined dict
    for label, api_method in methods:
        partial = batched_enrich(api_method, prospect_ids, ...)
        for item in partial.get("data", []):
            pid = item.get("entity_id") or item.get("prospect_id", "")
            if pid not in merged:
                merged[pid] = {}
            # Merge non-empty fields from this enrichment type
            for k, v in item.items():
                if v is not None and v != "":
                    merged[pid][k] = v
    result = {"status": "success", "data": list(merged.values())}
```

### Test Cases

#### Test 2.1: `--types all` produces one row per prospect (not two)

```bash
# Setup
explorium prospects search --company-name "Salesforce" --job-level cxo --total 5 -o csv --output-file tc2_input.csv
input_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc2_input.csv')))))")

# Action
explorium prospects enrich-file -f tc2_input.csv --types all -o csv --output-file tc2_output.csv

# Assertions:
# 1. Output row count must equal input row count (not 2x)
output_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc2_output.csv')))))")
echo "Input: $input_count, Output: $output_count"  # Must be equal

# 2. Each prospect_id appears exactly once
python3 -c "
import csv
from collections import Counter
rows = list(csv.DictReader(open('tc2_output.csv')))
counts = Counter(r['prospect_id'] for r in rows)
dupes = {k: v for k, v in counts.items() if v > 1}
assert not dupes, f'Duplicate prospect_ids: {dupes}'
print('PASS: no duplicate prospect_ids')
"
```

#### Test 2.2: Both contact and profile fields present in every row

```bash
# Uses tc2_output.csv from Test 2.1

# Assertions:
# 1. Header contains both contact fields (emails) and profile fields (experience)
python3 -c "
import csv
reader = csv.DictReader(open('tc2_output.csv'))
fields = reader.fieldnames
has_email = any('email' in f for f in fields)
has_experience = any('experience' in f for f in fields)
assert has_email, 'Missing email fields in header'
assert has_experience, 'Missing experience fields in header'
print('PASS: header has both contact and profile fields')
"

# 2. First data row has values in both contact AND profile columns
python3 -c "
import csv
rows = list(csv.DictReader(open('tc2_output.csv')))
row = rows[0]
email_fields = [k for k in row if 'email' in k and row[k]]
exp_fields = [k for k in row if 'experience' in k and row[k]]
assert email_fields, f'Row has no email data. Fields: {[k for k in row if \"email\" in k]}'
assert exp_fields, f'Row has no experience data. Fields: {[k for k in row if \"experience\" in k]}'
print(f'PASS: row has {len(email_fields)} email fields and {len(exp_fields)} experience fields')
"
```

#### Test 2.3: `bulk-enrich --types all` also produces one row per prospect

```bash
# Setup: extract prospect_ids from prior search
ids=$(python3 -c "
import csv
rows = list(csv.DictReader(open('tc2_input.csv')))
print(','.join(r['prospect_id'] for r in rows[:5] if r.get('prospect_id')))
")

# Action
explorium prospects bulk-enrich --ids "$ids" --types all -o csv --output-file tc2c_output.csv

# Assertion: one row per ID
python3 -c "
import csv
from collections import Counter
rows = list(csv.DictReader(open('tc2c_output.csv')))
counts = Counter(r['prospect_id'] for r in rows)
dupes = {k: v for k, v in counts.items() if v > 1}
assert not dupes, f'Duplicate prospect_ids: {dupes}'
print(f'PASS: {len(rows)} rows, no duplicates')
"
```

#### Test 2.4: Same behavior for businesses with `--types all`

```bash
# Setup
explorium businesses search --country US --industry "Software" --total 5 -o csv --output-file tc2d_input.csv
input_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc2d_input.csv')))))")

# Action
explorium businesses enrich-file -f tc2d_input.csv --types all -o csv --output-file tc2d_output.csv

# Assertion: one row per business
output_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc2d_output.csv')))))")
echo "Input: $input_count, Output: $output_count"  # Must be equal
```

---

## Ticket 3: `bulk-enrich` should preserve input columns when given `-f FILE`

### Problem

`bulk-enrich` output contains only `prospect_id` + enrichment fields. All input columns (name, title, company, country, city, skills, etc.) are dropped. This breaks piping workflows — the documented pipeline in SKILL.md loses data at the final step:

```bash
# Current documented pipeline — LOSES all search data at the last step
explorium businesses match -f companies.csv -o csv 2>/dev/null \
  | explorium prospects search -f - --job-level cxo --total 10 -o csv 2>/dev/null \
  | explorium prospects bulk-enrich -f - --types contacts -o csv \
  > final_results.csv
# final_results.csv has ONLY prospect_id + emails/phones — no names, titles, companies
```

The only alternative (`enrich-file`) re-matches and can fail (Ticket 1).

### Root Cause

In `explorium_cli/commands/prospects.py` (lines 446-561), the `bulk_enrich()` command reads `prospect_id` values from the input CSV but discards all other columns. The enrichment API response only contains enrichment fields, and no input columns are merged back.

Compare with `enrich-file` (line 676-679) which explicitly merges input columns:
```python
for k, v in id_to_input.get(eid, {}).items():
    row[f"input_{k}"] = v
```

### Fix

**Files to modify:**
- `explorium_cli/commands/prospects.py` — `bulk_enrich()`: when input comes from `-f FILE`, read and store all columns per `prospect_id`, then merge them back into enrichment output (same pattern as `enrich-file`)
- `explorium_cli/commands/businesses.py` — same change for `businesses bulk-enrich`

**Behavior:**
- When `--ids` is used (no input file) → no change (no input columns to preserve)
- When `-f FILE` is used → preserve all input columns with `input_` prefix, same as `enrich-file`

### Skill File Fix

Update the piping workflow example in `SKILL.md` (line 126-131) to warn about this limitation until the CLI fix ships, and recommend `enrich-file` as the alternative:

**Current (SKILL.md line 125-131):**
```bash
# Pipe match output into search, then into enrich
explorium businesses match -f companies.csv -o csv 2>/dev/null \
  | explorium prospects search -f - --job-level cxo --total 10 -o csv 2>/dev/null \
  | explorium prospects bulk-enrich -f - --types contacts -o csv \
  > final_results.csv
```

**Updated:**
```bash
# Pipe match output into search, then into enrich
# Note: bulk-enrich does NOT preserve input columns (name, title, company, etc.)
# Use enrich-file instead to keep all columns from previous steps
explorium businesses match -f companies.csv -o csv 2>/dev/null \
  | explorium prospects search -f - --job-level cxo --total 10 -o csv 2>/dev/null \
  | explorium prospects enrich-file -f - --types contacts -o csv \
  > final_results.csv
```

Also update the `bulk-enrich` row in the Prospects command table (SKILL.md line 91) to make the limitation clearer.

### Test Cases

#### Test 3.1: `bulk-enrich -f FILE` preserves input columns for prospects

```bash
# Setup: create input CSV with rich columns from a search
explorium prospects search --company-name "Salesforce" --job-level cxo --total 5 -o csv --output-file tc3_input.csv

# Capture input column names
input_cols=$(head -1 tc3_input.csv)

# Action
explorium prospects bulk-enrich -f tc3_input.csv --types contacts -o csv --output-file tc3_output.csv

# Assertions:
# 1. Output has input_ prefixed columns
python3 -c "
import csv
reader = csv.DictReader(open('tc3_output.csv'))
input_cols = [f for f in reader.fieldnames if f.startswith('input_')]
assert len(input_cols) > 0, 'No input_ columns found in output'
print(f'PASS: found {len(input_cols)} preserved input columns: {input_cols[:5]}...')
"

# 2. Key identity fields are preserved (not empty)
python3 -c "
import csv
rows = list(csv.DictReader(open('tc3_output.csv')))
for row in rows:
    name = row.get('input_full_name', '') or row.get('input_first_name', '')
    assert name, f'Missing input name for prospect {row.get(\"prospect_id\", \"?\")}'
print(f'PASS: all {len(rows)} rows have preserved name data')
"

# 3. Enrichment fields are also present
python3 -c "
import csv
rows = list(csv.DictReader(open('tc3_output.csv')))
email_cols = [f for f in rows[0] if 'email' in f.lower() and not f.startswith('input_')]
assert email_cols, 'No enrichment email columns found'
print(f'PASS: enrichment fields present: {email_cols[:3]}...')
"
```

#### Test 3.2: `bulk-enrich --ids` still works without input columns (no regression)

```bash
# Setup: extract IDs only
ids=$(python3 -c "
import csv
rows = list(csv.DictReader(open('tc3_input.csv')))
print(','.join(r['prospect_id'] for r in rows[:3] if r.get('prospect_id')))
")

# Action
explorium prospects bulk-enrich --ids "$ids" --types contacts -o csv --output-file tc3b_output.csv

# Assertion: no input_ columns (no file was provided)
python3 -c "
import csv
reader = csv.DictReader(open('tc3b_output.csv'))
input_cols = [f for f in reader.fieldnames if f.startswith('input_')]
assert len(input_cols) == 0, f'Unexpected input_ columns when using --ids: {input_cols}'
print('PASS: --ids mode has no input_ columns (correct)')
"
```

#### Test 3.3: Piping workflow preserves data end-to-end

```bash
# Full pipeline: search → bulk-enrich via pipe
explorium prospects search --company-name "Salesforce" --job-level cxo --total 5 -o csv 2>/dev/null \
  | explorium prospects bulk-enrich -f - --types contacts -o csv \
  > tc3c_output.csv

# Assertions:
# 1. Output has both input columns and enrichment columns
python3 -c "
import csv
reader = csv.DictReader(open('tc3c_output.csv'))
input_cols = [f for f in reader.fieldnames if f.startswith('input_')]
enrich_cols = [f for f in reader.fieldnames if 'email' in f.lower() and not f.startswith('input_')]
assert input_cols, 'Pipeline lost input columns'
assert enrich_cols, 'Pipeline has no enrichment columns'
print(f'PASS: pipeline preserved {len(input_cols)} input cols + {len(enrich_cols)} enrichment cols')
"
```

#### Test 3.4: Same behavior for `businesses bulk-enrich -f FILE`

```bash
# Setup
explorium businesses search --country US --industry "Software" --total 5 -o csv --output-file tc3d_input.csv

# Action
explorium businesses bulk-enrich -f tc3d_input.csv -o csv --output-file tc3d_output.csv

# Assertion: input columns preserved
python3 -c "
import csv
reader = csv.DictReader(open('tc3d_output.csv'))
input_cols = [f for f in reader.fieldnames if f.startswith('input_')]
assert len(input_cols) > 0, 'No input_ columns in business bulk-enrich output'
print(f'PASS: {len(input_cols)} input columns preserved for businesses')
"
```

---

## Ticket 4: Add `--region` shorthand for multi-country searches

### Problem

Searching across a geographic region (e.g., Western Europe) requires manually listing all ISO country codes:

```bash
--country "GB,DE,FR,NL,BE,LU,AT,CH,IE,ES,PT,IT,SE,NO,DK,FI"
```

This is error-prone (easy to forget a country) and hurts readability.

### Fix

**Files to modify:**
- `explorium_cli/commands/prospects.py` — `search()` command: add `--region` option
- `explorium_cli/commands/businesses.py` — `search()` command: add `--region` option
- New constant map (in `utils.py` or a new `regions.py`):

```python
REGION_SHORTCUTS = {
    "western-europe": ["GB", "DE", "FR", "NL", "BE", "LU", "AT", "CH", "IE", "ES", "PT", "IT"],
    "northern-europe": ["SE", "NO", "DK", "FI", "IS"],
    "eastern-europe": ["PL", "CZ", "HU", "RO", "BG", "SK", "HR", "SI", "RS", "UA"],
    "europe": ["GB", "DE", "FR", "NL", "BE", "LU", "AT", "CH", "IE", "ES", "PT", "IT",
               "SE", "NO", "DK", "FI", "IS", "PL", "CZ", "HU", "RO", "BG", "SK", "HR", "SI", "RS", "UA"],
    "north-america": ["US", "CA"],
    "latam": ["MX", "BR", "AR", "CL", "CO", "PE"],
    "middle-east": ["IL", "AE", "SA", "QA", "BH", "KW", "OM", "JO"],
    "apac": ["AU", "NZ", "SG", "HK", "JP", "KR", "IN", "TW"],
    "dach": ["DE", "AT", "CH"],
    "benelux": ["BE", "NL", "LU"],
    "nordics": ["SE", "NO", "DK", "FI", "IS"],
}
```

**Behavior:**
- `--region western-europe` expands to `--country GB,DE,FR,...`
- `--region` and `--country` can be combined: `--region nordics --country IL` merges both lists
- `--region` values are case-insensitive
- Invalid region names produce a clear error listing available regions

### Test Cases

#### Test 4.1: `--region` expands to correct country codes

```bash
# Action: search with --region
explorium prospects search --company-name "Salesforce" --job-level cxo --region western-europe --total 10 --summary -o csv --output-file tc4a_region.csv 2>tc4a_stderr.txt

# Action: search with equivalent --country
explorium prospects search --company-name "Salesforce" --job-level cxo --country "GB,DE,FR,NL,BE,LU,AT,CH,IE,ES,PT,IT" --total 10 --summary -o csv --output-file tc4a_country.csv 2>tc4a_stderr2.txt

# Assertions:
# 1. Both searches return results
region_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc4a_region.csv')))))")
country_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc4a_country.csv')))))")
echo "Region: $region_count, Country: $country_count"  # Both must be > 0

# 2. Results are from the same set of countries
python3 -c "
import csv
r_countries = set(r['country_name'] for r in csv.DictReader(open('tc4a_region.csv')))
c_countries = set(r['country_name'] for r in csv.DictReader(open('tc4a_country.csv')))
assert r_countries == c_countries, f'Country mismatch: {r_countries} vs {c_countries}'
print(f'PASS: same countries in both results: {r_countries}')
"
```

#### Test 4.2: `--region` and `--country` can be combined

```bash
# Action: combine region + individual country
explorium prospects search --company-name "Salesforce" --job-level cxo --region dach --country IL --total 10 --summary -o csv --output-file tc4b_output.csv

# Assertion: results include both DACH countries AND Israel
python3 -c "
import csv
countries = set(r['country_name'] for r in csv.DictReader(open('tc4b_output.csv')))
# DACH = DE, AT, CH and IL should all be possible
print(f'Countries found: {countries}')
# At minimum, should not error out — combined usage must work
assert len(countries) > 0, 'No results returned for combined region + country'
print('PASS: combined --region + --country works')
"
```

#### Test 4.3: Invalid region name produces helpful error

```bash
# Action: use invalid region
explorium prospects search --company-name "Salesforce" --region invalid-name --total 5 2>tc4c_stderr.txt; exit_code=$?

# Assertions:
# 1. Command fails with non-zero exit code
echo "Exit code: $exit_code"  # Must be non-zero

# 2. Error message lists available regions
grep -i "available\|unknown\|invalid" tc4c_stderr.txt  # Must match
grep -i "western-europe\|nordics\|dach" tc4c_stderr.txt  # Must list valid options
```

#### Test 4.4: Case-insensitive region names

```bash
# Action: use mixed case
explorium prospects search --company-name "Salesforce" --region "Western-Europe" --total 5 --summary -o csv --output-file tc4d_output.csv 2>tc4d_stderr.txt

# Assertion: works without error
result_count=$(python3 -c "import csv; print(len(list(csv.DictReader(open('tc4d_output.csv')))))")
echo "Results: $result_count"  # Must be > 0
```

#### Test 4.5: `--region` works on business search too

```bash
# Action
explorium businesses search --region nordics --industry "Software" --total 5 --summary -o csv --output-file tc4e_output.csv

# Assertion: returns businesses from Nordic countries
python3 -c "
import csv
rows = list(csv.DictReader(open('tc4e_output.csv')))
assert len(rows) > 0, 'No results for Nordic business search'
print(f'PASS: {len(rows)} Nordic businesses found')
"
```
