#!/usr/bin/env python
# Third-party dependencies:
#   pip install PyQt5
#   pip install pyinstaller  # Optional, build-time only
#
# Build EXE:
#   pyinstaller --noconfirm --clean ScreenSnipper.spec

from __future__ import annotations

import ctypes
import os
import sys
import winreg
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import (
    QAbstractNativeEventFilter,
    QEvent,
    QObject,
    QPoint,
    QRect,
    QSettings,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QBitmap,
    QColor,
    QClipboard,
    QCursor,
    QIcon,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "Screen Snipper"
APP_ID = "ScreenSnipper"
RUN_VALUE_NAME = "ScreenSnipper"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
LEGACY_SETTINGS_KEY_PATH = r"Software\ScreenSnipper"
AUTOSTART_INITIALIZED_VALUE = "AutostartInitialized"

HOTKEY_ID = 0x1001
WM_HOTKEY = 0x0312
MB_ICONERROR = 0x0010
MB_ICONWARNING = 0x0030

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

VK_S = 0x53
DEFAULT_HOTKEY_MODIFIERS = MOD_CONTROL | MOD_ALT
DEFAULT_HOTKEY_VK = VK_S
DEFAULT_HOTKEY_TEXT = "Ctrl + Alt + S"

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
BI_RGB = 0
DIB_RGB_COLORS = 0

BORDER_COLOR = QColor(0, 153, 255)
MASK_COLOR = QColor(0, 0, 0, 120)
HANDLE_FILL_COLOR = QColor(255, 255, 255)

MIN_SELECTION_SIZE = 2
FLOATING_DRAG_THRESHOLD = 4
SELECTION_HANDLE_SIZE = 8
SELECTION_HIT_MARGIN = 8
TOOLBAR_GAP = 12

FLOATING_BUTTON_ASSET_RELATIVE = Path("assets") / "floating_button.png"
TRAY_ICON_SIZES = (16, 20, 24, 32, 40, 48, 64)

FLOATING_SIZE_PRESETS = {
    "small": {"longest_edge": 88},
    "medium": {"longest_edge": 120},
    "large": {"longest_edge": 160},
}
DEFAULT_FLOATING_SIZE_PRESET = "small"
SUPPORTED_UI_LANGUAGES = ("zh_CN", "en_US")
DEFAULT_UI_LANGUAGE = "zh_CN"
SUPPORTED_CAPTURE_MODES = ("minimal", "refine")
DEFAULT_CAPTURE_MODE = "refine"

FLOATING_POSITION_KEY = "floating_button/position"
FLOATING_SIZE_PRESET_KEY = "floating_button/size_preset"
FLOATING_LAYOUT_INITIALIZED_V2_KEY = "floating_button/layout_initialized_v2"
UI_LANGUAGE_KEY = "ui/language"
CAPTURE_MODE_KEY = "capture/mode"
HOTKEY_MODIFIERS_KEY = "hotkey/modifiers"
HOTKEY_VK_KEY = "hotkey/virtual_key"
HOTKEY_TEXT_KEY = "hotkey/display_text"
AUTOSTART_INITIALIZED_KEY = "autostart/initialized"

UI_TEXTS = {
    "zh_CN": {
        "menu.capture": "截图",
        "menu.toggle_button.show": "显示悬浮按钮",
        "menu.toggle_button.hide": "隐藏悬浮按钮",
        "menu.size": "悬浮窗大小",
        "menu.size.small": "小",
        "menu.size.medium": "中",
        "menu.size.large": "大",
        "menu.autostart": "开机启动",
        "menu.settings": "设置...",
        "menu.exit": "退出",
        "tooltip.floating_button": "左键截图，拖动可移动，右键打开菜单",
        "dialog.settings.title": "设置",
        "dialog.settings.language": "界面语言",
        "dialog.settings.capture_mode": "截图模式",
        "dialog.settings.hotkey_title": "截图热键",
        "dialog.settings.current_hotkey": "当前热键：{hotkey}",
        "dialog.settings.current_hotkey_inactive": "当前热键：{hotkey}（未激活）",
        "dialog.settings.hotkey_hint": "点击下方输入框后直接按下新的快捷键，仅支持 Ctrl / Alt / Shift + 一个主键。",
        "dialog.settings.hotkey_placeholder": "按下新的快捷键",
        "dialog.settings.hotkey_preview": "新的热键：{hotkey}",
        "dialog.settings.restore_default": "恢复默认",
        "dialog.ok": "确定",
        "dialog.cancel": "取消",
        "dialog.settings.language.zh_CN": "中文",
        "dialog.settings.language.en_US": "English",
        "capture_mode.minimal.name": "极简模式",
        "capture_mode.minimal.description": "框选后立即复制",
        "capture_mode.refine.name": "精调模式",
        "capture_mode.refine.description": "框选后可继续调整后再复制",
        "overlay.confirm": "完成",
        "overlay.cancel": "取消",
        "overlay.hint": "可拖动调整，双击或回车完成",
        "message.hotkey_unavailable": "无法注册当前热键 {hotkey}。\n你仍可通过悬浮窗或系统托盘进行截图，并可在“设置...”中改为其他组合键。",
        "error.asset_missing": "找不到悬浮窗图片资源：{path}",
        "error.asset_load_failed": "悬浮窗图片资源加载失败。",
        "error.asset_process_failed": "悬浮窗图片资源处理失败。",
        "error.tray_unavailable": "当前系统会话不支持系统托盘。",
        "error.autostart_update_failed": "更新开机启动设置失败。",
        "error.hotkey_conflict": "热键 {hotkey} 已被其他程序占用，请选择其他组合键。",
        "error.initialization_failed": "程序初始化失败：{error}",
    },
    "en_US": {
        "menu.capture": "Capture",
        "menu.toggle_button.show": "Show Floating Button",
        "menu.toggle_button.hide": "Hide Floating Button",
        "menu.size": "Floating Button Size",
        "menu.size.small": "Small",
        "menu.size.medium": "Medium",
        "menu.size.large": "Large",
        "menu.autostart": "Launch at Startup",
        "menu.settings": "Settings...",
        "menu.exit": "Exit",
        "tooltip.floating_button": "Left-click to capture, drag to move, right-click for menu",
        "dialog.settings.title": "Settings",
        "dialog.settings.language": "Interface Language",
        "dialog.settings.capture_mode": "Capture Mode",
        "dialog.settings.hotkey_title": "Screenshot Hotkey",
        "dialog.settings.current_hotkey": "Current hotkey: {hotkey}",
        "dialog.settings.current_hotkey_inactive": "Current hotkey: {hotkey} (inactive)",
        "dialog.settings.hotkey_hint": "Click the input box below, then press a new shortcut. Only Ctrl / Alt / Shift + one main key is supported.",
        "dialog.settings.hotkey_placeholder": "Press a new hotkey",
        "dialog.settings.hotkey_preview": "New hotkey: {hotkey}",
        "dialog.settings.restore_default": "Restore Default",
        "dialog.ok": "OK",
        "dialog.cancel": "Cancel",
        "dialog.settings.language.zh_CN": "中文",
        "dialog.settings.language.en_US": "English",
        "capture_mode.minimal.name": "Minimal Mode",
        "capture_mode.minimal.description": "Copy immediately after selection",
        "capture_mode.refine.name": "Refine Mode",
        "capture_mode.refine.description": "Adjust the selection before copying",
        "overlay.confirm": "Done",
        "overlay.cancel": "Cancel",
        "overlay.hint": "Drag to adjust. Double-click or press Enter to finish.",
        "message.hotkey_unavailable": "Unable to register the current hotkey {hotkey}.\nYou can still capture via the floating button or tray menu, and change it from Settings...",
        "error.asset_missing": "Floating button image resource not found: {path}",
        "error.asset_load_failed": "Failed to load the floating button image resource.",
        "error.asset_process_failed": "Failed to process the floating button image resource.",
        "error.tray_unavailable": "The current Windows session does not support the system tray.",
        "error.autostart_update_failed": "Failed to update the startup setting.",
        "error.hotkey_conflict": "The hotkey {hotkey} is already in use by another application. Please choose a different shortcut.",
        "error.initialization_failed": "Initialization failed: {error}",
    },
}


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
shcore = getattr(ctypes.windll, "shcore", None)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("lPrivate", wintypes.DWORD),
    ]


