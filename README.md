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

