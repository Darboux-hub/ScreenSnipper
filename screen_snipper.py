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
from typing import Optional

from PyQt5.QtCore import (
    QAbstractNativeEventFilter,
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

MIN_SELECTION_SIZE = 2
FLOATING_DRAG_THRESHOLD = 4

FLOATING_BUTTON_ASSET_RELATIVE = Path("assets") / "floating_button.png"
TRAY_ICON_SIZES = (16, 20, 24, 32, 40, 48, 64)

FLOATING_SIZE_PRESETS = {
    "small": {"label": "小", "longest_edge": 120},
    "medium": {"label": "中", "longest_edge": 160},
    "large": {"label": "大", "longest_edge": 200},
}
DEFAULT_FLOATING_SIZE_PRESET = "small"

FLOATING_POSITION_KEY = "floating_button/position"
FLOATING_SIZE_PRESET_KEY = "floating_button/size_preset"
FLOATING_LAYOUT_INITIALIZED_V2_KEY = "floating_button/layout_initialized_v2"
HOTKEY_MODIFIERS_KEY = "hotkey/modifiers"
HOTKEY_VK_KEY = "hotkey/virtual_key"
HOTKEY_TEXT_KEY = "hotkey/display_text"
AUTOSTART_INITIALIZED_KEY = "autostart/initialized"


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
            raise RuntimeError(f"找不到悬浮窗图片资源：{asset_path}")

        image = QImage(str(asset_path))
        if image.isNull():
            raise RuntimeError("悬浮窗图片资源加载失败。")

        self._cropped_image = crop_transparent_image(image)
        if self._cropped_image.isNull():
            raise RuntimeError("悬浮窗图片资源处理失败。")

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

    def __init__(self, background: QPixmap, desktop_rect: QRect) -> None:
        super().__init__(None)
        self._background = background
        self._desktop_rect = QRect(desktop_rect)
        self._dragging = False
        self._start_point = QPoint()
        self._end_point = QPoint()
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

        if not self._selection_rect.isNull():
            painter.drawPixmap(self._selection_rect, self._background, self._selection_rect)
            painter.setPen(QPen(BORDER_COLOR, 2))
            painter.drawRect(self._selection_rect.adjusted(0, 0, -1, -1))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self._cancel()
            return
        if event.button() != Qt.LeftButton:
            return

        self._dragging = True
        self._start_point = event.pos()
        self._end_point = event.pos()
        self._selection_rect = QRect(self._start_point, self._end_point).normalized()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._dragging:
            return

        self._end_point = event.pos()
        self._selection_rect = QRect(self._start_point, self._end_point).normalized()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self._cancel()
            return
        if event.button() != Qt.LeftButton or not self._dragging:
            return

        self._dragging = False
        self._end_point = event.pos()
        self._selection_rect = QRect(self._start_point, self._end_point).normalized()

        if (
            self._selection_rect.width() < MIN_SELECTION_SIZE
            or self._selection_rect.height() < MIN_SELECTION_SIZE
        ):
            self._cancel()
            return

        self.selectionFinished.emit(self._background.copy(self._selection_rect))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self._cancel()
            return
        super().keyPressEvent(event)

    def _cancel(self) -> None:
        self.selectionCanceled.emit()


class ScreenCaptureController(QObject):
    captureEnded = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._overlay: Optional[SelectionOverlay] = None
        self._cleaned_up = False

    def is_capturing(self) -> bool:
        return self._overlay is not None

    def start_capture(self) -> bool:
        if self._cleaned_up or self._overlay is not None:
            return False

        desktop_rect = virtual_desktop_rect()
        try:
            background = capture_virtual_desktop(desktop_rect)
        except Exception as exc:
            print(f"Unable to capture the screen: {exc}", file=sys.stderr)
            return False

        self._overlay = SelectionOverlay(background, desktop_rect)
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

    def __init__(self, initial_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setText(initial_text)
        self.setPlaceholderText("按下新的快捷键")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        event.accept()
        if event.isAutoRepeat():
            return

        hotkey = hotkey_from_key_event(event)
        if hotkey is None:
            return

        self.setText(hotkey.display_text)
        self.hotkeyCaptured.emit(hotkey)


class HotkeySettingsDialog(QDialog):
    def __init__(self, current_hotkey: HotkeyConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_hotkey = current_hotkey.normalized()
        self._selected_hotkey = self._current_hotkey

        self.setWindowTitle("设置截图热键")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(360)

        self._current_label = QLabel(f"当前热键：{self._current_hotkey.display_text}")
        self._current_label.setWordWrap(True)

        self._hint_label = QLabel(
            "点击下方输入框后直接按下新的快捷键，仅支持 Ctrl / Alt / Shift + 一个主键。"
        )
        self._hint_label.setWordWrap(True)

        self._capture_edit = HotkeyCaptureEdit(self._current_hotkey.display_text, self)
        self._capture_edit.hotkeyCaptured.connect(self._on_hotkey_captured)

        self._preview_label = QLabel(f"新的热键：{self._selected_hotkey.display_text}")
        self._preview_label.setWordWrap(True)

        restore_button = QPushButton("恢复默认")
        restore_button.clicked.connect(self._restore_default)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.addButton(restore_button, QDialogButtonBox.ResetRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._current_label)
        layout.addWidget(self._hint_label)
        layout.addWidget(self._capture_edit)
        layout.addWidget(self._preview_label)
        layout.addWidget(button_box)

    def selected_hotkey(self) -> HotkeyConfig:
        return self._selected_hotkey.normalized()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._capture_edit.setFocus(Qt.ActiveWindowFocusReason)
        self._capture_edit.selectAll()

    def _on_hotkey_captured(self, hotkey: HotkeyConfig) -> None:
        self._selected_hotkey = hotkey.normalized()
        self._preview_label.setText(f"新的热键：{self._selected_hotkey.display_text}")

    def _restore_default(self) -> None:
        self._selected_hotkey = default_hotkey()
        self._capture_edit.setText(self._selected_hotkey.display_text)
        self._preview_label.setText(f"新的热键：{self._selected_hotkey.display_text}")


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
        self.setToolTip("左键截图，拖动可移动，右键打开菜单")
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
            raise RuntimeError("当前系统会话不支持系统托盘。")

        self._app = app
        self._settings_manager = SettingsManager()
        self._floating_asset = FloatingImageAsset(resolve_resource_path(FLOATING_BUTTON_ASSET_RELATIVE))
        self._autostart_manager = AutostartManager(self._settings_manager)
        self._hotkey_manager = GlobalHotkeyManager(app)
        self._capture_controller = ScreenCaptureController()

        self._cleaned_up = False
        self._floating_hidden_by_user = False
        self._restore_button_after_capture = False

        self._tray_icon = QSystemTrayIcon(self._build_icon(), self)
        self._tray_icon.setToolTip(APP_NAME)

        self._capture_action = QAction("截图", self)
        self._capture_action.triggered.connect(self.request_capture)

        self._toggle_button_action = QAction("隐藏悬浮按钮", self)
        self._toggle_button_action.triggered.connect(self._toggle_floating_button_visibility)

        self._size_menu = QMenu("悬浮窗大小")
        self._size_action_group = QActionGroup(self)
        self._size_action_group.setExclusive(True)
        self._size_actions: dict[str, QAction] = {}
        for preset in ("small", "medium", "large"):
            label = FLOATING_SIZE_PRESETS[preset]["label"]
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, p=preset: self._apply_size_preset(p))
            self._size_action_group.addAction(action)
            self._size_menu.addAction(action)
            self._size_actions[preset] = action

        self._autostart_action = QAction("开机启动", self)
        self._autostart_action.setCheckable(True)
        self._autostart_action.toggled.connect(self._toggle_autostart)

        self._hotkey_action = QAction("设置热键...", self)
        self._hotkey_action.triggered.connect(self._open_hotkey_dialog)

        self._exit_action = QAction("退出", self)
        self._exit_action.triggered.connect(self._quit_application)

        self._menu = QMenu()
        self._menu.addAction(self._capture_action)
        self._menu.addAction(self._toggle_button_action)
        self._menu.addMenu(self._size_menu)
        self._menu.addSeparator()
        self._menu.addAction(self._autostart_action)
        self._menu.addAction(self._hotkey_action)
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
        self._sync_hotkey_action()

        self._place_floating_button()
        self._floating_button.show()

        self._app.setWindowIcon(self._tray_icon.icon())
        self._app.aboutToQuit.connect(self.cleanup)
        self._tray_icon.show()

        if not hotkey_registered:
            warning_message = (
                f"无法注册当前热键 {initial_hotkey.display_text}。\n"
                "你仍可通过悬浮窗或系统托盘进行截图，并可在“设置热键...”中改为其他组合键。"
            )
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
        if self._capture_controller.start_capture():
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
            show_error_dialog("更新开机启动设置失败。")
        finally:
            self._sync_autostart_action()

    def _open_hotkey_dialog(self) -> None:
        dialog = HotkeySettingsDialog(self._hotkey_manager.current_hotkey, self._floating_button)
        if dialog.exec_() != QDialog.Accepted:
            return

        hotkey = dialog.selected_hotkey()
        if self._hotkey_manager.apply_hotkey(hotkey):
            self._settings_manager.save_hotkey(hotkey)
            self._sync_hotkey_action()
            return

        show_error_dialog(f"热键 {hotkey.display_text} 已被其他程序占用，请选择其他组合键。")

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
            self._toggle_button_action.setText("显示悬浮按钮")
        else:
            self._toggle_button_action.setText("隐藏悬浮按钮")

    def _sync_size_actions(self) -> None:
        current_preset = self._floating_button.current_preset
        for preset, action in self._size_actions.items():
            action.blockSignals(True)
            action.setChecked(preset == current_preset)
            action.blockSignals(False)

    def _sync_hotkey_action(self) -> None:
        hotkey = self._hotkey_manager.current_hotkey
        suffix = hotkey.display_text
        if not self._hotkey_manager.is_registered():
            suffix += "（未激活）"
        self._hotkey_action.setText(f"设置热键...  当前：{suffix}")

    def _quit_application(self) -> None:
        self._tray_icon.hide()
        QTimer.singleShot(0, self._app.quit)

    def _build_icon(self) -> QIcon:
        return self._floating_asset.tray_icon()


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
        show_error_dialog(str(exc))
        return 1

    app._tray_app = tray_app
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
