"""Corn-Store scraper configuration."""

# GitHub search queries. Each is a separate API call.
# Rate limit: 5000 req/hour authenticated, 60/hour unauthenticated.
# Always run with a token (GITHUB_TOKEN env var) to avoid rate limits.
SEARCH_QUERIES = [
    # Broad FOSS Android
    "topic:android topic:foss language:kotlin",
    "topic:android topic:foss language:java",
    "topic:android-app language:kotlin",
    "topic:android-app language:java",
    "topic:fdroid language:kotlin",
    "topic:fdroid language:java",

    # Popular Android apps
    "topic:android language:kotlin stars:>50",
    "topic:android language:kotlin stars:>500",
    "topic:android-app stars:>50",

    # Lower thresholds to catch smaller/newer apps
    "topic:android topic:kotlin stars:>10",
    "topic:android topic:kotlin stars:>2",
    "topic:android-app language:kotlin stars:>1",
    "topic:foss-android stars:>1",

    # Specific domains that often have FOSS Android apps
    "topic:android topic:privacy language:kotlin",
    "topic:android topic:security language:kotlin",
    "topic:android topic:music language:kotlin",
    "topic:android topic:reader language:kotlin",
    "topic:android topic:notes language:kotlin",
    "topic:android topic:file-manager language:kotlin",
    "topic:android topic:launcher language:kotlin",
    "topic:android topic:keyboard language:kotlin",
]

# Always include these repos, regardless of search results.
# Add new SimoesCTT repos here — they'll be indexed even if the
# search queries don't pick them up.
ALLOWLIST = [
    "SimoesCTT/Line16",
    "SimoesCTT/MarsClock",
    "SimoesCTT/Freedom-file-manager-",
    "SimoesCTT/PhaseScope",
    "SimoesCTT/PhaseFlow",
    "SimoesCTT/PhaseVib",
    "SimoesCTT/MedPhase",
    "SimoesCTT/ctt_android",
    "SimoesCTT/corn-store-app",
    "SimoesCTT/corn-store-index",
]

# Never index these, even if they match a search.
BLOCKLIST = [
    # Add repos here as needed
]

# Output path relative to repo root.
OUTPUT = "docs/index.json"

# Skip repos whose latest APK release is older than this many days.
RECENT_DAYS = 730

# Max results per search query (GitHub API caps at 100 per page).
MAX_PER_QUERY = 30

# Filled at runtime from the GITHUB_TOKEN env var. Not used directly —
# scrape.py reads os.environ['GITHUB_TOKEN'] and uses that.
GITHUB_TOKEN = None
