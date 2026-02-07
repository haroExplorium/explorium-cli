# Explorium CLI

A comprehensive command-line interface for interacting with all Explorium API endpoints.

## Installation

```bash
# From the project directory
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Configuration

### Initialize Configuration

```bash
# Set up your API key
explorium config init --api-key "your_api_key_here"
```

This creates a config file at `~/.explorium/config.yaml`.

### Configuration File

The config file supports the following options:

```yaml
# ~/.explorium/config.yaml
api_key: "your_api_key_here"
base_url: "https://api.explorium.ai/v1"
default_output: "json"
default_page_size: 100
```

### Environment Variables

You can override config values with environment variables:

| Environment Variable | Config Key |
|---------------------|------------|
| `EXPLORIUM_API_KEY` | `api_key` |
| `EXPLORIUM_BASE_URL` | `base_url` |
| `EXPLORIUM_DEFAULT_OUTPUT` | `default_output` |
| `EXPLORIUM_PAGE_SIZE` | `default_page_size` |

### View/Modify Configuration

```bash
# Show current configuration
explorium config show

# Set a specific value
explorium config set default_output table
explorium config set default_page_size 50
```

## Global Options

All commands support these global options:

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Path to config file |
| `-o, --output [json\|table\|csv]` | Output format (default: json) |
| `--output-file PATH` | Write output to file (clean JSON/CSV, no formatting) |
| `--help` | Show help message |

## Commands

### Businesses

#### Match Business

Match company name/domain to get unique business IDs.

```bash
# Match by name and domain
explorium businesses match --name "Starbucks" --domain "starbucks.com"

# Match by LinkedIn URL
explorium businesses match --linkedin "https://linkedin.com/company/starbucks"

# Match multiple businesses from file (JSON or CSV)
explorium businesses match -f companies.json
explorium businesses match -f companies.csv

# Show match statistics
explorium businesses match -f companies.csv --summary

# Output only matched IDs (one per line, pipeable)
explorium businesses match -f companies.csv --ids-only

# Override output format for this command
explorium businesses match -f companies.csv --format csv
```

**Input file format (`companies.json`):**
```json
[
  {"name": "Starbucks", "website": "starbucks.com"},
  {"name": "Microsoft", "website": "microsoft.com"}
]
```

#### Search Businesses

Search and filter businesses.

```bash
# Search by country and size
explorium businesses search --country us,ca --size "51-200,201-500"

# Search with revenue and tech filters
explorium businesses search \
  --country us \
  --revenue "10M-50M" \
  --tech "Python,React"

# Search by recent events
explorium businesses search \
  --events "new_funding_round,new_product" \
  --events-days 30

# Pagination
explorium businesses search --country us --page 2 --page-size 50

# Auto-paginate to collect a specific total
explorium businesses search --country us --total 500
```

**Available filters:**

| Option | Description | Example Values |
|--------|-------------|----------------|
| `--country` | Country codes | `us`, `ca`, `gb`, `de` |
| `--size` | Company size | `1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+` |
| `--revenue` | Revenue range | `0-500K`, `500K-1M`, `1M-5M`, `5M-10M`, `10M-50M`, `50M-100M`, `100M-500M`, `500M-1B`, `1B+` |
| `--industry` | Industry categories | LinkedIn industry categories |
| `--tech` | Technology stack | `Python`, `React`, `AWS`, etc. |
| `--events` | Recent events | See [Business Events](#business-events) |
| `--events-days` | Days for event recency | Default: 45 |

#### Enrich Business

Get detailed information about a business. You can use either an ID or match parameters (name, domain, linkedin).

```bash
# Enrich by ID
explorium businesses enrich --id "8adce3ca1cef0c986b22310e369a0793"

# Enrich by company name (no ID needed!)
explorium businesses enrich --name "Salesforce"

# Enrich by domain
explorium businesses enrich --domain "google.com"

# Enrich by LinkedIn URL
explorium businesses enrich --linkedin "https://linkedin.com/company/microsoft"

# Combine match parameters for better accuracy
explorium businesses enrich --name "Stripe" --domain "stripe.com"

# Adjust confidence threshold (default: 0.8)
explorium businesses enrich --name "Acme Corp" --min-confidence 0.6
```

**All enrichment types support match parameters:**
```bash
# Tech stack for Salesforce
explorium businesses enrich-tech --name "Salesforce"

