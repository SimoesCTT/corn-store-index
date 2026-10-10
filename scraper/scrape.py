"""Corn-Store indexer.

Walks GitHub, finds repos with signed release APKs, writes docs/index.json.
"""
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (SEARCH_QUERIES, ALLOWLIST, BLOCKLIST, OUTPUT,
                    RECENT_DAYS, MAX_PER_QUERY, GITHUB_TOKEN)
from verify import download_apk, analyze_apk, verify_signature

API = "https://api.github.com"

_headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "CornStoreScraper/1.0",
}
_token = GITHUB_TOKEN or os.environ.get("GITHUB_TOKEN")
if _token:
    _headers["Authorization"] = f"Bearer {_token}"


def gh_get(path: str):
    url = API + path
    req = urllib.request.Request(url, headers=_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  rate limited: {path}")
        elif e.code == 404:
            pass  # normal — repo doesn't exist or is private
        else:
            print(f"  HTTP {e.code}: {path}")
        return None
    except Exception as e:
        print(f"  error: {e}")
        return None


def search_repos(query: str, max_results: int) -> list[str]:
    out = []
    page = 1
    while len(out) < max_results:
        q = urllib.parse.quote(query)
        data = gh_get(f"/search/repositories?q={q}&per_page=30&page={page}")
        if not data or not data.get("items"):
            break
        for item in data["items"]:
            out.append(item["full_name"])
        if len(data["items"]) < 30:
            break
        page += 1
        if page > 4:
            break
    return out[:max_results]


def latest_apk_asset(repo: str):
    """Return dict for the newest release that has an .apk asset, or None."""
    releases = gh_get(f"/repos/{repo}/releases?per_page=10")
    if not releases:
        return None
    for rel in releases:
        for asset in rel.get("assets", []):
            if asset["name"].lower().endswith(".apk"):
                return {
                    "tag": rel["tag_name"],
                    "release_url": rel["html_url"],
                    "apk_url": asset["browser_download_url"],
                    "apk_name": asset["name"],
                    "apk_size": asset["size"],
                    "published_at": rel["published_at"],
                }
    return None


def repo_metadata(repo: str):
    data = gh_get(f"/repos/{repo}")
    if not data:
        return None
    return {
        "full_name": data["full_name"],
        "description": data.get("description") or "",
        "license": (data.get("license") or {}).get("spdx_id", ""),
        "stars": data.get("stargazers_count", 0),
        "homepage": data.get("homepage") or "",
        "topics": data.get("topics", []),
    }


def scrape_repo(repo: str, tmpdir: Path):
    asset = latest_apk_asset(repo)
    if not asset:
        return None

    published = datetime.fromisoformat(asset["published_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - published > timedelta(days=RECENT_DAYS):
        print(f"  too old: {published.date()}")
        return None

    apk_path = tmpdir / f"{repo.replace('/', '_')}.apk"
    if not download_apk(asset["apk_url"], apk_path):
        return None

    info = analyze_apk(apk_path)
    if not info or "package" not in info:
        print(f"  bad APK structure")
        apk_path.unlink(missing_ok=True)
        return None

    sig = verify_signature(apk_path)
    apk_path.unlink(missing_ok=True)
    if not sig or "sha256" not in sig:
        print(f"  rejected: {sig}")
        return None

    meta = repo_metadata(repo)
    if not meta:
        return None

    return {
        "package": info["package"],
        "versionCode": info.get("versionCode", ""),
        "versionName": info.get("versionName", ""),
        "minSdk": info.get("minSdk", ""),
        "targetSdk": info.get("targetSdk", ""),
        "label": info.get("label", repo.split("/")[-1]),
        "repo": meta["full_name"],
        "description": meta["description"],
        "license": meta["license"],
        "stars": meta["stars"],
        "homepage": meta["homepage"],
        "topics": meta["topics"],
        "tag": asset["tag"],
        "release_url": asset["release_url"],
        "apk_url": asset["apk_url"],
        "apk_name": asset["apk_name"],
        "apk_size": asset["apk_size"],
        "published_at": asset["published_at"],
        "signature_sha256": sig["sha256"],
    }


def main():
    print("=== Corn-Store indexer ===")
    token = _token or "(none — unauthenticated, low rate limit)"
    print(f"GitHub token: {'set' if _token else token}")
    print()

    seen = set()
    candidates = []

    for repo in ALLOWLIST:
        if repo not in seen and repo not in BLOCKLIST:
            seen.add(repo)
            candidates.append(repo)

    for query in SEARCH_QUERIES:
        print(f"search: {query}")
        for repo in search_repos(query, MAX_PER_QUERY):
            if repo in seen or repo in BLOCKLIST:
                continue
            seen.add(repo)
            candidates.append(repo)

    print(f"\n{len(candidates)} candidates\n")

    entries = {}
    errors = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for i, repo in enumerate(candidates, 1):
            print(f"[{i}/{len(candidates)}] {repo}")
            try:
                entry = scrape_repo(repo, tmpdir)
                if entry:
                    entries[entry["package"]] = entry
                    print(f"  ✓ {entry['package']}  {entry['versionName']}")
            except Exception as e:
                print(f"  error: {e}")
                errors += 1

    index = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "apps": sorted(entries.values(), key=lambda e: e["label"].lower()),
    }

    out = Path(OUTPUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=2))
    print(f"\n=== done ===")
    print(f"indexed: {len(entries)}")
    print(f"errors:  {errors}")
    print(f"wrote:   {out}")


if __name__ == "__main__":
    main()
