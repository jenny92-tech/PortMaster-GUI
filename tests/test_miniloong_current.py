#!/usr/bin/env python3
import ast
import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "PortMaster/pylibs/harbourmaster/hardware.py"
PLATFORM_SOURCE = ROOT / "PortMaster/pylibs/harbourmaster/platform.py"


class QuietLogger:
    def debug(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass


class NeverPresentPath:
    def __init__(self, _value):
        pass

    def is_dir(self):
        return False


def load_new_device_info(os_release):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "new_device_info"
    )
    module = ast.Module(body=[function], type_ignores=[])

    def safe_cat(path):
        if path == "/etc/os-release":
            return os_release
        return ""

    namespace = {
        "HM_TESTING": False,
        "Path": NeverPresentPath,
        "logger": QuietLogger(),
        "nice_device_to_device": lambda _value: "default",
        "os": os,
        "platform": sys.modules["platform"],
        "re": re,
        "safe_cat": safe_cat,
        "subprocess": subprocess,
    }
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["new_device_info"]


def literal_assignment(name):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    )
    return ast.literal_eval(assignment.value)


def load_platform_classes():
    tree = ast.parse(
        PLATFORM_SOURCE.read_text(encoding="utf-8"), filename=str(PLATFORM_SOURCE)
    )
    wanted = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name in {"PlatformBase", "PlatformLoong"}
    ]
    namespace = {
        "contextlib": contextlib,
        "logger": QuietLogger(),
        "Path": Path,
        "shutil": shutil,
    }
    exec(
        compile(ast.Module(body=wanted, type_ignores=[]), str(PLATFORM_SOURCE), "exec"),
        namespace,
    )
    return namespace["PlatformBase"], namespace["PlatformLoong"]


def platform_registry_entry():
    tree = ast.parse(
        PLATFORM_SOURCE.read_text(encoding="utf-8"), filename=str(PLATFORM_SOURCE)
    )
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "HM_PLATFORMS"
            for target in node.targets
        )
    )
    return {
        ast.literal_eval(key): value.id
        for key, value in zip(assignment.value.keys, assignment.value.values)
        if isinstance(value, ast.Name)
    }


def main():
    import platform

    sys.modules["platform"] = platform
    os_release = '\n'.join(
        [
            'NAME=LoongOS',
            'ID=loong',
            'VERSION_ID="1.4.0.27"',
        ]
    )
    info = load_new_device_info(os_release)()
    assert info["name"] == "Loong"
    assert info["device"] == "miniloong"
    assert info["version"] == "1.4.0.27"

    with tempfile.TemporaryDirectory() as temporary_root:
        control_dir = Path(temporary_root) / "control"
        control_dir.mkdir()
        (control_dir / "version").write_text("test-version\n", encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "ID": "loong",
                "VERSION_ID": "1.4.0.27",
                "DEVICE_INFO_VERSION": "",
                "PM_VERSION": "",
                "controlfolder": str(control_dir),
            }
        )
        result = subprocess.run(
            [
                "bash",
                "-c",
                '. "$1" >/dev/null 2>&1; printf "%s\\t%s\\t%s\\t%s" '
                '"$CFW_NAME" "$CFW_VERSION" "$DEVICE_NAME" "$ANALOG_STICKS"',
                "_",
                str(ROOT / "PortMaster/device_info.txt"),
            ],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )
        assert result.stdout == "Loong\t1.4.0.27\tMiniLoong Pocket One\t1"

    devices = literal_assignment("DEVICES")
    hardware = literal_assignment("HW_INFO")
    assert devices["MiniLoong Pocket One"] == {
        "device": "miniloong",
        "manufacturer": "MiniLoong",
        "cfw": ["Loong"],
    }
    assert hardware["miniloong"] == {
        "resolution": (960, 720),
        "analogsticks": 1,
        "cpu": "rk3566",
        "capabilities": ["power"],
        "ram": 1024,
    }

    control = (ROOT / "PortMaster/control.txt").read_text(encoding="utf-8")
    controller_db = (ROOT / "PortMaster/gamecontrollerdb.txt").read_text(encoding="utf-8")
    assert "platform-loong1_joypad-event-joystick" in control
    assert "1900fe3c039900001399000002010000,Loong Gamepad" in controller_db

    platform_base, platform_loong = load_platform_classes()
    assert issubclass(platform_loong, platform_base)
    assert platform_registry_entry()["loong"] == "PlatformLoong"
    assert platform_loong.WANT_XBOX_FIX is True

    with tempfile.TemporaryDirectory() as temporary_root:
        scripts_dir = Path(temporary_root) / "ports"
        source = scripts_dir / "PortMaster/PortMaster.sh"
        source.parent.mkdir(parents=True)
        source.write_text("#!/bin/bash\necho LoongOS\n", encoding="utf-8")
        hm = types.SimpleNamespace(tools_dir=scripts_dir, scripts_dir=scripts_dir)
        bash_files = []
        platform_loong(hm).portmaster_install(bash_files)

        target = scripts_dir / "PortMaster.sh"
        assert target.read_text(encoding="utf-8") == "#!/bin/bash\necho LoongOS\n"
        assert not source.exists()
        assert bash_files == [target]


if __name__ == "__main__":
    main()
