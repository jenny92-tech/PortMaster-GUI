#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STABLE_TAG=${1:-}
OUTPUT=${2:-"$ROOT/dist/maintained-release"}
EXPECTED_RELEASE_CHANNEL=stable
EXPECTED_RELEASE_VALUES="('stable', 'beta', 'alpha')"
source "$ROOT/release/portmaster-sources.sh"
case "$STABLE_TAG" in 20??.??.??-????) ;; *) echo "exact official stable tag required" >&2; exit 64 ;; esac
STABLE_REF=${PORTMASTER_OFFICIAL_STABLE_REF:-refs/tags/$STABLE_TAG}
git -C "$ROOT" rev-parse -q --verify "$STABLE_REF^{commit}" >/dev/null || {
  echo "official stable ref is not available locally: $STABLE_REF" >&2; exit 65;
}
git -C "$ROOT" merge-base --is-ancestor "$STABLE_REF" HEAD || {
  echo "candidate is not based on exact official stable tag $STABLE_TAG" >&2; exit 65;
}

ALLOWLIST=$(cat <<'EOF'
.github/workflows/build-miniloong.yaml
.github/workflows/follow-official-stable.yaml
README.md
PortMaster/PortMaster.sh
PortMaster/control.txt
PortMaster/device_info.txt
PortMaster/funcs.txt
PortMaster/gamecontrollerdb.txt
PortMaster/miniloong/PortMaster.txt
PortMaster/pugwash
PortMaster/pylibs/harbourmaster/config.py
PortMaster/pylibs/harbourmaster/hardware.py
PortMaster/pylibs/harbourmaster/platform.py
release/upstream-baseline.json
release/README.md
release/portmaster-sources.sh
tests/test_busybox_font_extraction.sh
tests/test_follow_stable_workflow.py
tests/test_miniloong_current.py
tests/test_miniloong_legacy.py
tests/test_runtimes_archive_comment.py
tools/build-maintained-release.sh
tools/installer.sh
tools/validate-maintained-candidate.sh
EOF
)
unexpected=$(git -C "$ROOT" diff --name-only "$STABLE_REF"...HEAD | while IFS= read -r path; do
  grep -Fqx "$path" <<< "$ALLOWLIST" || printf '%s\n' "$path"
done)
[ -z "$unexpected" ] || { echo "unexpected fork changes:" >&2; printf '%s\n' "$unexpected" >&2; exit 66; }

baseline_data=$(python3 - "$ROOT/release/upstream-baseline.json" <<'PY'
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
print(data["stable_tag"])
print(data["installer_sha256"])
PY
)
baseline_tag=$(printf '%s\n' "$baseline_data" | sed -n '1p')
baseline_hash=$(printf '%s\n' "$baseline_data" | sed -n '2p')
actual=$(git -C "$ROOT" show "$STABLE_REF:tools/installer.sh" | {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum; else shasum -a 256; fi
} | awk '{print $1}')
[ "$actual" = "$baseline_hash" ] || {
  echo "official installer changed from reviewed baseline $baseline_tag" >&2; exit 67;
}

for script in \
  "$ROOT/PortMaster/PortMaster.sh" \
  "$ROOT/PortMaster/control.txt" \
  "$ROOT/PortMaster/miniloong/PortMaster.txt" \
  "$ROOT/tools/build-maintained-release.sh" \
  "$ROOT/tools/installer.sh"; do
  bash -n "$script"
done
bash -n "$ROOT/release/portmaster-sources.sh"
python3 -m py_compile \
  "$ROOT/PortMaster/pylibs/harbourmaster/config.py" \
  "$ROOT/PortMaster/pylibs/harbourmaster/hardware.py" \
  "$ROOT/PortMaster/pylibs/harbourmaster/platform.py"
python3 "$ROOT/tests/test_miniloong_current.py"
python3 "$ROOT/tests/test_miniloong_legacy.py"
python3 "$ROOT/tests/test_runtimes_archive_comment.py"
bash "$ROOT/tests/test_busybox_font_extraction.sh"
python3 "$ROOT/tests/test_follow_stable_workflow.py"
bash "$ROOT/tools/build-maintained-release.sh" "$STABLE_TAG" "$OUTPUT"

for asset in PortMaster.zip version.json SHA256SUMS; do [ -s "$OUTPUT/$asset" ]; done
(cd "$OUTPUT" && {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum -c SHA256SUMS
  else shasum -a 256 -c SHA256SUMS
  fi
})

