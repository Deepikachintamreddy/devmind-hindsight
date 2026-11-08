"""
DevMind — Seed Route
POST /api/seed         → Load synthetic past debugging data into Hindsight memory.
POST /api/reset-memory → Reset memory bank (deletes and recreates in real mode, or clears demo store).
"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.services.memory import retain_fix, reset_memory_bank

router = APIRouter(prefix="/api", tags=["seed"])

DATA_FILE = Path(__file__).parent.parent / "data" / "synthetic_bugs.json"


@router.post("/seed")
async def seed_memory():
    """
    Load all synthetic bug fixes from JSON into Hindsight memory.
    Call once before the demo to populate the team knowledge base.
    """
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="synthetic_bugs.json not found")

    try:
        bugs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        seeded = 0

        for bug in bugs:
            await retain_fix(
                error_type=bug["error_type"],
                error_message=bug["error_message"],
                file_path=bug["file_path"],
                root_cause=bug["root_cause"],
                fix_applied=bug["fix_applied"],
                developer=bug["developer"],
                tags=bug.get("tags", []),
                timestamp=bug.get("reported_on"),
            )
            seeded += 1

        return {
            "status": "success",
            "message": f"Seeded {seeded} past debugging sessions into Hindsight memory ✓",
            "count": seeded,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed memory: {str(e)}")


@router.post("/reset-memory")
async def reset_memory():
    """
    Reset memory bank: deletes and recreates bank in real mode, or clears demo store.
    """
    try:
        await reset_memory_bank()
        return {"status": "success", "message": "Memory bank reset successfully ✓"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset memory bank: {str(e)}")
