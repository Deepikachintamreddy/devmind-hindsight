"""
DevMind — Agent Service
Orchestrates: Hindsight recall → LLM reasoning → structured response.
Falls back to a local demo LLM response when GROQ_API_KEY=DEMO.
"""
from __future__ import annotations
import re
import logging
from backend.config import GROQ_API_KEY, GROQ_MODEL, is_groq_demo
from backend.services.memory import recall_similar, reflect_on_bug, DEMO_MODE as MEM_DEMO

logger = logging.getLogger("devmind.agent")

GROQ_DEMO = is_groq_demo()

_groq = None
if not GROQ_DEMO:
    try:
        from groq import AsyncGroq
        _groq = AsyncGroq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client, falling back to DEMO: {e}")
        GROQ_DEMO = True


def strip_think_blocks(text: str) -> str:
    """
    Groq qwen3-32b can return <think>...</think> text.
    Strip any such block from the answer before returning it.
    """
    if not text:
        return ""
    # Strip complete <think>...</think> tags and everything between them
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL)
    # Also strip if a <think> tag opened and was cut off without closing
    cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


SYSTEM_PROMPT = """You are DevMind, an expert AI debugging assistant with access to your team's
entire debugging history. You have a persistent memory of every bug ever fixed by this team.

When a developer describes an error:
1. You will be given MEMORY CONTEXT — real past debugging sessions retrieved from team memory.
2. The retrieved memories are only the closest matches and may be unrelated. Only use a memory if it describes the same or a closely similar error. If none do, write 'No relevant team memory found' under MEMORY MATCH and give general advice, labeled as not from memory.
3. Under MEMORY MATCH: only state facts that appear in the retrieved memory (who fixed it, when, where, what was done). Do not mention commits, ticket numbers, or details that are not in the memory text. If none describe the same or a closely similar error, write "No relevant team memory found".
4. In RECOMMENDED FIX: label the steps taken from memory as "From team memory:" and any extra code or ideas as "Suggested (generated, not from memory):". If no relevant memory describes this error, label all advice as "Suggested (generated, not from memory):".
5. Reference the specific file, root cause, and fix from memory when relevant.
6. Be concise, technical, and direct — you're talking to engineers, not beginners.

Format your response with:
- 🧠 MEMORY MATCH: (only state facts that appear in retrieved memory: who fixed it, when, where, what was done. Do not mention commits, ticket numbers, or details not in the memory text. If none describe the same or similar error, write "No relevant team memory found")
- 🔍 ROOT CAUSE: (most likely root cause based on memory + reasoning)
- 🔧 RECOMMENDED FIX:
From team memory:
(steps and fixes taken directly from memory)
Suggested (generated, not from memory):
(any extra code, improvements, or general troubleshooting ideas)
- 📝 PREVENTION: (one-line tip to avoid this in future)
"""

NO_MEMORY_SYSTEM_PROMPT = """You are DevMind, an expert AI debugging assistant with NO access to any team history or past tickets.
Give general debugging advice only based on common engineering principles and the provided error message.

Rules:
1. You are a debugging assistant with NO access to any team history or past tickets.
2. Give general debugging advice only.
3. Never claim to have seen this error before.
4. Never mention past tickets, dates, teammates, or records.
5. Keep the exact output sections below, but always write "No team memory available" under MEMORY MATCH.
6. Be concise, technical, and direct — you're talking to engineers, not beginners.

Format your response with:
- 🧠 MEMORY MATCH: No team memory available
- 🔍 ROOT CAUSE: (most likely root cause based on standard error analysis)
- 🔧 RECOMMENDED FIX: (specific general troubleshooting and fix steps)
- 📝 PREVENTION: (one-line tip to avoid this in future)
"""


async def analyze_bug(
    error_message: str,
    stack_trace: str,
    file_path: str,
    developer: str,
    use_memory: bool = True,
) -> dict:
    """
    Full pipeline:
      1. When use_memory is True: recall() similar past bugs & reflect()
         When use_memory is False: skip recall and reflect, send no memory context
      2. Send to LLM for final diagnosis
    """
    memories: list[dict] = []
    reflection = ""
    memory_snippets: list[str] = []

    if use_memory:
        query = f"{error_message} {file_path} {stack_trace[:300]}"
        # ── Step 1: Retrieve similar memories ───────────────────────
        memories = await recall_similar(query)
        if memories:
            reflection = await reflect_on_bug(query)
        else:
            reflection = ""
        memory_snippets = [m["text"] for m in memories[:5]]

    memory_used = bool(use_memory and len(memory_snippets) > 0)
    memories_found = len(memory_snippets) if use_memory else 0

    memory_context = ""
    if use_memory:
        if reflection:
            memory_context += f"[TEAM MEMORY SYNTHESIS]\n{reflection}\n\n"
        if memories:
            memory_context += "[RAW MEMORY CHUNKS]\n"
            for i, m in enumerate(memories[:5], 1):
                memory_context += f"{i}. {m['text']}\n"

    # ── Step 2: Build prompt ─────────────────────────────────────
    user_message = (
        f"Developer: {developer}\n"
        f"File/Module: {file_path}\n"
        f"Error: {error_message}\n"
        f"Stack Trace:\n{stack_trace}\n\n"
    )
    if use_memory:
        if memory_context:
            user_message += f"--- RETRIEVED TEAM MEMORY ---\n{memory_context}"
        else:
            user_message += "--- TEAM MEMORY ---\nNo previous records found for this error."

    # ── Step 3: LLM call (or demo fallback) ─────────────────────
    if GROQ_DEMO or _groq is None:
        answer = _demo_llm_response(error_message, memories, reflection, use_memory=use_memory)
    else:
        try:
            selected_prompt = SYSTEM_PROMPT if use_memory else NO_MEMORY_SYSTEM_PROMPT
            response = await _groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": selected_prompt},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            raw_answer = response.choices[0].message.content or ""
            answer = strip_think_blocks(raw_answer)
        except Exception as e:
            logger.error(f"Groq completions error: {e}")
            raise RuntimeError(f"Groq API error: {e}") from e

    # Ensure think blocks are stripped in all cases
    answer = strip_think_blocks(answer)

    return {
        "analysis":       answer,
        "memory_used":    memory_used,
        "memories_found": memories_found,
        "has_reflection": bool(reflection) if use_memory else False,
        "memories":       memory_snippets,
    }


