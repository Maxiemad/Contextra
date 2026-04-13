"""Fetch public HTTP(S) URLs and extract readable text (with basic SSRF guards)."""
from __future__ import annotations

import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings


def _hostname_blocked(host: str) -> bool:
    h = host.lower().strip(".")
    if h in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
        return True
    if h.endswith(".localhost") or h.endswith(".local"):
        return True
    if h == "169.254.169.254" or h.startswith("169.254."):
        return True
    return False


def is_safe_http_url(url: str) -> bool:
    """Block obvious SSRF targets; not a substitute for a full egress firewall."""
    try:
        p = urlparse(url.strip())
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = p.hostname
    if not host:
        return False
    if _hostname_blocked(host):
        return False
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return False
        if ip.version == 4 and str(ip).startswith("169.254."):
            return False
    return True


def _extract_title(soup: BeautifulSoup) -> str:
    t = soup.title
    if t and t.string:
        s = t.string.strip()
        if s:
            return re.sub(r"\s+", " ", s)[:200]
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)[:200]
    return "Web page"


def html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    title = _extract_title(soup)
    body_el = soup.body or soup
    body_text = body_el.get_text(separator="\n", strip=True)
    body_text = re.sub(r"\n{3,}", "\n\n", body_text)
    return title, body_text


async def fetch_url_content(url: str) -> tuple[str, str, str]:
    """
    Returns (final_url, suggested_filename_stem, full_text_for_indexing).
    """
    settings = get_settings()
    max_bytes = min(2 * 1024 * 1024, max(64 * 1024, settings.max_upload_mb * 1024 * 1024))
    headers = {
        "User-Agent": "MultimodalRAG/1.0 (+https://github.com/)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
    }
    timeout = httpx.Timeout(25.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
        r.raise_for_status()
        if len(r.content) > max_bytes:
            raise ValueError(f"Response exceeds {max_bytes // (1024 * 1024)} MB cap.")
        if b"\x00" in r.content[:4096]:
            raise ValueError("Response looks binary; only HTML and plain text are supported.")
        ctype = (r.headers.get("content-type") or "").lower()
        final = str(r.url)
        if "text/html" in ctype or "application/xhtml" in ctype:
            is_html = True
        elif "text/plain" in ctype:
            is_html = False
        elif not ctype:
            is_html = b"<" in r.content[:1200]
        else:
            raise ValueError("URL must return HTML or plain text (not PDF/images).")

        if is_html:
            page_title, body = html_to_text(r.text)
            text = f"Title: {page_title}\nSource: {final}\n\n{body}"
            stem_src = page_title
        else:
            body = r.text.strip()
            text = f"Title: Plain text\nSource: {final}\n\n{body}"
            stem_src = Path(urlparse(final).path).name or "webpage"
            if not stem_src or stem_src == "/":
                stem_src = "webpage"

    stem = re.sub(r"[^\w\s.-]", "", stem_src)[:80].strip() or "webpage"
    stem = re.sub(r"[\s_]+", "_", stem).strip("_") or "webpage"
    return final, stem, text
