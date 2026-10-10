"""Convert Corn-Store index.json to Komi Store cached-data format.

Reads:  docs/index.json
Writes: docs/cached-data/trending/android.json
        docs/cached-data/new-releases/android.json
        docs/cached-data/most-popular/android.json
        docs/cached-data/topics/<slug>/android.json
"""
import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "index.json"
OUT_DIR = ROOT / "docs" / "cached-data"

# Map Corn-Store topic strings (from index.json) to Komi topic slugs.
# Komi's TopicCategory.toApiSlug() produces these exact strings.
TOPIC_MAP = {
    "android": "android",
    "kotlin": "kotlin",
    "foss": "foss",
    "fdroid": "fdroid",
    "privacy": "privacy",
    "security": "security",
    "utilities": "utilities",
    "productivity": "productivity",
    "finance": "finance",
    "science": "science",
    "education": "education",
    "medical": "medical",
}


def stable_id(package: str) -> int:
    """Deterministic 63-bit id from package name."""
    h = hashlib.sha256(package.encode()).digest()
    return int.from_bytes(h[:8], "big") & 0x7FFFFFFFFFFFFFFF


def last_updated(iso: str) -> str:
    """Return a single ISO timestamp representing the whole file's freshness."""
    return iso


def repo_entry(app: dict) -> dict:
    """Map one Corn-Store entry to a CachedGithubRepoSummary."""
    full_name = app.get("repo", "")
    owner_login = full_name.split("/")[0] if "/" in full_name else "SimoesCTT"

    return {
        "id": stable_id(app["package"]),
        "name": full_name.split("/")[-1] if "/" in full_name else app.get("label", ""),
        "fullName": full_name,
        "owner": {
            "login": owner_login,
            "avatarUrl": f"https://github.com/{owner_login}.png",
        },
        "description": app.get("description") or "",
        "defaultBranch": "main",
        "htmlUrl": f"https://github.com/{full_name}",
        "stargazersCount": app.get("stars", 0),
        "forksCount": 0,
        "language": "Kotlin",
        "topics": app.get("topics", []),
        "releasesUrl": f"https://api.github.com/repos/{full_name}/releases{{/id}}",
        "updatedAt": app.get("published_at", ""),
        "latestReleaseDate": app.get("published_at", ""),
        "trendingScore": float(app.get("stars", 0)),
        "popularityScore": int(app.get("stars", 0)),
        "dailyStars": 0,
        "availablePlatforms": ["Android"],
        "downloadCount": 0,
    }


def write_bundle(path: Path, category: str, apps: list[dict], generated_at: str):
    payload = {
        "category": category,
        "platform": "android",
        "lastUpdated": generated_at,
        "totalCount": len(apps),
        "repositories": [repo_entry(a) for a in apps],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {path.relative_to(ROOT)}  ({len(apps)} repos)")


def main():
    if not SRC.exists():
        print(f"ERROR: {SRC} not found")
        sys.exit(1)

    index = json.loads(SRC.read_text())
    apps = index.get("apps", [])
    generated_at = index.get("generated_at", datetime.now(timezone.utc).isoformat())
    print(f"Loaded {len(apps)} apps from {SRC.relative_to(ROOT)}")

    # Trending: sorted by stars descending
    trending = sorted(apps, key=lambda a: a.get("stars", 0), reverse=True)
    write_bundle(OUT_DIR / "trending" / "android.json", "trending", trending, generated_at)

    # New releases: sorted by published_at descending
    new_releases = sorted(apps, key=lambda a: a.get("published_at", ""), reverse=True)
    write_bundle(OUT_DIR / "new-releases" / "android.json", "new-releases", new_releases, generated_at)

    # Most popular: same as trending for now
    most_popular = sorted(apps, key=lambda a: a.get("stars", 0), reverse=True)
    write_bundle(OUT_DIR / "most-popular" / "android.json", "most-popular", most_popular, generated_at)

    # Topic bundles: filter apps by topics
    topics_seen: set[str] = set()
    for app in apps:
        for topic in app.get("topics", []):
            topic_lower = topic.lower()
            if topic_lower in TOPIC_MAP:
                topics_seen.add(TOPIC_MAP[topic_lower])

    for slug in sorted(topics_seen):
        filtered = [
            a for a in apps
            if any(t.lower() == slug for t in a.get("topics", []))
        ]
        if filtered:
            write_bundle(OUT_DIR / "topics" / slug / "android.json", "topic", filtered, generated_at)

    print(f"\nDone. {len(topics_seen)} topic bundles written.")


if __name__ == "__main__":
    main()
