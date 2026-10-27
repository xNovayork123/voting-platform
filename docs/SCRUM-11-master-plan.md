# SCRUM-11 — WhatsApp Chat Frequency & Sentiment Analysis — Master Plan

> Status: in development on branch `feature/scrum-11-chat-analysis`
> Owner: Nicolas Velasquez
> Related Jira: SCRUM-11 (epic), SCRUM-26 (message frequency), SCRUM-27 (tone intention)

## 1. Goal

Add an analysis feature that, given a WhatsApp chat export, reports:

1. **Active hours** — the hours each participant is active (acceptance #1).
2. **Message frequency** — average messages per day and the time of day messages
   are most frequent / peak hour (acceptance #2, SCRUM-26).
3. **Sentiment** — classify each message tone as positive / negative / neutral
   (acceptance #3, SCRUM-27).

## 2. Locked decisions

| Decision | Value | Reason |
|---|---|---|
| Input | `.txt` upload **and** pasted text | Same parser handles both; no live chat exists in the app |
| Sentiment engine | **VADER** (`vaderSentiment`, pip) | Offline, fast, tuned for social text, English |
| Language | English (en-US) | VADER lexicon is English |
| Persistence | **Stateless** — parse, analyze, return JSON; nothing stored in DB | No migrations, lowest risk |
| Code structure | Modules inside `voting/` (mirrors the `dataset_*` feature), **not** a new Django app | Matches team convention, smaller merge surface |
| Charts | Hand-rolled SVG (same style as `ResultsChart.jsx`), no chart library | Consistency, zero new frontend deps |
| Auth | Requires a logged-in session (`request.session["user_id"]`), 401 otherwise | Consistent with existing views |

## 3. File map

```
backend/voting/
  chat_parser.py       [NEW]  raw WhatsApp text -> ([{datetime, author, text}], stats)
  chat_analytics.py    [NEW]  frequency, active hours, peak hour            (SCRUM-26)
  chat_sentiment.py    [NEW]  VADER wrapper, positive/negative/neutral      (SCRUM-27)
  views.py             [EDIT] + analyze_chat view (~25 lines, appended)
  urls.py              [EDIT] + path("chat/analyze/", views.analyze_chat)
  fixtures/sample_chat_en.txt   [NEW] fictional English chat for tests + demo
backend/
  requirements.txt     [EDIT] + vaderSentiment
  voting/tests_chat.py [NEW]  unit tests for parser / analytics / sentiment

src/  (React frontend)
  ChatAnalysis.jsx     [NEW]  page
  ChatAnalysis.css     [NEW]
  App.js               [EDIT] import + page 'chatanalysis' in the render switch
  Dashboard.jsx        [EDIT] nav button to the page

docs/
  SCRUM-11-master-plan.md   [this file]
  SCRUM-11-INTEGRATION.md   [how to drop the feature into another version]
```

Shared-file edits are tiny (1–2 lines each) to keep the eventual merge clean.

## 4. Backend algorithms (the SCRUM-11 core)

### chat_parser.py — `parse_chat(raw_text) -> (messages, stats)`
- Tolerant regex for Android (`12/31/23, 11:59 PM - John: msg`) and
  iOS (`[12/31/23, 11:59:00 PM] John: msg`) export formats.
- Handles multi-line messages (continuation lines), system lines
  (encryption notice, "Messages and calls..."), and `<Media omitted>`.
- Returns the same `(data, stats)` shape used by `dataset_cleaner.py`.

### chat_analytics.py — frequency + hours (SCRUM-26)
- `activity_by_hour`: 24-slot array, count per hour 0–23 -> **peak hour**.
- `avg_messages_per_day = total_messages / distinct_days`.
- Per participant: total, average per day, list of active hours.

### chat_sentiment.py — tone (SCRUM-27)
- `SentimentIntensityAnalyzer().polarity_scores(text)["compound"]`.
- `compound >= 0.05` -> positive, `<= -0.05` -> negative, else neutral.
- Aggregate: overall %, per-participant %, overall tone label.

## 5. API

`POST /api/chat/analyze/` — multipart `file` (.txt) **or** JSON `{"text": "..."}`.
401 if not logged in.

```json
{
  "summary": {"total_messages":0,"participants":[],"days":0,"avg_messages_per_day":0,"date_range":{}},
  "activity_by_hour": [{"hour":0,"count":0}, "... 24 entries"],
  "peak_hour": 21,
  "per_participant": [{"name":"","messages":0,"avg_per_day":0,"active_hours":[]}],
  "sentiment": {"positive":0,"negative":0,"neutral":0,"overall":"positive"},
  "per_participant_sentiment": []
}
```

## 6. Frontend

`ChatAnalysis.jsx`: toggle Upload .txt / Paste text -> Analyze button -> POST -> render.
Sections: (1) summary cards, (2) activity-by-hour SVG bar chart,
(3) sentiment donut (reuses `ResultsChart` style), (4) per-participant table.
Standard props `{user, onLogout, onNavigate}`; reachable from `Dashboard` nav.

## 7. Test-now strategy (no real data needed yet)

`fixtures/sample_chat_en.txt` is a fictional English chat (several participants,
several days, varied hours, positive and negative messages). `voting/tests_chat.py`
runs the three modules against it -> green without depending on anyone. Local demo:
upload the sample on the page and see the charts.

## 8. Phases

| Phase | Work |
|---|---|
| 0 | Save plan, runnable base + git branch, install VADER, sample fixture |
| 1 | `chat_parser.py` + tests |
| 2 | `chat_analytics.py` + tests (SCRUM-26) |
| 3 | `chat_sentiment.py` + tests (SCRUM-27) |
| 4 | `analyze_chat` view + url |
| 5 | `ChatAnalysis.jsx/.css` + App.js/Dashboard wiring |
| 6 | Polish, local demo, write integration guide |

## 9. Integrating into a teammate's version

The feature is built to be portable. See `SCRUM-11-INTEGRATION.md`. Summary:
the three `chat_*.py` modules + fixture + tests are 100% standalone (copy as-is);
only four shared files take a tiny wiring edit (`views.py`, `urls.py`,
`requirements.txt`, `App.js`, `Dashboard.jsx`), plus `pip install vaderSentiment`.

## 10. Edge cases handled

WhatsApp date formats (Android/iOS, 12h/24h), multi-line messages, system lines,
`<Media omitted>`, emojis (VADER handles them partially), English-only lexicon
(consistent with the language decision).
