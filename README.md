# Personalized Travel Itinerary Planner

Skill Wallet Capstone Project 4: Generative AI | Intelligent SaaS Trip Planning.

Plan less. Wander more. This Streamlit application combines AI-assisted destination
recommendations, geographic route clustering, approximate budget tracking,
customizable day plans, SQLite persistence, and offline PDF/JSON exports.

## Features

- Demo Mode works completely offline with no API key.
- Gemini and Groq provider adapters share one `LLMProvider` interface.
- Destination recommendations are validated as exactly three Pydantic records.
- Haversine distance, deterministic geographic clustering, nearest-neighbor routing,
  and 2-opt route improvement.
- Approximate USD, INR, and destination-local currency calculations.
- Targeted activity swaps, day regeneration, and ten-step undo history.
- SQLite saved-trip library with search, sorting, duplication, notes, and deletion.
- Offline A4 PDF export and portable JSON import/export.

## Project structure

```text
app.py                         Streamlit entry point
core/                          Domain models and application services
ui/                            Streamlit presentation modules
tests/                         Pytest coverage for core behavior
data/trips.db                  Local SQLite database (created at runtime)
```

## Requirements

- Python 3.9 or newer
- Internet access only when using Gemini/Groq or the optional Google Font
- No external database is required

Dependencies are listed in [requirements.txt](./requirements.txt). API keys are
never committed; use [.env.example](./.env.example) or Streamlit secrets.

## Run locally

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Open the URL printed by Streamlit, usually `http://localhost:8501`.

### Demo Mode walkthrough

1. Select **Demo Mode (no key needed)** in the sidebar.
2. Choose “I don't have a destination yet” or enter `Paris`.
3. Select any vibe, duration, budget, party, pace, and interests.
4. Select **Save preferences**.
5. Open **Recommend** and select **Get 3 recommendations**.
6. Select **Plan this trip: Paris** or another recommendation.
7. Open **Itinerary** and select **Generate itinerary**.
8. Open **Customize** to swap an activity, regenerate a day, or undo a change.
9. Open **Saved trips**, save the itinerary, and try both JSON and PDF downloads.

Demo data is deterministic, uses real destinations and coordinates, and requires
no network request.

## AI providers

### Gemini

Set `GEMINI_API_KEY` in `.env` or `.streamlit/secrets.toml`, select Gemini, then
choose a supported model in the sidebar.

### Groq

Set `GROQ_API_KEY` in `.env` or `.streamlit/secrets.toml`, select Groq, then
choose a supported model in the sidebar. The default is
`openai/gpt-oss-120b`; the configured fallback is `openai/gpt-oss-20b`.
Both model IDs are documented on Groq's model pages. Account-level access can
still vary, so the app reports a clear error if both are unavailable.

Example `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "replace-with-your-key"
GROQ_API_KEY = "replace-with-your-key"
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"
```

Use the **Test connection** button before generating recommendations. Never paste
keys into source files or commit the secrets file.

## Streamlit Community Cloud deployment

1. Push this project to a GitHub repository.
2. Open [share.streamlit.io](https://share.streamlit.io).
3. Select **New app** and choose the repository, branch, and `app.py`.
4. Deploy using Python dependencies from `requirements.txt`.
5. Open **Advanced settings > Secrets** and add:

   ```toml
   GEMINI_API_KEY = "replace-with-your-key"
   GROQ_API_KEY = "replace-with-your-key"
   ```

6. Save and reboot the app.
7. Verify Demo Mode first, then test the selected provider.

SQLite storage on Community Cloud is ephemeral and may be lost when the app
restarts or redeploys. Use **Download trip as JSON** for portability and import
the file after a restart.

## Render deployment

Render can run the application as a web service. Use:

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`

Configure `GEMINI_API_KEY` or `GROQ_API_KEY` as encrypted environment variables.
Use a persistent disk if durable SQLite history is required.

## Vercel note

Vercel is optimized for stateless serverless functions and is not a natural
runtime for a long-lived Streamlit process or local SQLite writes. Deploy the
Streamlit app to Streamlit Community Cloud, Render, or another Python host.
Vercel can host a future separate frontend/API layer.

## Supabase/PostgreSQL migration SQL

The current [core/storage.py](./core/storage.py) boundary can be replaced by a
Supabase adapter without changing the UI. A relational migration can start with:

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz not null default now()
);

create table trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  destination text not null,
  country text,
  currency_local text not null default 'USD',
  preferences_json jsonb not null,
  summary text,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table days (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references trips(id) on delete cascade,
  day_number integer not null,
  day_date date,
  theme text not null,
  cluster_area text,
  day_total_usd numeric not null default 0,
  day_total_inr numeric not null default 0,
  day_total_local numeric not null default 0,
  transit_total_min integer not null default 0,
  unique (trip_id, day_number)
);

create table activities (
  id uuid primary key default gen_random_uuid(),
  day_id uuid not null references days(id) on delete cascade,
  slot_type text not null,
  name text not null,
  category text not null,
  description text,
  latitude double precision not null,
  longitude double precision not null,
  area text,
  start_time text,
  duration_min integer not null default 60,
  cost_local numeric not null default 0,
  currency_local text not null default 'USD',
  cost_usd numeric not null default 0,
  cost_inr numeric not null default 0,
  tips text,
  is_vegetarian_friendly boolean not null default true
);

create index trips_user_updated_idx on trips(user_id, updated_at desc);
create index days_trip_idx on days(trip_id, day_number);
create index activities_day_idx on activities(day_id);
```

## Troubleshooting

### Streamlit does not start

Confirm the virtual environment is active and reinstall dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Provider authentication fails

Use Demo Mode to verify the application locally. Then check the provider key,
the selected model, quota, and the **Test connection** result. Keys are read from
environment variables or Streamlit secrets and are not logged.

### Recommendations or itinerary JSON fails validation

The provider layer requests JSON-only output and the parser repairs fenced JSON
and trailing commas. If a live response still fails validation, retry the action
or switch to Demo Mode. Demo Mode is the reliable offline fallback.

### Saved trips are missing

Local trips are stored in `data/trips.db`. Cloud filesystems may be ephemeral.
Import a previously downloaded trip JSON file.

### PDF export fails

Confirm ReportLab is installed from `requirements.txt`. The exporter falls back
to Helvetica and strips unsupported glyphs when a Unicode font is unavailable.

## Screenshots

Add screenshots or a short screen recording here before publishing the capstone.
Recommended captures:

1. Wanderlust hero and preference sidebar.
2. Three recommendation cards.
3. Day-by-day itinerary and budget chart.
4. Customization before/after workflow.
5. Saved trip PDF download controls.

## Known limitations

- Currency rates are editable fallback approximations, not live exchange rates.
- Activity prices, opening hours, and transit times should be confirmed before travel.
- Demo Mode contains two fully detailed Paris days and extends longer trips by
  repeating a safe demo day structure.
- SQLite is local and ephemeral on many hosted platforms.
- Live provider output depends on API availability, model limits, and quota.
- The app does not provide paid map routing, booking, visa advice, or real-time
  emergency monitoring.

## Release validation checklist

- [x] Demo Mode starts without an API key.
- [x] Preferences can be saved and reset.
- [x] Three recommendations are generated and validated.
- [x] An itinerary can be generated and budget totals are visible.
- [x] An activity can be swapped and undone.
- [x] A day can be regenerated.
- [x] A trip can be saved, loaded, duplicated, renamed, and deleted.
- [x] JSON import/export works.
- [x] PDF export begins with a valid `%PDF` header.
- [x] Full test suite passes with `pytest -q`.
