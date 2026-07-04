#!/usr/bin/env python3
"""Build the "AI Radar" digest and splice it into README.md.

Sources (all free, no user API key required):
  * GitHub Trending  — most-starred AI/ML repos pushed in the last 7 days
  * Hacker News      — hottest AI/LLM stories from the last 48h (Algolia API)
  * Hugging Face     — current trending models

Each source is fetched independently; if one fails the rest still render.
"""
import datetime
import json
import os
import re
import urllib.parse
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


def github_trending():
    since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    q = f"topic:llm topic:machine-learning pushed:>{since} stars:>500"
    url = ("https://api.github.com/search/repositories?q="
           + urllib.parse.quote(q) + "&sort=stars&order=desc&per_page=5")
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = _get(url, headers)
    rows = []
    for it in data.get("items", [])[:5]:
        rows.append("| [{full}]({url}) | ⭐ {stars:,} | {lang} |".format(
            full=it["full_name"], url=it["html_url"],
            stars=it.get("stargazers_count", 0),
            lang="`{}`".format(it["language"]) if it.get("language") else "—"))
    if not rows:
        return ""
    out = ["### 🛰 Trending AI repos on GitHub", "",
           "| Repo | Stars | Lang |", "|---|---|---|", *rows]
    return "\n".join(out)


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


def huggingface():
    url = "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=5&full=false"
    data = _get(url)
    rows = []
    for m in data[:5]:
        mid = m.get("modelId") or m.get("id")
        task = m.get("pipeline_tag")
        tag = f" `{task}`" if task else ""
        rows.append("| [{id}](https://huggingface.co/{id}){tag} | ❤️ {likes:,} | ⬇️ {dl:,} |".format(
            id=mid, tag=tag, likes=m.get("likes", 0), dl=m.get("downloads", 0)))
    if not rows:
        return ""
    out = ["### 🔥 Trending on Hugging Face", "",
           "| Model | Likes | Downloads |", "|---|---|---|", *rows]
    return "\n".join(out)


def build():
    blocks = []
    for name, fn in (("github", github_trending), ("hn", hacker_news), ("hf", huggingface)):
        try:
            b = fn()
            if b:
                blocks.append(b)
        except Exception as e:  # noqa: BLE001 — never let one source break the digest
            print(f"[warn] source {name} failed: {e}")
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = "\n\n".join(blocks) if blocks else "_No data available right now — will refresh next hour._"
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