# Financial metrics for Microsoft
explorium businesses enrich-financial --domain "microsoft.com"

# Workforce trends for Amazon
explorium businesses enrich-workforce --name "Amazon"

# Website keyword search for Apple
explorium businesses enrich-keywords --name "Apple" --keywords "AI,privacy,security"
```

**Bulk enrichment:**
```bash
# By IDs
explorium businesses bulk-enrich --ids "id1,id2,id3"

# From file with IDs
explorium businesses bulk-enrich -f business_ids.txt

# From file with match parameters (no IDs needed!)
# companies.json: [{"name": "Salesforce"}, {"domain": "hubspot.com"}]
explorium businesses bulk-enrich --match-file companies.json

# Show match/enrichment statistics
explorium businesses bulk-enrich --match-file companies.json --summary

# Override output format
explorium businesses bulk-enrich --ids "id1,id2" --format csv
```

#### Enrich File (Match + Enrich in One Pass)

Match businesses from a CSV/JSON file and enrich in one step:

```bash
# From CSV file
explorium businesses enrich-file -f companies.csv

# From JSON file
explorium businesses enrich-file -f companies.json

# With lower confidence threshold
explorium businesses enrich-file -f companies.csv --min-confidence 0.6

# Show match statistics
explorium businesses enrich-file -f companies.csv --summary

# Override output format
explorium businesses enrich-file -f companies.csv --format csv
```

#### Lookalike

Find similar companies.

```bash
# By ID
explorium businesses lookalike --id "8adce3ca1cef0c986b22310e369a0793"

# By name (no ID needed!)
explorium businesses lookalike --name "Salesforce"

# By domain
explorium businesses lookalike --domain "stripe.com"
```

#### Autocomplete

Get autocomplete suggestions for company names.

```bash
explorium businesses autocomplete --query "star"
```

#### Business Events

```bash
# List business events
explorium businesses events list \
  --ids "id1,id2" \
  --events "new_funding_round,new_product"

# Enroll for event monitoring
explorium businesses events enroll \
  --ids "id1,id2" \
  --events "new_funding_round,ipo_announcement" \
  --key "my_enrollment_key"

# List enrollments
explorium businesses events enrollments
```

### Prospects

#### Match Prospect

Match person to get unique prospect ID.

```bash
# Match by first/last name + company (most common)
explorium prospects match \
  --first-name "Satya" --last-name "Nadella" --company-name "Microsoft"

# Match by LinkedIn URL (name is optional when linkedin/email is provided)
explorium prospects match --linkedin "https://linkedin.com/in/johndoe"

# Match by email
explorium prospects match --email "john.doe@example.com"

# Match from file (JSON or CSV) — auto-batches if >50 rows
explorium prospects match -f prospects.json
explorium prospects match -f prospects.csv

# Show match statistics
explorium prospects match -f prospects.csv --summary

# Output only matched IDs (one per line, pipeable)
explorium prospects match -f prospects.csv --ids-only

# Override output format for this command
explorium prospects match -f prospects.csv --format csv
```

**Match file formats** — use `full_name` + `company_name` for best results:

```csv
full_name,company_name
Satya Nadella,Microsoft
Marc Benioff,Salesforce
Tim Cook,Apple
```

Or with separate first/last name columns:
```csv
first_name,last_name,company_name
Satya,Nadella,Microsoft
Marc,Benioff,Salesforce
```

JSON format:
```json
[
  {"full_name": "Satya Nadella", "company_name": "Microsoft"},
  {"full_name": "Marc Benioff", "company_name": "Salesforce"},
  {"linkedin": "https://linkedin.com/in/sundarpichai"}
]
```

#### Search Prospects

Search and filter prospects.

```bash
# Search within a company
explorium prospects search \
  --business-id "8adce3ca1cef0c986b22310e369a0793"

# Filter by job level and department
explorium prospects search \
  --business-id "id" \
  --job-level "cxo,vp,director" \
  --department "Engineering,Sales"

# Filter by contact availability
explorium prospects search \
  --business-id "id" \
  --has-email \
  --has-phone

# Filter by experience
explorium prospects search \
  --business-id "id" \
  --experience-min 60 \
  --role-tenure-max 24

