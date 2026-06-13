#!/usr/bin/env python3
"""Profile Python import graph — find which modules cost memory/time."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APP_PORT"] = "7799"
os.environ["AUTH_ENABLED"] = "false"
mode = sys.argv[1] if len(sys.argv) > 1 else "full"
os.environ["LODESTAR_LITE"] = "true" if mode == "lite" else "false"

import time

def check_mem(label=""):
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss

def heavy_modules():
    """Return list of 'heavy' loaded modules (known big deps)."""
    heavy = []
    for name, mod in sorted(sys.modules.items()):
        if mod is None:
            continue
        if any(h in name for h in [
            "chromadb", "fastembed", "onnx", "sqlite_vec", "numpy",
            "feedparser", "playwright", "transformers", "torch",
            "sentence_transformers", "huggingface", "PIL", "cv2",
            "pandas", "scipy", "matplotlib", "sklearn",
        ]):
            heavy.append(name)
    return heavy

start = time.time()
rss_before = check_mem()

# Import the app — this triggers full boot
import app

rss_after = check_mem()
elapsed = time.time() - start

print(f"=== Import Profile ({mode} mode) ===")
print(f"Import time:  {elapsed:.2f}s")
print(f"RSS delta:    {rss_after - rss_before} KB")
print(f"Final RSS:    {rss_after} KB")
print()
print("Heavy modules loaded:")
for m in sorted(set(heavy_modules())):
    try:
        size = sys.getsizeof(sys.modules[m])
    except Exception:
        size = 0
    print(f"  {m}")
print()
# Top modules by size
sizes = []
for name, mod in sys.modules.items():
    if mod and hasattr(mod, "__file__") and mod.__file__:
        try:
            s = sys.getsizeof(mod)
            sizes.append((s, name))
        except Exception:
            pass
print("Largest modules by sys.getsizeof:")
for s, name in sorted(sizes, reverse=True)[:20]:
    print(f"  {s:>8}  {name}")
