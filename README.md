# GEO-to-Pipeline Dashboard

> **Peec MCP Challenge — Reporting Automation**
> Built for a B2B SaaS referral marketing platform

A daily-automated analytics dashboard that connects **Peec AI Share of Voice** to qualified pipeline. It proves, with real data, that AI search visibility (ChatGPT, Perplexity, Google AI Overviews) drives revenue.

---

## The Problem

B2B SaaS marketing teams face a dark funnel problem: AI search drives a growing share of inbound pipeline, but there is no way to prove it. Peec data lives in one dashboard. Deals live in HubSpot. Keywords live in Google Search Console. Nobody connects them.

This dashboard closes that gap -- automatically, every day.

---

## How Peec MCP Powers This

The workflow uses Peec in two complementary modes:

### 1. Interactive -- Claude + Peec MCP Server

`src/ingest/peec.py` connects to the Peec MCP server. Used for:
- Ad-hoc prompt-level Share of Voice pulls
- Topic exploration and prompt gap analysis
- Manual deep-dives before automated reporting kicks in

### 2. Automated CI -- GitHub Actions + Peec REST API

`src/ingest/peec_api.py` calls the Peec REST API directly -- no human in the loop.

`.github/workflows/peec-daily-refresh.yml` runs at **06:00 UTC every day**:

1. Pulls a 30-day rolling SoV dataset from Peec by topic and competitor
2. Enforces brand-prompt segregation (brand prompts never contaminate SoV metrics)
3. Filters to active prompts only (prevents archived-prompt baseline drift)
4. Writes two segmented CSVs: `peec_non_brand.csv` and `peec_brand_only.csv`
5. Commits updated data back to the repo -- the dashboard reads fresh data on next load

No manual exports. No stale data. No dashboards that require remembering to check them.

---

## Dashboard: 7 Pages

| Page | What It Shows |
|------|--------------|
| Overview | AI citation share vs. inbound qualified pipeline trend |
| Share of Voice | Brand vs. 5 competitors across topic clusters |
| Keyword Rankings | GSC keyword positions mapped to GEO topic clusters |
| Content Opportunities | High-impression / low-CTR queries with zero content coverage |
| AI Attribution | HubSpot deals segmented by AI search attribution source |
| Win Log | Auto-detected SoV gains and content gaps that drove pipeline |
| Digest & Alerts | Weekly Slack digest + citation threshold alerts |

---

## Real Business Impact

| Metric | Value |
|--------|-------|
| Inbound QP target | 1,000+ / quarter (3x growth goal) |
| AI-attributed deal share | ~25% of inbound pipeline |
| HubSpot deals joined | 2,000+ |
| GSC queries ingested | 20,000+ |
| Content gaps surfaced | 200+ ICP queries with zero existing content |
| Competitors tracked | 5 direct competitors in the referral software category |

---

## Architecture

```
Peec AI MCP Server                 Peec REST API
      |  (interactive)                 |  (CI / headless)
      |                                 |
      v                                 v
 src/ingest/peec.py         src/ingest/peec_api.py
                                        |
                             GitHub Actions cron (06:00 UTC)
                                        |
                              data/processed/*.csv
                                        |
              +--------------------+---------------------+
              |                    |                     |
         HubSpot API      Google Search Console    Streamlit App
         (deals)          (keyword rankings)       src/app.py
              |                    |                     |
              +--------------------+-------------> 7-page Dashboard
```

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/andreacaravello/geo-pipeline-dashboard
cd geo-pipeline-dashboard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Required: PEEC_API_KEY, PEEC_PROJECT_ID, HUBSPOT_API_KEY, GA4_PROPERTY_ID

# 3. Run dashboard
streamlit run src/app.py
```

For the automated daily pull, add `PEEC_API_KEY` and `PEEC_PROJECT_ID` as GitHub Secrets -- the Actions workflow handles everything else.

---

## Tech Stack

| Tool | Role |
|------|------|
| **Peec AI** | MCP server (interactive) + REST API (CI automation) |
| **GitHub Actions** | Daily cron -- pulls and commits fresh SoV data |
| **Streamlit** | 7-page live analytics dashboard |
| **HubSpot API** | Deal-level AI attribution data |
| **Google Search Console API** | Keyword rankings (20k+ queries) |
| **Python** | pandas, httpx, plotly, streamlit |

---

## Challenge Category

**Reporting Automation** -- a repeatable, scheduled workflow that pulls Peec AI data, joins it with HubSpot pipeline and GSC keyword data, and surfaces actionable insights without human intervention.

Built for the [Peec MCP Challenge](https://peec.ai/mcp-challenge) -- April 2026.
