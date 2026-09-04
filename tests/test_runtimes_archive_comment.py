#!/usr/bin/env python3
from pathlib import Path


launcher = (Path(__file__).resolve().parents[1] / "PortMaster" / "PortMaster.sh").read_text(
    encoding="utf-8"
)

assert 'unzip -z "$autoinstall_dir/runtimes.zip"' in launcher
assert 'ZIP_COMMENT="$(unzip -z "$file_name"' not in launcher

print("runtimes archive comment test: PASS")