user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.MessageBoxW.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

if hasattr(user32, "SetProcessDpiAwarenessContext"):
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL

if shcore and hasattr(shcore, "SetProcessDpiAwareness"):
    shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
    shcore.SetProcessDpiAwareness.restype = ctypes.c_long

if hasattr(user32, "SetProcessDPIAware"):
    user32.SetProcessDPIAware.argtypes = []
    user32.SetProcessDPIAware.restype = wintypes.BOOL


QT_MODIFIER_KEYS = {
    Qt.Key_Control,
    Qt.Key_Shift,
    Qt.Key_Alt,
    Qt.Key_Meta,
}

QT_TO_VK_SPECIAL = {
    Qt.Key_Space: 0x20,
    Qt.Key_Tab: 0x09,
    Qt.Key_Backspace: 0x08,
    Qt.Key_Return: 0x0D,
    Qt.Key_Enter: 0x0D,
    Qt.Key_Escape: 0x1B,
    Qt.Key_Insert: 0x2D,
    Qt.Key_Delete: 0x2E,
    Qt.Key_Home: 0x24,
    Qt.Key_End: 0x23,
    Qt.Key_PageUp: 0x21,
    Qt.Key_PageDown: 0x22,
    Qt.Key_Left: 0x25,
    Qt.Key_Up: 0x26,
    Qt.Key_Right: 0x27,
    Qt.Key_Down: 0x28,
}

VK_DISPLAY_NAMES = {
    0x08: "Backspace",
    0x09: "Tab",
    0x0D: "Enter",
    0x1B: "Esc",
    0x20: "Space",
    0x21: "Page Up",
    0x22: "Page Down",
    0x23: "End",
    0x24: "Home",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x2D: "Insert",
    0x2E: "Delete",
    0x60: "Num 0",
    0x61: "Num 1",
    0x62: "Num 2",
    0x63: "Num 3",
    0x64: "Num 4",
    0x65: "Num 5",
    0x66: "Num 6",
    0x67: "Num 7",
    0x68: "Num 8",
    0x69: "Num 9",
}


@dataclass(frozen=True)
class HotkeyConfig:
    modifiers: int
    virtual_key: int
    display_text: str

    def normalized(self) -> "HotkeyConfig":
        modifiers = normalize_win_modifiers(self.modifiers)
        display_text = self.display_text or hotkey_display_text(modifiers, self.virtual_key)
        return HotkeyConfig(modifiers, int(self.virtual_key), display_text)

    def is_valid(self) -> bool:
        return bool(normalize_win_modifiers(self.modifiers)) and bool(vk_to_display_text(self.virtual_key))


def create_settings() -> QSettings:
    return QSettings(QSettings.NativeFormat, QSettings.UserScope, APP_ID, APP_ID)


def default_hotkey() -> HotkeyConfig:
    return HotkeyConfig(DEFAULT_HOTKEY_MODIFIERS, DEFAULT_HOTKEY_VK, DEFAULT_HOTKEY_TEXT)


def normalize_size_preset(preset: str) -> str:
    return preset if preset in FLOATING_SIZE_PRESETS else DEFAULT_FLOATING_SIZE_PRESET


def normalize_ui_language(language: str) -> str:
    return language if language in SUPPORTED_UI_LANGUAGES else DEFAULT_UI_LANGUAGE


def normalize_capture_mode(mode: str) -> str:
    return mode if mode in SUPPORTED_CAPTURE_MODES else DEFAULT_CAPTURE_MODE


def tr(language: str, key: str, **kwargs) -> str:
    language = normalize_ui_language(language)
    template = UI_TEXTS.get(language, {}).get(key) or UI_TEXTS[DEFAULT_UI_LANGUAGE].get(key) or key
    return template.format(**kwargs)


def current_ui_language() -> str:
    settings = create_settings()
    value = str(settings.value(UI_LANGUAGE_KEY, DEFAULT_UI_LANGUAGE, type=str) or "")
    return normalize_ui_language(value)


def current_tr(key: str, **kwargs) -> str:
    return tr(current_ui_language(), key, **kwargs)


def capture_mode_label(language: str, mode: str) -> str:
    mode = normalize_capture_mode(mode)
    separator = "：" if normalize_ui_language(language) == "zh_CN" else ": "
    return f"{tr(language, f'capture_mode.{mode}.name')}{separator}{tr(language, f'capture_mode.{mode}.description')}"


def current_runtime_base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def resolve_resource_path(relative_path: Path) -> Path:
    return current_runtime_base_path() / relative_path


def configure_windows_dpi() -> None:
    per_monitor_v2 = ctypes.c_void_p(-4)
    if hasattr(user32, "SetProcessDpiAwarenessContext"):
        try:
            user32.SetProcessDpiAwarenessContext(per_monitor_v2)
            return
        except OSError:
            pass
    if shcore and hasattr(shcore, "SetProcessDpiAwareness"):
        try:
            shcore.SetProcessDpiAwareness(2)
            return
        except OSError:
            pass
    if hasattr(user32, "SetProcessDPIAware"):
        try:
            user32.SetProcessDPIAware()
        except OSError:
            pass


def show_message_dialog(message: str, flags: int) -> None:
    user32.MessageBoxW(None, message, APP_NAME, flags)


def show_error_dialog(message: str) -> None:
    show_message_dialog(message, MB_ICONERROR)


def show_warning_dialog(message: str) -> None:
    show_message_dialog(message, MB_ICONWARNING)


def virtual_desktop_rect() -> QRect:
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return QRect(left, top, width, height)