# Auto-paginate to collect a specific total
explorium prospects search --business-id "id" --total 200

# Search from CSV file (with business_id column)
explorium prospects search -f business_ids.csv
```

**Available filters:**

| Option | Description | Example Values |
|--------|-------------|----------------|
| `--business-id` | Business IDs to search within | Required (or use `--file`) |
| `--job-level` | Job levels | `cxo`, `vp`, `director`, `manager`, `senior`, `entry` |
| `--department` | Departments | `Engineering`, `Sales`, `Marketing`, `Finance`, `HR`, `Operations` |
| `--job-title` | Specific job titles | Any text |
| `--country` | Country codes | `us`, `ca`, `gb` |
| `--has-email` | Has email address | Flag |
| `--has-phone` | Has phone number | Flag |
| `--experience-min` | Min total experience (months) | Integer |
| `--experience-max` | Max total experience (months) | Integer |
| `--role-tenure-min` | Min current role tenure (months) | Integer |
| `--role-tenure-max` | Max current role tenure (months) | Integer |

#### Enrich Prospect

Get detailed information about a prospect. You can use either an ID or match parameters (name, linkedin, company).

```bash
# By ID
explorium prospects enrich contacts --id "prospect_id"
explorium prospects enrich social --id "prospect_id"
explorium prospects enrich profile --id "prospect_id"

# By name and company (no ID needed!)
explorium prospects enrich contacts \
  --first-name "Satya" \
  --last-name "Nadella" \
  --company-name "Microsoft"

# By LinkedIn URL
explorium prospects enrich contacts --linkedin "https://linkedin.com/in/satyanadella"

# Social media for Marc Benioff
explorium prospects enrich social \
  --first-name "Marc" \
  --last-name "Benioff" \
  --company-name "Salesforce"

# Professional profile for Sundar Pichai
explorium prospects enrich profile \
  --first-name "Sundar" \
  --last-name "Pichai" \
  --company-name "Google"

# Adjust confidence threshold
explorium prospects enrich contacts \
  --first-name "John" \
  --last-name "Smith" \
  --company-name "Acme Corp" \
  --min-confidence 0.6
```

**Bulk enrichment:**
```bash
# By IDs
explorium prospects bulk-enrich --ids "id1,id2,id3"

# From file with match parameters (no IDs needed!)
# prospects.json: [{"full_name": "Satya Nadella", "company_name": "Microsoft"}]
explorium prospects bulk-enrich --match-file prospects.json

# Choose enrichment type (contacts, profile, all)
explorium prospects bulk-enrich --ids "id1,id2" --types profile
explorium prospects bulk-enrich --match-file prospects.json --types all

# Show match/enrichment statistics
explorium prospects bulk-enrich --match-file prospects.json --summary

# Override output format
explorium prospects bulk-enrich --ids "id1,id2" --format csv
```

#### Enrich File (Match + Enrich in One Pass)

Match prospects from a CSV/JSON file and enrich in one step:

```bash
# From CSV file (default enrichment: contacts)
explorium prospects enrich-file -f prospects.csv

# Choose enrichment type (comma-separated: contacts, profile, all)
explorium prospects enrich-file -f prospects.csv --types profile
explorium prospects enrich-file -f prospects.csv --types all
explorium prospects enrich-file -f prospects.csv --types contacts,profile

# With lower confidence threshold
explorium prospects enrich-file -f prospects.csv --min-confidence 0.6

# Show match statistics
explorium prospects enrich-file -f prospects.csv --summary

# Override output format
explorium prospects enrich-file -f prospects.csv --format csv
```

#### Autocomplete

```bash
explorium prospects autocomplete --query "john"
```

#### Statistics

Get aggregated insights about prospects.

```bash
explorium prospects statistics \
  --business-id "id" \
  --group-by "department,job_level"
```

#### Prospect Events

```bash
# List prospect events
explorium prospects events list \
  --ids "id1,id2" \
  --events "prospect_changed_company"

# Enroll for event monitoring
explorium prospects events enroll \
  --ids "id1,id2" \
  --events "prospect_changed_role,prospect_changed_company" \
  --key "my_enrollment_key"

