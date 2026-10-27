# SCRUM-11 — How to integrate into another version

The feature is built to drop into any version of the app (including the
`dataset-import-export` backend) with almost no edits. There are two ways:
the **manual drop-in** (works across separate copies / zips) and the
**git merge** (if everyone shares one repo).

---

## What the feature is made of

**Standalone files — copy as-is, never cause conflicts:**

```
backend/voting/chat_parser.py
backend/voting/chat_analytics.py
backend/voting/chat_sentiment.py
backend/voting/fixtures/sample_chat_en.txt
backend/voting/tests_chat.py
src/ChatAnalysis.jsx
src/ChatAnalysis.css
docs/SCRUM-11-master-plan.md
docs/SCRUM-11-INTEGRATION.md
```

**Shared files — 1–2 line edits each (the only possible conflict points):**

| File | Edit |
|---|---|
| `backend/requirements.txt` | add `vaderSentiment>=3.3.2` |
| `backend/voting/urls.py` | add one `path("chat/analyze/", views.analyze_chat, ...)` |
| `backend/voting/views.py` | append the `analyze_chat` view (uses local imports, so no change to the import block) |
| `src/App.js` | add `import ChatAnalysis` + one render line for `page === 'chatanalysis'` |
| `src/Dashboard.jsx` | add one nav button calling `onNavigate('chatanalysis')` |

No database migrations: the feature is stateless.

---

## Option A — Manual drop-in (recommended across separate copies)

Use this when your teammates' latest version is a separate folder/zip (the
common case in this project).

1. **Copy the standalone files** listed above into the teammate's project at
   the same paths.

2. **Install VADER** in their backend environment:
   ```bash
   pip install vaderSentiment>=3.3.2
   ```
   and add `vaderSentiment>=3.3.2` to `backend/requirements.txt`.

3. **Add the URL** in `backend/voting/urls.py`, inside `urlpatterns`:
   ```python
   path('chat/analyze/', views.analyze_chat, name='chat-analyze'),
   ```

4. **Append the view** to the end of `backend/voting/views.py` (copy the whole
   `analyze_chat` function from this branch — it imports its helpers locally, so
   you do not touch the existing imports). It relies on `api_view`,
   `parser_classes`, `MultiPartParser`, `FormParser`, `Response`, and `status`,
   which `views.py` already imports.

5. **Wire the frontend** in `src/App.js`:
   ```jsx
   import ChatAnalysis from "./ChatAnalysis";   // near the other imports
   // ...inside the render switch, next to the other pages:
   {page === 'chatanalysis' && (
     <ChatAnalysis user={user} onLogout={handleLogout} onNavigate={handleNavigate} />
   )}
   ```
   and add a nav entry in `src/Dashboard.jsx`:
   ```jsx
   <button className="nav-item" onClick={() => onNavigate('chatanalysis')}>
     <span>💬</span> Chat Analysis
   </button>
   ```

6. **Verify** (see "Verification" below).

---

## Option B — Git merge (when sharing one repo)

Use this if the team's final version lives in the same git repository as this
branch (`feature/scrum-11-chat-analysis`).

```bash
# from the feature branch, pull in the team's latest
git fetch origin
git merge origin/master           # or main

# resolve conflicts — they can only appear in the 5 shared files above.
# each is a tiny additive block; keep both sides, then:
git add -A
git commit

# run the tests, then merge the feature into the team branch
git checkout master
git merge feature/scrum-11-chat-analysis
```

Because the heavy logic lives in standalone `chat_*.py` / `ChatAnalysis.*`
files, conflicts (if any) are limited to the small additive edits.

---

## Verification (after either option)

```bash
cd backend
python manage.py test voting.tests_chat      # 30 tests, all green
python manage.py check                        # no issues

# optional live check
python manage.py runserver
# then in the app: log in -> sidebar -> Chat Analysis -> paste the sample or
# upload backend/voting/fixtures/sample_chat_en.txt -> Analyze
```

Expected on the sample fixture: 32 messages, 3 participants, peak hour 9 PM,
overall sentiment positive.

---

## Notes for teammates

- The endpoint is `POST /api/chat/analyze/`, requires a logged-in session,
  and accepts a `.txt` file (form field `file`) **or** pasted text
  (form field `text`).
- English only (VADER lexicon). Other languages would need a different engine.
- Stateless by design: nothing is written to the database, so it cannot clash
  with the dataset import/export models or any other migration.
