# Real-Time Incident Data ETL Pipeline

A fully autonomous pipeline that extracts live public safety incident data from a legacy government dispatch system, translates raw first-responder shorthand into plain-English summaries using a large language model, and publishes the results to the cloud — on a 30-minute automated cycle with no human intervention.

-----

## The Problem This Solves

California’s CHP (Highway Patrol) publishes live traffic incident data through a public web dashboard. But the underlying system is built on ASP.NET WebForms — a Microsoft framework from the early 2000s that uses rotating cryptographic session tokens (`__VIEWSTATE`, `__EVENTVALIDATION`) to validate every page interaction. A standard HTTP request returns nothing useful; the server detects it isn’t a real browser and drops the connection.

On top of that, the raw data itself is unusable to the public — it’s dense with police radio codes, incident numbers, and GPS coordinates with no context.

This pipeline solves both problems.

-----

## How It Works: Stage by Stage

### Stage 1 — Extraction Engine (`chp_hotspots_engine.py`)

Rather than fighting the session token system with manual HTTP requests, the extraction layer uses **Playwright** to launch a real headless Chromium browser in server memory. The script navigates to the dashboard, waits for the network to go idle (avoiding crashes during the site’s auto-refresh cycles), selects the “Hot Spots” filter from the dropdown, and reads the resulting incident grid.

Critically, it doesn’t stop at the surface table. It loops through every row and programmatically clicks into each incident’s **Details page**, where the precise latitude/longitude coordinates are embedded in hidden anchor tags — data that never appears in the main grid at all.

### Stage 2 — AI Translation Agent (`agent.py`)

The raw extracted data is a structured JSON file, but the content is still machine language: police dispatch codes, terse location abbreviations, and incident type numbers. The agent feeds each record to the **Gemini API** with a tightly constrained prompt.

This is where the engineering discipline matters most. The prompt isn’t open-ended — it enforces hard rules:

- Translate police codes into plain English (e.g., `23103` → reckless driving)
- Weave the location naturally into a 2–4 sentence narrative
- Never use ALL CAPS, bullet points, or template headers
- Never acknowledge missing data — work with what exists

The agent also validates the output. If Gemini returns a summary containing phrases like *“I don’t have the specific location details”*, the script catches that string, flags the record as failed, and retries. If the API quota is exhausted mid-run, it saves progress gracefully rather than corrupting the dataset.

### Stage 3 — Cloud Sync (`push_to_github()`)

Both the extraction engine and the AI agent end with the same function: a direct write to the **GitHub REST API**. The updated JSON is Base64-encoded and sent as an authenticated HTTP PUT request, overwriting the live data file in the repository without a single manual `git commit`. A connected Streamlit app reads from that file, so the public-facing map updates automatically.

### Stage 4 — Orchestration (`pipeline.yml` / `run_pipeline.py`)

Locally, `run_pipeline.py` runs the full sequence on a 180-second loop from the command line, printing live status to the terminal. In production, that same logic is translated into a **GitHub Actions** workflow that spins up a fresh Ubuntu environment every 30 minutes, installs dependencies, runs both scripts, and commits the result — entirely serverless, entirely unattended.

-----

## Technology Stack

|Layer             |Tool                                              |
|------------------|--------------------------------------------------|
|Browser Automation|Playwright (Sync API, headless Chromium)          |
|AI Summarization  |Google Gemini 2.5 Flash via `google-genai` SDK    |
|Data Format       |JSON (structured from unstructured HTML)          |
|Cloud Storage     |GitHub REST API (authenticated PUT)               |
|Orchestration     |GitHub Actions (cron schedule) / `subprocess` loop|
|Language          |Python 3.11                                       |

-----

## Engineering Notes

- **Defensive selectors throughout:** The CHP dashboard undergoes frequent DOM changes. All locators use attribute-based selectors rather than brittle CSS paths, and every navigation step waits for `networkidle` before proceeding.
- **Quota-aware AI calls:** The agent caps itself at 3 Gemini calls per run and backs off progressively on rate-limit errors, preserving daily API quota across the 30-minute pipeline cycles.
- **No credentials in code:** All tokens (`GITHUB_TOKEN`, `GEMINI_API_KEY`) are injected via GitHub Actions secrets or a local `.env` file — never hardcoded.
