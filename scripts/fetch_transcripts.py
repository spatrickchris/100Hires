#!/usr/bin/env python3
"""Pulls YouTube transcripts into research/youtube-transcripts/.

Usage:
    pip install youtube-transcript-api requests
    python scripts/fetch_transcripts.py scripts/videos.txt

videos.txt lines look like:
    <youtube url> | <author-slug> | <short-title>

Tries free captions first (Bahasa, then English, then whatever exists).
If a video has no captions, set SUPADATA_API_KEY (free key at supadata.ai)
and it falls back to their API.
"""
import os
import re
import sys
import pathlib
import datetime

OUT = pathlib.Path(__file__).resolve().parent.parent / "research" / "youtube-transcripts"


def video_id(s):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else s.strip()


def fetch_captions(vid):
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    for langs in (["id"], ["en"], None):
        try:
            got = api.fetch(vid, languages=langs) if langs else api.fetch(vid)
            return " ".join(s.text for s in got.snippets)
        except Exception:
            continue
    return None


def fetch_supadata(vid):
    key = os.environ.get("SUPADATA_API_KEY")
    if not key:
        return None
    import requests
    r = requests.get(
        "https://api.supadata.ai/v1/youtube/transcript",
        params={"videoId": vid, "text": "true"},
        headers={"x-api-key": key},
        timeout=30,
    )
    if r.ok:
        return r.json().get("content")
    print(f"  supadata {r.status_code}: {r.text[:150]}")
    return None


def save(author, title, vid, text):
    folder = OUT / author
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{title}.md"
    head = (
        f"# {title.replace('-', ' ')}\n\n"
        f"- Video: https://www.youtube.com/watch?v={vid}\n"
        f"- Author: {author}\n"
        f"- Collected: {datetime.date.today().isoformat()}\n\n---\n\n"
    )
    path.write_text(head + text, encoding="utf-8")
    print(f"  saved {path}")


def main(listfile):
    for line in pathlib.Path(listfile).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, author, title = [p.strip() for p in line.split("|")]
        vid = video_id(url)
        print(f"fetching {vid} ({author})")
        text = fetch_captions(vid) or fetch_supadata(vid)
        if text:
            save(author, title, vid, text)
        else:
            print("  no captions found — try the Supadata fallback for this one")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
