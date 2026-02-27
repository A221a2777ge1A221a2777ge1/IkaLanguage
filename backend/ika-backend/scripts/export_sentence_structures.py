import json
import os
from pathlib import Path

# Try common locations
CANDIDATES = [
    Path("data/ika_grammar_patterns.json"),
    Path("data/exports/ika_grammar_patterns.json"),
    Path("app/data/ika_grammar_patterns.json"),
    Path("data/grammar/ika_grammar_patterns.json"),
]

path = None
for p in CANDIDATES:
    if p.exists():
        path = p
        break

if path is None:
    # fallback: search
    hits = list(Path(".").rglob("*grammar*pattern*.json")) + list(Path(".").rglob("*patterns*.json"))
    hits = [h for h in hits if h.is_file()]
    if not hits:
        raise SystemExit("ERROR: Could not find a grammar patterns JSON file. Run: find . -iname '*pattern*.json'")
    path = hits[0]

print(f"USING_FILE={path}")

data = json.loads(path.read_text(encoding="utf-8"))

# Support different shapes:
# - {"patterns":[{pattern_id, slots, ...}, ...]}
# - [{"pattern_id":..., "slots":[...]}]
# - {"sentence.svo": {"slots":[...]}, ...}
patterns = None
if isinstance(data, dict) and "patterns" in data and isinstance(data["patterns"], list):
    patterns = data["patterns"]
elif isinstance(data, list):
    patterns = data
elif isinstance(data, dict):
    # dict keyed by pattern_id
    patterns = []
    for k, v in data.items():
        if isinstance(v, dict):
            v = dict(v)
            v.setdefault("pattern_id", k)
            patterns.append(v)
else:
    raise SystemExit("ERROR: Unknown JSON structure for patterns.")

# Normalize and sort
out = []
for p in patterns:
    pid = p.get("pattern_id") or p.get("id") or p.get("name")
    slots = p.get("slots") or p.get("slot_order") or []
    kind = p.get("kind") or p.get("type") or ""
    if pid:
        out.append((pid, kind, slots))

out.sort(key=lambda x: x[0].lower())

print(f"TOTAL_PATTERNS={len(out)}\n")

for pid, kind, slots in out:
    slots_str = ", ".join(slots) if isinstance(slots, list) else str(slots)
    kind_str = f" [{kind}]" if kind else ""
    print(f"- {pid}{kind_str}")
    print(f"  slots: {slots_str}")
