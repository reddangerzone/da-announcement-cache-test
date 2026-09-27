# Delightful Assholes announcement automation

This project generates one permanent faction-announcement image from Torn API data.
All dates, comparisons, countdowns, and labels use UTC/TCT.
The files in this directory are intended to live at the deployment repository root,
beside the existing `api.py`.

## Working now

- Detects an unfinished ranked war.
- Distinguishes a future match from an active war.
- Extracts the opponent by faction ID rather than array position.
- Defaults a new match to `negotiating`.
- Calculates the next Tuesday at 05:00 TCT for an enlisted faction.
- Produces a branded PNG and machine-readable state JSON.
- Uses the official DA sunshine artwork in a dark, beveled announcement design
  matching the chain and ranked-war dashboards.
- Fits long faction names and leadership notes safely; oversized notes are
  shortened with a Discord handoff before they can overlap the event list.
- Filters and sorts normalized Torn/faction events.
- Merges Torn competitions and events, respects `fixed_start_time`, and skips malformed ranges.
- Infers enlistment from the latest ranked-war news action since Tuesday 05:00 TCT.
- Loads leadership-selected war status, notes, and faction events from `leadership.json`.
- Includes a password-protected Netlify leadership panel that commits control changes to GitHub.
- Includes an hourly GitHub Actions workflow and manual-run button.
- Refuses to replace the published output when ranked-war collection fails.

## Leadership panel deployment

Deploy this directory as a second Netlify site with `netlify.toml` at its base.
Configure these Netlify environment variables:

- `ADMIN_PASSWORD`: the shared leadership password
- `DA_GITHUB_TOKEN`: a fine-grained token with **Contents: read and write** for this repository only
- `DA_GITHUB_REPOSITORY`: `owner/repository`
- `DA_GITHUB_BRANCH`: normally `main`
- `LEADERSHIP_PATH`: only needed if the file is not at `leadership.json`

The password and GitHub token are read only by the serverless function. They are
never included in the static JavaScript. Each save creates a normal Git commit,
which gives leadership changes history and rollback without requiring a database.

## Local setup

Copy `.env.example` to `.env`, fill in local values, then:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The workflow expects a GitHub Actions secret named `TORN_API_KEYS` containing the
same JSON object used by the existing `api.py`.

The generated public image is available at
`https://YOUR-SITE.netlify.app/announcement.png`.
