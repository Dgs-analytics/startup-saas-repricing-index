# Data Sources & Methodology

## Internet Archive Wayback Machine CDX API

This project uses the **Wayback Machine CDX API** to retrieve historical snapshots of SaaS pricing pages.

### API Endpoint


### Query Parameters Used
- `url`: Domain to search (e.g., `slack.com`)
- `matchType=domain`: Match all subdomains
- `output=json`: Return JSON format
- `filter=statuscode:200`: Only successful HTTP 200 responses
- `filter=mimetype:text/html`: Only HTML pages
- `collapse=digest`: Deduplicate by content hash (SHA-256)

### Deduplication Strategy
The CDX API's `collapse=digest` parameter groups snapshots by their SHA-256 content hash. This ensures that identical pricing pages captured on different dates are counted as a single unique event. For example:
- 10 snapshots captured on different dates with identical HTML content = 1 unique event
- Ensures we measure pricing page *revisions*, not Wayback crawl frequency

### Rate Limiting
- 5 requests per second per domain
- Exponential backoff: 1s → 2s → 4s on 429 (Too Many Requests)
- Max 10 retries per request

### Data Limitations
1. **Incomplete coverage** — Wayback Machine does not crawl every website equally; popular sites have more snapshots
2. **JavaScript rendering** — Wayback Machine serves static HTML snapshots; JavaScript-rendered pricing is not captured
3. **Crawl frequency bias** — High-traffic sites are crawled more frequently, potentially inflating repricing frequency estimates
4. **Historical gaps** — Early internet years have sparse coverage; most data is from 2010 onwards

### Reproducibility
All data is publicly accessible via the Wayback Machine CDX API. To reproduce:
1. Clone the repository
2. Run `python main.py`
3. All 8,270+ snapshots are re-downloaded from Internet Archive (4-6 hours)
4. Metrics are recalculated deterministically from raw HTML

### Metrics Definitions

**Repricing Frequency:** Median number of unique pricing page versions per year, calculated as:
- Total unique events ÷ years in archive lifespan

**Annual Repricing Trends:** Count of unique pricing events per calendar year

**Lifespan:** Days between the earliest and latest snapshot in Wayback Machine for each domain

### What This IS NOT
- ❌ This does NOT measure actual price changes (requires parsing pricing tables)
- ❌ This does NOT account for products or plan variations
- ❌ This does NOT measure feature changes
- ✅ This ONLY measures how frequently the entire pricing page is revised