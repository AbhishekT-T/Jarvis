"""Tier smoke test for JARVIS 3-tier architecture.

Launches the Pro Tier (qwen3-coder:30b) and Vision Tier (gemma4:e4b)
through the real tools.py code paths, then verifies the sleep/wake
contract: both heavy tiers must be UNLOADED (keep_alive=0) after use,
while the Flash Tier (qwen2.5:3b, keep_alive=-1) stays resident.

Run from the repo root with the project .venv:
    .venv\\Scripts\\python.exe tier_smoke_test.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_project"))


def main() -> int:
    import tools
    import ollama

    def resident() -> list:
        """Names of models currently loaded in the Ollama server."""
        try:
            ps = ollama.ps()
            return [m.model for m in ps.models]
        except Exception as e:
            return [f"<ps error: {e}>"]

    print("=== 1. Pre-flight: models on disk ===", flush=True)
    for m in ollama.list().get("models", []):
        print(f"    {m['model']:<25} {m['size']/1e9:6.1f} GB", flush=True)

    print("\n=== 2. Residency check before any heavy-tier use ===", flush=True)
    print("    resident:", resident(), flush=True)

    print("\n=== 3. Pro Tier smoke test (qwen3-coder:30b) ===", flush=True)
    t0 = time.time()
    result = tools.ask_pro_coder(
        "Write a Python function that returns the nth Fibonacci number (iterative). "
        "Return only the code, no prose."
    )
    print(f"    elapsed: {time.time() - t0:.1f}s", flush=True)
    print(f"    result ({len(result)} chars):", flush=True)
    print(result[:1200], flush=True)
    print("\n    resident after Pro call (expect no qwen3-coder):", resident(), flush=True)

    print("\n=== 4. Vision model smoke test (gemma4:e4b) ===", flush=True)
    t0 = time.time()
    r = tools.capture_and_analyze_screen("Describe this screen in detail.")
    print(f"    elapsed: {time.time() - t0:.1f}s", flush=True)
    print(f"    result ({len(r)} chars):", flush=True)
    print(r[:1200], flush=True)
    print("\n    resident after Vision call (expect no gemma4):", resident(), flush=True)

    print("\n=== 5. Final residency check (expect qwen2.5:3b resident, heavy tiers gone) ===", flush=True)
    print("    resident:", resident(), flush=True)
    print("\nSMOKE TEST COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())