"""
DevMind — Debug Routes
POST /api/analyze       → Analyze an error using memory + LLM
POST /api/log-fix       → Retain a resolved bug into memory
POST /api/search        → Raw recall search from memory
GET  /api/memory-count  → Count memories stored in memory bank
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.agent import analyze_bug
from backend.services.memory import retain_fix, recall_similar, count_memories

router = APIRouter(prefix="/api", tags=["debug"])


# ── Request / Response Models ────────────────────────────────────

class AnalyzeRequest(BaseModel):
    error_message: str
    stack_trace: str = ""
    file_path: str = "unknown"
    developer: str = "anonymous"
    use_memory: bool = True


class AnalyzeResponse(BaseModel):
    analysis: str
    memory_used: bool
    memories_found: int
    has_reflection: bool
    memories: list[str] = []


class LogFixRequest(BaseModel):
    error_type: str
    error_message: str
    file_path: str
    root_cause: str
    fix_applied: str
    developer: str
    tags: list[str] = []


class SearchRequest(BaseModel):
    query: str


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/memory-count")
async def get_memory_count():
    """
    Return the total number of memories stored.
    Returns {"count": <int>} or {"count": null} if counting is not possible in real mode.
    """
    count = await count_memories()
    return {"count": count}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_error(req: AnalyzeRequest):
    """
    Core endpoint: analyze a bug using team memory + LLM.
    Supports use_memory=True (with memory) and use_memory=False (without memory).
    """
    try:
        result = await analyze_bug(
            error_message=req.error_message,
            stack_trace=req.stack_trace,
            file_path=req.file_path,
            developer=req.developer,
            use_memory=req.use_memory,
        )
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-fix")
async def log_fix(req: LogFixRequest):
    """
    Retain a resolved bug into Hindsight memory.
    Call this after fixing a bug so the team never loses the knowledge.
    """
    try:
        await retain_fix(
            error_type=req.error_type,
            error_message=req.error_message,
            file_path=req.file_path,
            root_cause=req.root_cause,
            fix_applied=req.fix_applied,
            developer=req.developer,
            tags=req.tags,
        )
        return {"status": "success", "message": "Fix retained in team memory via Hindsight ✓"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_memory(req: SearchRequest):
    """
    Raw recall search — returns matching memory chunks for a query.
    Useful for browsing past debugging sessions.
    """
    try:
        memories = await recall_similar(req.query)
        return {"status": "success", "results": memories, "count": len(memories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
