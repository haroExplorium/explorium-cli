# Update bulk-enrich docs to show match → enrich pipeline as primary workflow

**Type:** Task
**Priority:** Medium
**Component:** CLI / Documentation
**Labels:** `documentation`, `developer-experience`, `cli`

---

## Summary

The `bulk-enrich` documentation examples and the Pipeline section actively mislead users into writing intermediate scripts to extract prospect IDs, when in reality `bulk-enrich -f` accepts the match CSV output directly. Two small doc changes fix this.

---

## Problem

The `bulk-enrich --file` flag already accepts any CSV with a `prospect_id` column and ignores other columns. But the documentation doesn't make this clear:

1. **`bulk-enrich` examples (line ~531-538)** show `--file prospect_ids.txt`, implying you need a clean file with just IDs. This led an AI agent to write a Python script to extract IDs from match output into a separate file — completely unnecessary work.

2. **Pipeline section (line ~875-887)** shows the `--ids-only` approach first (which also implies ID extraction), and only shows the CSV pipeline for **businesses**, not prospects.

The information that `-f` ignores extra columns exists in the `--help` text (`CSV file with 'prospect_id' column (other columns are ignored)`), but the examples contradict it.

---

## Proposed Changes

### Change 1: Update `bulk-enrich` examples (line ~531-538)

**Current:**
```bash
**Using IDs:**
# Bulk enrich by prospect IDs
explorium prospects bulk-enrich --ids "a099...dade,8112...c99d"

# From a file with IDs (one per line)
explorium prospects bulk-enrich --file prospect_ids.txt
```

**Replace with:**
```bash
**Using IDs:**
# Bulk enrich by prospect IDs
explorium prospects bulk-enrich --ids "a099...dade,8112...c99d"

# From a CSV file (reads prospect_id column, ignores all other columns)
# This means match CSV output feeds directly into bulk-enrich:
explorium prospects match -f leads.csv --format csv --output-file matched.csv
explorium prospects bulk-enrich -f matched.csv --types all -o csv --output-file enriched.csv
```

### Change 2: Add prospect example to Pipeline section (line ~884-887)

**Current** (only shows businesses for the CSV path):
```bash
# Option 2: --format csv outputs a full CSV with prospect_id column
explorium businesses match -f companies.csv --format csv > matched.csv
explorium businesses bulk-enrich -f matched.csv
```

**Replace with:**
```bash
# Option 2: --format csv outputs a full CSV with prospect_id/business_id column.
# bulk-enrich reads that column and ignores everything else — no intermediate processing needed.
explorium businesses match -f companies.csv --format csv --output-file matched.csv
explorium businesses bulk-enrich -f matched.csv

explorium prospects match -f leads.csv --format csv --output-file matched.csv
explorium prospects bulk-enrich -f matched.csv --types all -o csv --output-file enriched.csv
```

---

## Acceptance Criteria

- [ ] `bulk-enrich` example section shows match → bulk-enrich as the primary file-based workflow
- [ ] Pipeline section includes a prospect-specific example alongside the existing business one
