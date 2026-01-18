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
| `-o, --output [json\|table]` | Output format (default: json) |
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

# Match multiple businesses from file
explorium businesses match -f companies.json
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
explorium businesses search --country us --page 2 --size 50
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
# Match by name and company
explorium prospects match \
  --first-name "John" \
  --last-name "Doe" \
  --business-id "8adce3ca1cef0c986b22310e369a0793"

# Match by LinkedIn URL
explorium prospects match --linkedin "https://linkedin.com/in/johndoe"

# Match from file
explorium prospects match -f prospects.json
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
```

**Available filters:**

| Option | Description | Example Values |
|--------|-------------|----------------|
| `--business-id` | Business IDs to search within | Required |
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
