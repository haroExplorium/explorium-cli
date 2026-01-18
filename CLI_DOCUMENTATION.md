# Explorium CLI Documentation

A command-line interface for interacting with the Explorium API.

## Installation

```bash
# Copy binary to system path
sudo cp dist/explorium /usr/local/bin/

# Or add to PATH
export PATH="$PATH:/path/to/dist"
```

## Global Options

These options apply to all commands and **must be placed BEFORE the command**:

| Option | Description |
|--------|-------------|
| `-o, --output` | Output format: `json` (default) or `table` |
| `-c, --config` | Path to config file (default: `~/.explorium/config.yaml`) |
| `--help` | Show help message |

**Example:**
```bash
# Correct - global option before command
explorium -o table businesses search --country us

# Wrong - will fail
explorium businesses search --country us -o table
```

---

## Configuration Commands

### `explorium config set`

Set configuration values.

```bash
# Set API key (required for all API operations)
explorium config set --api-key YOUR_API_KEY

# Set custom API URL
explorium config set --api-url https://api.explorium.ai
```

### `explorium config show`

Display current configuration.

```bash
explorium config show
```

### `explorium config clear`

Clear all configuration.

```bash
explorium config clear
```

---

## Business Commands

### `explorium businesses match`

Match businesses to get unique business IDs.

```bash
# Match by company name
explorium businesses match --name "Salesforce"

# Match by domain
explorium businesses match --domain "salesforce.com"

# Match by LinkedIn URL
explorium businesses match --linkedin "https://linkedin.com/company/salesforce"

# Batch match from JSON file
explorium businesses match --file companies.json
```

### `explorium businesses search`

Search and filter businesses.

```bash
# Search by country (alpha-2 codes)
explorium businesses search --country us

# Search by multiple countries
explorium businesses search --country "us,ca,gb"

# Search by company size
explorium businesses search --size "51-200"

# Search by revenue range
explorium businesses search --revenue "10M-25M"

# Search by technologies
explorium businesses search --tech "Python,AWS"

# Combined filters with pagination
explorium businesses search --country us --size "51-200" --page 1 --page-size 50
```

**Size ranges:** `1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+`

**Revenue ranges:** `0-500K`, `500K-1M`, `1M-5M`, `5M-10M`, `10M-25M`, `25M-75M`, `75M-200M`, `200M-500M`, `500M-1B`, `1B-10B`, `10B+`

### `explorium businesses enrich`

Enrich a single business with firmographics data. You can provide either a business ID directly, or use match parameters (name, domain, linkedin) to automatically resolve the ID.

**Using ID directly:**
```bash
# Enrich Salesforce by ID
explorium businesses enrich --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Enrich Colgate-Palmolive by ID
explorium businesses enrich --id 1006ff12c465532f8c574aeaa4461b16
```

**Using match parameters (enrich without knowing the ID):**
```bash
# Enrich Salesforce by company name
explorium businesses enrich --name "Salesforce"

# Enrich Google by domain
explorium businesses enrich --domain "google.com"

# Enrich Colgate-Palmolive by LinkedIn URL
explorium businesses enrich --linkedin "https://linkedin.com/company/colaboratoolive"

# Combine match parameters for better accuracy
explorium businesses enrich --name "Starbucks" --domain "starbucks.com"
```

**Match confidence threshold:**

By default, the CLI requires 80% match confidence. You can adjust this:
```bash
# Accept lower confidence matches (useful for less common companies)
explorium businesses enrich --name "Acme Corp" --min-confidence 0.5

# Require higher confidence (more strict matching)
explorium businesses enrich --name "Apple" --min-confidence 0.95
```

When a match confidence is below the threshold, the CLI shows suggestions:
```
Error: Best match confidence (0.65) is below threshold (0.80). Found 3 potential match(es).

Suggestions (try --min-confidence to lower threshold):
  1. Acme Corporation (ID: abc123..., confidence: 0.65)
  2. Acme Industries (ID: def456..., confidence: 0.52)
  3. Acme LLC (ID: ghi789..., confidence: 0.48)
```

### Business Enrichment Types

The CLI supports multiple enrichment types for businesses:

| Command | Description |
|---------|-------------|
| `enrich` | Firmographics data (basic company info) |
| `enrich-tech` | Technographics data (tech stack) |
| `enrich-financial` | Financial metrics and indicators |
| `enrich-funding` | Funding and acquisition data |
| `enrich-workforce` | Workforce trends and department distribution |
| `enrich-traffic` | Website traffic metrics |
| `enrich-social` | Social media / LinkedIn posts |
| `enrich-ratings` | Employee ratings (Glassdoor-style) |
| `enrich-keywords` | Website keyword search (requires --keywords) |
| `enrich-challenges` | Business challenges (public companies, 10-K) |
| `enrich-competitive` | Competitive landscape (public companies, 10-K) |
| `enrich-strategic` | Strategic insights (public companies, 10-K) |
| `enrich-website-changes` | Website changes tracking |
| `enrich-webstack` | Website technology stack |
| `enrich-hierarchy` | Company hierarchy (parent/subsidiaries) |
| `enrich-intent` | Bombora intent signals |

