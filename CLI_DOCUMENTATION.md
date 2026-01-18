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

Enrich a single business by ID (firmographics data).

```bash
# Enrich Salesforce
explorium businesses enrich --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Enrich Colgate-Palmolive
explorium businesses enrich --id 1006ff12c465532f8c574aeaa4461b16
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

```bash
# Tech stack
explorium businesses enrich-tech --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Financial metrics
explorium businesses enrich-financial --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Funding and acquisitions
explorium businesses enrich-funding --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Workforce trends
explorium businesses enrich-workforce --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Website traffic
explorium businesses enrich-traffic --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# LinkedIn posts
explorium businesses enrich-social --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Employee ratings
explorium businesses enrich-ratings --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Website keyword search
explorium businesses enrich-keywords --id 39ae2ed11b14a4ccb41d35e9d1ba5d11 --keywords "AI,cloud,automation"

# Business challenges (public companies only)
explorium businesses enrich-challenges --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Competitive landscape (public companies only)
explorium businesses enrich-competitive --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Strategic insights (public companies only)
explorium businesses enrich-strategic --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Website changes
explorium businesses enrich-website-changes --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Webstack
explorium businesses enrich-webstack --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Company hierarchy (parent/subsidiaries)
explorium businesses enrich-hierarchy --id 39ae2ed11b14a4ccb41d35e9d1ba5d11

# Bombora intent
explorium businesses enrich-intent --id 39ae2ed11b14a4ccb41d35e9d1ba5d11
```

### `explorium businesses bulk-enrich`

Bulk enrich multiple businesses (up to 50).

```bash
# Enrich Salesforce, Google, and Colgate Palmolive
explorium businesses bulk-enrich --ids "39ae2ed11b14a4ccb41d35e9d1ba5d11,c71497b026909c74b4ab3a4fbfcd122a,1006ff12c465532f8c574aeaa4461b16"
```

### `explorium businesses lookalike`

Find similar companies.

```bash
# Find companies similar to Salesforce
explorium businesses lookalike --id 39ae2ed11b14a4ccb41d35e9d1ba5d11
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

Enrich prospect data.

```bash
# Enrich contacts for Brigitta Ruha (email, phone)
explorium prospects enrich contacts --id a0997d3905e02c919f1f7092ad4947c8e0cddade

# Enrich LinkedIn posts for Sally Massey
explorium prospects enrich social --id 8112e31c5e3a4fc93d4413abeee778b5d4e5c99d

# Enrich professional profile
explorium prospects enrich profile --id a0997d3905e02c919f1f7092ad4947c8e0cddade
```

### `explorium prospects bulk-enrich`

Bulk enrich multiple prospects with contact information (up to 50).

```bash
# Bulk enrich Brigitta Ruha and Sally Massey
explorium prospects bulk-enrich --ids "a0997d3905e02c919f1f7092ad4947c8e0cddade,8112e31c5e3a4fc93d4413abeee778b5d4e5c99d"
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