def capture_virtual_desktop(rect: QRect) -> QPixmap:
    width = rect.width()
    height = rect.height()
    if width <= 0 or height <= 0:
        raise RuntimeError("Virtual desktop has invalid dimensions.")

    screen_dc = user32.GetDC(None)
    if not screen_dc:
        raise ctypes.WinError()

    memory_dc = gdi32.CreateCompatibleDC(screen_dc)
    if not memory_dc:
        user32.ReleaseDC(None, screen_dc)
        raise ctypes.WinError()

    bitmap_info = BITMAPINFO()
    bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bitmap_info.bmiHeader.biWidth = width
    bitmap_info.bmiHeader.biHeight = -height
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 32
    bitmap_info.bmiHeader.biCompression = BI_RGB

    bits = ctypes.c_void_p()
    dib_bitmap = gdi32.CreateDIBSection(
        memory_dc,
        ctypes.byref(bitmap_info),
        DIB_RGB_COLORS,
        ctypes.byref(bits),
        None,
        0,
    )
    if not dib_bitmap or not bits.value:
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)
        raise ctypes.WinError()

    old_bitmap = gdi32.SelectObject(memory_dc, dib_bitmap)
    if not old_bitmap:
        gdi32.DeleteObject(dib_bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)
        raise ctypes.WinError()

    try:
        success = gdi32.BitBlt(
            memory_dc,
            0,
            0,
            width,
            height,
            screen_dc,
            rect.x(),
            rect.y(),
            SRCCOPY | CAPTUREBLT,
        )
        if not success:
            raise ctypes.WinError()

        stride = width * 4
        raw_data = ctypes.string_at(bits.value, stride * height)
        image = QImage(raw_data, width, height, stride, QImage.Format_RGB32).copy()
        return QPixmap.fromImage(image)
    finally:
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteObject(dib_bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)


def crop_transparent_image(image: QImage) -> QImage:
    if image.isNull():
        return QImage()

    image = image.convertToFormat(QImage.Format_ARGB32)
    if not image.hasAlphaChannel():
        return image.copy()

    min_x = image.width()
    min_y = image.height()
    max_x = -1
    max_y = -1

    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 0:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return image.copy()

    return image.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def build_icon_from_image(image: QImage) -> QIcon:
    icon = QIcon()
    for size in TRAY_ICON_SIZES:
        scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.addPixmap(QPixmap.fromImage(scaled))
    return icon


def normalize_win_modifiers(modifiers: int) -> int:
    return int(modifiers) & (MOD_CONTROL | MOD_ALT | MOD_SHIFT)


def modifiers_to_text(modifiers: int) -> list[str]:
    parts: list[str] = []
    if modifiers & MOD_CONTROL:
        parts.append("Ctrl")
    if modifiers & MOD_ALT:
        parts.append("Alt")
    if modifiers & MOD_SHIFT:
        parts.append("Shift")
    return parts


def qt_modifiers_to_win(modifiers: Qt.KeyboardModifiers) -> int:
    result = 0
    if modifiers & Qt.ControlModifier:
        result |= MOD_CONTROL
    if modifiers & Qt.AltModifier:
        result |= MOD_ALT
    if modifiers & Qt.ShiftModifier:
        result |= MOD_SHIFT
    return result


def vk_to_display_text(virtual_key: int) -> str:
    if 0x30 <= virtual_key <= 0x39:
        return chr(virtual_key)
    if 0x41 <= virtual_key <= 0x5A:
        return chr(virtual_key)
    if 0x70 <= virtual_key <= 0x87:
        return f"F{virtual_key - 0x6F}"
    return VK_DISPLAY_NAMES.get(virtual_key, "")


def hotkey_display_text(modifiers: int, virtual_key: int) -> str:
    key_text = vk_to_display_text(virtual_key)
    if not key_text:
        return ""
    parts = modifiers_to_text(modifiers)
    parts.append(key_text)
    return " + ".join(parts)


def qt_key_to_virtual_key(key: int) -> int:
    if Qt.Key_A <= key <= Qt.Key_Z:
        return ord("A") + (key - Qt.Key_A)
    if Qt.Key_0 <= key <= Qt.Key_9:
        return ord("0") + (key - Qt.Key_0)
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        return 0x70 + (key - Qt.Key_F1)
    return QT_TO_VK_SPECIAL.get(key, 0)


def normalize_virtual_key(native_virtual_key: int, qt_key: int) -> int:
    native_virtual_key = int(native_virtual_key)
    if native_virtual_key and vk_to_display_text(native_virtual_key):
        return native_virtual_key
    return qt_key_to_virtual_key(qt_key)


def hotkey_from_key_event(event: QKeyEvent) -> Optional[HotkeyConfig]:
    modifiers = qt_modifiers_to_win(event.modifiers())
    if not modifiers or event.key() in QT_MODIFIER_KEYS:
        return None

    virtual_key = normalize_virtual_key(event.nativeVirtualKey(), event.key())
    display_text = hotkey_display_text(modifiers, virtual_key)
    if not display_text:
        return None

    hotkey = HotkeyConfig(modifiers, virtual_key, display_text).normalized()
    return hotkey if hotkey.is_valid() else None


def build_launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'

    interpreter = Path(sys.executable).resolve()
    pythonw = interpreter.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else interpreter
    script_path = Path(__file__).resolve()
    return f'"{launcher}" "{script_path}"'


def clamp_top_left(point: QPoint, size: QSize, bounds: QRect) -> QPoint:
    max_x = bounds.x() + max(0, bounds.width() - size.width())
    max_y = bounds.y() + max(0, bounds.height() - size.height())
    x = max(bounds.x(), min(point.x(), max_x))
    y = max(bounds.y(), min(point.y(), max_y))
    return QPoint(x, y)


