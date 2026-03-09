---
name: vibe-prospecting-multistep-workflow
version: 1.3.8
description: Use when needing to look up companies, find prospects, enrich contacts with emails and phone numbers, match businesses or people to Explorium IDs, get firmographics, technographics, funding data, or any B2B sales intelligence. Use when user mentions Explorium, prospect enrichment, company data, or lead research via CLI.
---

# Explorium CLI

B2B data enrichment CLI. Match companies/prospects to IDs, enrich with firmographics, contacts, profiles, tech stack, funding, and more. Includes AI-powered company research with web search.

## Setup (run once per session if needed)

### Cowork VM (recommended)

If the repo is already cloned, run the setup script. It pulls latest code, installs the CLI, syncs this skill, and configures the API key:

```bash
cd /path/to/explorium-cli && ./setup-cowork.sh
```

If the repo is not yet cloned:

```bash
git clone https://github.com/haroExplorium/explorium-cli.git
cd explorium-cli && ./setup-cowork.sh
```

### Standalone binary install

```bash
which explorium 2>/dev/null || ls ~/.local/bin/explorium 2>/dev/null
```

If not found, install with the one-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/haroExplorium/explorium-cli/main/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

### Configure Explorium API key

```bash
explorium config show
```

If output shows `api_key: NOT SET` (exit code 1), ask the user for their Explorium API key using AskUserQuestion, then:

```bash
explorium config init -k <API_KEY>
```

The setup script auto-discovers the key from: `~/.explorium/api_key` → `$PERSISTENT_DIR/*/.explorium/api_key` → `EXPLORIUM_API_KEY` env var.

### Configure Anthropic API key (for research command)

The `research run` command requires an Anthropic API key. Set it via:

```bash
export ANTHROPIC_API_KEY=<YOUR_KEY>
```

The setup script auto-discovers the key from: `~/.anthropic/api_key` → `$PERSISTENT_DIR/*/.anthropic/api_key` → `ANTHROPIC_API_KEY` env var.

## Global Options

Place BEFORE the subcommand:

```
-o, --output {json|table|csv}   Output format (default: json)
--output-file PATH              Write to file (clean output, no formatting)
```

## Commands Reference

See `commands-reference.md` in this directory for the full command reference with all options.

### Businesses

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `businesses match` | Match companies to IDs | `--name`, `--domain`, `--linkedin`, `-f FILE`, `--summary`, `--ids-only` |
| `businesses search` | Search/filter businesses | `--country`, `--size`, `--revenue`, `--industry`, `--tech`, `--total N` |
| `businesses enrich` | Firmographics (single) | `--id`, `--name`, `--domain`, `--min-confidence` |
| `businesses enrich-tech` | Technology stack | Same ID resolution options |
| `businesses enrich-financial` | Financial indicators | Same ID resolution options |
| `businesses enrich-funding` | Funding & acquisitions | Same ID resolution options |
| `businesses enrich-workforce` | Workforce trends | Same ID resolution options |
| `businesses enrich-traffic` | Website traffic | Same ID resolution options |
| `businesses enrich-social` | LinkedIn posts | Same ID resolution options |
| `businesses enrich-ratings` | Employee ratings | Same ID resolution options |
| `businesses enrich-keywords` | Website keywords | Same ID resolution options + `--keywords` |
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
| `businesses autocomplete` | Name/industry/tech suggestions | `--query`, `--field {name,industry,tech}` |
| `businesses events list` | List event types | `--ids`, `--events` |
| `businesses events enroll` | Subscribe to events | `--ids`, `--events`, `--key` |
| `businesses events enrollments` | List subscriptions | |

