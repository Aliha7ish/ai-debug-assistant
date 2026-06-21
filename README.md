# AI Debug Assistant

A FastAPI + SSR (Jinja2) platform with role-based session auth where users
submit programming issues and get an instant AI diagnosis: error category,
estimated difficulty, and a targeted recommendation — powered by Google's
Gemini API via `google-genai`.

## Stack

- **FastAPI** — backend framework, stateful request handling
- **Jinja2** — server-side rendered HTML (no separate frontend build)
- **SQLAlchemy + SQLite** — `database.db`, a single local file
- **passlib (bcrypt)** — password hashing
- **itsdangerous** — signed, timestamped session cookies (no server-side session store needed)
- **google-genai** — the AI diagnostic pipeline

## Project layout

```
├── main.py            # route controllers, session-cookie auth guards
├── database.py         # engine, session factory, declarative base
├── models.py            # User, ReviewSession (1:N)
├── auth.py               # password hashing + signed session tokens
├── ai_service.py          # isolated AI pipeline (prompt -> Gemini -> parsed JSON)
├── templates/
│   ├── login.html
│   ├── register.html
│   └── index.html        # dashboard: profile sidebar + submission form + log
├── static/
│   └── style.css
├── pyproject.toml         # uv-compatible
```

## Setup

### 1. Install dependencies (pick one)

```bash
uv sync                                 
```

### 2. Configure environment

Create `.env` file and put the followig:

```bash
GEMINI_API_KEY = #YOUR_GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

GEMINI_MODEL=gemini-3.5-flash
```

### 3. Run the dev server

```bash
uv run uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000**.

`database.db` is created automatically on first boot — no migration step needed.

## Verification checklist

1. Visiting `/` while logged out redirects to `/login`.
2. Register a new account at `/register`, then sign in at `/login`.
3. The dashboard shows a **profile card** with your username + email, and a **Log out** link.
4. Submit a programming issue (pick a language, describe the bug) — it POSTs to `/submit`.
5. The new entry appears at the top of the **session log**, tagged `SUCCESS` with its category, difficulty, and recommendation.
6. If `GEMINI_API_KEY` is missing or the API call fails for any reason, the entry is still saved — tagged `FAILED` with the error captured — and the server never crashes.
7. `database.db` persists everything: open it with any SQLite browser to confirm the `users` and `review_sessions` tables are populated and correctly linked by `user_id`.
