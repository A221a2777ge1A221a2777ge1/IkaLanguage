import re, json, subprocess

# pulls list from gsutil and builds a mapping of numeric id -> gs path
cmd = ["bash", "-lc", "gsutil ls gs://ikause.appspot.com/audio/"]
out = subprocess.check_output(cmd, text=True)

audio = {}
for line in out.splitlines():
    line = line.strip()
    m = re.search(r"/audio/(\d+)\.m4a$", line)
    if m:
        audio[m.group(1)] = line

with open("exports/audio_index.json", "w", encoding="utf-8") as f:
    json.dump(audio, f, ensure_ascii=False, indent=2)

print("Wrote exports/audio_index.json with", len(audio), "numbered audio files")
