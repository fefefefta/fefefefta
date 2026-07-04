#!/usr/bin/env python3
"""Build the "AI Radar" digest and splice it into README.md.

Source (free, no user API key required):
  * Hacker News — hottest AI/LLM stories from the last 96h (Algolia API)
"""
import datetime
import json
import os
import re
import urllib.request

README = os.path.join(os.path.dirname(__file__), "..", "README.md")
START = "<!--DIGEST:START-->"
END = "<!--DIGEST:END-->"
UA = "fefefefta-profile-digest"


def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _trunc(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


HN_KEYWORDS = re.compile(
    r"\b(AI|LLM|LLMs|GPT|model|models|agent|agents|OpenAI|Anthropic|Claude|"
    r"Gemini|neural|machine learning|ML|diffusion|transformer)\b", re.I)


def hacker_news():
    # Algolia ANDs query words, so we don't pass a boolean query. Instead we pull
    # recent popular stories and keep the AI-related ones by title/url keywords.
    cutoff = int((datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(hours=96)).timestamp())
    url = ("https://hn.algolia.com/api/v1/search?tags=story"
           f"&numericFilters=created_at_i>{cutoff}&hitsPerPage=50")
    data = _get(url)
    hits = [h for h in data.get("hits", [])
            if (h.get("points") or 0) > 20
            and HN_KEYWORDS.search((h.get("title") or "") + " " + (h.get("url") or ""))]
    hits.sort(key=lambda h: h.get("points", 0), reverse=True)
    rows = []
    for h in hits[:5]:
        title = _trunc(h.get("title", ""), 80)
        link = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
        rows.append(f"- [{title}]({link}) · ⬆️ {h.get('points', 0)} · 💬 {h.get('num_comments', 0)}")
    if not rows:
        return ""
    return "\n".join(["### 📰 Hot AI stories on Hacker News", "", *rows])


def build():
    try:
        block = hacker_news()
    except Exception as e:  # noqa: BLE001 — never let a fetch error break the digest
        print(f"[warn] hacker_news failed: {e}")
        block = ""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = block if block else "_No data available right now — will refresh next hour._"
    return f"\n{body}\n\n<sub>🕐 Auto-updated hourly · last refresh: {now}</sub>\n"


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()
    digest = build()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    replacement = f"{START}\n{digest}\n{END}"
    new = pattern.sub(lambda _: replacement, text)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README digest updated.")
    else:
        print("No change.")


if __name__ == "__main__":
    main()
