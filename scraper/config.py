"""Corn-Store scraper configuration."""

# GitHub search queries. Each is a separate API call.
# Rate limit: 30 req/min authenticated, 10 req/min unauthenticated.
SEARCH_QUERIES = [
    "topic:android topic:foss language:kotlin",
    "topic:android topic:kotlin stars:>10",
    "topic:android-app language:kotlin",
    "topic:fdroid language:kotlin",
    "topic:android language:kotlin stars:>50",
]

# Always include these repos, regardless of search results.
ALLOWLIST = [
    "SimoesCTT/Line16",
    "SimoesCTT/MarsClock",
    "SimoesCTT/Freedom-file-manager-",
    "SimoesCTT/PhaseScope",
    "SimoesCTT/PhaseFlow",
    "SimoesCTT/PhaseVib",
    "SimoesCTT/MedPhase",
    "SimoesCTT/ctt_android",
]

# Never index these.
BLOCKLIST = [
    # Add repos here as needed
]

# Output path relative to repo root.
OUTPUT = "docs/index.json"

# Skip repos whose latest APK release is older than this many days.
RECENT_DAYS = 730

# Max results per search query (GitHub caps at 100).
MAX_PER_QUERY = 30

# Set at runtime from env; left None here.
GITHUB_TOKEN = None
