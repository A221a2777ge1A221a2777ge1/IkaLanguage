from pathlib import Path
from app.tts_engine import build_ssml_with_ipa, synthesize_mp3_from_ssml

def main():
    text = "Ndewo. Kedu ka i mere?"
    ssml = build_ssml_with_ipa(text)

    mp3_bytes = synthesize_mp3_from_ssml(
        ssml=ssml,
        voice_name="en-GB-Standard-A",
        speaking_rate=1.0,
        pitch=0.0,
    )

    out = Path("out.mp3")
    out.write_bytes(mp3_bytes)
    print("Wrote:", out.resolve(), "bytes:", len(mp3_bytes))

if __name__ == "__main__":
    main()