def top_left_for_center(center: QPoint, size: QSize) -> QPoint:
    return QPoint(center.x() - size.width() // 2, center.y() - size.height() // 2)


def floating_center_position(size: QSize) -> QPoint:
    screen = QApplication.primaryScreen()
    geometry = screen.availableGeometry() if screen is not None else virtual_desktop_rect()
    center = QPoint(geometry.center().x(), geometry.center().y())
    return clamp_top_left(top_left_for_center(center, size), size, virtual_desktop_rect())


def resolve_floating_position(saved_position: Optional[QPoint], size: QSize) -> QPoint:
    if isinstance(saved_position, QPoint):
        return clamp_top_left(saved_position, size, virtual_desktop_rect())
    return floating_center_position(size)


class FloatingImageAsset:
    def __init__(self, asset_path: Path) -> None:
        if not asset_path.exists():
            raise RuntimeError(current_tr("error.asset_missing", path=asset_path))

        image = QImage(str(asset_path))
        if image.isNull():
            raise RuntimeError(current_tr("error.asset_load_failed"))

        self._cropped_image = crop_transparent_image(image)
        if self._cropped_image.isNull():
            raise RuntimeError(current_tr("error.asset_process_failed"))

        self._tray_icon = build_icon_from_image(self._cropped_image)

    def make_pixmap_for_preset(self, preset: str) -> QPixmap:
        preset = normalize_size_preset(preset)
        longest_edge = FLOATING_SIZE_PRESETS[preset]["longest_edge"]
        target_size = self._cropped_image.size().scaled(longest_edge, longest_edge, Qt.KeepAspectRatio)
        scaled = self._cropped_image.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap.fromImage(scaled)

    def tray_icon(self) -> QIcon:
        return QIcon(self._tray_icon)


class SettingsManager:
    def __init__(self) -> None:
        self._settings = create_settings()

    def load_floating_position(self) -> Optional[QPoint]:
        value = self._settings.value(FLOATING_POSITION_KEY, type=QPoint)
        return value if isinstance(value, QPoint) else None

    def save_floating_position(self, position: QPoint) -> None:
        self._settings.setValue(FLOATING_POSITION_KEY, QPoint(position))
        self._settings.sync()

    def load_size_preset(self) -> str:
        value = str(self._settings.value(FLOATING_SIZE_PRESET_KEY, DEFAULT_FLOATING_SIZE_PRESET, type=str) or "")
        return normalize_size_preset(value)

    def save_size_preset(self, preset: str) -> None:
        self._settings.setValue(FLOATING_SIZE_PRESET_KEY, normalize_size_preset(preset))
        self._settings.sync()

    def load_ui_language(self) -> str:
        value = str(self._settings.value(UI_LANGUAGE_KEY, DEFAULT_UI_LANGUAGE, type=str) or "")
        return normalize_ui_language(value)

    def save_ui_language(self, language: str) -> None:
        self._settings.setValue(UI_LANGUAGE_KEY, normalize_ui_language(language))
        self._settings.sync()

    def load_capture_mode(self) -> str:
        value = str(self._settings.value(CAPTURE_MODE_KEY, DEFAULT_CAPTURE_MODE, type=str) or "")
        return normalize_capture_mode(value)

    def save_capture_mode(self, mode: str) -> None:
        self._settings.setValue(CAPTURE_MODE_KEY, normalize_capture_mode(mode))
        self._settings.sync()

    def is_layout_initialized_v2(self) -> bool:
        value = self._settings.value(FLOATING_LAYOUT_INITIALIZED_V2_KEY, None)
        if value is None:
            return False
        return str(value).lower() in ("1", "true", "yes")

    def set_layout_initialized_v2(self, initialized: bool) -> None:
        self._settings.setValue(FLOATING_LAYOUT_INITIALIZED_V2_KEY, bool(initialized))
        self._settings.sync()

    def load_hotkey(self) -> HotkeyConfig:
        modifiers = int(self._settings.value(HOTKEY_MODIFIERS_KEY, DEFAULT_HOTKEY_MODIFIERS))
        virtual_key = int(self._settings.value(HOTKEY_VK_KEY, DEFAULT_HOTKEY_VK))
        display_text = str(self._settings.value(HOTKEY_TEXT_KEY, "", type=str) or "")
        hotkey = HotkeyConfig(modifiers, virtual_key, display_text).normalized()
        return hotkey if hotkey.is_valid() else default_hotkey()

    def save_hotkey(self, hotkey: HotkeyConfig) -> None:
        hotkey = hotkey.normalized()
        self._settings.setValue(HOTKEY_MODIFIERS_KEY, hotkey.modifiers)
        self._settings.setValue(HOTKEY_VK_KEY, hotkey.virtual_key)
        self._settings.setValue(HOTKEY_TEXT_KEY, hotkey.display_text)
        self._settings.sync()

    def is_autostart_initialized(self) -> bool:
        value = self._settings.value(AUTOSTART_INITIALIZED_KEY, None)
        if value is not None:
            return str(value).lower() in ("1", "true", "yes")

        legacy_value = self._load_legacy_autostart_initialized()
        if legacy_value:
            self.set_autostart_initialized(True)
            return True
        return False

    def set_autostart_initialized(self, initialized: bool) -> None:
        self._settings.setValue(AUTOSTART_INITIALIZED_KEY, bool(initialized))
        self._settings.sync()

    def _load_legacy_autostart_initialized(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, LEGACY_SETTINGS_KEY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, AUTOSTART_INITIALIZED_VALUE)
                return bool(value)
        except FileNotFoundError:
            return False


class AutostartManager:
    def __init__(self, settings_manager: SettingsManager) -> None:
        self._settings_manager = settings_manager
        self._command = build_launch_command()

    def ensure_default_enabled(self) -> None:
        current_value = self.current_value()
        if not self._settings_manager.is_autostart_initialized():
            if current_value is None or self._should_migrate_to_current_command(current_value):
                self.set_enabled(True)
            else:
                self._settings_manager.set_autostart_initialized(True)
            return

        if self._should_migrate_to_current_command(current_value):
            self.set_enabled(True)

    def is_enabled(self) -> bool:
        return self.current_value() is not None

    def current_value(self) -> Optional[str]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
                return str(value) if value else None
        except FileNotFoundError:
            return None

    def set_enabled(self, enabled: bool) -> None:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, self._command)
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
        self._settings_manager.set_autostart_initialized(True)

    def _should_migrate_to_current_command(self, current_value: Optional[str]) -> bool:
        if not current_value or current_value == self._command:
            return False
        if getattr(sys, "frozen", False):
            return True
        return "screen_snipper.py" in current_value.lower()


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, manager: "GlobalHotkeyManager") -> None:
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, event_type, message):
        if event_type not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            return False, 0

        msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
        if msg.message == WM_HOTKEY and int(msg.wParam) == HOTKEY_ID:
            self._manager.notify_hotkey()
            return True, 0
        return False, 0


class GlobalHotkeyManager(QObject):
    activated = pyqtSignal()

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._filter: Optional[GlobalHotkeyFilter] = GlobalHotkeyFilter(self)
        self._app.installNativeEventFilter(self._filter)
        self._current_hotkey = default_hotkey()
        self._registered = False
        self._cleaned_up = False

    @property
    def current_hotkey(self) -> HotkeyConfig:
        return self._current_hotkey

    def initialize(self, hotkey: HotkeyConfig) -> bool:
        hotkey = hotkey.normalized()
        self._current_hotkey = hotkey
        self._registered = self._register_hotkey(hotkey)
        return self._registered

    def is_registered(self) -> bool:
        return self._registered

    def apply_hotkey(self, hotkey: HotkeyConfig) -> bool:
        hotkey = hotkey.normalized()
        previous_hotkey = self._current_hotkey
        previous_registered = self._registered

        if previous_registered:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self._registered = False

        if self._register_hotkey(hotkey):
            self._current_hotkey = hotkey
            self._registered = True
            return True

        self._current_hotkey = previous_hotkey
        if previous_registered and self._register_hotkey(previous_hotkey):
            self._registered = True
        return False

    def cleanup(self) -> None:
        if self._cleaned_up:
            return

        self._cleaned_up = True
        if self._registered:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self._registered = False

        if self._filter is not None:
            self._app.removeNativeEventFilter(self._filter)
            self._filter = None

    def notify_hotkey(self) -> None:
        if self._registered:
            self.activated.emit()

    def _register_hotkey(self, hotkey: HotkeyConfig) -> bool:
        if not hotkey.is_valid():
            return False
        return bool(
            user32.RegisterHotKey(
                None,
                HOTKEY_ID,
                hotkey.modifiers | MOD_NOREPEAT,
                hotkey.virtual_key,
            )
        )


