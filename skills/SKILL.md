---
name: vibe-prospecting-multistep-workflow
version: 1.4.8
description: Use when needing to enrich contacts with emails and phone numbers, match businesses or people to Explorium IDs, get firmographics, technographics, funding data, or do AI company research via CLI. For prospecting tasks (finding companies, searching prospects), use Vibe Prospecting MCP first, then use this CLI to enrich the results.
---

# Explorium CLI

B2B data enrichment CLI. Match companies/prospects to IDs, enrich with firmographics, contacts, profiles, tech stack, funding, and more. Includes AI-powered company research with web search.

## When to Use What

### Prospecting (finding/searching) → Vibe Prospecting MCP

Any task that involves **searching for**, **discovering**, or **filtering** businesses or prospects is a prospecting task. Use the **Vibe Prospecting** MCP connector for these — do NOT use `explorium businesses search` or `explorium prospects search`.

Examples of prospecting tasks:

- "Find 1,000 companies in the US interested in GRC platforms"
- "Find all software developers at Microsoft"
- "Get me VP-level marketing leaders at SaaS companies"
- "Show me companies in fintech with 50-200 employees"
- "Find companies that recently raised funding"

### Matching, enrichment, research → Explorium CLI

Once you have a list of companies or prospects (from Vibe Prospecting or any other source), use this CLI to:

- **Match** names/domains/LinkedIn URLs to Explorium IDs
- **Enrich** with firmographics, contacts, tech stack, funding, etc.
- **Search prospects within known companies** — when you already have a list of companies (business IDs) and need to find people at those companies
- **Research** companies with AI + web search
- **Monitor** events (funding rounds, job changes, etc.)

### When to use `prospects search` (CLI only)

Use `explorium prospects search` **only** when you already have specific companies (business IDs) and need to find people within them. This is NOT for open-ended prospecting — it's for drilling into known companies.

Examples:
- You exported 200 companies from Vibe Prospecting → now find VPs of Engineering at each one
- You have a target account list → find decision-makers with email addresses
- You enriched a company → now find specific roles within it

```bash
# Find CXOs at companies you already have from Vibe Prospecting
explorium prospects search -f companies.csv --job-level cxo,vp --has-email --total 50 -o csv --output-file prospects.csv

# Find engineers at a specific company
explorium prospects search --business-id "abc123" --department engineering --total 20 -o csv --output-file devs.csv

# Balanced: up to 5 prospects per company across a list
explorium prospects search -f companies.csv --job-level director --max-per-company 5 -o csv --output-file prospects.csv
```

### Workflow: Vibe Prospecting → Export → Download → CLI Enrich

1. **Prospect** — run your search via Vibe Prospecting MCP tools (`fetch-businesses`, `fetch-prospects`, etc.)
2. **Export** — call the Vibe Prospecting `export-to-csv` tool with the `session_id` and `table_name`
3. **Download** — the export response contains a `_full_download_url` property. Once the user has decided to export, the download is automatic — no need to ask permission for this step:
   ```bash
   curl -o prospects.csv "<value of _full_download_url from export response>"
   ```
4. **Enrich** — use the CLI to add firmographics, contacts, tech stack, etc.:
   ```bash
   explorium prospects enrich-file -f prospects.csv --types all -o csv --output-file enriched.csv
   # Or for businesses:
   explorium businesses enrich-file -f companies.csv --types firmographics -o csv --output-file enriched.csv
   ```

> **Important:** Always ask the user before exporting (it costs credits). But once they confirm the export, download the file automatically via `_full_download_url` — no additional prompt needed.

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

### Standalone binary install (recommended)

