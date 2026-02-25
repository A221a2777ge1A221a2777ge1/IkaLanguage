import json, re
from collections import Counter

# Strong Igbo markers (from your earlier mixed file) — adjust as you learn
IGBO_STRONG = {
    "adịghị", "ọ bụ", "gịnị", "ebe", "onye", "maka", "anyị", "ha", "ga", "ya mere"
}

# Strong Ika markers (from your own ika_dictionary inventory)
IKA_STRONG = {
    "elebe", "kị", "wụ", "onyẹn", "egho", "ole", "rị", "gwọ", "omẹni", "ke", "ẹnyin", "wẹ"
}

def tokenize(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\u00C0-\u024F\u1E00-\u1EFF\s']", " ", s)
    return [t for t in re.split(r"\s+", s) if t]

def score_sentence(ika_text):
    toks = tokenize(ika_text)
    s = 0
    joined = " ".join(toks)

    for m in IGBO_STRONG:
        if " " in m:
            if m in joined:
                s += 3
        else:
            if m in toks:
                s += 3

    for m in IKA_STRONG:
        if " " in m:
            if m in joined:
                s -= 2
        else:
            if m in toks:
                s -= 2

    return s, toks

def main():
    lexicon = json.load(open("exports/lexicon.json", "r", encoding="utf-8"))

    flagged = []
    counts = Counter()

    for e in lexicon:
        ika = e.get("target_text") or ""
        sc, toks = score_sentence(ika)
        # heuristic: only apply to longer texts (sentences/phrases), not single words
        if len(toks) >= 3:
            if sc >= 3:
                label = "likely_igbo"
            elif sc <= -2:
                label = "likely_ika"
            else:
                label = "uncertain"
        else:
            label = "short_or_word"

        e2 = dict(e)
        e2["_igbo_score"] = sc
        e2["_igbo_label"] = label
        flagged.append(e2)
        counts[label] += 1

    json.dump(flagged, open("exports/lexicon_flagged.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("Wrote exports/lexicon_flagged.json")
    print("Counts:", dict(counts))

if __name__ == "__main__":
    main()