### Prospects

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `prospects match` | Match people to IDs | `--first-name`, `--last-name`, `--company-name`, `--email`, `--linkedin`, `-f FILE`, `--summary`, `--ids-only` |
| `prospects search` | Search prospects | `--business-id`, `--company-name`, `-f FILE`, `--job-level`, `--department`, `--job-title`, `--country`, `--has-email`, `--has-phone`, `--total N`, `--max-per-company N`, `--summary` |
| `prospects enrich contacts` | Emails & phones (single) | `--id`, `--first-name`, `--last-name`, `--company-name`, `--email`, `--linkedin` |
| `prospects enrich social` | LinkedIn posts | Same ID resolution options |
| `prospects enrich profile` | Professional profile | Same ID resolution options |
| `prospects bulk-enrich` | Bulk enrich (with `-f FILE`: preserves input columns with `input_` prefix; with `--ids`: enrichment fields only) | `--ids`, `-f FILE`, `--match-file`, `--types {contacts,profile,all}`, `--summary` |
| `prospects enrich-file` | Match + enrich in one | `-f FILE`, `--types {contacts,profile,all}`, `--summary` |
| `prospects autocomplete` | Name/title/dept suggestions | `--query`, `--field {name,job-title,department}` |
| `prospects statistics` | Aggregated insights | `--business-id`, `--group-by` |
| `prospects events list` | List event types | `--ids`, `--events` |
| `prospects events enroll` | Subscribe to events | `--ids`, `--events`, `--key` |
| `prospects events enrollments` | List subscriptions | |

### Research

AI-powered company research using Claude + web search. Requires `ANTHROPIC_API_KEY` environment variable.

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `research run` | Research companies with AI + web search | `-f FILE`, `--prompt`, `--threads`, `--max-searches`, `--no-polish`, `--verbose` |

#### `research run`

Reads a CSV/JSON file, asks a question about each company using AI with web search, and outputs the original data with 3 new columns: `research_answer`, `research_reasoning`, `research_confidence`.

```
-f, --file FILENAME        Input CSV or JSON file with company records  [required]
-p, --prompt TEXT          Research question to answer for each company  [required]
-t, --threads INTEGER      Max concurrent research tasks (default: 10)
--max-searches INTEGER     Max web searches per company (default: 5)
--no-polish                Skip prompt polishing with Sonnet
-v, --verbose              Show detailed progress and polished prompt
```

**How it works:**
1. Reads input file and auto-detects company name and domain columns
2. Polishes the raw question into a precise research prompt using Claude Sonnet (skip with `--no-polish`)
3. Fans out research across all companies concurrently (controlled by `--threads`)
4. Each company is researched using Claude Haiku with web search tool
5. Results are merged back into the original records

**Example:**
```bash
explorium research run -f companies.csv --prompt "Is this a B2B company?" -o csv --output-file researched.csv
```

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

## CSV Column Mapping

The CLI auto-maps CSV columns (case-insensitive):

**Businesses:** `name`/`company_name`/`company`, `domain`/`website`/`url`, `linkedin_url`/`linkedin`
**Prospects:** `full_name`/`name`, `first_name`, `last_name`, `email`/`email_address`, `linkedin`/`linkedin_url`, `company_name`/`company`
**Research:** `company_name`/`company`/`name`/`business_name` (for company), `domain`/`website`/`url` (for domain)

LinkedIn URLs without `https://` are auto-fixed.

**Note:** All `-f`/`--file` options accept CSVs with any number of columns. The CLI reads only the columns it needs and ignores the rest. You can pass the output of one command directly as input to the next without stripping columns.

## Stdin Piping

All `-f`/`--file` options accept `-` to read from stdin, enabling command pipelines:

```bash
# Pipe match output into search, then into enrich
# bulk-enrich -f preserves input columns with input_ prefix
explorium businesses match -f companies.csv -o csv 2>/dev/null \
  | explorium prospects search -f - --job-level cxo --total 10 -o csv 2>/dev/null \
  | explorium prospects bulk-enrich -f - --types contacts -o csv \
  > final_results.csv
```

Format (CSV vs JSON) is auto-detected from content. `--summary` output goes to stderr and won't corrupt piped data.

## Workflows

### Single company lookup

```bash
explorium businesses enrich --name "Acme Corp" -o table
```

### Single prospect with contacts

```bash
explorium prospects enrich contacts --first-name John --last-name Doe --company-name "Acme Corp"
```

### Discover valid filter values

```bash
# Find valid industry categories for --industry
explorium businesses autocomplete --query "software" --field industry

# Find valid technologies for --tech
explorium businesses autocomplete --query "React" --field tech

# Find valid job titles
explorium prospects autocomplete --query "founder" --field job-title
```

### Search prospects by company name

