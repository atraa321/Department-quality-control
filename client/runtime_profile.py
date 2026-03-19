import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeProfile:
    is_windows: bool
    windows_major: int
    windows_minor: int
    compatibility_mode: str
    use_software_opengl: bool
    enable_high_dpi_scaling: bool
    use_translucent_overlay: bool
    overlay_antialiasing: bool
    prefer_chromium_browser: bool
    defer_shell_init_ms: int

    @property
    def is_win7(self):
        return self.is_windows and self.windows_major == 6 and self.windows_minor == 1

    @property
    def compatibility_enabled(self):
        return self.compatibility_mode == "win7"

    @property
    def display_name(self):
        if self.compatibility_enabled:
            return "Win7 兼容模式"
        return "标准模式"


def build_runtime_profile(config=None):
    config = config or {}
    requested_mode = str(config.get("compatibility_mode") or "auto").strip().lower()
    if requested_mode not in ("auto", "standard", "win7"):
        requested_mode = "auto"

    is_windows = sys.platform == "win32"
    windows_major = 0
    windows_minor = 0
    if is_windows and hasattr(sys, "getwindowsversion"):
        version = sys.getwindowsversion()
        windows_major = int(getattr(version, "major", 0) or 0)
        windows_minor = int(getattr(version, "minor", 0) or 0)

    auto_win7 = is_windows and windows_major == 6 and windows_minor == 1
    compatibility_enabled = requested_mode == "win7" or (requested_mode == "auto" and auto_win7)

    return RuntimeProfile(
        is_windows=is_windows,
        windows_major=windows_major,
        windows_minor=windows_minor,
        compatibility_mode="win7" if compatibility_enabled else "standard",
        use_software_opengl=True,
        enable_high_dpi_scaling=not compatibility_enabled,
        use_translucent_overlay=not compatibility_enabled,
        overlay_antialiasing=not compatibility_enabled,
        prefer_chromium_browser=compatibility_enabled,
        defer_shell_init_ms=350 if compatibility_enabled else 0,
    )


def preferred_browser_paths():
    roots = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = (os.environ.get(env_name) or "").strip()
        if root and root not in roots:
            roots.append(root)

    relative_paths = [
        r"Google\Chrome\Application\chrome.exe",
        r"Chromium\Application\chrome.exe",
        r"Microsoft\Edge\Application\msedge.exe",
        r"360Chrome\Chrome\Application\360chrome.exe",
        r"360ChromeX\Chrome\Application\360ChromeX.exe",
        r"360se6\Application\360se.exe",
        r"360se\Application\360se.exe",
        r"CentBrowser\Application\chrome.exe",
    ]

    seen = set()
    for root in roots:
        for relative_path in relative_paths:
            candidate = os.path.join(root, relative_path)
            normalized = os.path.normcase(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            yield candidate