class SelectionOverlay(QWidget):
    selectionFinished = pyqtSignal(QPixmap)
    selectionCanceled = pyqtSignal()

    def __init__(self, background: QPixmap, desktop_rect: QRect, capture_mode: str, language: str) -> None:
        super().__init__(None)
        self._background = background
        self._desktop_rect = QRect(desktop_rect)
        self._capture_mode = normalize_capture_mode(capture_mode)
        self._language = normalize_ui_language(language)
        self._interaction = "idle"
        self._resize_region = "none"
        self._start_point = QPoint()
        self._interaction_start_rect = QRect()
        self._previous_selection_rect = QRect()
        self._selection_rect = QRect()

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setGeometry(self._desktop_rect)

        self._toolbar = QWidget(self)
        self._toolbar.setObjectName("overlayToolbar")
        self._toolbar.setStyleSheet(
            """
            QWidget#overlayToolbar {
                background-color: rgba(28, 31, 36, 220);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 10px;
            }
            QLabel#overlayHintLabel {
                color: white;
            }
            QPushButton {
                color: white;
                background-color: rgba(255, 255, 255, 24);
                border: 1px solid rgba(255, 255, 255, 70);
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 42);
            }
            """
        )
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(10)

        self._hint_label = QLabel(self._toolbar)
        self._hint_label.setObjectName("overlayHintLabel")
        self._confirm_button = QPushButton(self._toolbar)
        self._cancel_button = QPushButton(self._toolbar)
        self._confirm_button.setFocusPolicy(Qt.NoFocus)
        self._cancel_button.setFocusPolicy(Qt.NoFocus)
        self._hint_label.setWordWrap(False)
        toolbar_layout.addWidget(self._hint_label)
        toolbar_layout.addWidget(self._confirm_button)
        toolbar_layout.addWidget(self._cancel_button)
        self._confirm_button.clicked.connect(self._confirm_selection)
        self._cancel_button.clicked.connect(self._cancel)

        for widget in (self._toolbar, self._hint_label, self._confirm_button, self._cancel_button):
            widget.installEventFilter(self)

        self._update_toolbar_texts()
        self._toolbar.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self.grabKeyboard()

    def closeEvent(self, event) -> None:
        self.releaseKeyboard()
        super().closeEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawPixmap(0, 0, self._background)
        painter.fillRect(self.rect(), MASK_COLOR)

        if self._has_valid_selection():
            painter.drawPixmap(self._selection_rect, self._background, self._selection_rect)
            painter.setPen(QPen(BORDER_COLOR, 2))
            painter.drawRect(self._selection_rect.adjusted(0, 0, -1, -1))
            if self._capture_mode == "refine":
                painter.setPen(QPen(BORDER_COLOR, 1))
                painter.setBrush(HANDLE_FILL_COLOR)
                for handle_rect in self._handle_rects():
                    painter.drawRect(handle_rect)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self._cancel()
            return
        if event.button() != Qt.LeftButton:
            return

        local_pos = self._clamp_point(event.pos())
        self._start_point = local_pos
        self._interaction_start_rect = QRect(self._selection_rect)
        self._previous_selection_rect = QRect(self._selection_rect)
        self._resize_region = "none"

        if self._capture_mode == "refine" and self._has_valid_selection():
            hit_region = self._hit_test_region(local_pos)
            if hit_region == "move":
                self._interaction = "move"
                self._toolbar.hide()
                event.accept()
                return
            if hit_region != "none":
                self._interaction = "resize"
                self._resize_region = hit_region
                self._toolbar.hide()
                event.accept()
                return

        self._interaction = "draw"
        self._selection_rect = QRect(local_pos, local_pos).normalized()
        self._toolbar.hide()
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        local_pos = self._clamp_point(event.pos())
        if self._interaction == "idle":
            self._update_cursor(local_pos)
            return

        if self._interaction == "draw":
            self._selection_rect = QRect(self._start_point, local_pos).normalized()
        elif self._interaction == "move":
            delta = local_pos - self._start_point
            self._selection_rect = self._translated_rect(self._interaction_start_rect, delta)
        elif self._interaction == "resize":
            self._selection_rect = self._resized_rect(self._interaction_start_rect, local_pos, self._resize_region)

        self._update_toolbar_geometry()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self._cancel()
            return
        if event.button() != Qt.LeftButton or self._interaction == "idle":
            return

        local_pos = self._clamp_point(event.pos())
        if self._interaction == "draw":
            self._selection_rect = QRect(self._start_point, local_pos).normalized()
            if not self._has_valid_selection():
                if self._capture_mode == "minimal":
                    self._cancel()
                    return
                if self._is_valid_rect(self._previous_selection_rect):
                    self._selection_rect = QRect(self._previous_selection_rect)
                    self._show_toolbar_if_needed()
                else:
                    self._selection_rect = QRect()
                    self._toolbar.hide()
                self._interaction = "idle"
                self._update_cursor(local_pos)
                self.update()
                return

            if self._capture_mode == "minimal":
                self._interaction = "idle"
                self._confirm_selection()
                return

            self._show_toolbar_if_needed()

        elif self._capture_mode == "refine":
            self._show_toolbar_if_needed()

        self._interaction = "idle"
        self._update_cursor(local_pos)
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.LeftButton
            and self._capture_mode == "refine"
            and self._has_valid_selection()
            and self._selection_rect.contains(event.pos())
        ):
            self._confirm_selection()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self._cancel()
            return
        if (
            self._capture_mode == "refine"
            and event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and self._has_valid_selection()
        ):
            self._confirm_selection()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.MouseButtonPress and isinstance(event, QMouseEvent) and event.button() == Qt.RightButton:
            self._cancel()
            return True
        return super().eventFilter(watched, event)

    def _cancel(self) -> None:
        self._toolbar.hide()
        self.selectionCanceled.emit()

    def _confirm_selection(self) -> None:
        if not self._has_valid_selection():
            return
        self.selectionFinished.emit(self._background.copy(self._selection_rect))

    def _update_toolbar_texts(self) -> None:
        self._hint_label.setText(tr(self._language, "overlay.hint"))
        self._confirm_button.setText(tr(self._language, "overlay.confirm"))
        self._cancel_button.setText(tr(self._language, "overlay.cancel"))
        self._toolbar.adjustSize()

    def _show_toolbar_if_needed(self) -> None:
        if self._capture_mode != "refine" or not self._has_valid_selection():
            self._toolbar.hide()
            return
        self._update_toolbar_geometry()
        self._toolbar.show()
        self._toolbar.raise_()

    def _update_toolbar_geometry(self) -> None:
        if self._capture_mode != "refine" or not self._has_valid_selection():
            self._toolbar.hide()
            return

        size_hint = self._toolbar.sizeHint()
        width = size_hint.width()
        height = size_hint.height()
        target_x = self._selection_rect.center().x() - width // 2
        above_y = self._selection_rect.top() - height - TOOLBAR_GAP
        below_y = self._selection_rect.bottom() + TOOLBAR_GAP + 1
        if above_y >= 0:
            target_y = above_y
        else:
            target_y = min(max(0, below_y), max(0, self.height() - height))
        target_x = max(0, min(target_x, max(0, self.width() - width)))
        self._toolbar.setGeometry(target_x, target_y, width, height)

    def _has_valid_selection(self) -> bool:
        return self._is_valid_rect(self._selection_rect)

    @staticmethod
    def _is_valid_rect(rect: QRect) -> bool:
        return rect.width() >= MIN_SELECTION_SIZE and rect.height() >= MIN_SELECTION_SIZE

    def _clamp_point(self, point: QPoint) -> QPoint:
        max_x = max(0, self.width() - 1)
        max_y = max(0, self.height() - 1)
        return QPoint(max(0, min(point.x(), max_x)), max(0, min(point.y(), max_y)))

    def _translated_rect(self, rect: QRect, delta: QPoint) -> QRect:
        width = rect.width()
        height = rect.height()
        max_left = max(0, self.width() - width)
        max_top = max(0, self.height() - height)
        left = max(0, min(rect.left() + delta.x(), max_left))
        top = max(0, min(rect.top() + delta.y(), max_top))
        return QRect(left, top, width, height)

    def _resized_rect(self, rect: QRect, point: QPoint, region: str) -> QRect:
        left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
        min_span = MIN_SELECTION_SIZE - 1
        max_x = max(0, self.width() - 1)
        max_y = max(0, self.height() - 1)

        if "left" in region:
            left = max(0, min(point.x(), right - min_span))
        if "right" in region:
            right = min(max_x, max(point.x(), left + min_span))
        if "top" in region:
            top = max(0, min(point.y(), bottom - min_span))
        if "bottom" in region:
            bottom = min(max_y, max(point.y(), top + min_span))

        return QRect(QPoint(left, top), QPoint(right, bottom)).normalized()

    def _handle_points(self) -> list[QPoint]:
        rect = self._selection_rect
        return [
            QPoint(rect.left(), rect.top()),
            QPoint(rect.center().x(), rect.top()),
            QPoint(rect.right(), rect.top()),
            QPoint(rect.right(), rect.center().y()),
            QPoint(rect.right(), rect.bottom()),
            QPoint(rect.center().x(), rect.bottom()),
            QPoint(rect.left(), rect.bottom()),
            QPoint(rect.left(), rect.center().y()),
        ]

    def _handle_rects(self) -> list[QRect]:
        half = SELECTION_HANDLE_SIZE // 2
        rects = []
        for point in self._handle_points():
            rects.append(QRect(point.x() - half, point.y() - half, SELECTION_HANDLE_SIZE, SELECTION_HANDLE_SIZE))
        return rects

    def _hit_test_region(self, point: QPoint) -> str:
        if not self._has_valid_selection():
            return "none"

        rect = self._selection_rect
        margin = SELECTION_HIT_MARGIN
        outer_rect = rect.adjusted(-margin, -margin, margin, margin)
        if not outer_rect.contains(point):
            return "none"

        near_left = abs(point.x() - rect.left()) <= margin
        near_right = abs(point.x() - rect.right()) <= margin
        near_top = abs(point.y() - rect.top()) <= margin
        near_bottom = abs(point.y() - rect.bottom()) <= margin
        inside_x = rect.left() <= point.x() <= rect.right()
        inside_y = rect.top() <= point.y() <= rect.bottom()

        if near_left and near_top:
            return "top_left"
        if near_right and near_top:
            return "top_right"
        if near_left and near_bottom:
            return "bottom_left"
        if near_right and near_bottom:
            return "bottom_right"
        if near_left and inside_y:
            return "left"
        if near_right and inside_y:
            return "right"
        if near_top and inside_x:
            return "top"
        if near_bottom and inside_x:
            return "bottom"
        if rect.contains(point):
            return "move"
        return "none"

    def _update_cursor(self, point: QPoint) -> None:
        if self._capture_mode != "refine" or not self._has_valid_selection():
            self.setCursor(QCursor(Qt.CrossCursor))
            return

        region = self._hit_test_region(point)
        cursor_shape = Qt.CrossCursor
        if region == "move":
            cursor_shape = Qt.SizeAllCursor
        elif region in ("left", "right"):
            cursor_shape = Qt.SizeHorCursor
        elif region in ("top", "bottom"):
            cursor_shape = Qt.SizeVerCursor
        elif region in ("top_left", "bottom_right"):
            cursor_shape = Qt.SizeFDiagCursor
        elif region in ("top_right", "bottom_left"):
            cursor_shape = Qt.SizeBDiagCursor
        self.setCursor(QCursor(cursor_shape))


