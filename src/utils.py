"""
Utilities: logging, secure key storage, and capture exclusion.

Exclusion order:
1) DWM exclusion (DWMWA_EXCLUDED_FROM_CAPTURE)  -> modern Windows 10/11
2) Display Affinity EXCLUDEFROMCAPTURE          -> legacy but still honored
3) Display Affinity MONITOR                     -> partial fallback

We also expose which method applied so the GUI can show a status badge.
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple

import keyring
from .config import KEYRING_SERVICE, KEYRING_KEY, APP_TITLE, DEFAULT_LOG_LEVEL

# -------- logging to EXE folder (or project root in dev) --------
def _resolve_log_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]

LOG_FILE = str(_resolve_log_dir() / "app.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Try to read DEFAULT_LOG_LEVEL from config; fall back safely
try:
    from .config import DEFAULT_LOG_LEVEL as _CFG_LOG_LEVEL
except Exception:
    _CFG_LOG_LEVEL = "INFO"

level_name = os.getenv("INVISIBLECHAT_LOG", DEFAULT_LOG_LEVEL).upper()
level = getattr(logging, level_name, logging.INFO)

logging.basicConfig(
    filename=LOG_FILE,
    level=level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(APP_TITLE)
logger.info("==== InvisibleChat boot ====")

# -------- Windows imports --------
try:
    import ctypes
    from ctypes import wintypes
    IS_WINDOWS = True
except Exception:
    IS_WINDOWS = False
    logger.warning("Non-Windows runtime; capture exclusion becomes a no-op.")

# -------- keyring helpers --------
def save_api_key(api_key: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, api_key)
    logger.info("API key stored in keyring.")

def get_api_key() -> Optional[str]:
    try:
        key = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        logger.info("API key fetch: %s", "present" if key else "missing")
        return key
    except Exception as exc:
        logger.error("Keyring read failed: %s", exc, exc_info=True)
        return None

# -------- capture exclusion --------
def _get_root_hwnd(hwnd: int) -> int:
    """Return true top-level HWND (GA_ROOT)."""
    if not IS_WINDOWS:
        return hwnd
    GA_ROOT = 2
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    GetAncestor = user32.GetAncestor
    GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    GetAncestor.restype = wintypes.HWND
    root = GetAncestor(wintypes.HWND(hwnd), GA_ROOT)
    r = int(root) if root else int(hwnd)
    logger.info("Resolved top-level hwnd: %s -> %s", hwnd, r)
    return r

def _exclude_via_dwm(hwnd: int) -> Tuple[bool, str]:
    """
    Preferred path on Win 10 2004+ / Win 11 — used by Chromium/Teams/etc.
    Returns (applied, label).
    """
    if not IS_WINDOWS:
        return True, "DWM (non-Windows assumed)"
    try:
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
    except Exception:
        logger.info("dwmapi missing; skipping DWM exclusion.")
        return False, "None"

    DWMWA_EXCLUDED_FROM_CAPTURE = 39
    BOOL = wintypes.BOOL
    UINT = wintypes.UINT
    HWND = wintypes.HWND
    LPCVOID = ctypes.c_void_p

    try:
        DwmSetWindowAttribute = dwmapi.DwmSetWindowAttribute
        DwmSetWindowAttribute.argtypes = [HWND, UINT, LPCVOID, UINT]
        DwmSetWindowAttribute.restype = ctypes.HRESULT

        root = _get_root_hwnd(hwnd)
        true_val = BOOL(1)
        hr = DwmSetWindowAttribute(HWND(root), UINT(DWMWA_EXCLUDED_FROM_CAPTURE),
                                   ctypes.byref(true_val), ctypes.sizeof(true_val))
        if hr == 0:
            logger.info("DWM exclusion applied successfully.")
            return True, "DWM"
        logger.error("DwmSetWindowAttribute failed hr=0x%x", hr)
        return False, "None"
    except Exception as exc:
        logger.error("DWM exclusion exception: %s", exc, exc_info=True)
        return False, "None"

def _exclude_via_affinity(hwnd: int) -> Tuple[bool, str]:
    """Legacy path + fallback to MONITOR. Returns (applied, label)."""
    if not IS_WINDOWS:
        return True, "Affinity (non-Windows assumed)"

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    func = user32.SetWindowDisplayAffinity
    func.argtypes = [wintypes.HWND, wintypes.DWORD]
    func.restype = wintypes.BOOL

    WDA_EXCLUDEFROMCAPTURE = 0x00000011
    WDA_MONITOR = 0x00000001

    root = _get_root_hwnd(hwnd)
    ok = func(wintypes.HWND(root), WDA_EXCLUDEFROMCAPTURE)
    if ok:
        logger.info("DisplayAffinity EXCLUDEFROMCAPTURE applied.")
        return True, "Affinity"
    err = ctypes.get_last_error()
    logger.error("DisplayAffinity EXCLUDEFROMCAPTURE failed err=%s", err)

    ok2 = func(wintypes.HWND(root), WDA_MONITOR)
    if ok2:
        logger.warning("DisplayAffinity MONITOR fallback applied (partial).")
        return True, "Monitor"
    err2 = ctypes.get_last_error()
    logger.error("DisplayAffinity MONITOR failed err=%s", err2)
    return False, "None"

def set_window_excluded_from_capture(hwnd: int) -> str:
    """
    Try DWM first, then Affinity, then MONITOR.
    Return a short label describing what applied: "DWM", "Affinity", "Monitor", or "None".
    """
    if not IS_WINDOWS:
        return "DWM"

    ok, label = _exclude_via_dwm(hwnd)
    if ok:
        return label

    ok2, label2 = _exclude_via_affinity(hwnd)
    return label2
