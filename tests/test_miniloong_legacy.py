#!/usr/bin/env python3
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from unittest import mock

from test_miniloong_current import load_new_device_info, load_platform_classes


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SOURCE = ROOT / "PortMaster/pylibs/harbourmaster/config.py"


class QuietLogger:
    def debug(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass


def load_config(root):
    loguru = types.ModuleType("loguru")
    loguru.logger = QuietLogger()
    old_cwd = Path.cwd()
    environment = {
        "PM_ROOT_PREFIX": str(root),
        "HM_TOOLS_DIR": "",
        "HM_PORTS_DIR": "",
        "HM_SCRIPTS_DIR": "",
    }
    try:
        os.chdir(root)
        with mock.patch.dict(sys.modules, {"loguru": loguru}):
            with mock.patch.dict(os.environ, environment, clear=False):
                for name in ("HM_TOOLS_DIR", "HM_PORTS_DIR", "HM_SCRIPTS_DIR"):
                    os.environ.pop(name, None)
                return runpy.run_path(str(CONFIG_SOURCE))
    finally:
        os.chdir(old_cwd)


def test_config_paths():
    with tempfile.TemporaryDirectory() as temporary_root:
        root = Path(temporary_root)
        (root / "loong").mkdir()
        (root / "loong/loong_version").write_text(
            '{"verShow":"1.3.0.32"}\n', encoding="utf-8"
        )
        legacy = root / "mnt/sdcard/roms/ports"
        legacy.mkdir(parents=True)

        config = load_config(root)
        assert config["HM_DEFAULT_TOOLS_DIR"] == legacy
        assert config["HM_DEFAULT_PORTS_DIR"] == legacy
        assert config["HM_DEFAULT_SCRIPTS_DIR"] == legacy

        (root / "etc").mkdir()
        (root / "etc/os-release").write_text(
            'NAME=LoongOS\nID=loong\nVERSION_ID="1.4.0.27"\n',
            encoding="utf-8",
        )
        current = root / "roms/ports"
        current.mkdir(parents=True)

        config = load_config(root)
        assert config["HM_DEFAULT_TOOLS_DIR"] == current
        assert config["HM_DEFAULT_PORTS_DIR"] == current
        assert config["HM_DEFAULT_SCRIPTS_DIR"] == current


def test_legacy_identity():
    import platform

    sys.modules["platform"] = platform
    info = load_new_device_info("", '{"verShow":"1.3.0.32"}')()
    assert info["name"] == "Loong"
    assert info["device"] == "miniloong"
    assert info["version"] == "1.3.0.32"

    with tempfile.TemporaryDirectory() as temporary_root:
        root = Path(temporary_root)
        (root / "loong").mkdir()
        (root / "loong/loong_version").write_text(
            '{"verShow":"1.3.0.32"}\n', encoding="utf-8"
        )
        fake_bin = root / "bin"
        fake_bin.mkdir()
        fake_sudo = fake_bin / "sudo"
        fake_sudo.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        fake_sudo.chmod(0o755)
        installed = root / "mnt/sdcard/roms/ports/PortMaster"
        installed.mkdir(parents=True)
        shutil.copy2(ROOT / "PortMaster/control.txt", installed / "control.txt")
        shutil.copy2(ROOT / "PortMaster/device_info.txt", installed / "device_info.txt")
        (installed / "funcs.txt").write_text("#!/bin/bash\n", encoding="utf-8")
        (installed / "version").write_text("test-version\n", encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "PM_ROOT_PREFIX": str(root),
                "DEVICE_INFO_VERSION": "",
                "PM_VERSION": "",
            }
        )
        result = subprocess.run(
            [
                "bash",
                "-c",
                '. "$1" >/dev/null 2>&1; printf "%s\\t%s\\t%s" '
                '"$CFW_NAME" "$CFW_VERSION" "$directory"',
                "_",
                str(installed / "control.txt"),
            ],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )
        assert result.stdout == "Loong\t1.3.0.32\tmnt/sdcard/roms"


def test_legacy_launcher_install():
    _, platform_loong = load_platform_classes()
    with tempfile.TemporaryDirectory() as temporary_root:
        scripts_dir = Path(temporary_root) / "ports"
        core = scripts_dir / "PortMaster"
        source = core / "miniloong/PortMaster.txt"
        source.parent.mkdir(parents=True)
        source.write_text("#!/bin/bash\necho legacy\n", encoding="utf-8")
        core_launcher = core / "PortMaster.sh"
        core_launcher.write_text("#!/bin/bash\necho core\n", encoding="utf-8")

        hm = types.SimpleNamespace(tools_dir=scripts_dir, scripts_dir=scripts_dir)
        platform = platform_loong(hm)
        platform.LEGACY_TOOLS_DIR = scripts_dir
        bash_files = []
        platform.portmaster_install(bash_files)

        target = scripts_dir / "PortMaster.sh"
        assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        assert core_launcher.is_file()
        assert bash_files == [target]


def test_contract_text():
    core_launcher = (ROOT / "PortMaster/PortMaster.sh").read_text(encoding="utf-8")
    control = (ROOT / "PortMaster/control.txt").read_text(encoding="utf-8")
    installer = (ROOT / "tools/installer.sh").read_text(encoding="utf-8")
    wrapper = (ROOT / "PortMaster/miniloong/PortMaster.txt").read_text(encoding="utf-8")

    assert not (ROOT / "PortMaster/mod_Loong.txt").exists()
    assert '"$PORTMASTER_LAUNCHER_DIR/control.txt"' in core_launcher
    assert 'export directory="mnt/sdcard/roms"' in control
    assert installer.index('if [ "${ID:-}" = "loong" ]') < installer.index(
        'elif [ -f "/loong/loong_version" ]'
    )
    assert 'LOONG_LEGACY="Y"' in installer
    assert 'python_3.11.squashfs' in wrapper
    assert '"$controlfolder/PortMaster.sh" "$@"' in wrapper


def main():
    test_config_paths()
    test_legacy_identity()
    test_legacy_launcher_install()
    test_contract_text()


if __name__ == "__main__":
    main()
