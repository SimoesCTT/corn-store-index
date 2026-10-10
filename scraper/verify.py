"""APK metadata extraction and signature verification."""
import os
import subprocess
import urllib.request
from pathlib import Path


def _tool(name: str, default: str) -> str:
    return os.environ.get(name, default)


def download_apk(url: str, dest: Path, max_bytes: int = 100 * 1024 * 1024) -> bool:
    """Download APK. Refuses files over 100 MB."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CornStore/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            size = int(r.headers.get("Content-Length", 0))
            if size and size > max_bytes:
                print(f"  too large: {size} bytes")
                return False
            dest.write_bytes(r.read(max_bytes))
        return True
    except Exception as e:
        print(f"  download failed: {e}")
        return False


def analyze_apk(apk_path: Path) -> dict | None:
    """Run aapt2 dump badging. Returns dict with package info or None."""
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
            # package: name='com.foo.bar' versionCode='2' versionName='1.0'
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
    """Return {'sha256': fingerprint} or {'error': reason} or None."""
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
            # Android's well-known debug certificate
            if fp.startswith("9e0e6b13ef4f6f4cc8d0b4a8d1a5c9a0"):
                return {"error": "signed with debug key"}
            return {"sha256": fp}
    return {"error": "no certificate found"}
