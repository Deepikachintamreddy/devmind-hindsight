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
        └── 3. Groq LLM (qwen3-32b)
                  │
                  └── Combines memory + reasoning → targeted fix
```

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
# Edit .env and add:
# HINDSIGHT_API_KEY  → https://ui.hindsight.vectorize.io  (promo: MEMHACK99 for $50 free)
# GROQ_API_KEY       → https://groq.com (free tier)
```

### 3. Run
```bash
cd e:\microsft_hackathon\devmind
python -m uvicorn main:app --reload --port 8000
```

### 4. Seed Demo Data (Important!)
Open http://localhost:8000 and click **🌱 Seed Demo Data**  
This loads 10 realistic past debugging sessions into Hindsight memory.

### 5. Try a Demo Scenario
Click any **Quick Demo Scenario** button, then hit **Analyze with Memory**.  
Watch DevMind recall the exact fix from memory! 🎯

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Analyze a bug using memory + LLM |
| `POST` | `/api/log-fix` | Retain a resolved bug into memory |
| `POST` | `/api/search` | Raw search across team memory |
| `POST` | `/api/seed` | Seed synthetic past debugging data |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger API docs |

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
- **LLM:** [Groq](https://groq.com/) with `qwen/qwen3-32b`
- **Backend:** FastAPI + Python 3.10+
- **Frontend:** Vanilla HTML/CSS/JS (zero dependencies)

---

## 🏆 Built for HackWithHyderabad 3.0

