#!/usr/bin/env python3
"""
Quick CLI test: build SSML from text, call TTS, write out.mp3.
Run from repo root (ika_app or backend/ika-backend) with PYTHONPATH including app parent.

  cd backend/ika-backend
  python scripts/test_tts.py "hello water"
  # or
  python scripts/test_tts.py "biko" --output out.mp3
"""
import argparse
import sys
from pathlib import Path

# Add backend/ika-backend so "app" package resolves
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.tts.ssml import load_ipa_dictionary, text_to_ssml
from app.tts_engine import synthesize_mp3_from_ssml


def main():
    parser = argparse.ArgumentParser(description="Build SSML, synthesize TTS, write MP3")
    parser.add_argument("text", nargs="?", default="hello water", help="Text to synthesize")
    parser.add_argument("--output", "-o", default="out.mp3", help="Output MP3 path")
    parser.add_argument("--voice", default="default", help="Voice id")
    parser.add_argument("--speaking-rate", type=float, default=1.0)
    parser.add_argument("--pitch", type=float, default=0.0)
    args = parser.parse_args()

    data_dir = _root / "data"
    ipa_dict = load_ipa_dictionary(str(data_dir))
    ssml = text_to_ssml(args.text, ipa_dict)
    print("SSML length:", len(ssml))
    if "<phoneme" in ssml:
        print("SSML contains <phoneme> tags")
    audio = synthesize_mp3_from_ssml(
        ssml,
        voice=args.voice,
        speaking_rate=args.speaking_rate,
        pitch=args.pitch,
    )
    out_path = Path(args.output)
    out_path.write_bytes(audio)
    print(f"Wrote {len(audio)} bytes to {out_path}")


if __name__ == "__main__":
    main()
