# Clarity Planner

Turn a messy brain-dump into a structured, time-blocked daily plan using Claude.

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

<<<<<<< HEAD
1. Paste anything — a rough task list, scattered thoughts, random notes
2. Set the time you want your day to start
3. Click **Generate My Plan**

Claude extracts every actionable item, estimates realistic durations, assigns context-aware transition buffers between tasks, and builds a time-blocked schedule ordered by priority.

Download the result as an `.ics` file to import all events directly into Google Calendar or Apple Calendar.
=======
1. Paste anything including a rough task list, scattered thoughts, random notes
2. Set the time you want your day to start
3. Click **Generate My Plan**

Claude extracts every actionable item, estimates realistic durations, assigns priorities, and builds a time-blocked schedule with buffers between tasks.

You can download the full plan as JSON.
>>>>>>> 502ffcbe746a3a1717c50b3aa25d5f34de3ec2df

## Reproducibility

Dependencies are pinned in `uv.lock`. Anyone cloning this repo gets the exact same environment with `uv sync`.