class ScreenCaptureController(QObject):
    captureEnded = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._overlay: Optional[SelectionOverlay] = None
        self._cleaned_up = False

    def is_capturing(self) -> bool:
        return self._overlay is not None

    def start_capture(self, capture_mode: str, language: str) -> bool:
        if self._cleaned_up or self._overlay is not None:
            return False

        desktop_rect = virtual_desktop_rect()
        try:
            background = capture_virtual_desktop(desktop_rect)
        except Exception as exc:
            print(f"Unable to capture the screen: {exc}", file=sys.stderr)
            return False

        self._overlay = SelectionOverlay(background, desktop_rect, capture_mode, language)
        self._overlay.selectionFinished.connect(self._finish_capture)
        self._overlay.selectionCanceled.connect(self._cancel_capture)
        self._overlay.destroyed.connect(self._overlay_destroyed)
        self._overlay.show()
        return True

    def cleanup(self) -> None:
        if self._cleaned_up:
            return

        self._cleaned_up = True
        self._close_overlay()

    def _finish_capture(self, pixmap: QPixmap) -> None:
        QApplication.clipboard().setPixmap(pixmap, QClipboard.Clipboard)
        self._close_overlay()
        self.captureEnded.emit()

    def _cancel_capture(self) -> None:
        self._close_overlay()
        self.captureEnded.emit()

    def _close_overlay(self) -> None:
        if self._overlay is None:
            return

        overlay = self._overlay
        self._overlay = None
        overlay.blockSignals(True)
        overlay.close()
        overlay.deleteLater()

    def _overlay_destroyed(self) -> None:
        self._overlay = None