# ── Demo LLM Response (no API key needed) ────────────────────────

def _demo_llm_response(
    error_message: str,
    memories: list[dict],
    reflection: str,
    use_memory: bool = True,
) -> str:
    """
    Returns a realistic-looking DevMind response for demo/offline mode.
    When memory is populated (after seeding), it references real past fixes.
    When use_memory is False, it returns generic non-memory advice.
    """
    if not use_memory:
        return (
            f"🧠 MEMORY MATCH:\n"
            f"No team memory available\n\n"
            f"🔍 ROOT CAUSE:\n"
            f"Based on the error message '{error_message[:120]}', this is likely caused by:\n"
            f"- A missing or misconfigured dependency\n"
            f"- An unhandled edge case in the code path\n"
            f"- A recent environment or configuration change\n\n"
            f"🔧 RECOMMENDED FIX:\n"
            f"1. Check recent code changes (git log --oneline -10)\n"
            f"2. Verify environment variables and config files\n"
            f"3. Add error handling and logging around the failure point\n"
            f"4. Once fixed, click '➕ Log a Fix' to save it to team memory!\n\n"
            f"📝 PREVENTION:\n"
            f"Log resolved fixes so the team avoids repeating debugging work."
        )
    if use_memory and memories:
        top = memories[0]["text"]
        # Extract fields from stored memory text
        lines = {
            line.split(": ", 1)[0].strip(): line.split(": ", 1)[1].strip()
            for line in top.splitlines()
            if ": " in line
        }
        developer  = lines.get("Developer",   "a teammate")
        root_cause = lines.get("Root Cause",  "see memory below")
        fix        = lines.get("Fix Applied", "see memory below")
        err_type   = lines.get("Error Type",  "similar error")
        reported   = lines.get("Reported On", "")
        when_str   = f" on {reported}" if reported else ""
        file_mod   = lines.get("File/Module", "")
        where_str  = f" in {file_mod}" if file_mod else ""

        return (
            f"🧠 MEMORY MATCH:\n"
            f"Found {len(memories)} matching record(s) in team memory.\n"
            f"Fixed by {developer}{when_str}{where_str}: {err_type} — {fix}.\n\n"
            f"🔍 ROOT CAUSE:\n"
            f"{root_cause}\n\n"
            f"🔧 RECOMMENDED FIX:\n"
            f"From team memory:\n"
            f"- {fix}\n\n"
            f"Suggested (generated, not from memory):\n"
            f"- Verify all related call sites and add regression tests covering this condition.\n\n"
            f"📝 PREVENTION:\n"
            f"Log every resolved bug into DevMind so the whole team benefits from the fix.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️  Running in DEMO MODE. Add GROQ_API_KEY to .env for full AI-powered responses."
        )
    else:
        return (
            f"🧠 MEMORY MATCH:\n"
            f"No relevant team memory found\n\n"
            f"🔍 ROOT CAUSE:\n"
            f"Based on the error message '{error_message[:120]}', this is likely caused by:\n"
            f"- A missing or misconfigured dependency\n"
            f"- An unhandled edge case in the code path\n"
            f"- A recent environment or configuration change\n\n"
            f"🔧 RECOMMENDED FIX:\n"
            f"Suggested (generated, not from memory):\n"
            f"1. Check recent code changes (git log --oneline -10)\n"
            f"2. Verify environment variables and config files\n"
            f"3. Add error handling and logging around the failure point\n"
            f"4. Once fixed, click '➕ Log a Fix' to save it to team memory!\n\n"
            f"📝 PREVENTION:\n"
            f"Seed your DevMind memory with past fixes so the team never repeats the same debugging work.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️  Running in DEMO MODE. Click '🌱 Seed Demo Data' first, then re-analyze to see memory in action!"
        )
