"""
DevMind — Live Integration Test
Tests recall, reflect, and runs analysis with use_memory=False vs use_memory=True
for the JWT null userId error.
Does NOT seed by default; pass --seed to seed the 10 synthetic bugs.
Works with real Hindsight if configured in .env, or falls back to demo mode.
CRITICAL: Does NOT print any API keys.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure devmind root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.config import get_app_mode, is_hindsight_demo, is_groq_demo, MEMORY_BANK_ID
from backend.services.memory import init_memory_bank, retain_fix, recall_similar, reflect_on_bug, count_memories
from backend.services.agent import analyze_bug

DATA_FILE = BASE_DIR / "backend" / "data" / "synthetic_bugs.json"


async def run_live_test(seed: bool = False):
    print("=" * 60)
    print("  DevMind Live Test: Recall, Reflect & Comparison")
    if seed:
        print("  (Seeding enabled via --seed)")
    print("=" * 60)

    # 1. Display mode (DO NOT PRINT API KEYS)
    app_mode = get_app_mode()
    h_mode = "demo" if is_hindsight_demo() else "real"
    g_mode = "demo" if is_groq_demo() else "real"
    print(f"Overall Mode   : {app_mode.upper()}")
    print(f"Hindsight Mode : {h_mode.upper()} (bank: '{MEMORY_BANK_ID}')")
    print(f"Groq Mode      : {g_mode.upper()}")
    print("-" * 60)

    # 2. Bank Initialization
    print("\n[Step 1] Initializing Hindsight memory bank...")
    try:
        await init_memory_bank()
        print("✓ Memory bank ready.")
    except Exception as e:
        print(f"! Notice during bank initialization: {e}")

    # 3. Load synthetic bugs
    print("\n[Step 2] Loading synthetic bugs from data file...")
    if not DATA_FILE.exists():
        print(f"ERROR: Data file not found at {DATA_FILE}")
        return

    bugs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Found {len(bugs)} bug records in data file.")

    # 4. Seed all 10 bugs ONLY if --seed flag was passed
    if seed:
        print("\n[Step 3] Seeding bugs into memory (--seed flag enabled)...")
        seeded_count = 0
        for i, bug in enumerate(bugs, 1):
            try:
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
                seeded_count += 1
                print(f"  [{i:02d}/10] Seeded: {bug['error_type']} ({bug['file_path']})")
            except Exception as e:
                print(f"  [{i:02d}/10] FAILED to seed {bug.get('error_type')}: {e}")

        print(f"\n✓ Successfully seeded {seeded_count}/{len(bugs)} bugs into memory.")
    else:
        print("\n[Step 3] Skipping seeding (default). Pass --seed to seed the 10 bugs.")

    # Memory count check
    mem_count = await count_memories()
    print(f"Current total stored memories: {mem_count if mem_count is not None else 'N/A'}")

    # 5. Test Recall on the JWT null userId error
    query = "TypeError: Cannot read properties of null (reading 'userId')"
    stack_trace = (
        "TypeError: Cannot read properties of null (reading 'userId')\n"
        "    at verifyToken (src/middleware/auth.js:47:22)\n"
        "    at Layer.handle [as handle_request] (express/lib/router/layer.js:95:5)"
    )
    file_path = "src/middleware/auth.js"
    developer = "Priya Sharma"

    print("\n" + "=" * 60)
    print("[Step 4] Testing RECALL for JWT null userId error:")
    print(f"Query: \"{query}\"")
    print("=" * 60)

    try:
        recalled = await recall_similar(query)
        print(f"\nMemories Found: {len(recalled)}")
        for idx, item in enumerate(recalled, 1):
            text = item.get("text", "")
            print(f"\n--- [Memory #{idx}] ---")
            print(text.strip())
    except Exception as e:
        print(f"ERROR during recall: {e}")

    # 6. Test Reflect on the JWT null userId error
    print("\n" + "=" * 60)
    print("[Step 5] Testing REFLECT for JWT null userId error:")
    print(f"Query: \"{query}\"")
    print("=" * 60)

    try:
        reflection = await reflect_on_bug(query)
        print("\nReflection Output:")
        if reflection:
            print(reflection.strip())
        else:
            print("(No reflection output returned)")
    except Exception as e:
        print(f"ERROR during reflect: {e}")

    # 7. Comparison: Analysis WITHOUT memory vs WITH memory
    print("\n" + "=" * 60)
    print("[Step 6] Comparing Analysis: WITHOUT Memory vs WITH Memory")
    print(f"Error: \"{query}\"")
    print("=" * 60)

    # 7a. Analysis WITHOUT memory (use_memory=False)
    print("\n>>> 1. WITHOUT MEMORY (use_memory=False) <<<")
    try:
        res_no_mem = await analyze_bug(
            error_message=query,
            stack_trace=stack_trace,
            file_path=file_path,
            developer=developer,
            use_memory=False,
        )
        print(f"Memory Used    : {res_no_mem['memory_used']}")
        print(f"Memories Found : {res_no_mem['memories_found']}")
        print(f"Snippets Length: {len(res_no_mem['memories'])}")
        print("\n[Analysis Output - Without Memory]:")
        print(res_no_mem["analysis"].strip())
    except Exception as e:
        print(f"ERROR during analysis without memory: {e}")

    # 7b. Analysis WITH memory (use_memory=True)
    print("\n" + "-" * 60)
    print(">>> 2. WITH MEMORY (use_memory=True) <<<")
    try:
        res_with_mem = await analyze_bug(
            error_message=query,
            stack_trace=stack_trace,
            file_path=file_path,
            developer=developer,
            use_memory=True,
        )
        print(f"Memory Used    : {res_with_mem['memory_used']}")
        print(f"Memories Found : {res_with_mem['memories_found']}")
        print(f"Snippets Length: {len(res_with_mem['memories'])}")
        print("\n[Analysis Output - With Memory]:")
        print(res_with_mem["analysis"].strip())
    except Exception as e:
        print(f"ERROR during analysis with memory: {e}")

    print("\n" + "=" * 60)
    print("  Live Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevMind Live Test")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed 10 bugs into memory before running tests (disabled by default)",
    )
    args = parser.parse_args()
    asyncio.run(run_live_test(seed=args.seed))
