import os, json, datetime
from google.cloud import firestore

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("CLOUDSDK_CORE_PROJECT")
db = firestore.Client(project=PROJECT)

def to_jsonable(x):
    # Firestore Timestamp / DatetimeWithNanoseconds -> ISO string
    if hasattr(x, "isoformat"):
        try:
            return x.isoformat()
        except Exception:
            pass

    if isinstance(x, (datetime.datetime, datetime.date)):
        return x.isoformat()

    if isinstance(x, dict):
        return {k: to_jsonable(v) for k, v in x.items()}

    if isinstance(x, (list, tuple)):
        return [to_jsonable(v) for v in x]

    return x

def export_collection(col_name, out_path):
    docs = db.collection(col_name).stream()
    rows = []
    for d in docs:
        row = d.to_dict()
        row = to_jsonable(row)
        row["_doc_id"] = d.id
        rows.append(row)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(rows)} docs -> {out_path}")

def main():
    export_collection("lexicon", "exports/lexicon.json")
    export_collection("words", "exports/words.json")

if __name__ == "__main__":
    main()