if [ -n "${PORTMASTER_CONSUMER_ROOT:-}" ]; then
  [ -f "$PORTMASTER_CONSUMER_ROOT/Cargo.toml" ] || {
    echo "current Port App Manager consumer is unavailable" >&2
    exit 68
  }
  PAM_PORTMASTER_CANDIDATE="$OUTPUT/PortMaster.zip" \
    cargo test --manifest-path "$PORTMASTER_CONSUMER_ROOT/Cargo.toml" --locked \
      -p appmanager-core \
      installer::tests::maintained_portmaster_candidate_installs_for_miniloong_profiles \
      -- --exact --nocapture
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$OUTPUT/PortMaster.zip" -d "$TMP/package"
[ -f "$TMP/package/PortMaster/control.txt" ]
[ -f "$TMP/package/PortMaster/device_info.txt" ]
[ -f "$TMP/package/PortMaster/funcs.txt" ]
[ -f "$TMP/package/PortMaster/pylibs.zip" ]
[ -f "$TMP/package/PortMaster/miniloong/PortMaster.txt" ]
[ ! -e "$TMP/package/PortMaster/mod_Loong.txt" ]
[ "$(grep -Fc 'mount -o loop,ro' "$TMP/package/PortMaster/miniloong/PortMaster.txt")" = "1" ]
grep -Fq 'export PYTHONHOME="$python_mount"' "$TMP/package/PortMaster/miniloong/PortMaster.txt"
! grep -Fq 'flock' "$TMP/package/PortMaster/miniloong/PortMaster.txt"
grep -Fq '"$controlfolder/PortMaster.sh" "$@"' "$TMP/package/PortMaster/miniloong/PortMaster.txt"
[ ! -e "$TMP/package/PortMaster/libs" ]
[ "$(cat "$TMP/package/PortMaster/version")" = "$STABLE_TAG" ]
grep -Fq "PORTMASTER_VERSION = '$STABLE_TAG'" "$TMP/package/PortMaster/pugwash"
grep -Fq "PORTMASTER_RELEASE_CHANNEL = '$EXPECTED_RELEASE_CHANNEL'" "$TMP/package/PortMaster/pugwash"
grep -Fq "PORTMASTER_RELEASE_URL = '$JENNY92_PORTMASTER_GUI_RELEASES_URL/latest/download/'" "$TMP/package/PortMaster/pugwash"
grep -Fq "PORTMASTER_RELEASE_VALUES = $EXPECTED_RELEASE_VALUES" "$TMP/package/PortMaster/pugwash"
grep -Fq 'PORTMASTER_MAINTAINER = "Jenny92"' "$TMP/package/PortMaster/pugwash"
grep -Fq 'maintainer_label = f"Maintainer: {PORTMASTER_MAINTAINER}"' "$TMP/package/PortMaster/pugwash"
grep -Fq "release_info = harbourmaster.fetch_json(PORTMASTER_RELEASE_URL + 'version.json')" "$TMP/package/PortMaster/pugwash"
grep -Fq "release_info[release_channel]['url']" "$TMP/package/PortMaster/pugwash"
grep -Fq "md5_source=release_info[release_channel]['md5']" "$TMP/package/PortMaster/pugwash"
python3 - "$OUTPUT/version.json" "$OUTPUT/PortMaster.zip" "$STABLE_TAG" "$JENNY92_PORTMASTER_GUI_RELEASE_ASSET_BASE" <<'PY'
import hashlib, json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
archive_md5=hashlib.md5(open(sys.argv[2], "rb").read()).hexdigest()
assert set(data) == {"stable", "beta", "alpha"}
expected = {
    "version": sys.argv[3],
    "url": f"{sys.argv[4]}/{sys.argv[3]}/PortMaster.zip",
    "md5": archive_md5,
}
assert all(data[channel] == expected for channel in ("stable", "beta", "alpha"))
PY

# Re-run the maintained detection checks against the packaged files, not only
# the source checkout.
mkdir -p "$TMP/package/PortMaster/pylibs"
(cd "$TMP/package/PortMaster" && unzip -q pylibs.zip)
mkdir -p "$TMP/package/tools"
cp "$ROOT/tools/installer.sh" "$TMP/package/tools/installer.sh"
cp "$ROOT/tests/test_miniloong_current.py" "$TMP/package/PortMaster/test_miniloong_current.py"
cp "$ROOT/tests/test_miniloong_legacy.py" "$TMP/package/PortMaster/test_miniloong_legacy.py"
(cd "$TMP/package/PortMaster" && python3 test_miniloong_current.py)
(cd "$TMP/package/PortMaster" && python3 test_miniloong_legacy.py)

echo "Maintained PortMaster release candidate validated for $STABLE_TAG"