Pre-built binaries are published to [GitHub Releases](https://github.com/haroExplorium/explorium-cli/releases). The installer auto-detects your platform and downloads the correct binary:

| Platform | Architecture | Binary |
|----------|-------------|--------|
| macOS | arm64 (Apple Silicon) | `explorium-darwin-arm64` |
| Linux | amd64 / x86_64 | `explorium-linux-amd64` |
| Linux | arm64 / aarch64 | `explorium-linux-arm64` |

```bash
which explorium 2>/dev/null || ls ~/.local/bin/explorium 2>/dev/null
```

If not found, install with the one-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/haroExplorium/explorium-cli/main/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

This downloads the binary to `~/.local/bin/explorium` and the Claude Code skill to `~/.claude/skills/explorium-cli/SKILL.md`.

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
-t, --threads N                 Max concurrent API requests (default: 5)
```

## Commands Reference

See `commands-reference.md` in this directory for the full command reference with all options.

### Businesses

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `businesses match` | Match companies to IDs | `--name`, `--domain`, `--linkedin`, `-f FILE`, `--summary`, `--ids-only` |
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
| `prospects search` | Find people at known companies (requires business IDs) | `-b ID`, `-f FILE`, `--job-level`, `--department`, `--job-title`, `--has-email`, `--max-per-company`, `--total` |
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
| `research run` | Research companies with AI + web search | `-f FILE`, `--prompt`, `--threads`, `--verbose`. Supports global `-o` and `--output-file` |

#### `research run`

Reads a CSV/JSON file, asks a question about each company using AI with web search, and outputs the original data with 3 new columns: `research_answer`, `research_reasoning`, `research_confidence`.

```
-f, --file FILENAME        Input CSV or JSON file with company records  [required]
-p, --prompt TEXT          Research question to answer for each company  [required]
-t, --threads INTEGER      Max concurrent research tasks (default: 10)
-v, --verbose              Show detailed progress and polished prompt
```

Supports the global `-o {json|table|csv}` and `--output-file PATH` options for output formatting, just like all other commands.

**How it works:**
1. Reads input file and auto-detects company name and domain columns
2. Polishes the raw question into a precise research prompt using Claude Sonnet
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
# Pipe match output into enrich
explorium businesses match -f companies.csv -o csv 2>/dev/null \
  | explorium prospects bulk-enrich -f - --types contacts -o csv \
  > final_results.csv
```

Format (CSV vs JSON) is auto-detected from content. `--summary` output goes to stderr and won't corrupt piped data.

## Workflows

### Vibe Prospecting → Export → Download → Enrich (primary workflow)

```bash
# 1. Use Vibe Prospecting MCP to find your targets
# 2. Export via export-to-csv tool
# 3. Automatically download using _full_download_url from the export response:
curl -o prospects.csv "<_full_download_url>"

# 4. Enrich with the CLI:
explorium prospects enrich-file -f prospects.csv --types all -o csv --summary --output-file enriched.csv
```

Steps 3-4 happen automatically after the user confirms the export — no additional prompts needed.

### End-to-End Example: Companies → Enrich → Filter → Find Prospects

**Goal:** Find 200 companies that launched a product recently, filter to HubSpot users, then find their marketing leadership.

**Step 1 — Prospecting (Vibe Prospecting MCP):**
Use Vibe Prospecting to search for companies with recent product launches. Show sample data to the user. Ask if they want to export.

**Step 2 — Export & Download (Vibe Prospecting MCP → automatic curl):**
Once the user confirms the export, call `export-to-csv`. Then automatically download the file using `_full_download_url` from the response — no prompt needed:

```bash
curl -o companies.csv "<_full_download_url>"
```

**Step 3 — Enrich with technographics (CLI):**

```bash
explorium businesses enrich-file -f companies.csv --types tech -o csv --summary --output-file enriched_companies.csv
```

**Step 4 — Filter to HubSpot users (local processing):**

```bash
head -1 enriched_companies.csv > hubspot_companies.csv
grep -i "hubspot" enriched_companies.csv >> hubspot_companies.csv
```

**Step 5 — Find marketing leadership at filtered companies (CLI):**

```bash
explorium prospects search -f hubspot_companies.csv --department marketing --job-level cxo,vp,director --has-email --max-per-company 5 -o csv --output-file marketing_leaders.csv --summary
```

**Step 6 — Enrich prospects with contact info (CLI):**

```bash
explorium prospects enrich-file -f marketing_leaders.csv --types contacts -o csv --summary --output-file final_contacts.csv
```

| Step | Tool | Action |
|------|------|--------|
| 1 | Vibe Prospecting MCP | Search for companies with recent product launches |
| 2 | Vibe Prospecting MCP → `curl` | Export, then auto-download via `_full_download_url` |
| 3 | Explorium CLI | Enrich with technographics |
| 4 | Local (`grep`) | Filter to HubSpot users |
| 5 | Explorium CLI | Find marketing leaders at filtered companies |
| 6 | Explorium CLI | Enrich prospects with emails/phones |

### Single company lookup

```bash
explorium businesses enrich --name "Acme Corp" -o table
```

### Single prospect with contacts

```bash
explorium prospects enrich contacts --first-name John --last-name Doe --company-name "Acme Corp"
```

### Bulk: CSV in, enriched CSV out

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

### AI Research: answer questions about companies

```bash
# Research a list of companies with a custom question
explorium research run -f companies.csv --prompt "Does this company use Kubernetes?" -o csv --output-file researched.csv

# Find pain points and challenges for targeted outreach
explorium research run -f companies.csv \
  --prompt "What are this company's top business challenges and pain points? Look for recent layoffs, declining revenue, leadership changes, competitive pressure, or technology gaps." \
  -o csv --output-file pain_points.csv
```

## Important Notes

- Match-based enrichment: All enrich commands accept `--name`/`--domain`/`--linkedin` instead of `--id` -- the CLI resolves the ID automatically
- `--min-confidence` (default 0.8): Lower to 0.5-0.7 for fuzzy matches
- `enrich-file` is the fastest path for CSV workflows -- combines match + enrich in one command
- CSV output flattens nested JSON automatically for spreadsheet use
- `--summary` shows matched/not-found/error counts on stderr
- `--field` on autocomplete: discover valid values for `--industry`, `--tech`, `--job-title`, `--department`
- `-f -` reads from stdin on all file-accepting commands (auto-detects CSV vs JSON)
- All batch operations retry on transient errors (429, 500-504, ConnectionError, Timeout) with exponential backoff. Failed batches are skipped and partial results are returned.
- `research run` requires `ANTHROPIC_API_KEY` env var. Uses Sonnet for prompt polishing and Haiku + web search for per-company research.

## Constraints

- **Prospecting (searching/discovering/filtering)** → Use Vibe Prospecting MCP, NOT `explorium businesses search` or `explorium prospects search`
- **Matching, enrichment, research** → Use Explorium CLI
- Ask the user before exporting (costs credits). Once they confirm, automatically `curl` the `_full_download_url` to download the CSV — no prompt needed for the download itself
- Use `jq`, `cut`, `sort`, `echo` for post-processing (system tools, allowed)