# List enrollments
explorium prospects events enrollments
```

### Pipeline: Match → Bulk-Enrich

The `--ids-only` and `--format csv` flags make it easy to pipe match output into bulk-enrich:

```bash
# Option 1: Use --ids-only to get IDs, save to file, then enrich
explorium prospects match -f leads.csv --ids-only > prospect_ids.txt
explorium prospects bulk-enrich -f prospect_ids.txt

# Option 2: Use --format csv to get full match CSV, then enrich from it
explorium businesses match -f companies.csv --format csv > matched.csv
explorium businesses bulk-enrich -f matched.csv
```

CSV column matching for ID files is case-insensitive: `prospect_id`, `Prospect_Id`, and `PROSPECT_ID` all work.

### Subcommand `--format` Option

Commands that support `--format` can override the global `-o` option:

```bash
# Global JSON, but this command outputs CSV
explorium -o json prospects match --email "john@co.com" --format csv

# Works on match, bulk-enrich, and enrich-file
explorium businesses bulk-enrich --ids "id1,id2" --format table
```

### Webhooks

Manage webhook configurations for receiving event notifications.

```bash
# Create webhook
explorium webhooks create \
  --partner-id "my_partner" \
  --url "https://myapp.com/webhook"

# Get webhook configuration
explorium webhooks get --partner-id "my_partner"

# Update webhook URL
explorium webhooks update \
  --partner-id "my_partner" \
  --url "https://myapp.com/new-webhook"

# Delete webhook
explorium webhooks delete --partner-id "my_partner"
```

## Event Types Reference

### Business Events

| Event | Description |
|-------|-------------|
| `ipo_announcement` | Company IPO announcement |
| `new_funding_round` | New funding round |
| `new_investment` | Company made an investment |
| `new_product` | New product launch |
| `new_office` | New office opening |
| `closing_office` | Office closure |
| `new_partnership` | New partnership announcement |
| `merger_and_acquisitions` | M&A activity |
| `company_award` | Company received an award |
| `cost_cutting` | Cost cutting measures |
| `lawsuits_and_legal_issues` | Legal issues |
| `outages_and_security_breaches` | Security incidents |
| `increase_in_*_department` | Department growth (e.g., `increase_in_engineering_department`) |
| `decrease_in_*_department` | Department reduction |
| `hiring_in_*_department` | Active hiring in department |

### Prospect Events

| Event | Description |
|-------|-------------|
| `prospect_changed_role` | Prospect changed their role |
| `prospect_changed_company` | Prospect moved to new company |
| `prospect_job_start_anniversary` | Work anniversary |

## Output to File

Use `--output-file` to write clean data to a file instead of the terminal. File output contains no Rich formatting or ANSI codes.

```bash
# Write JSON to file
explorium businesses search --country us --output-file results.json

# Write CSV to file
explorium -o csv businesses search --country us --output-file results.csv

# Table format falls back to JSON when writing to file
explorium -o table businesses search --country us --output-file results.json
```

A confirmation message is printed to stderr: `Output written to: results.json`

## Match Statistics

Use `--summary` on match, bulk-enrich, and enrich-file commands to print match statistics to stderr.

```bash
# Match with summary
explorium prospects match -f prospects.csv --summary
# Stderr: Matched: 77/88, Failed: 11

# Bulk enrich with summary
explorium businesses bulk-enrich --match-file companies.json --summary
# Stderr: Matched: 45/50, Failed: 5

# Enrich file with summary
explorium prospects enrich-file -f prospects.csv --summary
# Stderr: Matched: 23/25, Failed: 2
```

## Output Formats

### JSON (default)

```bash
explorium businesses search --country us -o json
```

Output is pretty-printed JSON suitable for piping to tools like `jq`:

```bash
explorium businesses search --country us -o json | jq '.data[].name'
```

### Table

```bash
explorium businesses search --country us -o table
```

Output is a formatted table using Rich library.

## Examples

### Complete Workflow Example

```bash
# 1. Initialize configuration
explorium config init --api-key "your_key"

# 2. Enrich a target company directly by name (no need to match first!)
explorium businesses enrich --name "Salesforce" -o table

# 3. Get their tech stack
explorium businesses enrich-tech --name "Salesforce"

# 4. Find similar companies
explorium businesses lookalike --name "Salesforce"

