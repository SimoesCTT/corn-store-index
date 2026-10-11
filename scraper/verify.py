"""APK metadata extraction and signature verification, with local cache."""
import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path

CACHE_DIR = Path(os.environ.get("CORN_CACHE", Path.home() / ".cache" / "corn-store"))


def _tool(name: str, default: str) -> str:
    return os.environ.get(name, default)


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def cached_apk(url: str) -> Path | None:
    """Return path to cached APK if present, else None."""
    p = CACHE_DIR / f"{cache_key(url)}.apk"
    return p if p.exists() and p.stat().st_size > 0 else None


def download_apk(url: str, dest: Path, max_bytes: int = 100 * 1024 * 1024) -> bool:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = cached_apk(url)
    if cached:
        # Copy from cache instead of re-downloading
        import shutil
        shutil.copy(cached, dest)
        return True

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CornStore/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            size = int(r.headers.get("Content-Length", 0))
            if size and size > max_bytes:
                print(f"  too large: {size} bytes")
                return False
            data = r.read(max_bytes)
        dest.write_bytes(data)
        # Save to cache
        cached_path = CACHE_DIR / f"{cache_key(url)}.apk"
        cached_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"  download failed: {e}")
        return False


def analyze_apk(apk_path: Path) -> dict | None:
    aapt2 = _tool("AAPT2", "aapt2")
    try:
        out = subprocess.run(
            [aapt2, "dump", "badging", str(apk_path)],
            capture_output=True, text=True, timeout=45, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  aapt2 failed: {e}")
        return None

    info = {}
    for line in out.splitlines():
        if line.startswith("package:"):
            for part in line.split():
                if part.startswith("name="):
                    info["package"] = part.split("=", 1)[1].strip("'")
                elif part.startswith("versionCode="):
                    info["versionCode"] = part.split("=", 1)[1].strip("'")
                elif part.startswith("versionName="):
                    info["versionName"] = part.split("=", 1)[1].strip("'")
        elif line.startswith("sdkVersion:"):
            info["minSdk"] = line.split(":", 1)[1].strip().strip("'")
        elif line.startswith("targetSdkVersion:"):
            info["targetSdk"] = line.split(":", 1)[1].strip().strip("'")
        elif line.startswith("application-label:"):
            info["label"] = line.split(":", 1)[1].strip().strip("'")

    return info if "package" in info else None


def verify_signature(apk_path: Path) -> dict | None:
    apksigner = _tool("APKSIGNER", "apksigner")
    try:
        out = subprocess.run(
            [apksigner, "verify", "--print-certs", str(apk_path)],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        return None

    if out.returncode != 0:
        return {"error": "signature verification failed"}

    combined = out.stdout + out.stderr
    for line in combined.splitlines():
        if "SHA-256 digest:" in line:
            fp = line.split(":", 1)[1].strip().replace(" ", "").lower()
            if fp.startswith("9e0e6b13ef4f6f4cc8d0b4a8d1a5c9a0"):
                return {"error": "signed with debug key"}
            return {"sha256": fp}
    return {"error": "no certificate found"}
