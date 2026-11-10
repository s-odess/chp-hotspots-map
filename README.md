# Real-Time Incident Data ETL Pipeline

A Python pipeline that extracts live incident data from the California Highway Patrol (CHP) public dispatch dashboard, translates dispatch shorthand into plain-English summaries with the Gemini API, and publishes structured JSON to GitHub.

**Status:** The pipeline runs end to end when launched by hand. The demo video shows the command line extracting a live incident and generating its summary. A GitHub Actions workflow is included, and its cron schedule is disabled because the pipeline has not been run on a recurring schedule, owing to Gemini API quota limits on the free tier.

**Demo video:** https://lnkd.in/p/gc9uwAyJ

---

## Why This Project Exists

The CHP dashboard (https://cad.chp.ca.gov/Traffic.aspx) is an ASP.NET WebForms application. Each page interaction carries session state tokens (`__VIEWSTATE`, `__EVENTVALIDATION`), so the extraction layer drives a real headless browser with Playwright. The raw records contain dispatch codes, terse location strings, and coordinates that appear only on each incident's detail page. The pipeline collects those fields and turns them into text that a driver can read.

## How It Works

### 1. Extraction (`engine/chp_hotspots_engine.py`)

Playwright launches headless Chromium, opens the dashboard, waits for the network to go idle, selects the "Hot Spots" search, and reads the incident grid. The script then opens the Details page for every row. It reads latitude and longitude from the detail page with a regular expression and takes the location from the detail page, falling back to the grid column. The output is `live_hotspots.json`, one record per incident with these fields: `Incident_No`, `Time`, `Type`, `Location`, `Latitude`, `Longitude`, and a `Summary` placeholder.

### 2. Summarization (`engine/agent.py`)

The agent reads the JSON, skips records without coordinates, and sends the remaining dispatch fields to Gemini 2.5 Flash through the `google-genai` SDK. The prompt sets the rules: plain English, two to four sentences, dispatch codes translated (for example, 23103 to reckless driving and 118 to traffic collision), the location named early, no headlines, no ALL CAPS, and no coordinates in the text.

- Rate-limit and server errors (429, 503, `RESOURCE_EXHAUSTED`) trigger retries with waits of 15, 30, and 45 seconds.
- A summary that contains a known missing-location phrase counts as unfinished, and the next run regenerates it.
- Each run writes at most three summaries to stay inside the free-tier quota.
- When the quota runs out, the agent saves its progress and writes a placeholder for the remaining records.

### 3. Publishing

When `GITHUB_TOKEN` and `GITHUB_REPO` are set, the scripts can publish `live_hotspots.json` through the GitHub REST API (an authenticated PUT with Base64 content). The GitHub Actions workflow commits the file with git instead.

## Run It Locally

```
pip install -r engine/requirements.txt
playwright install chromium
```

Create `.env.txt` in the repository root:

```
GEMINI_API_KEY=your_key
GITHUB_TOKEN=your_token      # optional, enables publishing through the API
GITHUB_REPO=owner/repo       # optional
```

Run the two stages from the repository root:

```
python engine/chp_hotspots_engine.py
python engine/agent.py
```

Run `python run_pipeline.py` to repeat both stages every 180 seconds until you press Ctrl+C.

## Scheduled Workflow

`.github/workflows/pipeline.yml` runs the extraction and summarization stages, then commits `live_hotspots.json`. It currently runs on manual dispatch. The 30-minute cron schedule is commented out in the file and returns once a scheduled run has been verified. The workflow reads `GEMINI_API_KEY` and `GH_PAT` from repository secrets.

## Known Limitations

- Each extraction run rewrites `live_hotspots.json` with the current incidents and placeholder summaries, so summaries from earlier runs do not carry forward. With the three-summary cap, most records show a placeholder at any given moment.
- Summaries draw on the grid fields, the location, and the coordinates. An earlier version captured more of each detail page, and restoring that depth is the next step.
- The pipeline has no front end. The output is the JSON file.
- The selectors target the dashboard's current element names and IDs. A layout change on the CHP site requires a selector update.
- The free-tier Gemini quota limits throughput.

## Technology

| Layer | Tool |
| --- | --- |
| Language | Python 3.11 |
| Browser automation | Playwright (sync API, headless Chromium) |
| HTML parsing | BeautifulSoup |
| Summarization | Gemini 2.5 Flash through `google-genai` |
| Data format | JSON |
| Publishing | GitHub REST API (`requests`) or git commit in the workflow |
| Scheduling | GitHub Actions (manual dispatch), or the local `run_pipeline.py` loop |
| Configuration | `python-dotenv` and repository secrets |

## Repository Layout

- `engine/chp_hotspots_engine.py`: extraction
- `engine/agent.py`: summarization
- `engine/requirements.txt`: dependencies
- `run_pipeline.py`: local loop that runs both stages
- `live_hotspots.json`: latest output
- `.github/workflows/pipeline.yml`: GitHub Actions workflow
- `fetch_feed.py`, `chp_postback_test.py`, `parse_timeout.py`, `process_hotspots.py`, `test_env.py`: earlier experiments kept for reference (`fetch_feed.py` is a network sniffer, `chp_postback_test.py` is a raw token-replay test, and `process_hotspots.py` is a legacy HTML parser). The current pipeline does not use them.

## Security

Credentials come from environment variables, `.env.txt`, or GitHub Actions secrets. No credentials appear in the code.