**Using ID:**
```bash
# Tech stack for Salesforce
explorium businesses enrich-tech --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Financial metrics for Colgate-Palmolive
explorium businesses enrich-financial --id 1006ff12c465532f8c574aeaa4461b16

# Funding and acquisitions for Google
explorium businesses enrich-funding --id c71497b026909c74b4ab3a4fbfcd122a
```

**Using match parameters (no ID required):**
```bash
# Tech stack - what technologies does Salesforce use?
explorium businesses enrich-tech --name "Salesforce"
explorium businesses enrich-tech --domain "salesforce.com"

# Financial metrics for Microsoft
explorium businesses enrich-financial --name "Microsoft" --domain "microsoft.com"

# Funding and acquisitions for Stripe
explorium businesses enrich-funding --name "Stripe"

# Workforce trends for Amazon
explorium businesses enrich-workforce --domain "amazon.com"

# Website traffic for Netflix
explorium businesses enrich-traffic --name "Netflix"

# LinkedIn posts for HubSpot
explorium businesses enrich-social --name "HubSpot"

# Employee ratings for Glassdoor
explorium businesses enrich-ratings --domain "glassdoor.com"

# Website keyword search - does Apple mention "AI" on their website?
explorium businesses enrich-keywords --name "Apple" --keywords "AI,machine learning,privacy"

# Business challenges for Tesla (public company, from 10-K filings)
explorium businesses enrich-challenges --name "Tesla"

# Competitive landscape for Coca-Cola (public company)
explorium businesses enrich-competitive --name "Coca-Cola"

# Strategic insights for JPMorgan (public company)
explorium businesses enrich-strategic --name "JPMorgan Chase"

# Website changes tracking for Shopify
explorium businesses enrich-website-changes --domain "shopify.com"

# Webstack - what does Airbnb's website run on?
explorium businesses enrich-webstack --name "Airbnb"

# Company hierarchy for Johnson & Johnson
explorium businesses enrich-hierarchy --name "Johnson & Johnson"

# Bombora intent signals for Zoom
explorium businesses enrich-intent --name "Zoom Video Communications"
```

### `explorium businesses bulk-enrich`

Bulk enrich multiple businesses (up to 50).

**Using IDs:**
```bash
# Enrich Salesforce, Google, and Colgate Palmolive by IDs
explorium businesses bulk-enrich --ids "39ae2ed11b14a4ccb41d35e9d1ba5d11,c71497b026909c74b4ab3a4fbfcd122a,1006ff12c465532f8c574aeaa4461b16"

# From a file with IDs (one per line)
explorium businesses bulk-enrich --file business_ids.txt
```

**Using match file (no IDs required):**

Create a JSON file `companies_to_enrich.json`:
```json
[
  {"name": "Salesforce", "domain": "salesforce.com"},
  {"name": "HubSpot", "domain": "hubspot.com"},
  {"name": "Zendesk"},
  {"domain": "freshworks.com"},
  {"linkedin_url": "https://linkedin.com/company/intercom"}
]
```

Then run:
```bash
# Bulk enrich by resolving company names/domains to IDs automatically
explorium businesses bulk-enrich --match-file companies_to_enrich.json

# With lower confidence threshold
explorium businesses bulk-enrich --match-file companies_to_enrich.json --min-confidence 0.6
```

### `explorium businesses lookalike`

Find similar companies.

**Using ID:**
```bash
# Find companies similar to Salesforce by ID
explorium businesses lookalike --id 39ae2ed11b14a4ccb41d35e9d1ba5d11
```

**Using match parameters:**
```bash
# Find companies similar to Salesforce (without knowing the ID)
explorium businesses lookalike --name "Salesforce"

# Find companies similar to Stripe
explorium businesses lookalike --domain "stripe.com"

# Find companies similar to Notion
explorium businesses lookalike --name "Notion" --domain "notion.so"
```

### `explorium businesses autocomplete`

Get company name suggestions.

```bash
explorium businesses autocomplete --query "sales"
```

### Business Events

