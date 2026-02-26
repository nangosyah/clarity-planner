import os
import json
import uuid
import anthropic
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clarity Planner",
    page_icon="🗓️",
    layout="wide",
)

# ── Styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { max-width: 1100px; padding-top: 2rem; }
    .task-card {
        background: #f8f9fa;
        border-left: 4px solid #4c72b0;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }
    .task-card.high   { border-color: #d64045; }
    .task-card.medium { border-color: #f0a500; }
    .task-card.low    { border-color: #43aa8b; }
    .time-badge {
        display: inline-block;
        background: #e9ecef;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .priority-badge {
        display: inline-block;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
    }
    .priority-badge.high   { background: #d64045; }
    .priority-badge.medium { background: #f0a500; }
    .priority-badge.low    { background: #43aa8b; }
    .cal-btn {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        text-decoration: none;
        cursor: pointer;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# ── Claude helpers ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a productivity assistant that extracts and structures tasks from unorganised text.

Given a brain-dump of thoughts, tasks, or a to-do list, you MUST return a single valid JSON object with this exact structure:

{
  "summary": "One sentence overview of the day's goals",
  "tasks": [
    {
      "title": "Short task title",
      "description": "What needs to be done",
      "duration_minutes": 30,
      "priority": "high|medium|low",
      "category": "Work|Personal|Admin|Learning|Health|Other"
    }
  ]
}

Rules:
- Extract every actionable item you find.
- Estimate realistic durations (15–180 min). Default to 30 min if unclear.
- Assign priority based on urgency/importance cues in the text. Default to "medium".
- Order tasks from highest to lowest priority.
- Return ONLY the JSON object — no markdown fences, no explanation."""


def parse_brain_dump(text: str, start_time: datetime) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not set. Add it to a .env file or Streamlit secrets.")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)

    with st.spinner("Thinking through your tasks…"):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )

    raw = next(
        (block.text for block in response.content if block.type == "text"), "{}"
    )

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        st.error("Claude returned unexpected output. Try rephrasing your input.")
        st.code(raw)
        st.stop()

    # Attach computed start/end datetimes
    cursor = start_time
    for task in plan.get("tasks", []):
        task["start"] = cursor.strftime("%H:%M")
        task["start_dt"] = cursor.isoformat()
        duration = int(task.get("duration_minutes", 30))
        cursor += timedelta(minutes=duration)
        task["end"] = cursor.strftime("%H:%M")
        task["end_dt"] = cursor.isoformat()
        cursor += timedelta(minutes=5)  # 5-min buffer

    return plan


# ── iCalendar generator ───────────────────────────────────────────────────────
PRIORITY_MAP = {"high": 1, "medium": 5, "low": 9}


def build_ics(plan: dict) -> str:
    """Return a valid .ics file string for all tasks in the plan."""
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def ics_dt(iso: str) -> str:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y%m%dT%H%M%S")  # local time, no Z

    def fold(line: str) -> str:
        """iCal line folding: max 75 octets per line."""
        if len(line) <= 75:
            return line
        chunks = [line[:75]]
        line = line[75:]
        while line:
            chunks.append(" " + line[:74])
            line = line[74:]
        return "\r\n".join(chunks)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Clarity Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Clarity Plan {datetime.now().strftime('%d %b %Y')}",
    ]

    for task in plan.get("tasks", []):
        priority = task.get("priority", "medium").lower()
        desc = task.get("description", "").replace("\n", "\\n").replace(",", "\\,")
        title = task.get("title", "Task").replace(",", "\\,")
        category = task.get("category", "Other")

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@clarity-planner",
            f"DTSTAMP:{now_stamp}",
            fold(f"DTSTART:{ics_dt(task['start_dt'])}"),
            fold(f"DTEND:{ics_dt(task['end_dt'])}"),
            fold(f"SUMMARY:{title}"),
            fold(f"DESCRIPTION:{desc}"),
            f"CATEGORIES:{category}",
            f"PRIORITY:{PRIORITY_MAP.get(priority, 5)}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# ── Google Calendar single-event URL ─────────────────────────────────────────
def gcal_url(task: dict) -> str:
    from urllib.parse import urlencode, quote

    def gcal_dt(iso: str) -> str:
        return datetime.fromisoformat(iso).strftime("%Y%m%dT%H%M%S")

    params = {
        "action": "TEMPLATE",
        "text": task.get("title", "Task"),
        "dates": f"{gcal_dt(task['start_dt'])}/{gcal_dt(task['end_dt'])}",
        "details": task.get("description", ""),
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


# ── UI ────────────────────────────────────────────────────────────────────────
st.title("🗓️ Clarity Planner")
st.caption("Turn your messy thoughts into a structured time-blocked plan.")

col_input, col_options = st.columns([3, 1])

with col_input:
    brain_dump = st.text_area(
        "Paste your brain-dump, task list, or rough notes here",
        height=220,
        placeholder=(
            "e.g. Need to finish the report for Sarah by EOD, also have to reply to "
            "the client email about pricing, gym session, pick up groceries, call mum, "
            "read chapter 3 of the book I started, review pull request from Jake…"
        ),
    )

with col_options:
    st.markdown("**Options**")
    start_hour = st.slider("Day starts at", 6, 12, 8)
    start_minute = st.selectbox("Minute", [0, 15, 30, 45], index=0)
    start_dt = datetime.now().replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    )
    st.markdown(f"Plan begins at **{start_dt.strftime('%H:%M')}**")

run = st.button("✨ Generate My Plan", type="primary", disabled=not brain_dump.strip())

# ── Result ────────────────────────────────────────────────────────────────────
if run and brain_dump.strip():
    plan = parse_brain_dump(brain_dump.strip(), start_dt)

    tasks = plan.get("tasks", [])
    if not tasks:
        st.warning("No tasks found. Try adding more detail to your notes.")
        st.stop()

    st.divider()
    st.subheader("📋 Your Plan")
    st.markdown(f"*{plan.get('summary', '')}*")
    st.caption(
        f"{len(tasks)} tasks · "
        f"~{sum(t.get('duration_minutes', 0) for t in tasks)} min total · "
        f"Finishes around {tasks[-1].get('end', '—')}"
    )

    # Metrics row
    high = sum(1 for t in tasks if t.get("priority") == "high")
    medium = sum(1 for t in tasks if t.get("priority") == "medium")
    low = sum(1 for t in tasks if t.get("priority") == "low")
    m1, m2, m3 = st.columns(3)
    m1.metric("🔴 High priority", high)
    m2.metric("🟡 Medium priority", medium)
    m3.metric("🟢 Low priority", low)

    st.divider()

    # Task cards
    for task in tasks:
        priority = task.get("priority", "medium").lower()
        card_html = f"""
        <div class="task-card {priority}">
            <span class="time-badge">{task.get('start', '')} – {task.get('end', '')}</span>
            <span class="priority-badge {priority}">{priority.upper()}</span>
            &nbsp;<strong>{task['title']}</strong>
            &nbsp;<small style="color:#6c757d">· {task.get('category','Other')} · {task.get('duration_minutes',30)} min</small>
            <p style="margin:0.3rem 0 0; font-size:0.9rem; color:#495057">{task.get('description','')}</p>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # ── Calendar export ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("📅 Add to Calendar")

    ics_data = build_ics(plan)
    fname = f"clarity_plan_{datetime.now().strftime('%Y%m%d_%H%M')}.ics"

    col_dl, col_info = st.columns([1, 2])

    with col_dl:
        st.download_button(
            label="⬇️ Download .ics (all events)",
            data=ics_data,
            file_name=fname,
            mime="text/calendar",
            type="primary",
            help="Opens in Google Calendar, Apple Calendar, or Outlook",
        )

    with col_info:
        st.info(
            "**Google Calendar:** download the file → open it → Google Calendar "
            "will ask you to import all events at once.\n\n"
            "**Apple Calendar:** double-click the .ics file — it imports instantly."
        )

    # Individual Google Calendar links per task
    with st.expander("Add individual events to Google Calendar"):
        for task in tasks:
            url = gcal_url(task)
            st.markdown(
                f"[+ {task.get('start','')} · {task['title']}]({url})",
                unsafe_allow_html=False,
            )
