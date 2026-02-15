# Explorium CLI — Full Commands Reference

Generated from `explorium --help` (all subcommands).

## Global Options

All commands accept these options (place BEFORE the subcommand):

```
-c, --config PATH              Path to config file
-o, --output [json|table|csv]  Output format (default: json)
--output-file PATH             Write output to file (clean JSON/CSV, no formatting)
```

---

## Businesses

### `businesses match`

Match companies to get unique business IDs.

```
-n, --name TEXT           Company name
-d, --domain TEXT         Company domain/website
-l, --linkedin TEXT       LinkedIn company URL
-f, --file FILENAME       JSON or CSV file with businesses to match
--summary                 Print match statistics to stderr
--ids-only                Output only matched business IDs, one per line
--output-file PATH        Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses search`

Search and filter businesses.

```
--country TEXT             Country codes (comma-separated)
--size TEXT                Company size ranges (comma-separated)
--revenue TEXT             Revenue ranges (comma-separated)
--industry TEXT            Industry categories (comma-separated)
--tech TEXT                Technologies (comma-separated)
--events TEXT              Event types (comma-separated)
--events-days INTEGER      Days for event recency
--total INTEGER            Total records to collect (auto-paginate)
--page INTEGER             Page number (ignored if --total)
--page-size INTEGER        Results per page
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses enrich`

Enrich a single business with firmographics data.

```
-i, --id TEXT              Business ID (skip matching if provided)
-n, --name TEXT            Company name (for matching)
-d, --domain TEXT          Company domain/website (for matching)
-l, --linkedin TEXT        LinkedIn company URL (for matching)
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses enrich-tech`

Enrich a single business with technographics data (tech stack).

Same options as `businesses enrich`.

### `businesses enrich-financial`

Enrich a single business with financial metrics data.

Same options as `businesses enrich`.

### `businesses enrich-funding`

Enrich a single business with funding and acquisition data.

Same options as `businesses enrich`.

### `businesses enrich-workforce`

Enrich a single business with workforce trends data.

Same options as `businesses enrich`.

### `businesses enrich-traffic`

Enrich a single business with website traffic data.

Same options as `businesses enrich`.

### `businesses enrich-social`

Enrich a single business with social media (LinkedIn posts) data.

Same options as `businesses enrich`.

### `businesses enrich-ratings`

Enrich a single business with employee ratings data.

Same options as `businesses enrich`.

### `businesses enrich-keywords`

Search for keywords on a company's website.

```
-i, --id TEXT              Business ID (skip matching if provided)
-n, --name TEXT            Company name (for matching)
-d, --domain TEXT          Company domain/website (for matching)
-l, --linkedin TEXT        LinkedIn company URL (for matching)
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
-k, --keywords TEXT        Keywords to search (comma-separated)  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses enrich-challenges`

Enrich a public company with business challenges (from 10-K filings).

Same options as `businesses enrich`.

### `businesses enrich-competitive`

Enrich a public company with competitive landscape (from 10-K filings).

Same options as `businesses enrich`.

### `businesses enrich-strategic`

Enrich a public company with strategic insights (from 10-K filings).

Same options as `businesses enrich`.

### `businesses enrich-website-changes`

Enrich a single business with website changes data.

Same options as `businesses enrich`.

### `businesses enrich-webstack`

Enrich a single business with webstack data.

Same options as `businesses enrich`.

### `businesses enrich-hierarchy`

Enrich a single business with company hierarchy data.

Same options as `businesses enrich`.

### `businesses enrich-intent`

Enrich a single business with Bombora intent data.

Same options as `businesses enrich`.

### `businesses bulk-enrich`

Bulk enrich multiple businesses (up to 50).

```
--ids TEXT                 Business IDs (comma-separated)
-f, --file FILENAME        CSV file with 'business_id' column
--match-file FILENAME      JSON file with match params (name, domain) to resolve IDs
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
--summary                  Print match/enrichment statistics to stderr
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses enrich-file`

Match businesses from a file and enrich in one pass.

```
-f, --file FILENAME        CSV or JSON file with businesses to match and enrich  [required]
--types TEXT                Enrichment types, comma-separated: firmographics, all
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
--summary                  Print match/enrichment statistics to stderr
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses lookalike`

Find similar companies.

Same options as `businesses enrich`.

### `businesses autocomplete`

Get autocomplete suggestions for company names.

```
-q, --query TEXT           Search query  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses events list`

List events for businesses.

```
--ids TEXT                 Business IDs (comma-separated)  [required]
--events TEXT              Event types (comma-separated)  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses events enroll`

Enroll businesses for event monitoring.

```
--ids TEXT                 Business IDs (comma-separated)  [required]
--events TEXT              Event types (comma-separated)  [required]
--key TEXT                 Enrollment key  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `businesses events enrollments`

List event enrollments.

```
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