```bash
# List events for Salesforce (event types required)
explorium businesses events list --ids "39ae2ed11b14a4ccb41d35e9d1ba5d11" --events "new_funding_round,new_product"

# Enroll Salesforce for event monitoring
explorium businesses events enroll --ids "39ae2ed11b14a4ccb41d35e9d1ba5d11" --events "new_funding_round" --key my-key

# List enrollments
explorium businesses events enrollments
```

**Business event types:** `ipo_announcement`, `new_funding_round`, `new_investment`, `new_product`, `new_office`, `closing_office`, `new_partnership`, `increase_in_engineering_department`, `increase_in_sales_department`, `hiring_in_engineering_department`, `hiring_in_sales_department`, and more.

---

## Prospect Commands

### `explorium prospects match`

Match prospects to get unique prospect IDs.

```bash
# Match by LinkedIn URL
explorium prospects match --linkedin "https://www.linkedin.com/in/brigittaruha/"

# Match by name and company
explorium prospects match --first-name "Sally" --last-name "Massey" --company-name "Colgate-Palmolive"
```

### `explorium prospects search`

Search and filter prospects.

```bash
# Search within Colgate Palmolive
explorium prospects search --business-id "1006ff12c465532f8c574aeaa4461b16"

# Search executives at Colgate Palmolive
explorium prospects search --business-id 1006ff12c465532f8c574aeaa4461b16 --job-level "cxo,vp,director"

# Search by department at Salesforce
explorium prospects search --business-id 39ae2ed11b14a4ccb41d35e9d1ba5d11 --department "Engineering,Sales"

# Search with contact filters at Google
explorium prospects search --business-id c71497b026909c74b4ab3a4fbfcd122a --has-email --has-phone

# Combined filters with pagination
explorium prospects search --business-id 1006ff12c465532f8c574aeaa4461b16 --job-level cxo --page 1 --page-size 25
```

### `explorium prospects enrich`

Enrich prospect data. You can provide either a prospect ID directly, or use match parameters (name, linkedin, company) to automatically resolve the ID.

**Using ID:**
```bash
# Enrich contacts for Brigitta Ruha by ID (email, phone)
explorium prospects enrich contacts --id a0997d3905e02c919f1f7092ad4947c8e0cddade

# Enrich LinkedIn posts for Sally Massey by ID
explorium prospects enrich social --id 8112e31c5e3a4fc93d4413abeee778b5d4e5c99d

# Enrich professional profile by ID
explorium prospects enrich profile --id a0997d3905e02c919f1f7092ad4947c8e0cddade
```

**Using match parameters (enrich without knowing the ID):**
```bash
# Get contact info for Satya Nadella at Microsoft
explorium prospects enrich contacts --first-name "Satya" --last-name "Nadella" --company-name "Microsoft"

# Get contact info by LinkedIn URL
explorium prospects enrich contacts --linkedin "https://linkedin.com/in/satyanadella"

# Get LinkedIn posts for Marc Benioff
explorium prospects enrich social --first-name "Marc" --last-name "Benioff" --company-name "Salesforce"

# Get professional profile for Sundar Pichai
explorium prospects enrich profile --first-name "Sundar" --last-name "Pichai" --company-name "Google"

# With lower confidence threshold for less prominent prospects
explorium prospects enrich contacts --first-name "John" --last-name "Smith" --company-name "Acme Corp" --min-confidence 0.6
```

**Available enrichment types:**
| Command | Description |
|---------|-------------|
| `contacts` | Email addresses and phone numbers |
| `social` | LinkedIn posts and activity |
| `profile` | Full professional profile (experience, education, skills) |

### `explorium prospects bulk-enrich`

Bulk enrich multiple prospects with contact information (up to 50).

**Using IDs:**
```bash
# Bulk enrich by prospect IDs
explorium prospects bulk-enrich --ids "a0997d3905e02c919f1f7092ad4947c8e0cddade,8112e31c5e3a4fc93d4413abeee778b5d4e5c99d"

# From a file with IDs (one per line)
explorium prospects bulk-enrich --file prospect_ids.txt
```

**Using match file (no IDs required):**

Create a JSON file `prospects_to_enrich.json`:
```json
[
  {"full_name": "Satya Nadella", "company_name": "Microsoft"},
  {"full_name": "Marc Benioff", "company_name": "Salesforce"},
  {"linkedin": "https://linkedin.com/in/sundarpichai"},
  {"full_name": "Tim Cook", "company_name": "Apple"}
]
```

Then run:
```bash
# Bulk enrich by resolving names/linkedin to IDs automatically
explorium prospects bulk-enrich --match-file prospects_to_enrich.json

# With lower confidence threshold
explorium prospects bulk-enrich --match-file prospects_to_enrich.json --min-confidence 0.6
```

### Prospect Events

