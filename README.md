# Swedish Weather Agent

Fetches a 3-day min/max temperature forecast for 10 Swedish regions from
Open-Meteo, appends the results to a cumulative CSV, and (optionally)
uploads it to Google Drive in a folder called "weather sweden".

## Files

- `regions.py` — the 10 region definitions (name, postal codes, lat/lon).
- `weather_agent.py` — main script: fetch -> merge into CSV -> upload to Drive.
- `weather_forecast_sweden.csv` — the cumulative output file (created on first run).
- `weather_agent.log` — run log (append-only, useful for debugging failed runs).
- `test_offline.py` — offline test using mocked API responses (no network needed).

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Run it (without Google Drive)

```bash
python3 weather_agent.py
```

This fetches data for all 10 regions, writes/updates
`weather_forecast_sweden.csv` locally, and logs the run. If Google Drive
credentials aren't set, it logs a warning and skips the upload step —
everything else still works.

## 3. Set up Google Drive access (one-time)

The script uses a Google OAuth 2.0 **refresh token** so it can run
unattended. You need to create OAuth credentials once:

1. Go to https://console.cloud.google.com/ and create (or pick) a project.
2. Enable the **Google Drive API** for that project.
3. Go to "APIs & Services" -> "Credentials" -> "Create Credentials" ->
   "OAuth client ID". Choose **Desktop app** as the application type.
   Download the `client_id` and `client_secret`.
4. Run a one-time authorization flow to get a refresh token. The simplest
   way is the Google OAuth Playground:
   - Go to https://developers.google.com/oauthplayground
   - Click the gear icon, check "Use your own OAuth credentials", and
     enter your client ID/secret.
   - In the scopes list, select `https://www.googleapis.com/auth/drive.file`
     (gives access only to files/folders the app creates — recommended).
   - Click "Authorize APIs", sign in, and grant access.
   - Click "Exchange authorization code for tokens" to get a **refresh token**.

5. Set these as environment variables wherever you run the script:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REFRESH_TOKEN="your-refresh-token"
```

On first run with these set, the script will:
- create the `/weather sweden` folder in your Drive if it doesn't exist
- create `weather_forecast_sweden.csv` inside it
- on every subsequent run, download isn't needed locally — it uses the
  local CSV as the source of truth and overwrites the Drive copy with
  the merged result.

You can revoke access anytime under
Google Account -> Security -> Third-party access -> Remove.

## 4. Scheduling daily runs at 06:00

The script itself does not schedule itself — pick one:

### Option A: cron (Linux/macOS, always-on machine)

```bash
crontab -e
# add this line:
0 6 * * * cd /path/to/weather_agent && /usr/bin/python3 weather_agent.py >> cron.log 2>&1
```

Make sure the environment variables (GOOGLE_CLIENT_ID etc.) are available
to cron — either export them in `/etc/environment`, or source a `.env`
file at the top of a wrapper shell script.

### Option B: Windows Task Scheduler

Create a basic task that runs daily at 06:00, action = "Start a program",
program = `python.exe`, arguments = `weather_agent.py`, start in = the
project folder. Set environment variables via the "Edit Environment
Variables for your account" system dialog.

### Option C: GitHub Actions (no always-on machine needed)

Create `.github/workflows/weather.yml`:

```yaml
name: Daily weather fetch
on:
  schedule:
    - cron: "0 6 * * *"   # 06:00 UTC -- adjust for your timezone
  workflow_dispatch: {}     # allows manual runs too

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python3 weather_agent.py
        env:
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          GOOGLE_REFRESH_TOKEN: ${{ secrets.GOOGLE_REFRESH_TOKEN }}
      - name: Commit updated CSV back to repo (optional)
        run: |
          git config user.name "weather-agent"
          git config user.email "actions@github.com"
          git add weather_forecast_sweden.csv weather_agent.log
          git diff --staged --quiet || git commit -m "Daily weather update"
          git push
```

Store the three Google credentials as encrypted repo secrets under
Settings -> Secrets and variables -> Actions.

## 5. Notes on the CSV schema

| column       | description                              |
|--------------|-------------------------------------------|
| date         | forecast date (YYYY-MM-DD)                |
| region       | region name (e.g. "Stockholm-Malardalen") |
| postal_codes | postal code prefix range (e.g. "10-19")   |
| min_c        | minimum temperature, °C                   |
| max_c        | maximum temperature, °C                   |

Each run fetches a 3-day forecast for all 10 regions (30 rows) and merges
them into the CSV, **replacing** any existing row with the same
`(date, region)` so re-running the same day doesn't create duplicates,
while new dates get appended. Over time the file grows by roughly 3 new
date-rows per region per day (since each day "rolls" the 3-day window
forward by one day, with 2 days overlapping the previous run).