# 5. Get contact info for their CEO
explorium prospects enrich contacts \
  --first-name "Marc" \
  --last-name "Benioff" \
  --company-name "Salesforce"

# 6. Traditional workflow still works with IDs
# Match a target company
explorium businesses match --name "Acme Corp" --domain "acme.com"
# Returns: business_id = "abc123"

# Find decision makers
explorium prospects search \
  --business-id "abc123" \
  --job-level "cxo,vp" \
  --department "Engineering,Product" \
  --has-email \
  -o table

# 7. Set up event monitoring
explorium businesses events enroll \
  --ids "abc123" \
  --events "new_funding_round,new_product" \
  --key "acme_monitoring"

# 8. Register webhook for notifications
explorium webhooks create \
  --partner-id "my_app" \
  --url "https://myapp.com/explorium-webhook"
```

### Match-Based Enrichment (No IDs Required)

The fastest way to get data is using match parameters directly:

```bash
# Business enrichment by name/domain
explorium businesses enrich --name "Stripe"
explorium businesses enrich-tech --domain "notion.so"
explorium businesses enrich-financial --name "Shopify"

# Prospect enrichment by name/linkedin
explorium prospects enrich contacts \
  --first-name "Tim" \
  --last-name "Cook" \
  --company-name "Apple"

explorium prospects enrich profile \
  --linkedin "https://linkedin.com/in/jeffweiner08"

# Bulk enrichment from match files
explorium businesses bulk-enrich --match-file companies.json
explorium prospects bulk-enrich --match-file prospects.json

# One-pass file enrichment (match + enrich combined)
explorium businesses enrich-file -f companies.csv
explorium prospects enrich-file -f prospects.csv --types all
```

### Batch Processing

```bash
# Create a file with company data
cat > companies.json << 'EOF'
[
  {"name": "Company A", "website": "companya.com"},
  {"name": "Company B", "website": "companyb.com"},
  {"name": "Company C", "website": "companyc.com"}
]
EOF

# Match all companies
explorium businesses match -f companies.json -o json > matched.json

# Extract business IDs and bulk enrich
cat matched.json | jq -r '.data[].business_id' > ids.txt
explorium businesses bulk-enrich -f ids.txt -o json > enriched.json
```

## CSV Column Names

CSV files for `match`, `enrich-file`, and other file-based commands accept common column name aliases (**case-insensitive**). If no recognized columns are found, the CLI shows an error listing expected vs found columns.

**Business columns:**

| Canonical | Also Accepted |
|-----------|---------------|
| `name` | `company_name`, `company`, `business_name` |
| `domain` | `website`, `url`, `company_domain`, `company_website`, `site` |
| `linkedin_url` | `linkedin`, `linkedin_company_url`, `company_linkedin` |

**Prospect columns:**

| Canonical | Also Accepted |
|-----------|---------------|
| `first_name` | `firstname`, `first` |
| `last_name` | `lastname`, `last`, `surname` |
| `full_name` | `name`, `fullname`, `prospect_name` |
| `email` | `email_address`, `e-mail`, `e_mail` |
| `linkedin` | `linkedin_url`, `linkedin_profile` |
| `company_name` | `company`, `employer`, `organization` |

**Note:** When matching prospects, `full_name` is automatically omitted from the API payload when a strong identifier (`linkedin` or `email`) is present but `company_name` is absent. The API cannot use a name without company context when a direct identifier is available.

## Error Handling

The CLI provides clear error messages:

```bash
# Missing API key
$ explorium businesses search --country us
Error: API key not configured. Run 'explorium config init --api-key YOUR_KEY'

# Invalid filter
$ explorium businesses search --size "invalid"
Error: Invalid size filter. Valid values: 1-10, 11-50, 51-200, ...

# API error
$ explorium businesses enrich --id "invalid_id"
Error: API request failed (404): Business not found
```

## Troubleshooting

### API Key Issues

```bash
# Verify your API key is set
explorium config show

# Test with a simple request
explorium businesses autocomplete --query "test"
```

### Debug Mode

Set the `EXPLORIUM_DEBUG=1` environment variable for verbose output:

```bash
EXPLORIUM_DEBUG=1 explorium businesses search --country us
```

## License

Proprietary - Explorium AI