```bash
# List events for prospects (event types required)
explorium prospects events list --ids "a0997d3905e02c919f1f7092ad4947c8e0cddade" --events "prospect_changed_company"

# Enroll for job change monitoring
explorium prospects events enroll --ids "a0997d3905e02c919f1f7092ad4947c8e0cddade" --events "prospect_changed_company" --key my-key

# List enrollments
explorium prospects events enrollments
```

**Prospect event types:** `prospect_changed_role`, `prospect_changed_company`, `prospect_job_start_anniversary`

---

## Webhook Commands

> **Note:** Webhook commands require partner access. Contact Explorium for partner credentials.

```bash
# Create webhook
explorium webhooks create --partner-id YOUR_PARTNER_ID --url "https://example.com/webhook"

# Get webhook details
explorium webhooks get --partner-id YOUR_PARTNER_ID

# Update webhook
explorium webhooks update --partner-id YOUR_PARTNER_ID --url "https://new-url.com/webhook"

# Delete webhook
explorium webhooks delete --partner-id YOUR_PARTNER_ID
```

---

## Output Formats

```bash
# JSON (default) - Enrich Salesforce
explorium businesses enrich --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Table format
explorium -o table businesses search --country us
```

---

## Configuration File

Default location: `~/.explorium/config.yaml`

```yaml
api_key: your-api-key-here
api_url: https://api.explorium.ai
```

Use custom config:
```bash
explorium -c /path/to/config.yaml businesses search --country us
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `config set/show/clear` | Manage configuration |
| `businesses match` | Match businesses to IDs |
| `businesses search` | Search/filter businesses |
| `businesses enrich` | Enrich with firmographics |
| `businesses enrich-tech` | Enrich with technographics |
| `businesses enrich-financial` | Enrich with financial metrics |
| `businesses enrich-funding` | Enrich with funding/acquisitions |
| `businesses enrich-workforce` | Enrich with workforce trends |
| `businesses enrich-traffic` | Enrich with website traffic |
| `businesses enrich-social` | Enrich with LinkedIn posts |
| `businesses enrich-ratings` | Enrich with employee ratings |
| `businesses enrich-keywords` | Search keywords on website |
| `businesses enrich-challenges` | Business challenges (10-K) |
| `businesses enrich-competitive` | Competitive landscape (10-K) |
| `businesses enrich-strategic` | Strategic insights (10-K) |
| `businesses enrich-website-changes` | Enrich with website changes |
| `businesses enrich-webstack` | Enrich with webstack data |
| `businesses enrich-hierarchy` | Enrich with company hierarchy |
| `businesses enrich-intent` | Enrich with Bombora intent |
| `businesses bulk-enrich` | Bulk enrich businesses |
| `businesses lookalike` | Find similar companies |
| `businesses autocomplete` | Company name suggestions |
| `businesses events list/enroll/enrollments` | Event operations |
| `prospects match` | Match prospects to IDs |
| `prospects search` | Search/filter prospects |
| `prospects enrich contacts/social/profile` | Enrich prospects |
| `prospects bulk-enrich` | Bulk enrich prospects |
| `prospects events list/enroll/enrollments` | Event operations |
| `webhooks create/get/update/delete` | Webhook management (partner access) |

---

## Match-Based Enrichment

All enrichment commands support **match-based enrichment** - you can enrich without knowing the ID by providing match parameters.

### Business Match Parameters

| Option | Description |
|--------|-------------|
| `--id` | Direct business ID (skips matching) |
| `--name` | Company name for matching |
| `--domain` | Company domain/website for matching |
| `--linkedin` | LinkedIn company URL for matching |
| `--min-confidence` | Minimum match confidence (0-1, default: 0.8) |

### Prospect Match Parameters

| Option | Description |
|--------|-------------|
| `--id` | Direct prospect ID (skips matching) |
| `--first-name` | First name for matching |
| `--last-name` | Last name for matching |
| `--linkedin` | LinkedIn profile URL for matching |
| `--company-name` | Company name for matching |
| `--min-confidence` | Minimum match confidence (0-1, default: 0.8) |

### Quick Examples

```bash
# Business enrichment without ID
explorium businesses enrich --name "Salesforce"
explorium businesses enrich-tech --domain "google.com"
explorium businesses lookalike --name "Stripe"

# Prospect enrichment without ID
explorium prospects enrich contacts --first-name "Satya" --last-name "Nadella" --company-name "Microsoft"
explorium prospects enrich profile --linkedin "https://linkedin.com/in/marcbenioff"

# Bulk enrichment with match file
explorium businesses bulk-enrich --match-file companies.json
explorium prospects bulk-enrich --match-file prospects.json
```
