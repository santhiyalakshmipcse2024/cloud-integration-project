"""Download axe-core into ./vendor (pin a version you have reviewed)."""
import sys, urllib.request
from pathlib import Path

VERSION = sys.argv[1] if len(sys.argv) > 1 else "4.10.2"
dest = Path(__file__).resolve().parents[1] / "vendor"
dest.mkdir(exist_ok=True)
url = f"https://cdn.jsdelivr.net/npm/axe-core@{VERSION}/axe.min.js"
urllib.request.urlretrieve(url, dest / "axe.min.js")
print(f"axe-core {VERSION} saved to {dest / 'axe.min.js'}")
