# 🧠 DevMind — Developer Debugging Memory Agent

> *"GitHub Copilot remembers nothing. DevMind never forgets."*

DevMind is an AI-powered debugging assistant that remembers every bug your team has ever fixed.
When a developer hits an error, DevMind searches the **entire team's debugging history** using
[Hindsight](https://github.com/vectorize-io/hindsight) persistent memory — then uses an LLM to
synthesize a targeted fix based on what actually worked before.

---

## ✨ What Makes It Different

| Stateless AI Assistant | DevMind with Hindsight Memory |
|---|---|
| "Check the logs, restart the service" | "Priya fixed this exact error on Nov 2 — it was a Redis TTL mismatch. Here's the fix." |
| Gives generic advice | References real past fixes from your team |
| Forgets every session | Builds institutional debugging knowledge over time |
| Same answer for everyone | Personalised to your team's codebase and patterns |

---

## 🏗️ Architecture

```
Developer hits a bug
        │
        ▼
   DevMind UI (Browser)
        │
        ▼
   FastAPI Backend (/api/analyze)
        │
        ├── 1. Hindsight recall()  ← search past debugging memory
        │         │
        │         └── Returns matching past bug fixes
        │
        ├── 2. Hindsight reflect() ← synthesize knowledge across memories
        │
        └── 3. Groq LLM (openai/gpt-oss-120b)
                  │
                  └── Combines memory + reasoning → targeted fix
```

---

## ⚙️ Environment Variables

Configure these in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `HINDSIGHT_API_KEY` | *(empty)* | Hindsight API key from [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io) (or `DEMO` for offline mode) |
| `HINDSIGHT_BASE_URL` | `https://api.hindsight.vectorize.io` | Hindsight API base URL |
| `GROQ_API_KEY` | *(empty)* | Groq API key from [groq.com](https://groq.com) (or `DEMO` for offline mode) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | LLM model identifier on Groq |
| `APP_PORT` | `8000` | Port for the FastAPI server |
| `MEMORY_BANK_ID` | `devmind-debug-bank` | Hindsight memory bank identifier |

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
cd devmind
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env and set your HINDSIGHT_API_KEY and GROQ_API_KEY
```

### 3. Run Server
```bash
cd devmind
python main.py
```
Or with uvicorn:
```bash
cd devmind
python -m uvicorn main:app --reload --port 8000
```

### 4. Seed Demo Data
Open http://localhost:8000 and click **🌱 Seed Demo Data**  
This loads 10 realistic past debugging sessions into Hindsight memory.

### 5. Try a Demo Scenario
Click any **Quick Demo Scenario** button, then hit **Analyze with Memory**.  
Watch DevMind compare standard AI troubleshooting against past team fixes! 🎯

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check returning status and mode (`real` vs `demo`) |
| `GET` | `/api/memory-count` | Get total count of stored debugging memories |
| `POST` | `/api/analyze` | Analyze a bug with or without team memory |
| `POST` | `/api/log-fix` | Retain a resolved bug into memory |
| `POST` | `/api/search` | Search past bug snippets in memory |
| `POST` | `/api/seed` | Seed synthetic past debugging sessions |
| `POST` | `/api/reset-memory` | Delete and recreate memory bank (or clear demo store) |
| `GET` | `/docs` | Interactive Swagger API documentation |
| `GET` | `/` | Web UI dashboard |

---

## 🧠 How Hindsight Memory Is Used

```python
# When a fix is found → RETAIN into memory
await client.aretain(bank_id=MEMORY_BANK_ID, content="""
  [BUG FIX LOGGED]
  Developer: Priya Sharma
  Error: TypeError: Cannot read properties of null (reading 'userId')
  Root Cause: JWT token expired silently — req.user was null
  Fix: Added explicit token expiry check in auth.js line 47
""")

# When a new bug occurs → RECALL from memory
results = await client.arecall(bank_id=MEMORY_BANK_ID, query=error_message)

# REFLECT for synthesized team knowledge
reflection = await client.areflect(bank_id=MEMORY_BANK_ID, query=error_message)
```

---

## 🛠️ Tech Stack

- **Memory:** [Hindsight by Vectorize](https://hindsight.vectorize.io/) — persistent agent memory
- **LLM:** [Groq](https://groq.com/) with `openai/gpt-oss-120b`
- **Backend:** FastAPI + Python 3.10+
- **Frontend:** Vanilla HTML/CSS/JS (zero dependencies)
