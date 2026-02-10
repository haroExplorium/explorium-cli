---
name: explorium-cli
description: Use when needing to look up companies, find prospects, enrich contacts with emails and phone numbers, match businesses or people to Explorium IDs, get firmographics, technographics, funding data, or any B2B sales intelligence. Use when user mentions Explorium, prospect enrichment, company data, or lead research via CLI.
---

# Explorium CLI

B2B data enrichment CLI. Match companies/prospects to IDs, enrich with firmographics, contacts, profiles, tech stack, funding, and more.

## Setup (run once per session if needed)

**Step 1: Check if binary is installed**

```bash
which explorium 2>/dev/null || ls ~/.local/bin/explorium 2>/dev/null
```

If not found, install with the one-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/haroExplorium/explorium-cli/main/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

This downloads the CLI binary to `~/.local/bin/explorium`, makes it executable, and adds it to PATH.

**Step 2: Check if API key is configured**

```bash
explorium config show
```

If output shows `api_key: Not set`, ask the user for their Explorium API key using AskUserQuestion, then:

```bash
explorium config init -k <API_KEY>
```

## Global Options

Place BEFORE the subcommand:

```
-o, --output {json|table|csv}   Output format (default: json)
--output-file PATH              Write to file (clean output, no formatting)
```

## Commands Reference

See `commands-reference.md` in this skill directory for the full command reference with all options.

### Businesses

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `businesses match` | Match companies to IDs | `--name`, `--domain`, `--linkedin`, `-f FILE`, `--summary`, `--ids-only` |
| `businesses search` | Search/filter businesses | `--country`, `--size`, `--revenue`, `--tech`, `--total N` |
| `businesses enrich` | Firmographics (single) | `--id`, `--name`, `--domain`, `--min-confidence` |
| `businesses enrich-tech` | Technology stack | Same ID resolution options |
| `businesses enrich-financial` | Financial indicators | Same ID resolution options |
| `businesses enrich-funding` | Funding & acquisitions | Same ID resolution options |
| `businesses enrich-workforce` | Workforce trends | Same ID resolution options |
| `businesses enrich-traffic` | Website traffic | Same ID resolution options |
| `businesses enrich-social` | LinkedIn posts | Same ID resolution options |
| `businesses enrich-ratings` | Employee ratings | Same ID resolution options |
| `businesses enrich-keywords` | Website keywords | Same ID resolution options + `--keyword` |
| `businesses enrich-challenges` | 10-K challenges | Same ID resolution options |
| `businesses enrich-competitive` | Competitive landscape | Same ID resolution options |
| `businesses enrich-strategic` | Strategic insights | Same ID resolution options |
| `businesses enrich-website-changes` | Website changes | Same ID resolution options |
| `businesses enrich-webstack` | Web technologies | Same ID resolution options |
| `businesses enrich-hierarchy` | Company hierarchy | Same ID resolution options |
| `businesses enrich-intent` | Bombora intent signals | Same ID resolution options |
| `businesses bulk-enrich` | Bulk firmographics | `--ids`, `-f FILE`, `--match-file`, `--summary` |
| `businesses enrich-file` | Match + enrich in one | `-f FILE`, `--types`, `--summary` |
| `businesses lookalike` | Similar companies | `--id`, `--name`, `--domain` |
| `businesses autocomplete` | Name suggestions | `--query` |
| `businesses events list` | List event types | `--ids` |
| `businesses events enroll` | Subscribe to events | `--ids`, `--events`, `--key` |
| `businesses events enrollments` | List subscriptions | |

### Prospects

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `prospects match` | Match people to IDs | `--first-name`, `--last-name`, `--company-name`, `--email`, `--linkedin`, `-f FILE`, `--summary` |
| `prospects search` | Search prospects | `--business-id`, `--job-level`, `--department`, `--has-email`, `--total N` |
| `prospects enrich contacts` | Emails & phones (single) | `--id`, `--first-name`, `--last-name`, `--company-name`, `--email`, `--linkedin` |
| `prospects enrich social` | LinkedIn posts | Same ID resolution options |
| `prospects enrich profile` | Professional profile | Same ID resolution options |
| `prospects bulk-enrich` | Bulk enrich | `--ids`, `-f FILE`, `--match-file`, `--types {contacts,profile,all}`, `--summary` |
| `prospects enrich-file` | Match + enrich in one | `-f FILE`, `--types {contacts,profile,all}`, `--summary` |
| `prospects autocomplete` | Name suggestions | `--query` |
| `prospects statistics` | Aggregated insights | `--business-id`, `--group-by` |
| `prospects events list` | List event types | `--ids` |
| `prospects events enroll` | Subscribe to events | `--ids`, `--events`, `--key` |

### Config & Webhooks

| Command | Purpose |
|---------|---------|
| `config init -k KEY` | Set API key |
| `config show` | Display config |
| `config set KEY VALUE` | Set config value |
| `webhooks create --partner-id ID --url URL` | Create webhook |
| `webhooks get --partner-id ID` | Get webhook |
| `webhooks update --partner-id ID --url URL` | Update webhook |
| `webhooks delete --partner-id ID` | Delete webhook |

## Key Workflows

### Single company lookup

```bash
explorium businesses enrich --name "Acme Corp" -o table
```

### Single prospect with contacts

```bash
explorium prospects enrich contacts --first-name John --last-name Doe --company-name "Acme Corp"
```

### Bulk: CSV in, enriched CSV out (recommended for files)

```bash
# One command: match + enrich, flat CSV output
explorium prospects enrich-file -f leads.csv --types all -o csv --summary --output-file enriched.csv
explorium businesses enrich-file -f companies.csv --types firmographics -o csv --summary --output-file enriched.csv
```

### Pipeline: match then enrich separately

```bash
# Match first
explorium prospects match -f leads.csv -o csv --output-file matched.csv --summary
# Then enrich the matched file directly (reads prospect_id column)
explorium prospects bulk-enrich -f matched.csv --types all -o csv --output-file enriched.csv
```

### Search and collect

```bash
# Get 200 SaaS companies in the US
explorium businesses search --country US --tech "Salesforce" --total 200 -o csv --output-file results.csv
```

## CSV Column Mapping

The CLI auto-maps CSV columns (case-insensitive):

**Businesses:** `name`/`company_name`/`company`, `domain`/`website`/`url`, `linkedin_url`/`linkedin`
**Prospects:** `full_name`/`name`, `first_name`, `last_name`, `email`/`email_address`, `linkedin`/`linkedin_url`, `company_name`/`company`

LinkedIn URLs without `https://` are auto-fixed.

## Important Notes

- Match-based enrichment: All enrich commands accept `--name`/`--domain`/`--linkedin` instead of `--id` — the CLI resolves the ID automatically
- `--min-confidence` (default 0.8): Lower to 0.5-0.7 for fuzzy matches
- `enrich-file` is the fastest path for CSV workflows — combines match + enrich in one command
- CSV output flattens nested JSON automatically for spreadsheet use
- `--summary` shows matched/not-found/error counts on stderr
- All batch operations retry on transient errors (422, 429, 500-504) with exponential backoff
