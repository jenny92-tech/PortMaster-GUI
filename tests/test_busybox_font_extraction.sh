#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

prepare_fixture() {
  local target=$1
  mkdir -p "$target/pylibs/resources"
  cp "$ROOT/PortMaster/funcs.txt" "$ROOT/PortMaster/PortMasterDialog.txt" "$target/"
  printf 'test-version\n' > "$target/version"
}

# A failed retry must preserve the recovery archive even when a partial font
# from an interrupted extraction is already present.
font_failure="$TMP/font-failure"
prepare_fixture "$font_failure"
mkdir -p "$font_failure/bin"
printf 'partial-jp\n' > "$font_failure/pylibs/resources/NotoSansJP-Regular.ttf"
printf 'not-an-xz-archive\n' > "$font_failure/pylibs/resources/NotoSans.tar.xz"
cat > "$font_failure/bin/xz" <<'SH'
#!/bin/sh
exit 1
SH
chmod +x "$font_failure/bin/xz"
PATH="$font_failure/bin:/usr/bin:/bin" controlfolder="$font_failure" CFW_NAME=Loong ESUDO='' \
  bash -c '. "$1" >/dev/null 2>&1' _ "$font_failure/funcs.txt" || true
[ -f "$font_failure/pylibs/resources/NotoSans.tar.xz" ]

# A successful decompression is incomplete until every bundled font exists.
font_incomplete="$TMP/font-incomplete"
prepare_fixture "$font_incomplete"
mkdir -p "$font_incomplete/source"
printf 'jp-only\n' > "$font_incomplete/source/NotoSansJP-Regular.ttf"
tar -cJf "$font_incomplete/pylibs/resources/NotoSans.tar.xz" \
  -C "$font_incomplete/source" NotoSansJP-Regular.ttf
controlfolder="$font_incomplete" CFW_NAME=Loong ESUDO='' \
  bash -c '. "$1" >/dev/null 2>&1' _ "$font_incomplete/funcs.txt"
[ -f "$font_incomplete/pylibs/resources/NotoSans.tar.xz" ]

# A complete archive is removed only after all five output files are present.
font_complete="$TMP/font-complete"
prepare_fixture "$font_complete"
mkdir -p "$font_complete/source"
for font in HK JP KR SC TC; do
  printf '%s-font\n' "$font" > "$font_complete/source/NotoSans${font}-Regular.ttf"
done
tar -cJf "$font_complete/pylibs/resources/NotoSans.tar.xz" -C "$font_complete/source" .
controlfolder="$font_complete" CFW_NAME=Loong ESUDO='' \
  bash -c '. "$1" >/dev/null 2>&1' _ "$font_complete/funcs.txt"
[ ! -e "$font_complete/pylibs/resources/NotoSans.tar.xz" ]
for font in HK JP KR SC TC; do
  grep -Fxq "$font-font" "$font_complete/pylibs/resources/NotoSans${font}-Regular.ttf"
done

echo "BusyBox font extraction tests: PASS"