---

## Prospects

### `prospects match`

Match prospects to get unique prospect IDs. Match by email, LinkedIn URL, or full name + company name.

```
--first-name TEXT          First name
--last-name TEXT           Last name
-e, --email TEXT           Email address
-l, --linkedin TEXT        LinkedIn profile URL
--company-name TEXT        Company name (required with first/last name)
-f, --file FILENAME        JSON or CSV file with prospects to match
--summary                  Print match statistics to stderr
--ids-only                 Output only matched prospect IDs, one per line
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects search`

Search and filter prospects.

```
-b, --business-id TEXT     Business IDs (comma-separated)
-f, --file FILENAME        CSV file with 'business_id' column
--job-level TEXT           Job levels (comma-separated: cxo,vp,director,manager,senior,entry)
--department TEXT          Departments (comma-separated)
--job-title TEXT           Job title keywords
--country TEXT             Country codes (comma-separated)
--has-email                Only prospects with email
--has-phone                Only prospects with phone
--experience-min INTEGER   Min total experience (months)
--experience-max INTEGER   Max total experience (months)
--role-tenure-min INTEGER  Min current role tenure (months)
--role-tenure-max INTEGER  Max current role tenure (months)
--max-per-company INTEGER  Max prospects per company (searches each company in parallel)
--total INTEGER            Total records to collect (auto-paginate)
--page INTEGER             Page number (ignored if --total)
--page-size INTEGER        Results per page
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects enrich contacts`

Enrich prospect contact information (email, phone).

```
-i, --id TEXT              Prospect ID (skip matching if provided)
--first-name TEXT          First name (for matching)
--last-name TEXT           Last name (for matching)
-l, --linkedin TEXT        LinkedIn profile URL (for matching)
--company-name TEXT        Company name (for matching)
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects enrich profile`

Enrich prospect professional profile.

Same options as `prospects enrich contacts`.

### `prospects enrich social`

Enrich prospect social media profiles.

Same options as `prospects enrich contacts`.

### `prospects bulk-enrich`

Bulk enrich multiple prospects (up to 50).

**Note:** Output contains only `prospect_id` and enrichment fields — input columns (name, title, company) are not preserved. To keep input columns, use `enrich-file` instead, or join the output with your input file on `prospect_id`.

```
--ids TEXT                 Prospect IDs (comma-separated)
-f, --file FILENAME        CSV file with 'prospect_id' column
--match-file FILENAME      JSON file with match params (full_name, linkedin, company_name) to resolve IDs
--types TEXT                Enrichment types, comma-separated: contacts, profile, all
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
--summary                  Print match/enrichment statistics to stderr
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects enrich-file`

Match prospects from a file and enrich in one pass.

```
-f, --file FILENAME        CSV or JSON file with prospects to match and enrich  [required]
--types TEXT                Enrichment types, comma-separated: contacts, profile, all
--min-confidence FLOAT     Minimum match confidence (0-1, default: 0.8)
--summary                  Print match/enrichment statistics to stderr
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects autocomplete`

Get autocomplete suggestions for prospect names.

```
-q, --query TEXT           Search query  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects statistics`

Get aggregated prospect statistics.

```
-b, --business-id TEXT     Business IDs (comma-separated)  [required]
--group-by TEXT            Fields to group by (comma-separated)
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects events list`

List events for prospects.

```
--ids TEXT                 Prospect IDs (comma-separated)  [required]
--events TEXT              Event types (comma-separated)  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects events enroll`

Enroll prospects for event monitoring.

```
--ids TEXT                 Prospect IDs (comma-separated)  [required]
--events TEXT              Event types (comma-separated)  [required]
--key TEXT                 Enrollment key  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `prospects events enrollments`

List event enrollments.

```
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

---

## Config

### `config init`

Initialize configuration with API key.

```
-k, --api-key TEXT         Your Explorium API key  [required]
--config-path PATH         Custom config file path
```

### `config show`

Show current configuration.

```
--config-path PATH         Config file to show
```

### `config set`

Set a configuration value.

```
KEY                        Configuration key (positional)
VALUE                      Configuration value (positional)
--config-path PATH         Config file to modify
```

---

## Webhooks

### `webhooks create`

Register a new webhook.

```
-p, --partner-id TEXT      Partner identifier  [required]
-u, --url TEXT             Webhook URL  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `webhooks get`

Get webhook configuration.

```
-p, --partner-id TEXT      Partner identifier  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `webhooks update`

Update webhook URL.

```
-p, --partner-id TEXT      Partner identifier  [required]
-u, --url TEXT             New webhook URL  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```

### `webhooks delete`

Delete a webhook.

```
-p, --partner-id TEXT      Partner identifier  [required]
--output-file PATH         Write output to file instead of stdout
-o, --output [json|table|csv]
```