```bash
# No need to resolve business_id manually -- --company-name does it internally
explorium prospects search --company-name "Salesforce" --job-level cxo --country US --total 50 --summary -o csv --output-file results.csv
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

### Balanced search across companies

```bash
# Get up to 5 prospects per company (searches each company in parallel)
explorium prospects search -f biz_ids.csv --job-level cxo,vp --max-per-company 5 -o csv --output-file prospects.csv
```

### Full pipeline: companies -> filter -> prospects -> contacts

```bash
# 1. Find target companies
explorium businesses search --country US --tech "Salesforce" --total 100 -o csv --output-file companies.csv
# 2. Match to get business IDs
explorium businesses match -f companies.csv --ids-only --output-file biz_ids.csv
# 3. Search prospects across those companies
explorium prospects search -f biz_ids.csv --job-level cxo,vp --has-email --total 200 -o csv --output-file prospects.csv
# 4. Enrich with contacts
explorium prospects bulk-enrich -f prospects.csv --types all -o csv --output-file enriched.csv
```

### AI Research: answer questions about companies

```bash
# Research a list of companies with a custom question
explorium research run -f companies.csv --prompt "Does this company use Kubernetes?" -o csv --output-file researched.csv

# With more control
explorium research run -f companies.csv \
  --prompt "What is this company's main product?" \
  --threads 20 \
  --max-searches 3 \
  --verbose \
  -o csv --output-file researched.csv

# Find pain points and challenges for targeted outreach
explorium research run -f companies.csv \
  --prompt "What are this company's top business challenges and pain points? Look for recent layoffs, declining revenue, leadership changes, competitive pressure, or technology gaps." \
  -o csv --output-file pain_points.csv
```

### Event-Driven Marketing Leader Discovery

**Goal**: Find marketing leadership at companies actively posting about events

```bash
# Step 1: Match and enrich prospects (gets business_id)
explorium prospects enrich-file \
  -f prospects.csv \
  --types firmographics \
  --summary \
  -o csv --output-file matched_prospects.csv

# Step 2: Enrich companies with social posts
explorium businesses enrich-file \
  -f matched_prospects.csv \
  --types all \
  --summary \
  -o json --output-file companies_with_social.json

# Step 3: Filter for event posts
jq -r 'select(.social_posts != null) | select(.social_posts | tostring | test("(?i)(conference|webinar|event|summit)")) | .business_id' companies_with_social.json > event_companies.txt
echo "business_id" > event_companies.csv
cat event_companies.txt >> event_companies.csv

# Step 4: Find marketing leaders
explorium prospects search \
  -f event_companies.csv \
  --department "Marketing" \
  --job-level "cxo,vp" \
  --has-email \
  --max-per-company 3 \
  -o csv --output-file marketing_leaders.csv --summary

# Step 5: Enrich with contacts
explorium prospects enrich-file \
  -f marketing_leaders.csv \
  --types contacts \
  --summary \
  -o csv --output-file final_marketing_leaders.csv
```

## Important Notes

- Match-based enrichment: All enrich commands accept `--name`/`--domain`/`--linkedin` instead of `--id` -- the CLI resolves the ID automatically
- `--min-confidence` (default 0.8): Lower to 0.5-0.7 for fuzzy matches
- `enrich-file` is the fastest path for CSV workflows -- combines match + enrich in one command
- CSV output flattens nested JSON automatically for spreadsheet use
- `--summary` shows matched/not-found/error counts on stderr
- `--company-name` on `prospects search`: resolves company names to business IDs automatically (accepts comma-separated names)
- `prospects search --summary`: prints aggregate stats (countries, job levels, companies, email/phone counts) to stderr
- `--field` on autocomplete: discover valid values for `--industry`, `--tech`, `--job-title`, `--department`
- `-f -` reads from stdin on all file-accepting commands (auto-detects CSV vs JSON)
- All batch operations retry on transient errors (429, 500-504, ConnectionError, Timeout) with exponential backoff. Failed batches are skipped and partial results are returned.
- `research run` requires `ANTHROPIC_API_KEY` env var. Uses Sonnet for prompt polishing and Haiku + web search for per-company research.

## Constraints

- Use ONLY Explorium CLI for all data operations
- DO NOT use Vibe Prospecting MCP for operations the CLI can handle
- Use `jq`, `cut`, `sort`, `echo` for post-processing (system tools, allowed)
