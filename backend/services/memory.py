"""
DevMind — Memory Service
Wraps Hindsight retain / recall / reflect calls.
Falls back to an in-process demo store when HINDSIGHT_API_KEY=DEMO.
"""
from __future__ import annotations
import difflib
import logging
import re
from typing import Any
from backend.config import (
    HINDSIGHT_API_KEY,
    HINDSIGHT_BASE_URL,
    MEMORY_BANK_ID,
    is_hindsight_demo,
)

logger = logging.getLogger("devmind.memory")

# ── Demo in-memory store: mapping of document_id -> content ──────
_DEMO_STORE: dict[str, str] = {}

DEMO_MODE = is_hindsight_demo()

_client = None
if not DEMO_MODE:
    try:
        from hindsight_client import Hindsight
        _client = Hindsight(base_url=HINDSIGHT_BASE_URL, api_key=HINDSIGHT_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Hindsight client, falling back to DEMO: {e}")
        DEMO_MODE = True


def make_document_id(error_type: str, file_path: str) -> str:
    """Build a stable document_id slug from error_type + file_path."""
    clean_error = re.sub(r"[^a-zA-Z0-9]+", "-", error_type).strip("-").lower()
    clean_file = re.sub(r"[^a-zA-Z0-9]+", "-", file_path).strip("-").lower()
    return f"{clean_error}--{clean_file}"


async def init_memory_bank() -> None:
    """
    At startup, create the Hindsight memory bank with acreate_bank.
    Wrapped in try/except so an existing bank does not crash it.
    """
    if DEMO_MODE or _client is None:
        logger.info("Running in DEMO mode; skipping Hindsight memory bank initialization.")
        return

    try:
        logger.info(f"Ensuring Hindsight memory bank '{MEMORY_BANK_ID}' exists...")
        await _client.acreate_bank(
            bank_id=MEMORY_BANK_ID,
            name="DevMind Memory Bank",
        )
        logger.info(f"Hindsight bank '{MEMORY_BANK_ID}' created successfully.")
    except Exception as e:
        # If the bank already exists or returns a known status, log and continue gracefully
        logger.info(f"Hindsight bank '{MEMORY_BANK_ID}' initialization notice (existing bank or ok): {e}")


async def reset_memory_bank() -> None:
    """
    Delete the bank with adelete_bank and recreate it with init_memory_bank() in real mode,
    or clear the demo store in demo mode.
    """
    if DEMO_MODE or _client is None:
        _DEMO_STORE.clear()
        logger.info("Demo memory store cleared.")
        return

    try:
        logger.info(f"Deleting Hindsight memory bank '{MEMORY_BANK_ID}'...")
        await _client.adelete_bank(bank_id=MEMORY_BANK_ID)
        logger.info(f"Hindsight bank '{MEMORY_BANK_ID}' deleted.")
    except Exception as e:
        logger.warning(f"Notice while deleting Hindsight bank '{MEMORY_BANK_ID}': {e}")

    # Recreate the bank fresh
    await init_memory_bank()


async def close_client() -> None:
    """Close Hindsight client session on shutdown if supported."""
    global _client
    if _client and hasattr(_client, "aclose"):
        try:
            await _client.aclose()
        except Exception:
            pass


async def count_memories() -> int | None:
    """
    Return the total number of memories stored.
    Uses Hindsight alist_memories in real mode, or the demo store length in demo mode.
    If counting is not possible in real mode, returns None.
    """
    if DEMO_MODE or _client is None:
        return len(_DEMO_STORE)

    try:
        res = await _client.alist_memories(bank_id=MEMORY_BANK_ID, limit=100)
        if hasattr(res, "total") and res.total is not None:
            return int(res.total)
        if hasattr(res, "items") and res.items is not None:
            return len(res.items)
        return None
    except Exception as e:
        logger.warning(f"Could not count Hindsight memories: {e}")
        return None


# ── Public API ───────────────────────────────────────────────────

async def retain_fix(
    error_type: str,
    error_message: str,
    file_path: str,
    root_cause: str,
    fix_applied: str,
    developer: str,
    tags: list[str] | None = None,
    timestamp: str | None = None,
    document_id: str | None = None,
) -> None:
    """Persist a resolved bug into memory (Hindsight or demo store)."""
    if not document_id:
        document_id = make_document_id(error_type, file_path)

    tag_str = ", ".join(tags or [])
    reported_str = f"Reported On: {timestamp}\n" if timestamp else ""
    content = (
        f"[BUG FIX LOGGED]\n"
        f"Developer: {developer}\n"
        f"{reported_str}"
        f"Error Type: {error_type}\n"
        f"Error Message: {error_message}\n"
        f"File/Module: {file_path}\n"
        f"Root Cause: {root_cause}\n"
        f"Fix Applied: {fix_applied}\n"
        f"Tags: {tag_str}"
    )

    if DEMO_MODE or _client is None:
        _DEMO_STORE[document_id] = content
        return

    try:
        kwargs: dict[str, Any] = {"document_id": document_id}
        if timestamp:
            kwargs["timestamp"] = timestamp
        await _client.aretain(bank_id=MEMORY_BANK_ID, content=content, **kwargs)
    except Exception as e:
        logger.error(f"Hindsight aretain failed: {e}")
        raise RuntimeError(f"Hindsight retain error: {e}") from e


def extract_recall_score(item: Any) -> float | None:
    """
    Extract a relevance score from recall result item if present.
    Returns float score or None if no score field exists.
    """
    # 1. Check item.scores / item['scores']
    scores_obj = getattr(item, "scores", None)
    if scores_obj is None and isinstance(item, dict):
        scores_obj = item.get("scores")

    if scores_obj is not None:
        if isinstance(scores_obj, (int, float)):
            return float(scores_obj)
        # Check standard Hindsight score fields in preference order: final -> reranker -> semantic
        for attr in ("final", "reranker", "semantic"):
            val = getattr(scores_obj, attr, None)
            if val is not None and isinstance(val, (int, float)):
                return float(val)
        if isinstance(scores_obj, dict):
            for key in ("final", "reranker", "semantic", "score"):
                val = scores_obj.get(key)
                if val is not None and isinstance(val, (int, float)):
                    return float(val)

    # 2. Check item.score / item['score']
    direct_score = getattr(item, "score", None)
    if direct_score is None and isinstance(item, dict):
        direct_score = item.get("score")
    if direct_score is not None and isinstance(direct_score, (int, float)):
        return float(direct_score)

    return None


async def recall_similar(query: str) -> list[dict]:
    """Search memory for past bugs similar to the query (returns up to 5 closest matches)."""
    if DEMO_MODE or _client is None:
        return _demo_recall(query)

    try:
        result = await _client.arecall(bank_id=MEMORY_BANK_ID, query=query)
        raw_results = getattr(result, "results", []) or []

        memories = []
        for item in raw_results[:5]:
            text = getattr(item, "text", str(item)) if not isinstance(item, dict) else item.get("text", str(item))
            score = extract_recall_score(item)
            entry: dict[str, Any] = {"text": text}
            if score is not None:
                entry["score"] = score
            memories.append(entry)

        return memories
    except Exception as e:
        logger.error(f"Hindsight arecall failed: {e}")
        raise RuntimeError(f"Hindsight recall error: {e}") from e


async def reflect_on_bug(query: str) -> str:
    """Synthesize a coherent answer across all related memories."""
    if DEMO_MODE or _client is None:
        matches = _demo_recall(query)
        if not matches:
            return ""
        # Build a simple synthesis from top matches
        return "Team memory synthesis:\n" + "\n---\n".join(m["text"] for m in matches[:3])

    try:
        result = await _client.areflect(bank_id=MEMORY_BANK_ID, query=query)
        return getattr(result, "text", "") or ""
    except Exception as e:
        logger.error(f"Hindsight areflect failed: {e}")
        raise RuntimeError(f"Hindsight reflect error: {e}") from e


# ── Demo fuzzy-search helper ─────────────────────────────────────

def _demo_recall(query: str) -> list[dict]:
    """
    Simple keyword + fuzzy match against the in-process demo store.
    Good enough to power the demo without a real Hindsight instance.
    """
    if not _DEMO_STORE:
        return []

    q_words = set(query.lower().split())
    scored: list[tuple[float, str]] = []

    for chunk in _DEMO_STORE.values():
        chunk_lower = chunk.lower()
        # Word overlap score
        chunk_words = set(chunk_lower.split())
        overlap = len(q_words & chunk_words) / max(len(q_words), 1)
        # Sequence similarity bonus
        seq = difflib.SequenceMatcher(None, query.lower(), chunk_lower[:300]).ratio()
        score = overlap * 0.7 + seq * 0.3
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"text": chunk, "score": round(score, 3)} for score, chunk in scored[:5]]
