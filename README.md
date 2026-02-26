# Clarity Planner

Turn a messy brain-dump into a structured, time-blocked daily plan — powered by Claude.

## Setup

```bash
# 1. Install dependencies (creates .venv + uv.lock automatically)
uv sync

# 2. Add your Anthropic API key
cp .env.example .env
# Edit .env and paste your key: ANTHROPIC_API_KEY=sk-ant-...

# 3. Run
uv run streamlit run app.py
```

## Usage

1. Paste anything — a rough task list, scattered thoughts, random notes
2. Set the time you want your day to start
3. Click **Generate My Plan**

Claude extracts every actionable item, estimates realistic durations, assigns priorities, and builds a time-blocked schedule with 5-minute buffers between tasks.

You can download the full plan as JSON.

## Reproducibility

Dependencies are pinned in `uv.lock`. Anyone cloning this repo gets the exact same environment with `uv sync`.