class HotkeyCaptureEdit(QLineEdit):
    hotkeyCaptured = pyqtSignal(object)

    def __init__(self, initial_text: str, placeholder_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setText(initial_text)
        self.setPlaceholderText(placeholder_text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        event.accept()
        if event.isAutoRepeat():
            return

        hotkey = hotkey_from_key_event(event)
        if hotkey is None:
            return

        self.setText(hotkey.display_text)
        self.hotkeyCaptured.emit(hotkey)


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_language: str,
        current_capture_mode: str,
        current_hotkey: HotkeyConfig,
        hotkey_registered: bool,
        hotkey_apply_callback: Callable[[HotkeyConfig], bool],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._language = normalize_ui_language(current_language)
        self._capture_mode = normalize_capture_mode(current_capture_mode)
        self._current_hotkey = current_hotkey.normalized()
        self._selected_hotkey = self._current_hotkey
        self._hotkey_registered = hotkey_registered
        self._hotkey_apply_callback = hotkey_apply_callback

        self.setWindowTitle(tr(self._language, "dialog.settings.title"))
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(420)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self._language_combo = QComboBox(self)
        for language in SUPPORTED_UI_LANGUAGES:
            self._language_combo.addItem(tr(self._language, f"dialog.settings.language.{language}"), language)
        self._language_combo.setCurrentIndex(self._language_combo.findData(self._language))

        self._capture_mode_combo = QComboBox(self)
        for mode in SUPPORTED_CAPTURE_MODES:
            self._capture_mode_combo.addItem(capture_mode_label(self._language, mode), mode)
        self._capture_mode_combo.setCurrentIndex(self._capture_mode_combo.findData(self._capture_mode))

        form_layout.addRow(tr(self._language, "dialog.settings.language"), self._language_combo)
        form_layout.addRow(tr(self._language, "dialog.settings.capture_mode"), self._capture_mode_combo)

        hotkey_key = "dialog.settings.current_hotkey" if self._hotkey_registered else "dialog.settings.current_hotkey_inactive"
        self._hotkey_title = QLabel(tr(self._language, "dialog.settings.hotkey_title"))
        self._current_label = QLabel(tr(self._language, hotkey_key, hotkey=self._current_hotkey.display_text))
        self._current_label.setWordWrap(True)
        self._hotkey_title.setStyleSheet("font-weight: 600;")

        self._hint_label = QLabel(tr(self._language, "dialog.settings.hotkey_hint"))
        self._hint_label.setWordWrap(True)

        self._capture_edit = HotkeyCaptureEdit(
            self._current_hotkey.display_text,
            tr(self._language, "dialog.settings.hotkey_placeholder"),
            self,
        )
        self._capture_edit.hotkeyCaptured.connect(self._on_hotkey_captured)

        self._preview_label = QLabel(tr(self._language, "dialog.settings.hotkey_preview", hotkey=self._selected_hotkey.display_text))
        self._preview_label.setWordWrap(True)

        self._restore_button = QPushButton(tr(self._language, "dialog.settings.restore_default"))
        self._restore_button.clicked.connect(self._restore_default)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.addButton(self._restore_button, QDialogButtonBox.ResetRole)
        button_box.button(QDialogButtonBox.Ok).setText(tr(self._language, "dialog.ok"))
        button_box.button(QDialogButtonBox.Cancel).setText(tr(self._language, "dialog.cancel"))
        button_box.accepted.connect(self._accept_with_validation)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addSpacing(6)
        layout.addWidget(self._hotkey_title)
        layout.addWidget(self._current_label)
        layout.addWidget(self._hint_label)
        layout.addWidget(self._capture_edit)
        layout.addWidget(self._preview_label)
        layout.addWidget(button_box)

    def selected_language(self) -> str:
        return normalize_ui_language(str(self._language_combo.currentData() or self._language))

    def selected_capture_mode(self) -> str:
        return normalize_capture_mode(str(self._capture_mode_combo.currentData() or self._capture_mode))

    def selected_hotkey(self) -> HotkeyConfig:
        return self._selected_hotkey.normalized()

    def _on_hotkey_captured(self, hotkey: HotkeyConfig) -> None:
        self._selected_hotkey = hotkey.normalized()
        self._preview_label.setText(
            tr(self._language, "dialog.settings.hotkey_preview", hotkey=self._selected_hotkey.display_text)
        )

    def _restore_default(self) -> None:
        self._selected_hotkey = default_hotkey()
        self._capture_edit.setText(self._selected_hotkey.display_text)
        self._preview_label.setText(
            tr(self._language, "dialog.settings.hotkey_preview", hotkey=self._selected_hotkey.display_text)
        )

    def _accept_with_validation(self) -> None:
        hotkey = self.selected_hotkey()
        should_apply_hotkey = hotkey != self._current_hotkey or not self._hotkey_registered
        if should_apply_hotkey and not self._hotkey_apply_callback(hotkey):
            show_error_dialog(tr(self._language, "error.hotkey_conflict", hotkey=hotkey.display_text))
            return
        self.accept()


class FloatingButton(QWidget):
    captureRequested = pyqtSignal()
    menuRequested = pyqtSignal(QPoint)
    positionCommitted = pyqtSignal(QPoint)

    def __init__(self, image_asset: FloatingImageAsset, size_preset: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._image_asset = image_asset
        self._size_preset = DEFAULT_FLOATING_SIZE_PRESET
        self._display_pixmap = QPixmap()
        self._hovered = False
        self._pressed = False
        self._dragging = False
        self._press_global_pos = QPoint()
        self._press_window_pos = QPoint()

        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip(current_tr("tooltip.floating_button"))
        self.apply_size_preset(size_preset)

    @property
    def current_preset(self) -> str:
        return self._size_preset

    def apply_size_preset(self, preset: str) -> None:
        preset = normalize_size_preset(preset)
        pixmap = self._image_asset.make_pixmap_for_preset(preset)
        if pixmap.isNull():
            return

        self._size_preset = preset
        self._display_pixmap = pixmap
        self.setFixedSize(self._display_pixmap.size())
        mask_image = self._display_pixmap.toImage().createAlphaMask()
        self.setMask(QBitmap.fromImage(mask_image))
        self.update()

    def move_to(self, position: QPoint) -> None:
        self.move(clamp_top_left(position, self.size(), virtual_desktop_rect()))

    def paintEvent(self, event) -> None:
        if self._display_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if self._pressed and not self._dragging:
            painter.setOpacity(0.84)
        elif self._hovered:
            painter.setOpacity(0.96)
        painter.drawPixmap(self.rect(), self._display_pixmap)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self._dragging = False
            self._press_global_pos = event.globalPos()
            self._press_window_pos = self.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.update()
            event.accept()
            return

        if event.button() == Qt.RightButton:
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._pressed:
            super().mouseMoveEvent(event)
            return

        delta = event.globalPos() - self._press_global_pos
        if not self._dragging and delta.manhattanLength() >= FLOATING_DRAG_THRESHOLD:
            self._dragging = True

        if self._dragging:
            self.move_to(self._press_window_pos + delta)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self.menuRequested.emit(event.globalPos())
            event.accept()
            return

        if event.button() != Qt.LeftButton or not self._pressed:
            super().mouseReleaseEvent(event)
            return

        self._pressed = False
        self.setCursor(QCursor(Qt.PointingHandCursor))
        if self._dragging:
            self._dragging = False
            self.positionCommitted.emit(self.pos())
        else:
            self.captureRequested.emit()
        self.update()
        event.accept()


class TrayApp(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        if not QSystemTrayIcon.isSystemTrayAvailable():
            raise RuntimeError(current_tr("error.tray_unavailable"))

        self._app = app
        self._settings_manager = SettingsManager()
        self._language = self._settings_manager.load_ui_language()
        self._capture_mode = self._settings_manager.load_capture_mode()
        self._floating_asset = FloatingImageAsset(resolve_resource_path(FLOATING_BUTTON_ASSET_RELATIVE))
        self._autostart_manager = AutostartManager(self._settings_manager)
        self._hotkey_manager = GlobalHotkeyManager(app)
        self._capture_controller = ScreenCaptureController()

        self._cleaned_up = False
        self._floating_hidden_by_user = False
        self._restore_button_after_capture = False

        self._tray_icon = QSystemTrayIcon(self._build_icon(), self)
        self._tray_icon.setToolTip(APP_NAME)

        self._capture_action = QAction(self)
        self._capture_action.triggered.connect(self.request_capture)

        self._toggle_button_action = QAction(self)
        self._toggle_button_action.triggered.connect(self._toggle_floating_button_visibility)

        self._size_menu = QMenu()
        self._size_action_group = QActionGroup(self)
        self._size_action_group.setExclusive(True)
        self._size_actions: dict[str, QAction] = {}
        for preset in ("small", "medium", "large"):
            action = QAction(self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, p=preset: self._apply_size_preset(p))
            self._size_action_group.addAction(action)
            self._size_menu.addAction(action)
            self._size_actions[preset] = action

        self._autostart_action = QAction(self)
        self._autostart_action.setCheckable(True)
        self._autostart_action.toggled.connect(self._toggle_autostart)

        self._settings_action = QAction(self)
        self._settings_action.triggered.connect(self._open_settings_dialog)

        self._exit_action = QAction(self)
        self._exit_action.triggered.connect(self._quit_application)

        self._menu = QMenu()
        self._menu.addAction(self._capture_action)
        self._menu.addAction(self._toggle_button_action)
        self._menu.addMenu(self._size_menu)
        self._menu.addSeparator()
        self._menu.addAction(self._autostart_action)
        self._menu.addAction(self._settings_action)
        self._menu.addSeparator()
        self._menu.addAction(self._exit_action)
        self._tray_icon.setContextMenu(self._menu)

        initial_size_preset = self._settings_manager.load_size_preset()
        self._floating_button = FloatingButton(self._floating_asset, initial_size_preset)
        self._floating_button.captureRequested.connect(self.request_capture)
        self._floating_button.menuRequested.connect(self._show_context_menu)
        self._floating_button.positionCommitted.connect(self._save_floating_position)

        self._capture_controller.captureEnded.connect(self._restore_floating_button_after_capture)
        self._hotkey_manager.activated.connect(self.request_capture)

        initial_hotkey = self._settings_manager.load_hotkey()
        hotkey_registered = self._hotkey_manager.initialize(initial_hotkey)

        self._autostart_manager.ensure_default_enabled()
        self._sync_autostart_action()
        self._sync_toggle_button_action()
        self._sync_size_actions()
        self._retranslate_ui()

        self._place_floating_button()
        self._floating_button.show()

        self._app.setWindowIcon(self._tray_icon.icon())
        self._app.aboutToQuit.connect(self.cleanup)
        self._tray_icon.show()

        if not hotkey_registered:
            warning_message = self._tr("message.hotkey_unavailable", hotkey=initial_hotkey.display_text)
            QTimer.singleShot(0, lambda: show_warning_dialog(warning_message))

    def cleanup(self) -> None:
        if self._cleaned_up:
            return

        self._cleaned_up = True
        self._tray_icon.hide()
        self._floating_button.hide()
        self._capture_controller.cleanup()
        self._hotkey_manager.cleanup()

    def request_capture(self) -> None:
        if self._capture_controller.is_capturing():
            return

        self._restore_button_after_capture = self._floating_button.isVisible() and not self._floating_hidden_by_user
        if self._floating_button.isVisible():
            self._floating_button.hide()
            self._app.processEvents()

        QTimer.singleShot(0, self._start_capture_now)

    def _start_capture_now(self) -> None:
        if self._capture_controller.start_capture(self._capture_mode, self._language):
            return

        if self._restore_button_after_capture and not self._floating_hidden_by_user:
            self._floating_button.show()
            self._floating_button.raise_()
        self._restore_button_after_capture = False

    def _restore_floating_button_after_capture(self) -> None:
        if self._restore_button_after_capture and not self._floating_hidden_by_user:
            self._floating_button.show()
            self._floating_button.raise_()
        self._restore_button_after_capture = False

    def _toggle_floating_button_visibility(self) -> None:
        if self._floating_hidden_by_user:
            self._floating_hidden_by_user = False
            position = resolve_floating_position(self._settings_manager.load_floating_position(), self._floating_button.size())
            self._floating_button.move_to(position)
            self._floating_button.show()
            self._floating_button.raise_()
        else:
            self._floating_hidden_by_user = True
            self._floating_button.hide()
        self._sync_toggle_button_action()

    def _show_context_menu(self, global_pos: QPoint) -> None:
        self._menu.exec_(global_pos)

    def _toggle_autostart(self, enabled: bool) -> None:
        try:
            self._autostart_manager.set_enabled(enabled)
        except OSError as exc:
            print(f"Unable to update autostart setting: {exc}", file=sys.stderr)
            show_error_dialog(self._tr("error.autostart_update_failed"))
        finally:
            self._sync_autostart_action()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(
            self._language,
            self._capture_mode,
            self._hotkey_manager.current_hotkey,
            self._hotkey_manager.is_registered(),
            self._hotkey_manager.apply_hotkey,
            self._floating_button,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        self._language = dialog.selected_language()
        self._capture_mode = dialog.selected_capture_mode()
        hotkey = dialog.selected_hotkey()
        self._settings_manager.save_ui_language(self._language)
        self._settings_manager.save_capture_mode(self._capture_mode)
        self._settings_manager.save_hotkey(hotkey)
        self._retranslate_ui()

    def _apply_size_preset(self, preset: str) -> None:
        preset = normalize_size_preset(preset)
        current_center = self._floating_button.geometry().center()
        self._floating_button.apply_size_preset(preset)
        position = clamp_top_left(
            top_left_for_center(current_center, self._floating_button.size()),
            self._floating_button.size(),
            virtual_desktop_rect(),
        )
        self._floating_button.move_to(position)
        self._settings_manager.save_size_preset(preset)
        self._settings_manager.save_floating_position(self._floating_button.pos())
        self._sync_size_actions()

    def _save_floating_position(self, position: QPoint) -> None:
        self._settings_manager.save_floating_position(position)

    def _place_floating_button(self) -> None:
        if not self._settings_manager.is_layout_initialized_v2():
            position = floating_center_position(self._floating_button.size())
            self._floating_button.move_to(position)
            self._settings_manager.save_floating_position(self._floating_button.pos())
            self._settings_manager.set_layout_initialized_v2(True)
            return

        position = resolve_floating_position(self._settings_manager.load_floating_position(), self._floating_button.size())
        self._floating_button.move_to(position)
        self._settings_manager.save_floating_position(self._floating_button.pos())

    def _sync_autostart_action(self) -> None:
        enabled = self._autostart_manager.is_enabled()
        self._autostart_action.blockSignals(True)
        self._autostart_action.setChecked(enabled)
        self._autostart_action.blockSignals(False)

    def _sync_toggle_button_action(self) -> None:
        if self._floating_hidden_by_user:
            self._toggle_button_action.setText(self._tr("menu.toggle_button.show"))
        else:
            self._toggle_button_action.setText(self._tr("menu.toggle_button.hide"))

    def _sync_size_actions(self) -> None:
        current_preset = self._floating_button.current_preset
        for preset, action in self._size_actions.items():
            action.blockSignals(True)
            action.setChecked(preset == current_preset)
            action.blockSignals(False)

    def _retranslate_ui(self) -> None:
        self._capture_action.setText(self._tr("menu.capture"))
        self._size_menu.setTitle(self._tr("menu.size"))
        self._autostart_action.setText(self._tr("menu.autostart"))
        self._settings_action.setText(self._tr("menu.settings"))
        self._exit_action.setText(self._tr("menu.exit"))
        for preset, action in self._size_actions.items():
            action.setText(self._tr(f"menu.size.{preset}"))
        self._floating_button.setToolTip(self._tr("tooltip.floating_button"))
        self._sync_toggle_button_action()

    def _quit_application(self) -> None:
        self._tray_icon.hide()
        QTimer.singleShot(0, self._app.quit)

    def _build_icon(self) -> QIcon:
        return self._floating_asset.tray_icon()

    def _tr(self, key: str, **kwargs) -> str:
        return tr(self._language, key, **kwargs)


def main() -> int:
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
    configure_windows_dpi()

    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ID)

    try:
        tray_app = TrayApp(app)
    except Exception as exc:
        print(f"Initialization failed: {exc}", file=sys.stderr)
        show_error_dialog(current_tr("error.initialization_failed", error=exc))
        return 1

    app._tray_app = tray_app
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
