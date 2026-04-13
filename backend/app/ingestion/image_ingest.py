"""Image: OCR + OpenAI vision (optional) + Ollama vision (free local, with timeout)."""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

from PIL import Image

from app.config import get_settings


def _mime_for_path(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")


def _resize_for_vision(path: Path, max_side: int = 1536) -> Path:
    """Downscale huge screenshots so OCR + Ollama are faster."""
    try:
        with Image.open(path) as im:
            w, h = im.size
            if max(w, h) <= max_side:
                return path
            im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            out = path.parent / f"_rag_thumb_{path.stem}.jpg"
            im.save(out, format="JPEG", quality=88)
            return out
    except Exception:
        return path


def _ollama_vision_caption(path: Path) -> str:
    """
    Official ollama Python client. Bounded by timeout so upload jobs don't hang for 10+ minutes.
    """
    settings = get_settings()
    if not settings.use_ollama_vision:
        return ""

    try:
        from ollama import Client
    except ImportError:
        return ""

    host = settings.ollama_base_url.rstrip("/")
    timeout = float(max(15, settings.ollama_vision_timeout_sec))
    client = Client(host=host, timeout=timeout)

    def _call() -> str:
        r = client.chat(
            model=settings.ollama_vision_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Briefly describe this image for search: visible text, charts, or scene. "
                        "Keep under 400 words."
                    ),
                    "images": [str(path.resolve())],
                }
            ],
        )
        msg = getattr(r, "message", None)
        if msg is None and isinstance(r, dict):
            msg = r.get("message")
        content = getattr(msg, "content", None) if msg is not None else None
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        return (content or "").strip()

    # Extra guard: executor timeout in case client ignores timeout
    to = int(min(timeout, float(settings.ollama_vision_timeout_sec) + 5))
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_call)
        try:
            return fut.result(timeout=to)
        except FuturesTimeout:
            return ""
        except Exception:
            return ""


def extract_image_text(path: Path) -> str:
    """
    1) Tesseract OCR if installed (on resized image if large)
    2) OpenAI vision if OPENAI_API_KEY
    3) Ollama vision if enabled (timeout-bounded)
    """
    settings = get_settings()
    work_path = _resize_for_vision(path)

    ocr_text = ""
    try:
        import pytesseract

        img = Image.open(work_path)
        ocr_text = pytesseract.image_to_string(img) or ""
    except Exception:
        ocr_text = ""

    ocr_text = ocr_text.strip()
    vision_note = ""
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
            b64 = base64.standard_b64encode(work_path.read_bytes()).decode("ascii")
            mime = _mime_for_path(work_path)
            resp = client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Describe this image briefly for retrieval: charts, labels, "
                                    "and key text. If it is a chart, explain axes and trends."
                                ),
                            },
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }
                ],
                max_tokens=500,
            )
            vision_note = (resp.choices[0].message.content or "").strip()
        except Exception:
            vision_note = ""

    ollama_note = ""
    if not vision_note:
        ollama_note = _ollama_vision_caption(work_path)

    if work_path != path and work_path.exists() and "_rag_thumb_" in work_path.name:
        try:
            work_path.unlink()
        except OSError:
            pass

    parts = []
    if ocr_text:
        parts.append("## OCR Text\n" + ocr_text)
    if vision_note:
        parts.append("## Visual / Semantic Description (OpenAI)\n" + vision_note)
    if ollama_note:
        parts.append("## Visual / Semantic Description (Ollama)\n" + ollama_note)
    if not parts:
        return (
            "[No image description indexed. Do this once: `ollama pull "
            + settings.ollama_vision_model
            + "` then re-upload the image. Optional: install Tesseract for OCR, or set OPENAI_API_KEY for cloud vision. "
            + "Tip: set USE_OLLAMA_VISION=false in .env for faster uploads (OCR only).]"
        )
    return "\n\n".join(parts)
