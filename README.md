# Real-Time Incident Data ETL Pipeline

A Python pipeline that extracts live incident data from the California Highway Patrol (CHP) public dispatch dashboard, translates dispatch shorthand into plain-English summaries with the Gemini API, and publishes structured JSON to GitHub.

**Status:** The pipeline runs end to end when launched by hand, and the demo video shows a live run. A GitHub Actions workflow is included, and its cron schedule is disabled because the pipeline has not been run on a recurring schedule, owing to Gemini API quota limits on the free tier.

**Demo video:** [chp-pipeline-demo.mp4](chp-pipeline-demo.mp4), a screen recording of a live command line run in Ubuntu under WSL. It shows extraction of 14 incidents, Gemini summaries for three of them, the GitHub sync, and the runner entering its 180-second wait.

---

## Why This Project Exists

The CHP dashboard (https://cad.chp.ca.gov/Traffic.aspx) is an ASP.NET WebForms application. Each page interaction carries session state tokens (`__VIEWSTATE`, `__EVENTVALIDATION`), so the extraction layer drives a real headless browser with Playwright. The raw records contain dispatch codes, terse location strings, and coordinates that appear only on each incident's detail page. The pipeline collects those fields and turns them into text that a driver can read.

## How It Works

### 1. Extraction (`engine/chp_hotspots_engine.py`)

Playwright launches headless Chromium, opens the dashboard, waits for the network to go idle, selects the "Hot Spots" search, and reads the incident grid. The script then opens the Details page for every row. From each detail page it reads the coordinates with a regular expression, the location, and, when the page provides it, the dispatch activity log from the `gvIncidentDetails` table. The output is `live_hotspots.json`, one record per incident with these fields: `Incident_No`, `Time`, `Type`, `Location`, `Latitude`, `Longitude`, `Raw_Details`, and a `Summary` placeholder. When a timeout or error occurs on one incident, the script logs it and moves on to the next.

### 2. Summarization (`engine/agent.py`)

The agent reads the JSON, skips records without coordinates, and sends the remaining dispatch fields to Gemini 2.5 Flash through the `google-genai` SDK. The prompt sets the rules: plain English, two to four sentences, dispatch codes translated (for example, 23103 to reckless driving and 118 to traffic collision), the location named early, no headlines, no ALL CAPS, and no coordinates in the text.

- Rate-limit and server errors (429, 503, `RESOURCE_EXHAUSTED`) trigger retries with waits of 15, 30, and 45 seconds.
- Any other API error stops summarization, saves the current state, and leaves a placeholder on the affected record.
- `MAX_PER_RUN` caps each run at three summaries to stay inside the free-tier quota.
- `FORCE_REFRESH` clears existing summaries at the start of each run, a setting meant for demos. With it set to `False`, the agent keeps finished summaries and regenerates only unfinished ones, including any summary that contains missing-location wording.

### 3. Orchestration (`engine/run_pipeline.py`)

The runner executes extraction and then summarization every 180 seconds, and the output of each stage streams live to the terminal. When a stage exits with an error, the runner prints a failure message, skips the remaining stage, and starts the next cycle after the interval.

### 4. Publishing

When `GITHUB_TOKEN` and `GITHUB_REPO` are set, both stages publish `live_hotspots.json` through the GitHub REST API (an authenticated PUT with Base64 content). The GitHub Actions workflow commits the file with git instead.

## Run It Locally

Use Python 3.11 or newer. Run these commands from the repository root:

```
cd engine
pip install -r requirements.txt
python -m playwright install chromium
```

Create a file named `.env.txt` in the `engine` folder:

```
GEMINI_API_KEY=your_key
GITHUB_TOKEN=your_token      # optional, enables publishing through the API
GITHUB_REPO=owner/repo       # optional
```

Start the loop:

```
python run_pipeline.py
```

Press Ctrl+C to stop it. Run a single stage with `python chp_hotspots_engine.py` or `python agent.py` from the `engine` folder.

I filmed the demo in Ubuntu under WSL. On the Windows machine I used, Smart App Control blocked a compiled dependency of Playwright (`greenlet`), so the pipeline would not start there. Linux programs fall outside that block, and the same code ran unchanged in Ubuntu. If you see the Windows message "An Application Control policy has blocked this file," run the pipeline in WSL.

## Scheduled Workflow

`.github/workflows/pipeline.yml` runs the extraction and summarization stages on Python 3.11, then commits `live_hotspots.json`. It currently runs on manual dispatch. The 30-minute cron schedule is commented out in the file and returns once a scheduled run has been verified. The workflow reads `GEMINI_API_KEY` and `GH_PAT` from repository secrets.

## Known Limitations

- In current runs the script does not find the detail-page log table and reports "Log details unavailable," so summaries rest on the incident type, time, and location. An earlier version captured more of each detail page, and restoring that depth is the next step.
- Each run summarizes at most three incidents, so most records in `live_hotspots.json` have no summary at any given time.
- The pipeline has no front end. An earlier attempt at a map front end never displayed correctly, so the output is the JSON file.
- The selectors target the dashboard's current element names and IDs. A layout change on the CHP site requires a selector update.
- The free-tier Gemini quota limits throughput.

## Technology

| Layer | Tool |
| --- | --- |
| Language | Python 3.11 or newer |
| Browser automation | Playwright (sync API, headless Chromium) |
| HTML parsing | BeautifulSoup |
| Summarization | Gemini 2.5 Flash through `google-genai` |
| Data format | JSON |
| Publishing | GitHub REST API (`requests`) or git commit in the workflow |
| Orchestration | `engine/run_pipeline.py` loop, or GitHub Actions (manual dispatch) |
| Configuration | `python-dotenv` and repository secrets |

## Repository Layout

- `engine/chp_hotspots_engine.py`: extraction
- `engine/agent.py`: summarization
- `engine/run_pipeline.py`: runner that executes both stages in a loop
- `engine/requirements.txt`: dependencies
- `live_hotspots.json`: latest output published by the sync step
- `chp-pipeline-demo.mp4`: demo video of a live run
- `.github/workflows/pipeline.yml`: GitHub Actions workflow
- `fetch_feed.py`, `chp_postback_test.py`, `parse_timeout.py`, `process_hotspots.py`, `test_env.py`: earlier experiments kept for reference (`fetch_feed.py` is a network sniffer, `chp_postback_test.py` is a raw token-replay test, and `process_hotspots.py` is a legacy HTML parser). The current pipeline does not use them.

## Security

Credentials come from environment variables, `.env.txt`, or GitHub Actions secrets. No credentials appear in the code.
