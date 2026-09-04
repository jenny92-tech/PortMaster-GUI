#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/release/portmaster-sources.sh"
STABLE_TAG=${1:-}
OUTPUT=${2:-"$ROOT/dist/maintained-release"}
case "$STABLE_TAG" in 20??.??.??-????) ;; *) echo "exact official stable tag required" >&2; exit 64 ;; esac

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
STAGE="$TMP/PortMaster"
if [ -e "$OUTPUT" ]; then
  [ -d "$OUTPUT" ] || { echo "output path is not a directory: $OUTPUT" >&2; exit 65; }
  [ -z "$(find "$OUTPUT" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
    echo "output directory must be empty: $OUTPUT" >&2
    exit 65
  }
fi
mkdir -p "$STAGE" "$OUTPUT"
cp -a "$ROOT/PortMaster/." "$STAGE/"

# Shared/user-owned content is deliberately absent. The enhanced installer
# preserves those locations from the live environment.
rm -rf "$STAGE/libs" "$STAGE/config" "$STAGE/themes" "$STAGE/logs" "$STAGE/cache"
rm -f "$STAGE/log.txt" "$STAGE/pugwash.txt" "$STAGE/harbourmaster.txt" "$STAGE/pugwash.bak"

rm -f "$STAGE/pylibs.zip"
(cd "$STAGE" && zip -9qr pylibs.zip pylibs exlibs \
  -x '*__pycache__/*' -x '*.DS_Store' -x '._*' -x '*NotoSans*.ttf')
rm -rf "$STAGE/pylibs" "$STAGE/exlibs"

python3 - "$STAGE/pugwash" "$STABLE_TAG" "$JENNY92_PORTMASTER_GUI_RELEASES_URL" <<'PY'
import re
import sys

path, version, fork_releases_url = sys.argv[1:]
release_url = f"{fork_releases_url}/latest/download/"
text = open(path, encoding="utf-8").read()
updated, count = re.subn(r"^PORTMASTER_VERSION = '[^']*'", f"PORTMASTER_VERSION = '{version}'", text, count=1, flags=re.M)
if count != 1:
    raise SystemExit("PORTMASTER_VERSION declaration not found")
updated, count = re.subn(
    r"^PORTMASTER_RELEASE_CHANNEL = '[^']*'",
    "PORTMASTER_RELEASE_CHANNEL = 'stable'",
    updated,
    count=1,
    flags=re.M,
)
if count != 1:
    raise SystemExit("PORTMASTER_RELEASE_CHANNEL declaration not found")
updated, count = re.subn(
    r"^PORTMASTER_RELEASE_URL = '[^']*'",
    f"PORTMASTER_RELEASE_URL = '{release_url}'",
    updated,
    count=1,
    flags=re.M,
)
if count != 1:
    raise SystemExit("PORTMASTER_RELEASE_URL declaration not found")
updated, count = re.subn(
    r"^PORTMASTER_RELEASE_VALUES = \([^\n]*\)",
    "PORTMASTER_RELEASE_VALUES = ('stable', 'beta', 'alpha')",
    updated,
    count=1,
    flags=re.M,
)
if count != 1:
    raise SystemExit("PORTMASTER_RELEASE_VALUES declaration not found")
open(path, "w", encoding="utf-8").write(updated)
PY
printf '%s\n' "$STABLE_TAG" > "$STAGE/version"
(cd "$TMP" && zip -9qr "$OUTPUT/PortMaster.zip" PortMaster)

python3 - "$OUTPUT/version.json" "$OUTPUT/PortMaster.zip" "$STABLE_TAG" "$JENNY92_PORTMASTER_GUI_RELEASE_ASSET_BASE" <<'PY'
import hashlib
import json
import sys

path, archive_path, version, release_base = sys.argv[1:]
digest = hashlib.md5()
with open(archive_path, "rb") as archive:
    for chunk in iter(lambda: archive.read(1024 * 1024), b""):
        digest.update(chunk)
record = {
    "version": version,
    "url": f"{release_base}/{version}/PortMaster.zip",
    "md5": digest.hexdigest(),
}
# Keep the official PortMaster update protocol intact. This fork currently
# publishes stable only, so every selectable channel resolves to that same
# validated release. Independent beta/alpha releases can be enabled later by
# changing only this release-generation policy.
data = {channel: dict(record) for channel in ("alpha", "beta", "stable")}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY

(cd "$OUTPUT" && {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum version.json PortMaster.zip
  else shasum -a 256 version.json PortMaster.zip
  fi
} > SHA256SUMS)

echo "Maintained PortMaster release assets built in $OUTPUT"
