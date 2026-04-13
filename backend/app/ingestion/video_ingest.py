"""Video: extract audio, speech-to-text; optional key frames as image captions."""
import subprocess
import tempfile
from pathlib import Path

from app.config import get_settings


def _run_ffmpeg_extract_audio(video_path: Path, wav_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe_audio_openai(wav_path: Path) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return ""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    with open(wav_path, "rb") as f:
        tr = client.audio.transcriptions.create(model="whisper-1", file=f)
    return (tr.text or "").strip()


def extract_frame_png(video_path: Path, out_png: Path, t_sec: float = 1.0) -> bool:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(t_sec),
        "-i",
        str(video_path),
        "-vframes",
        "1",
        str(out_png),
    ]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and out_png.exists()


def extract_video_content(path: Path) -> str:
    """
    Pipeline: audio -> Whisper transcript; optional single frame -> vision description.
    """
    settings = get_settings()
    parts: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        try:
            _run_ffmpeg_extract_audio(path, wav)
        except Exception as e:
            return (
                f"[Video audio extraction failed: {e}. "
                "Install ffmpeg and ensure the file has an audio track.]"
            )

        transcript = transcribe_audio_openai(wav)
        if transcript:
            parts.append("## Audio Transcript\n" + transcript)
        else:
            parts.append(
                "[No transcript: set OPENAI_API_KEY for Whisper, or audio extraction failed.]"
            )

        frame = Path(tmp) / "frame.png"
        if extract_frame_png(path, frame) and settings.openai_api_key:
            try:
                from app.ingestion.image_ingest import extract_image_text

                cap = extract_image_text(frame)
                if cap and "No text extracted" not in cap:
                    parts.append("## Sample Frame Understanding\n" + cap)
            except Exception:
                pass

    return "\n\n".join(parts)
