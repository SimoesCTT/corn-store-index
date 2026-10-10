# Corn-Store Index

A daily-updated catalog of FOSS Android apps distributed via GitHub Releases.

The scraper walks GitHub looking for repositories that publish signed APK
files as release assets, extracts their metadata, verifies their signatures,
and writes a JSON index at:

    https://simoesctt.github.io/corn-store-index/index.json

Consumed by the Corn-Store client and by Obtainium.

## What's in the index

Each entry contains:
- package name, version code, version name, min SDK
- app label (from AndroidManifest)
- source repo, description, license, stars
- release tag, release URL, direct APK URL, APK size
- signing certificate SHA-256

## Running locally

    pip install -r requirements.txt
    export AAPT2=$HOME/Android/Sdk/build-tools/34.0.0/aapt2
    export APKSIGNER=$HOME/Android/Sdk/build-tools/34.0.0/apksigner
    export GITHUB_TOKEN=ghp_yourtoken
    python3 scraper/scrape.py

## Running in CI

Handled by `.github/workflows/scrape.yml`. Runs daily at 03:00 UTC and on
manual dispatch.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
