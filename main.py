# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import hashlib
import math
import ntpath
import os
import re
import stat as stat_module
import struct
import sys
import tempfile
import threading
import time
import wave
from datetime import datetime
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QEasingCurve,
    QModelIndex,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSettings,
    QSize,
    Qt,
    QThread,
    QSortFilterProxyModel,
    Signal,
    QAbstractTableModel,
    QPoint,
    QTimer,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "FileTidy 文件净理"
APP_VERSION = "1.2.2"
APPLEDOUBLE_MAGIC = b"\x00\x05\x16\x07"
DS_STORE_MAGIC = b"Bud1"
CFB_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
EXPLORER_CACHE_MAGIC = b"CMMM"
EXPLORER_INDEX_MAGIC = b"IMMM"
FILE_ATTRIBUTE_REPARSE_POINT = getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

# 内联 SVG Path；图标在内存中以 4x 分辨率渲染，不依赖外部图片文件。
ICON_PATHS = {
    "shield": "M12 2 20 5v6c0 5.1-3.4 9.7-8 11-4.6-1.3-8-5.9-8-11V5l8-3zm0 3.1L7 7v4c0 3.7 2.2 7.1 5 8.4 2.8-1.3 5-4.7 5-8.4V7l-5-1.9zm-1 9.5-2.1-2.1-1.4 1.4L11 17.4l5.5-5.5-1.4-1.4-4.1 4.1z",
    "folder": "M10 4H2v16h20V6H12l-2-2zm10 14H4V8h16v10z",
    "plus": "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z",
    "scan": "M4 4h6v2H6v4H4V4zm10 0h6v6h-2V6h-4V4zM4 14h2v4h4v2H4v-6zm14 0h2v6h-6v-2h4v-4zM8 8h8v8H8V8zm2 2v4h4v-4h-4z",
    "trash": "M6 7h12l-1 14H7L6 7zm3-4h6l1 2h4v2H4V5h4l1-2zm0 6 1 10h2L11 9H9zm4 0-1 10h2l1-10h-2z",
    "search": "M10 3a7 7 0 1 0 4.4 12.45L20 21l1-1-5.55-5.6A7 7 0 0 0 10 3zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10z",
    "file": "M6 2h8l5 5v15H6V2zm7 2v4h4l-4-4zM8 11v2h9v-2H8zm0 4v2h9v-2H8z",
    "check": "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z",
    "settings": "M19.4 13a7.8 7.8 0 0 0 0-2l2-1.5-2-3.5-2.3.9a7.5 7.5 0 0 0-1.7-1L15 3h-4l-.4 2.9a7.5 7.5 0 0 0-1.7 1L6.6 6l-2 3.5 2 1.5a7.8 7.8 0 0 0 0 2l-2 1.5 2 3.5 2.3-.9a7.5 7.5 0 0 0 1.7 1L11 21h4l.4-2.9a7.5 7.5 0 0 0 1.7-1l2.3.9 2-3.5-2-1.5zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z",
    "info": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z",
    "close": "M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7l-1.4-1.4L9.2 12 2.9 5.7l1.4-1.4 6.3 6.3 6.3-6.3 1.4 1.4z",
    "export": "M5 20h14v-2H5v2zM12 2 6 8h4v7h4V8h4l-6-6z",
}


def make_icon(name: str, color: str = "#475569", size: int = 18) -> QIcon:
    path = ICON_PATHS.get(name, ICON_PATHS["file"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * 4}" '
        f'height="{size * 4}" viewBox="0 0 24 24">'
        f'<path fill="{color}" d="{path}"/></svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size * 4, size * 4)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(4)
    return QIcon(pixmap)


class AnimatedButton(QPushButton):
    """轻量悬停透明度动画按钮。"""

    def __init__(self, text: str = "", parent: QWidget | None = None, primary: bool = False):
        super().__init__(text, parent)
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)
        self._fade: QPropertyAnimation | None = None
        self.setProperty("primary", primary)

    def _animate_opacity(self, value: float) -> None:
        if self._fade:
            self._fade.stop()
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(200)
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(value)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.start()

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate_opacity(0.82)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate_opacity(1.0)
        super().leaveEvent(event)


class ComboDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):  # noqa: N802 - Qt API
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(34, size.height()))


class AnimatedStack(QWidget):
    """QStackedLayout + 280ms OutCubic 截图推拉转场。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self._animation: QParallelAnimationGroup | None = None

    def addWidget(self, widget: QWidget) -> int:  # noqa: N802 - Qt API style
        return self.stack.addWidget(widget)

    def currentIndex(self) -> int:  # noqa: N802
        return self.stack.currentIndex()

    def setCurrentIndex(self, index: int, direction: int = 1) -> None:  # noqa: N802
        if index == self.stack.currentIndex():
            return
        old = self.stack.currentWidget()
        snapshot = old.grab() if old else QPixmap()
        self.stack.setCurrentIndex(index)
        if snapshot.isNull():
            return
        overlay = QLabel(self)
        overlay.setPixmap(snapshot)
        overlay.setScaledContents(True)
        overlay.setGeometry(self.rect())
        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(1.0)
        overlay.setGraphicsEffect(effect)
        overlay.raise_()

        slide = QPropertyAnimation(overlay, b"pos")
        slide.setDuration(280)
        slide.setStartValue(overlay.pos())
        slide.setEndValue(overlay.pos() + QPoint(-48 * direction, 0))
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(280)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(slide)
        group.addAnimation(fade)
        group.finished.connect(overlay.deleteLater)
        group.finished.connect(lambda: setattr(self, "_animation", None))
        self._animation = group
        group.start()


def is_reparse_point(st: os.stat_result) -> bool:
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def path_is_within_root(path: str, root: str, path_module=None) -> bool:
    r"""判断 path 是否处于 root 目录下，兼容 Windows 盘符和 UNC/SMB 共享根。

    Windows 对裸 UNC 共享根（\\server\share）有一个特殊行为：
    abspath() 可能保留为没有尾部反斜杠的形式，splitdrive() 会把整个
    共享名识别为 drive、tail 为空；commonpath() 随后可能把该根目录
    当作相对路径，从而误拦截共享内的全部文件。这里将共享根规范化为
    `\\server\share\` 后再做 commonpath，仍严格检查路径边界。
    path_module 参数仅用于跨平台单元测试；正常运行时自动使用 os.path。
    """
    path_module = path_module or os.path
    try:
        def canonical(value: str) -> str:
            absolute = path_module.normpath(path_module.abspath(value))
            drive, tail = path_module.splitdrive(absolute)
            if path_module is ntpath and drive.startswith("\\\\") and not tail:
                absolute = drive + path_module.sep
            return absolute

        path_abs = canonical(path)
        root_abs = canonical(root)
        common = path_module.commonpath([path_abs, root_abs])
        return path_module.normcase(path_module.normpath(common)) == path_module.normcase(
            path_module.normpath(root_abs)
        )
    except (ValueError, OSError):
        return False


PROTECTED_DIR_NAMES = {
    "@eadir",                       # Synology thumbnail / metadata store
    "#recycle",                    # Synology recycle bin
    "$recycle.bin",                # Windows recycle bin
    "system volume information",   # Windows volume metadata
    "lost+found",                  # Linux filesystem recovery directory
    ".trash", ".trashes",         # macOS / Unix trash
    ".spotlight-v100",             # macOS search index
    ".fseventsd",                  # macOS filesystem event database
    ".temporaryitems",             # macOS temporary item store
}


def is_protected_directory(name: str) -> bool:
    folded = name.casefold()
    return folded in PROTECTED_DIR_NAMES or folded.startswith(".trash-")


def _path_contains_protected_directory(path: str, include_leaf: bool = False) -> bool:
    """按路径组件识别保护目录；不使用字符串前缀，兼容盘符和 UNC。"""
    absolute = os.path.normpath(os.path.abspath(path))
    parts = re.split(r"[\\/]", absolute)
    directory_parts = parts if include_leaf else parts[:-1]
    return any(is_protected_directory(part) for part in directory_parts)


def path_has_protected_directory(path: str, root: str) -> bool:
    """候选文件或其扫描根路径位于保护目录内时，拒绝删除。"""
    try:
        if not path_is_within_root(path, root):
            return True
        return _path_contains_protected_directory(path, include_leaf=False) or _path_contains_protected_directory(
            root, include_leaf=True
        )
    except (ValueError, OSError):
        # 无法可靠解析路径时按保护原则拒绝删除。
        return True


def validate_parent_chain(path: str, root: str) -> tuple[bool, str]:
    """删除前逐级复核扫描根目录及父目录，防止目录被替换成符号链接/重解析点。"""
    if not path_is_within_root(path, root):
        return False, "路径不在原扫描目录内"
    try:
        root_abs = os.path.abspath(root)
        root_stat = os.stat(root_abs, follow_symlinks=False)
        if os.path.islink(root_abs) or is_reparse_point(root_stat) or not stat_module.S_ISDIR(root_stat.st_mode):
            return False, "原扫描根目录已变为链接、重解析点或非目录"
        relative = os.path.relpath(path, root_abs)
        parts = [part for part in re.split(r"[\\/]", relative) if part not in ("", ".")]
        current = root_abs
        for part in parts[:-1]:
            current = os.path.join(current, part)
            parent_stat = os.stat(current, follow_symlinks=False)
            if os.path.islink(current) or is_reparse_point(parent_stat) or not stat_module.S_ISDIR(parent_stat.st_mode):
                return False, f"父目录已变为链接/重解析点或不再是目录：{current}"
        return True, "父目录链复核通过"
    except OSError as exc:
        return False, f"无法复核扫描根目录或父目录：{exc}"


def read_header(path: str, length: int = 8) -> bytes | None:
    try:
        with open(path, "rb") as stream:
            return stream.read(length)
    except OSError:
        return None


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str | None:
    """计算文件完整 SHA-256；用于跨 SMB 环境可靠复核内容，不依赖 inode/时间戳精度。"""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as stream:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def candidate_for(
    path: str,
    st: os.stat_result,
    include_windows_cache: bool = False,
    include_explorer_cache: bool = False,
    include_android_cache: bool = False,
) -> tuple[str, str, bool] | None:
    """返回 (规则名, 检测依据, 是否高置信度)；不匹配返回 None。

    只按精确文件名模式 + 文件格式标记识别缓存，不使用宽泛扩展名规则。
    """
    name = os.path.basename(path)
    folded = name.casefold()

    if folded == ".ds_store":
        header = read_header(path, 4)
        if header == DS_STORE_MAGIC:
            return ("macOS .DS_Store", "文件名匹配，且文件头为 Bud1（Finder Store）", True)
        return None

    if name.startswith("._") and len(name) > 2:
        header = read_header(path, 4)
        companion = os.path.join(os.path.dirname(path), name[2:])
        try:
            companion_exists = os.path.lexists(companion)
        except OSError:
            companion_exists = False
        if header == APPLEDOUBLE_MAGIC and companion_exists:
            return ("macOS AppleDouble", "._ 前缀 + AppleDouble 文件头 + 对应原文件存在", True)
        return None

    if include_windows_cache and folded in ("thumbs.db", "ehthumbs.db"):
        header = read_header(path, 8)
        if header == CFB_MAGIC:
            label = "Windows 缩略图缓存" if folded == "thumbs.db" else "Windows 媒体缩略图缓存"
            return (label, "文件名匹配，且文件头为 Compound File Binary", True)

    if include_android_cache:
        # Android Gallery 缩略图索引文件：只接受 .thumbnails 目录中的精确 THUMBDATA 命名。
        parent_name = os.path.basename(os.path.dirname(path)).casefold()
        if parent_name == ".thumbnails" and re.fullmatch(r"\.?thumbdata\d+--?\d+", folded):
            return (
                "Android Gallery THUMBDATA 缓存",
                "位于 .thumbnails 目录，且文件名符合 .thumbdataN-数字 / .thumbdataN--数字 格式",
                True,
            )

    if include_explorer_cache:
        # Vista 至 Windows 11 的 Explorer 缩略图/图标数据库。
        # 数据库为 CMMM；索引数据库为 IMMM（不同版本签名可能位于偏移 0 或 4）。
        match = re.fullmatch(
            r"(thumbcache|iconcache)_(?:\d+|sr|wide|exif|wide_alternate|custom_stream|idx)\.db",
            folded,
        )
        if match:
            family = match.group(1)
            is_index = folded.endswith("_idx.db")
            header = read_header(path, 8) or b""
            if is_index and (header[:4] == EXPLORER_INDEX_MAGIC or header[4:8] == EXPLORER_INDEX_MAGIC):
                label = "Windows Explorer 缩略图索引缓存" if family == "thumbcache" else "Windows Explorer 图标索引缓存"
                return (label, "精确数据库名称匹配，且索引文件头含 IMMM 标记", True)
            if not is_index and header[:4] == EXPLORER_CACHE_MAGIC:
                label = "Windows Explorer 缩略图缓存" if family == "thumbcache" else "Windows Explorer 图标缓存"
                return (label, "精确数据库名称匹配，且数据库文件头为 CMMM 标记", True)

    return None


@dataclass
class FileRecord:
    path: str
    root: str
    name: str
    rule: str
    size: int
    mtime_ns: int
    st_dev: int
    st_ino: int
    sha256: str
    reason: str
    eligible: bool
    selected: bool = True
    state: str = "待清理"

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "root": self.root,
            "name": self.name,
            "rule": self.rule,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
            "st_dev": self.st_dev,
            "st_ino": self.st_ino,
            "sha256": self.sha256,
            "reason": self.reason,
            "eligible": self.eligible,
            "selected": self.selected,
            "state": self.state,
        }


class ScanWorker(QThread):
    """后台扫描；每批发现结果立即发给 UI，而不是等整个目录扫描结束。"""

    progress = Signal(int, int, str)
    batch = Signal(object)
    completed = Signal(object)

    def __init__(self, roots: list[str], enabled_rules: set[str]):
        super().__init__()
        self.roots = roots
        self.enabled_rules = enabled_rules
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        scanned = 0
        found = 0
        errors: list[str] = []
        skipped_reparse = 0
        skipped_protected = 0
        protected_paths: list[str] = []
        uncertain_count = 0
        uncertain_paths: list[str] = []
        started = time.monotonic()
        last_emit = started
        last_batch = started
        pending: list[dict[str, Any]] = []
        seen_roots: set[str] = set()
        seen_files: set[str] = set()

        for root in self.roots:
            if self.cancel_event.is_set():
                break
            root_abs = os.path.abspath(root)
            if _path_contains_protected_directory(root_abs, include_leaf=True):
                skipped_protected += 1
                if len(protected_paths) < 300:
                    protected_paths.append(root_abs)
                continue
            root_key = os.path.normcase(root_abs)
            if root_key in seen_roots:
                continue
            seen_roots.add(root_key)
            if not os.path.isdir(root_abs):
                errors.append(f"目录不可访问：{root_abs}")
                continue
            try:
                root_stat = os.stat(root_abs, follow_symlinks=False)
                if os.path.islink(root_abs) or is_reparse_point(root_stat):
                    errors.append(f"扫描根目录是链接/重解析点，已跳过：{root_abs}")
                    continue
            except OSError as exc:
                errors.append(f"无法读取扫描根目录：{root_abs}（{exc}）")
                continue

            stack = [root_abs]
            visited_dirs: set[str] = set()
            while stack and not self.cancel_event.is_set():
                current = stack.pop()
                key = os.path.normcase(os.path.abspath(current))
                if key in visited_dirs:
                    continue
                visited_dirs.add(key)
                try:
                    with os.scandir(current) as iterator:
                        for entry in iterator:
                            if self.cancel_event.is_set():
                                break
                            scanned += 1
                            try:
                                entry_stat = entry.stat(follow_symlinks=False)
                                if entry.is_symlink() or is_reparse_point(entry_stat):
                                    skipped_reparse += 1
                                    continue
                                if entry.is_dir(follow_symlinks=False):
                                    if is_protected_directory(entry.name):
                                        skipped_protected += 1
                                        if len(protected_paths) < 300:
                                            protected_paths.append(entry.path)
                                        continue
                                    stack.append(entry.path)
                                    continue
                                if not entry.is_file(follow_symlinks=False):
                                    continue

                                match = candidate_for(
                                    entry.path,
                                    entry_stat,
                                    include_windows_cache=("windows_cache" in self.enabled_rules),
                                    include_explorer_cache=("explorer_cache" in self.enabled_rules),
                                    include_android_cache=("android_cache" in self.enabled_rules),
                                )
                                if not match:
                                    if (entry.name.casefold() == ".ds_store" and "ds_store" in self.enabled_rules) or (
                                        entry.name.startswith("._") and "appledouble" in self.enabled_rules
                                    ):
                                        uncertain_count += 1
                                        if len(uncertain_paths) < 300:
                                            uncertain_paths.append(entry.path)
                                    continue

                                rule, reason, eligible = match
                                rule_key = {
                                    "macOS .DS_Store": "ds_store",
                                    "macOS AppleDouble": "appledouble",
                                    "Windows 缩略图缓存": "windows_cache",
                                    "Windows 媒体缩略图缓存": "windows_cache",
                                    "Windows Explorer 缩略图缓存": "explorer_cache",
                                    "Windows Explorer 图标缓存": "explorer_cache",
                                    "Windows Explorer 缩略图索引缓存": "explorer_cache",
                                    "Windows Explorer 图标索引缓存": "explorer_cache",
                                    "Android Gallery THUMBDATA 缓存": "android_cache",
                                }.get(rule)
                                if rule_key not in self.enabled_rules:
                                    continue

                                path_key = os.path.normcase(os.path.abspath(entry.path))
                                if path_key in seen_files:
                                    continue
                                seen_files.add(path_key)

                                # 用直接 stat 的前后快照包围哈希读取，避免使用 scandir 缓存的元数据。
                                before = os.stat(entry.path, follow_symlinks=False)
                                if os.path.islink(entry.path) or is_reparse_point(before) or not stat_module.S_ISREG(before.st_mode):
                                    skipped_reparse += 1
                                    continue
                                fingerprint = sha256_file(entry.path)
                                if fingerprint is None:
                                    uncertain_count += 1
                                    errors.append(f"候选文件无法读取并计算 SHA-256，已跳过：{entry.path}")
                                    continue
                                after = os.stat(entry.path, follow_symlinks=False)
                                before_mtime = getattr(before, "st_mtime_ns", int(before.st_mtime * 1e9))
                                after_mtime = getattr(after, "st_mtime_ns", int(after.st_mtime * 1e9))
                                if before.st_size != after.st_size or before_mtime != after_mtime:
                                    uncertain_count += 1
                                    errors.append(f"扫描期间文件发生变化，已跳过：{entry.path}")
                                    continue

                                record = FileRecord(
                                    path=os.path.abspath(entry.path),
                                    root=root_abs,
                                    name=entry.name,
                                    rule=rule,
                                    size=after.st_size,
                                    mtime_ns=after_mtime,
                                    st_dev=getattr(after, "st_dev", 0),
                                    st_ino=getattr(after, "st_ino", 0),
                                    sha256=fingerprint,
                                    reason=reason + "；已生成 SHA-256 内容指纹",
                                    eligible=eligible,
                                    selected=eligible,
                                    state="待清理" if eligible else "需人工核查",
                                ).as_dict()
                                pending.append(record)
                                found += 1

                                now = time.monotonic()
                                if len(pending) >= 24 or now - last_batch >= 0.18:
                                    self.batch.emit(pending)
                                    pending = []
                                    last_batch = now
                            except OSError as exc:
                                errors.append(f"无法读取：{entry.path}（{exc}）")
                            now = time.monotonic()
                            if now - last_emit >= 0.10:
                                self.progress.emit(scanned, found, entry.path)
                                last_emit = now
                except OSError as exc:
                    errors.append(f"无法遍历目录：{current}（{exc}）")

        if pending:
            self.batch.emit(pending)

        elapsed = time.monotonic() - started
        summary = {
            "scanned": scanned,
            "found": found,
            "errors": errors,
            "skipped_reparse": skipped_reparse,
            "skipped_protected": skipped_protected,
            "protected_paths": protected_paths,
            "uncertain_count": uncertain_count,
            "uncertain_paths": uncertain_paths,
            "elapsed": elapsed,
            "cancelled": self.cancel_event.is_set(),
        }
        self.progress.emit(scanned, found, "扫描结束")
        self.completed.emit(summary)


class DeleteWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    completed = Signal(object)

    def __init__(self, records: list[dict[str, Any]]):
        super().__init__()
        self.records = records
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    @staticmethod
    def _inside_root(path: str, root: str) -> bool:
        return path_is_within_root(path, root)

    def _revalidate(self, record: dict[str, Any]) -> tuple[bool, str]:
        """删除前复核内容哈希；不再把 SMB 不稳定的 inode/纳秒时间戳当成唯一依据。"""
        path = record["path"]
        root = record["root"]
        if not self._inside_root(path, root):
            return False, "路径不在原扫描目录内，已拦截"
        if path_has_protected_directory(path, root):
            return False, "文件位于受保护的系统目录/回收站内，已拦截"
        parents_ok, parents_reason = validate_parent_chain(path, root)
        if not parents_ok:
            return False, parents_reason + "；已拦截"
        try:
            before = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            return False, f"文件无法访问：{exc}"
        if os.path.islink(path) or is_reparse_point(before) or not stat_module.S_ISREG(before.st_mode):
            return False, "文件类型已变化或属于链接/重解析点，已拦截"
        if before.st_size != record["size"]:
            return False, "文件大小与扫描时不同，可能已被替换或修改；已保护"

        fingerprint = sha256_file(path)
        if fingerprint is None:
            return False, "无法重新读取文件内容（可能是 SMB 权限或连接问题）；已保护"
        try:
            after = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            return False, f"复核后文件无法访问：{exc}"
        if after.st_size != before.st_size:
            return False, "复核期间文件大小发生变化；已保护"
        before_mtime = getattr(before, "st_mtime_ns", int(before.st_mtime * 1e9))
        after_mtime = getattr(after, "st_mtime_ns", int(after.st_mtime * 1e9))
        if before_mtime != after_mtime:
            return False, "复核期间文件被修改；已保护"
        if fingerprint != record.get("sha256"):
            return False, "SHA-256 内容指纹与扫描时不同，文件可能已被替换或修改；已保护"

        match = candidate_for(
            path, after, include_windows_cache=True, include_explorer_cache=True, include_android_cache=True
        )
        if not match:
            return False, "删除前文件特征复核未通过；已保护"
        if match[0] != record["rule"]:
            return False, "删除前复核发现文件类型与扫描记录不一致；已保护"
        return True, "内容指纹及文件特征复核通过"

    def run(self) -> None:
        results: list[dict[str, Any]] = []
        total = len(self.records)
        last_progress_emit = time.monotonic()
        for index, record in enumerate(self.records, start=1):
            if self.cancel_event.is_set():
                results.append({"path": record["path"], "status": "已取消", "message": "用户取消，未处理"})
                continue
            ok, reason = self._revalidate(record)
            if not ok:
                results.append({"path": record["path"], "status": "已拦截", "message": reason})
                self.log.emit(f"已拦截：{record['path']} | {reason}")
            else:
                try:
                    os.remove(record["path"])
                    results.append({"path": record["path"], "status": "已删除", "message": "删除成功；SHA-256 复核通过"})
                    self.log.emit(f"已删除：{record['path']}")
                except OSError as exc:
                    results.append({"path": record["path"], "status": "删除失败", "message": f"{exc}（检查共享文件夹写入/删除权限或文件占用）"})
                    self.log.emit(f"删除失败：{record['path']} | {exc}")
            now = time.monotonic()
            if now - last_progress_emit >= 0.1 or index == total:
                self.progress.emit(index, total, record["path"])
                last_progress_emit = now
        self.completed.emit(results)


class ResultsModel(QAbstractTableModel):
    selectionChanged = Signal()
    HEADERS = ["选择", "状态", "文件类型", "文件名", "大小", "完整路径", "识别依据 / 复核信息"]
    SELECTABLE_STATES = {"待清理", "删除失败", "已取消"}

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.rows: list[dict[str, Any]] = []

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if row.get("selected") else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            values = [
                "",
                row.get("state", "待清理"),
                row.get("rule", ""),
                row.get("name", ""),
                format_size(row.get("size", 0)),
                row.get("path", ""),
                row.get("reason", ""),
            ]
            return values[col]
        if role == Qt.ItemDataRole.ToolTipRole:
            if col == 3:
                return row.get("name", "")
            if col == 5:
                return row.get("path", "")
            if col == 6:
                return row.get("reason", "")
            return None
        if role == Qt.ItemDataRole.ForegroundRole and col == 1:
            state = row.get("state", "")
            if state == "已删除":
                return QColor("#16A34A")
            if state in ("删除失败", "已拦截"):
                return QColor("#DC2626")
            if state == "需人工核查":
                return QColor("#D97706")
            return QColor("#2563EB")
        if role == Qt.ItemDataRole.FontRole and col in (3, 5):
            font = QFont("Consolas" if col == 5 else "Segoe UI")
            return font
        if role == Qt.ItemDataRole.BackgroundRole and index.row() % 2 == 1:
            return QColor("#FAFBFC")
        return None

    def flags(self, index: QModelIndex):
        base = super().flags(index)
        if index.isValid() and index.column() == 0:
            row = self.rows[index.row()]
            if row.get("eligible") and row.get("state") in self.SELECTABLE_STATES:
                return base | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            return base & ~Qt.ItemFlag.ItemIsEnabled
        return base | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):  # noqa: N802
        if index.isValid() and index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole:
            row = self.rows[index.row()]
            if not row.get("eligible") or row.get("state") not in self.SELECTABLE_STATES:
                return False
            checked = value == Qt.CheckState.Checked or value == Qt.CheckState.Checked.value
            row["selected"] = checked
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            self.selectionChanged.emit()
            return True
        return False

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()
        self.selectionChanged.emit()

    def append_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        first = len(self.rows)
        last = first + len(rows) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self.rows.extend(rows)
        self.endInsertRows()
        self.selectionChanged.emit()

    def selected_records(self) -> list[dict[str, Any]]:
        return [
            row.copy() for row in self.rows
            if row.get("selected") and row.get("eligible") and row.get("state") in self.SELECTABLE_STATES
        ]

    def select_all_eligible(self, checked: bool) -> None:
        changed = False
        for row in self.rows:
            if row.get("eligible") and row.get("state") in self.SELECTABLE_STATES:
                if row.get("selected") != checked:
                    row["selected"] = checked
                    changed = True
        if changed and self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, 0), [Qt.ItemDataRole.CheckStateRole])
        self.selectionChanged.emit()

    def apply_delete_results(self, results: list[dict[str, Any]]) -> None:
        by_path = {item["path"]: item for item in results}
        for row in self.rows:
            result = by_path.get(row["path"])
            if not result:
                continue
            row["state"] = result["status"]
            row["reason"] = result["message"]
            row["selected"] = False
            if result["status"] in ("已删除", "已拦截"):
                row["eligible"] = False
            elif result["status"] in ("删除失败", "已取消"):
                # 失败或取消的候选仍可重新勾选；用户修复权限/网络后可以重试。
                row["eligible"] = True
        if self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, len(self.HEADERS) - 1))
        self.selectionChanged.emit()


class CheckBoxDelegate(QStyledItemDelegate):
    """显式绘制居中复选框，避免不同 Fusion/高 DPI 环境下勾选标记不明显。"""

    def paint(self, painter, option, index):  # noqa: N802 - Qt API
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter)
        button = QStyleOptionButton()
        size = 18
        button.rect = option.rect.adjusted(
            (option.rect.width() - size) // 2,
            (option.rect.height() - size) // 2,
            -((option.rect.width() - size) // 2),
            -((option.rect.height() - size) // 2),
        )
        if index.flags() & Qt.ItemFlag.ItemIsEnabled:
            button.state |= QStyle.StateFlag.State_Enabled
        if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
            button.state |= QStyle.StateFlag.State_On
        else:
            button.state |= QStyle.StateFlag.State_Off
        painter.save()
        style.drawControl(QStyle.ControlElement.CE_CheckBox, button, painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):  # noqa: N802 - Qt API
        if not (index.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return False
        toggle = False
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            toggle = True
        elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Space:
            toggle = True
        if not toggle:
            return False
        current = index.data(Qt.ItemDataRole.CheckStateRole)
        new_value = Qt.CheckState.Unchecked if current == Qt.CheckState.Checked else Qt.CheckState.Checked
        return model.setData(index, new_value, Qt.ItemDataRole.CheckStateRole)


class ResultsProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "全部结果"
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if model is None or source_row >= len(model.rows):
            return True
        row = model.rows[source_row]
        if self.mode == "仅看已勾选" and not row.get("selected"):
            return False
        if self.mode == "仅看待清理" and row.get("state") != "待清理":
            return False
        if self.mode == "仅看可重试" and row.get("state") not in ("删除失败", "已取消"):
            return False
        if self.mode == "仅看已删除" and row.get("state") != "已删除":
            return False
        if self.mode == "仅看异常" and row.get("state") not in ("删除失败", "已拦截"):
            return False
        return super().filterAcceptsRow(source_row, source_parent)


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def play_synthesized_feedback(success: bool) -> None:
    """可选的短提示音；用 wave 标准库合成，Windows 使用 winsound 异步播放。"""
    if os.name != "nt":
        return
    try:
        import winsound

        sample_rate = 22050
        notes = (523.25, 659.25, 783.99) if success else (220.0, 164.81)
        samples = bytearray()
        note_seconds = 0.095 if success else 0.16
        for frequency in notes:
            count = int(sample_rate * note_seconds)
            for i in range(count):
                t = i / sample_rate
                attack = min(1.0, i / max(1, int(sample_rate * 0.008)))
                release = max(0.0, 1.0 - i / count)
                envelope = attack * (release ** 1.2)
                value = int(4200 * envelope * math.sin(2.0 * math.pi * frequency * t))
                samples.extend(struct.pack("<h", value))
        sound_path = os.path.join(tempfile.gettempdir(), "nas_junk_cleaner_feedback.wav")
        with wave.open(sound_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(samples))
        winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        # 音效仅作辅助反馈，播放失败不影响文件检查或删除结果。
        return


def card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if title:
        label = QLabel(title)
        label.setObjectName("CardTitle")
        layout.addWidget(label)
    return frame, layout


def make_pill(text: str, variant: str = "blue") -> QLabel:
    label = QLabel(text)
    label.setObjectName(f"Pill_{variant}")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setContentsMargins(9, 3, 9, 3)
    return label


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Qwejay", "NASJunkCleaner")
        self.scan_worker: ScanWorker | None = None
        self.delete_worker: DeleteWorker | None = None
        self.model = ResultsModel(self)
        self.proxy = ResultsProxy(self)
        self.proxy.setSourceModel(self.model)
        self._log_lines = 0
        self._pending_logs: list[str] = []
        self._busy = False
        self._scanning = False
        self._build_ui()
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(100)
        self._log_timer.timeout.connect(self._flush_queued_logs)
        self._log_timer.start()
        self._apply_style()
        self._restore_settings()
        self.model.selectionChanged.connect(self.proxy.invalidateFilter)
        self.model.selectionChanged.connect(self._update_selection_summary)
        self._update_selection_summary()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"{APP_NAME} · {APP_VERSION}")
        self.setMinimumSize(1040, 700)
        self.resize(1280, 820)
        self.setWindowIcon(make_icon("shield", "#2563EB", 32))

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 18, 22, 16)
        root_layout.setSpacing(14)

        header = QHBoxLayout()
        identity = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(make_icon("shield", "#2563EB", 30).pixmap(30, 30))
        identity.addWidget(mark)
        titles = QVBoxLayout()
        app_title = QLabel("FileTidy 文件净理")
        app_title.setObjectName("AppTitle")
        subtitle = QLabel("保守识别系统元数据 · 先预览，再删除")
        subtitle.setObjectName("Muted")
        titles.addWidget(app_title)
        titles.addWidget(subtitle)
        identity.addLayout(titles)
        header.addLayout(identity)
        header.addStretch(1)
        self.nav_work = AnimatedButton("清理工作台")
        self.nav_work.setIcon(make_icon("folder", "#2563EB"))
        self.nav_rules = AnimatedButton("安全规则")
        self.nav_rules.setIcon(make_icon("shield", "#64748B"))
        self.nav_work.clicked.connect(lambda: self._switch_page(0))
        self.nav_rules.clicked.connect(lambda: self._switch_page(1))
        header.addWidget(self.nav_work)
        header.addWidget(self.nav_rules)
        root_layout.addLayout(header)

        self.alert = QLabel("安全模式已启用：扫描仅预览；通过严格验证的候选项会默认勾选，您可以逐项取消。")
        self.alert.setObjectName("InfoBanner")
        self.alert.setWordWrap(True)
        root_layout.addWidget(self.alert)

        self.pages = AnimatedStack()
        self.pages.addWidget(self._build_workspace())
        self.pages.addWidget(self._build_rules_page())
        root_layout.addWidget(self.pages, 1)

        # 日志默认折叠，按需查看。
        log_header = QHBoxLayout()
        self.log_toggle = QPushButton("显示运行日志  ▸")
        self.log_toggle.setObjectName("TextButton")
        self.log_toggle.clicked.connect(self._toggle_logs)
        log_header.addWidget(self.log_toggle)
        log_header.addStretch(1)
        self.log_count_label = QLabel("0 条记录")
        self.log_count_label.setObjectName("MutedSmall")
        log_header.addWidget(self.log_count_label)
        root_layout.addLayout(log_header)

        self.log_panel = QFrame()
        self.log_panel.setObjectName("LogPanel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(10, 8, 10, 8)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(3000)
        self.log_view.setMinimumHeight(110)
        log_layout.addWidget(self.log_view)
        self.log_panel.setVisible(False)
        root_layout.addWidget(self.log_panel)

        self.setCentralWidget(root)
        self.statusBar().showMessage("就绪")

    def _build_workspace(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(12)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧：紧凑工作区，不使用侧栏滚动条；说明文字统一放入悬停提示。
        left = QWidget()
        left.setMinimumWidth(280)
        left.setMaximumWidth(370)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(7)

        left_content = QWidget()
        left_content.setMinimumWidth(0)
        left_content_layout = QVBoxLayout(left_content)
        left_content_layout.setContentsMargins(0, 0, 0, 0)
        left_content_layout.setSpacing(7)
        left_layout.addWidget(left_content, 1)

        path_card, path_layout = card("扫描目录")
        path_layout.setContentsMargins(12, 10, 12, 10)
        path_layout.setSpacing(6)
        self.path_input = QLineEdit()
        self.path_input.setToolTip(
            "输入 SMB / UNC / 本地目录路径，无需映射网络盘。每次添加一个目录。\n"
            + r"例如：\\192.168.0.152\共享文件夹 或 Z:\资料"
        )
        self.path_input.setPlaceholderText(r'例如：\\192.168.0.152\files 或 Z:\资料')
        self.path_input.returnPressed.connect(self._add_root)
        path_layout.addWidget(self.path_input)
        path_actions = QHBoxLayout()
        self.add_path_btn = AnimatedButton("添加目录")
        self.add_path_btn.setIcon(make_icon("plus", "#FFFFFF"))
        self.add_path_btn.setProperty("primary", True)
        self.add_path_btn.clicked.connect(self._add_root)
        self.browse_btn = AnimatedButton("浏览…")
        self.browse_btn.setIcon(make_icon("folder", "#475569"))
        self.browse_btn.clicked.connect(self._browse_root)
        path_actions.addWidget(self.add_path_btn, 1)
        path_actions.addWidget(self.browse_btn)
        path_layout.addLayout(path_actions)
        self.root_list = QListWidget()
        self.root_list.setMinimumHeight(62)
        self.root_list.setMaximumHeight(86)
        self.root_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.root_list.setToolTip("已添加的扫描目录。可多选后移除；项目较多时可在列表内使用鼠标滚轮浏览。")
        self.root_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        path_layout.addWidget(self.root_list)
        remove_root_row = QHBoxLayout()
        self.remove_root_btn = QPushButton("移除选中目录")
        self.remove_root_btn.setObjectName("TextButton")
        self.remove_root_btn.clicked.connect(self._remove_roots)
        remove_root_row.addWidget(self.remove_root_btn)
        remove_root_row.addStretch(1)
        path_layout.addLayout(remove_root_row)
        left_content_layout.addWidget(path_card)

        rules_card, rules_layout = card("识别规则")
        rules_layout.setContentsMargins(12, 10, 12, 9)
        rules_layout.setSpacing(4)

        def add_rule_option(checkbox: QCheckBox, description: str) -> None:
            # 说明不进入布局；鼠标悬停复选框时才显示，避免占用侧栏高度。
            checkbox.setMinimumHeight(25)
            checkbox.setToolTip(description)
            checkbox.setToolTipDuration(15000)
            rules_layout.addWidget(checkbox)

        self.ds_checkbox = QCheckBox("macOS .DS_Store 文件")
        self.ds_checkbox.setChecked(True)
        self.ds_checkbox.setToolTip("仅当文件头为 Bud1 时才会列为可清理候选")
        add_rule_option(self.ds_checkbox, "仅接受前 4 字节为 Bud1 的 Finder 元数据；普通同名文件自动跳过。")

        self.apple_checkbox = QCheckBox("AppleDouble ._ 元数据文件")
        self.apple_checkbox.setChecked(True)
        self.apple_checkbox.setToolTip("必须同时验证 AppleDouble 文件头及对应原文件存在")
        add_rule_option(self.apple_checkbox, "必须通过 AppleDouble 文件头验证，并且同目录存在对应原文件。删除会丢失该文件携带的 macOS 扩展属性/资源分叉。")

        self.windows_cache_checkbox = QCheckBox("Windows 旧式缩略图缓存")
        self.windows_cache_checkbox.setChecked(False)
        self.windows_cache_checkbox.setToolTip("旧式 Windows 文件夹缩略图缓存；默认关闭，需验证 Compound File Binary 文件头")
        add_rule_option(self.windows_cache_checkbox, "默认关闭。仅文件名精确匹配，且文件头符合 Compound File Binary（OLE）格式时列为候选。")

        self.explorer_cache_checkbox = QCheckBox("Windows Explorer 缩略图/图标缓存")
        self.explorer_cache_checkbox.setChecked(False)
        self.explorer_cache_checkbox.setToolTip("新版 Windows 缩略图/图标缓存；默认关闭，需精确文件名及 CMMM / IMMM 文件头双重匹配")
        add_rule_option(self.explorer_cache_checkbox, "默认关闭。要求精确数据库名称及 CMMM / IMMM 文件头双重匹配；Windows 可能在以后重新生成缓存。")

        self.android_cache_checkbox = QCheckBox("Android THUMBDATA 索引缓存")
        self.android_cache_checkbox.setChecked(False)
        self.android_cache_checkbox.setToolTip("默认关闭；只识别 .thumbnails 目录内符合 THUMBDATA 命名的索引文件，不扫描其中的图片")
        add_rule_option(self.android_cache_checkbox, "默认关闭。只识别 .thumbnails 目录中的 THUMBDATA 索引，不删除目录里的 JPG/PNG 图片；索引可能保留已删除照片的低清预览。")

        separator = QFrame()
        separator.setObjectName("RuleDivider")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        rules_layout.addWidget(separator)

        self.sound_checkbox = QCheckBox("启用完成 / 拦截提示音")
        self.sound_checkbox.setChecked(False)
        self.sound_checkbox.setMinimumHeight(25)
        self.sound_checkbox.setToolTip("声音提示默认关闭。此选项只控制任务完成/拦截时的声音，不改变任何文件识别或删除行为。")
        self.sound_checkbox.setToolTipDuration(15000)
        rules_layout.addWidget(self.sound_checkbox)

        safety_row = QHBoxLayout()
        safety_row.addStretch(1)
        safety_hint = QLabel("安全说明  ⓘ")
        safety_hint.setObjectName("HoverHint")
        safety_hint.setCursor(Qt.CursorShape.WhatsThisCursor)
        safety_hint.setToolTip(
            "安全策略\n"
            "• 不按 .tmp、.log、.bak 等宽泛扩展名清理。\n"
            "• @eaDir、回收站及系统索引目录会整体跳过。\n"
            "• 不删除 desktop.ini、Office 锁文件、普通隐藏文件或整个目录。\n"
            "• 删除 AppleDouble ._ 文件会丢失其中的 macOS 扩展属性/资源分叉元数据。\n"
            "• 扫描只预览；删除前重新验证路径、文件特征和 SHA-256 内容。"
        )
        safety_hint.setToolTipDuration(20000)
        safety_row.addWidget(safety_hint)
        rules_layout.addLayout(safety_row)
        left_content_layout.addWidget(rules_card)
        left_content_layout.addStretch(1)

        self.scan_btn = AnimatedButton("开始扫描", primary=True)
        self.scan_btn.setIcon(make_icon("scan", "#FFFFFF", 18))
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.clicked.connect(self._start_scan)
        self.cancel_btn = AnimatedButton("取消当前任务")
        self.cancel_btn.setIcon(make_icon("close", "#DC2626"))
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_task)
        left_layout.addWidget(self.scan_btn)
        left_layout.addWidget(self.cancel_btn)

        # 右侧：结果工作区。
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        summary_row = QHBoxLayout()
        summary_row.setSpacing(8)
        self.scanned_stat = self._stat_card("已扫描项目", "0")
        self.found_stat = self._stat_card("候选文件", "0")
        self.selected_stat = self._stat_card("已勾选", "0")
        summary_row.addWidget(self.scanned_stat[0])
        summary_row.addWidget(self.found_stat[0])
        summary_row.addWidget(self.selected_stat[0])
        right_layout.addLayout(summary_row)

        results_card, results_layout = card("检测结果")
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文件名或路径…")
        self.search_input.addAction(make_icon("search", "#94A3B8"), QLineEdit.ActionPosition.LeadingPosition)
        self.search_input.textChanged.connect(self.proxy.setFilterFixedString)
        toolbar.addWidget(self.search_input, 1)
        self.filter_combo = QComboBox()
        self.filter_combo.setView(QListView())
        self.filter_combo.setItemDelegate(ComboDelegate(self.filter_combo))
        self.filter_combo.addItems(["全部结果", "仅看待清理", "仅看已勾选", "仅看可重试", "仅看已删除", "仅看异常"])
        self.filter_combo.currentTextChanged.connect(self.proxy.set_mode)
        self.filter_combo.setMinimumWidth(132)
        toolbar.addWidget(self.filter_combo)
        results_layout.addLayout(toolbar)

        selection_row = QHBoxLayout()
        self.select_safe_btn = QPushButton("全选可清理项目")
        self.select_safe_btn.setObjectName("TextButtonBlue")
        self.select_safe_btn.clicked.connect(lambda: self.model.select_all_eligible(True))
        self.clear_selection_btn = QPushButton("清空勾选")
        self.clear_selection_btn.setObjectName("TextButton")
        self.clear_selection_btn.clicked.connect(lambda: self.model.select_all_eligible(False))
        selection_row.addWidget(self.select_safe_btn)
        selection_row.addWidget(self.clear_selection_btn)
        selection_row.addStretch(1)
        self.result_count = QLabel("扫描结果将在此实时显示")
        self.result_count.setObjectName("MutedSmall")
        selection_row.addWidget(self.result_count)
        results_layout.addLayout(selection_row)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # 默认不启用动态排序：扫描批次追加时保持行位置稳定，复选框不会因排序跳行。
        self.table.setSortingEnabled(False)
        self.table.setItemDelegateForColumn(0, CheckBoxDelegate(self.table))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 54)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 88)
        self.table.setColumnWidth(2, 170)
        self.table.setColumnWidth(3, 180)
        self.table.setColumnWidth(4, 86)
        self.table.setColumnWidth(5, 280)
        self.table.setMinimumHeight(300)
        results_layout.addWidget(self.table, 1)

        self.confirm_panel = QFrame()
        self.confirm_panel.setObjectName("ConfirmPanel")
        confirm_layout = QVBoxLayout(self.confirm_panel)
        confirm_layout.setContentsMargins(12, 10, 12, 10)
        confirm_title = QLabel("请确认删除")
        confirm_title.setObjectName("ConfirmTitle")
        self.confirm_text = QLabel("将删除已勾选的候选文件。")
        self.confirm_text.setWordWrap(True)
        self.confirm_text.setObjectName("Muted")
        confirm_layout.addWidget(confirm_title)
        confirm_layout.addWidget(self.confirm_text)
        confirm_actions = QHBoxLayout()
        self.confirm_delete_btn = AnimatedButton("确认删除所选文件")
        self.confirm_delete_btn.setProperty("danger", True)
        self.confirm_delete_btn.setIcon(make_icon("trash", "#FFFFFF"))
        self.confirm_delete_btn.clicked.connect(self._confirm_delete)
        self.confirm_cancel_btn = QPushButton("返回检查")
        self.confirm_cancel_btn.setObjectName("TextButton")
        self.confirm_cancel_btn.clicked.connect(lambda: self.confirm_panel.setVisible(False))
        confirm_actions.addStretch(1)
        confirm_actions.addWidget(self.confirm_cancel_btn)
        confirm_actions.addWidget(self.confirm_delete_btn)
        confirm_layout.addLayout(confirm_actions)
        self.confirm_panel.setVisible(False)
        results_layout.addWidget(self.confirm_panel)

        action_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFixedHeight(8)
        action_row.addWidget(self.progress, 1)
        self.progress_label = QLabel("就绪")
        self.progress_label.setMinimumWidth(128)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.progress_label.setObjectName("MutedSmall")
        action_row.addWidget(self.progress_label)
        results_layout.addLayout(action_row)

        bottom_actions = QHBoxLayout()
        self.export_btn = QPushButton("导出报告")
        self.export_btn.setIcon(make_icon("export", "#475569"))
        self.export_btn.clicked.connect(self._export_report)
        self.delete_btn = AnimatedButton("删除已勾选项目")
        self.delete_btn.setIcon(make_icon("trash", "#FFFFFF"))
        self.delete_btn.setProperty("danger", True)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._show_delete_confirmation)
        bottom_actions.addWidget(self.export_btn)
        bottom_actions.addStretch(1)
        bottom_actions.addWidget(self.delete_btn)
        results_layout.addLayout(bottom_actions)
        right_layout.addWidget(results_card, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 870])
        page_layout.addWidget(splitter)
        return page

    def _stat_card(self, title: str, value: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("StatCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("MutedSmall")
        value_label = QLabel(value)
        value_label.setObjectName("StatValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return frame, value_label

    def _build_rules_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel("安全规则与保护机制")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        intro = QLabel("本工具采用保守识别策略：只把能够通过文件名与文件内容双重验证的系统元数据列为候选项。扫描时计算 SHA-256，删除前再次比对完整内容，不依赖 SMB 可能不稳定的 inode / 时间戳精度。")
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        rule_items = [
            (".DS_Store", "macOS Finder 文件夹元数据。必须同时满足文件名为 .DS_Store、前 4 字节为 Bud1。没有通过文件头验证的同名文件不会被纳入候选清单。", "success"),
            ("._*", "AppleDouble 资源分叉/扩展属性元数据文件。必须以 ._ 开头、前 4 字节为 00 05 16 07，并且同目录存在去掉 ._ 前缀后的对应对象。删除它不会删除主文件，但会丢弃其中的 macOS 扩展属性或资源分叉。", "success"),
            ("Thumbs.db / ehthumbs.db", "旧式 Windows 文件夹缩略图缓存。默认关闭；启用后要求文件头匹配 Compound File Binary（OLE）格式。", "warning"),
            ("thumbcache_*.db / iconcache_*.db", "Windows Vista 至 Windows 11 的资源管理器缩略图与图标缓存数据库。仅识别精确数据库名称并验证 CMMM 文件头；*_idx.db 索引文件验证 IMMM 标记。默认关闭，删除后 Windows 会在需要时重新生成缓存。缓存可能保留已经删除文件的缩略图，因此也可能包含隐私痕迹。", "warning"),
            ("Android .thumbnails / THUMBDATA", "只识别 .thumbnails 目录内名称符合 .thumbdataN-数字 或 .thumbdataN--数字 的 Gallery 缩略图索引文件，不会删除同目录的 JPG/PNG 缩略图。默认关闭；删除可释放空间，但也会丢失索引中可能残留的已删除照片低清预览。", "warning"),
            ("Synology @eaDir（保护项）", "Synology 目录可能保存缩略图、扩展属性及索引/媒体元数据。本版本扫描时会整体跳过 @eaDir，不进入其中查找候选文件，也不会删除其内容。", "blue"),
            ("保护目录与普通文件", "@eaDir、#recycle、$RECYCLE.BIN、System Volume Information、lost+found、.Trash/.Trashes、.Spotlight-V100、.fseventsd 等保护目录会整体跳过。普通 .tmp、.log、.bak、.old、desktop.ini、Office/LibreOffice 锁文件、安装包、文档、照片、视频和压缩包不会被识别或删除。", "blue"),
        ]
        for name, desc, variant in rule_items:
            frame, box = card()
            row = QHBoxLayout()
            name_label = QLabel(name)
            name_label.setObjectName("RuleName")
            row.addWidget(name_label)
            row.addStretch(1)
            row.addWidget(make_pill("高置信度规则" if variant == "success" else ("默认关闭" if variant == "warning" else "保护策略"), variant))
            box.addLayout(row)
            body = QLabel(desc)
            body.setWordWrap(True)
            body.setObjectName("Muted")
            box.addWidget(body)
            layout.addWidget(frame)

        safeguard, safeguard_layout = card("删除前的二次保护")
        safeguards = [
            "扫描阶段只读取目录项、文件头及候选文件内容以计算 SHA-256，不修改文件。",
            "只有文件名与文件头双重验证通过的高置信度候选才会默认勾选；用户可逐项取消或清空。",
            "扫描时为候选文件生成完整 SHA-256 内容指纹；删除前重新计算并比对，避免 SMB 时间戳 / inode 差异导致误拦截。",
            "删除前重新检查路径范围、扫描根目录及每一级父目录，防止目录被替换为符号链接/重解析点；并复核普通文件类型、文件大小及规则特征。",
            "跳过符号链接和 Windows 重解析点；扫描阶段整体跳过 @eaDir、回收站、系统卷信息等保护目录。",
            "删除操作写入日志，支持导出 CSV 报告；无法访问的目录会在日志中列出。",
        ]
        for text in safeguards:
            label = QLabel("•  " + text)
            label.setWordWrap(True)
            label.setObjectName("BodyText")
            safeguard_layout.addWidget(label)
        layout.addWidget(safeguard)
        layout.addStretch(1)
        back = QPushButton("返回清理工作台")
        back.setIcon(make_icon("folder", "#2563EB"))
        back.clicked.connect(lambda: self._switch_page(0))
        layout.addWidget(back, 0, Qt.AlignmentFlag.AlignRight)

        scroll = QScrollArea()
        scroll.setObjectName("RulesPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(page)
        return scroll

    def _apply_style(self) -> None:
        self.setStyleSheet(r"""
            QWidget { background: #F8FAFC; color: #111827; font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 13px; }
            QMainWindow { background: #F8FAFC; }
            QLabel { background: transparent; }
            QLabel#AppTitle { color: #111827; font-size: 21px; font-weight: 700; }
            QLabel#PageTitle { color: #111827; font-size: 22px; font-weight: 700; }
            QLabel#Muted { color: #475569; font-size: 12px; }
            QLabel#MutedSmall { color: #94A3B8; font-size: 11px; }
            QLabel#CardTitle { color: #111827; font-size: 14px; font-weight: 650; }
            QLabel#StatValue { color: #111827; font-size: 23px; font-weight: 700; }
            QLabel#RuleName { color: #111827; font-size: 14px; font-weight: 650; }
            QLabel#BodyText { color: #334155; font-size: 13px; }
            QLabel#WarningText { color: #92400E; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 10px; font-size: 12px; }
            QLabel#HoverHint { color: #2563EB; font-size: 11px; padding: 2px 2px; }
            QLabel#HoverHint:hover { color: #1D4ED8; }
            QToolTip { color: #F8FAFC; background: #111827; border: 1px solid #334155; border-radius: 6px; padding: 7px 9px; font-size: 12px; }
            QFrame#RuleDivider { color: #E5E7EB; background: #E5E7EB; max-height: 1px; border: 0; }
            QScrollArea#RulesPageScroll { background: transparent; border: 0; }
            QScrollBar:vertical { background: #F8FAFC; width: 10px; margin: 2px; border: 0; }
            QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 4px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: #94A3B8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLabel#InfoBanner { color: #1D4ED8; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 12px; }
            QLabel#ConfirmTitle { color: #991B1B; font-size: 14px; font-weight: 700; }
            QFrame#Card, QFrame#StatCard { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; }
            QFrame#StatCard { background: #FFFFFF; }
            QFrame#ConfirmPanel { background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; }
            QFrame#LogPanel { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; }
            QLineEdit { background: #FFFFFF; color: #111827; border: 1px solid #D1D5DB; border-radius: 6px; padding: 7px 9px; selection-background-color: #DBEAFE; }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QLineEdit::placeholder { color: #94A3B8; }
            QListWidget { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 4px; outline: none; }
            QListWidget::item { padding: 4px 5px; border-radius: 4px; color: #334155; }
            QListWidget::item:selected { background: #EFF6FF; color: #2563EB; font-weight: 600; }
            QComboBox { background: #FFFFFF; color: #334155; border: 1px solid #D1D5DB; border-radius: 6px; padding: 7px 9px; min-height: 20px; }
            QComboBox:focus { border: 1px solid #2563EB; }
            QComboBox::drop-down { border: 0; width: 24px; }
            QComboBox QAbstractItemView { background: #FFFFFF; border: 1px solid #E5E7EB; selection-background-color: #EFF6FF; selection-color: #2563EB; outline: none; }
            QCheckBox { color: #334155; spacing: 7px; padding: 1px 0; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #CBD5E1; background: #FFFFFF; }
            QCheckBox::indicator:checked { background: #2563EB; border-color: #2563EB; }
            QPushButton { background: #FFFFFF; color: #334155; border: 1px solid #D1D5DB; border-radius: 6px; padding: 8px 12px; font-weight: 550; }
            QPushButton:hover { background: #F1F5F9; border-color: #CBD5E1; }
            QPushButton:pressed { background: #E2E8F0; }
            QPushButton:disabled { color: #94A3B8; background: #F8FAFC; border-color: #E5E7EB; }
            QPushButton[primary="true"] { background: #2563EB; color: #FFFFFF; border: 1px solid #2563EB; }
            QPushButton[primary="true"]:hover { background: #1D4ED8; }
            QPushButton[danger="true"] { background: #DC2626; color: #FFFFFF; border: 1px solid #DC2626; }
            QPushButton[danger="true"]:hover { background: #B91C1C; }
            QPushButton#TextButton, QPushButton#TextButtonBlue { background: transparent; border: 0; padding: 5px 3px; }
            QPushButton#TextButton { color: #64748B; }
            QPushButton#TextButton:hover { color: #111827; background: #F1F5F9; }
            QPushButton#TextButtonBlue { color: #2563EB; font-weight: 650; }
            QPushButton#TextButtonBlue:hover { background: #EFF6FF; }
            QTableView { background: #FFFFFF; alternate-background-color: #FAFBFC; border: 1px solid #E5E7EB; border-radius: 6px; color: #334155; selection-background-color: #EFF6FF; selection-color: #1D4ED8; gridline-color: #F3F4F6; outline: none; }
            QTableView::item { padding: 6px 7px; border-bottom: 1px solid #F3F4F6; }
            QTableView::item:selected { background: #EFF6FF; color: #1D4ED8; font-weight: 600; }
            QHeaderView::section { background: #F8FAFC; color: #64748B; border: 0; border-bottom: 1px solid #E5E7EB; padding: 9px 7px; font-size: 11px; font-weight: 650; }
            QProgressBar { background: #E2E8F0; border: 0; border-radius: 4px; }
            QProgressBar::chunk { background: #2563EB; border-radius: 4px; }
            QPlainTextEdit { background: #0F172A; color: #D1E2F3; border: 0; border-radius: 6px; padding: 8px; font-family: Consolas, monospace; font-size: 11px; }
            QSplitter::handle { background: transparent; width: 8px; }
            QStatusBar { color: #64748B; background: #F8FAFC; border-top: 1px solid #E5E7EB; }
            QLabel#Pill_success { color: #15803D; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 12px; font-size: 11px; }
            QLabel#Pill_warning { color: #B45309; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; font-size: 11px; }
            QLabel#Pill_blue { color: #1D4ED8; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 12px; font-size: 11px; }
        """)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F8FAFC"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8FAFC"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#111827"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#334155"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#EFF6FF"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1D4ED8"))
        self.setPalette(palette)

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index, 1 if index > self.pages.currentIndex() else -1)
        self.nav_work.setProperty("active", index == 0)
        self.nav_rules.setProperty("active", index == 1)
        self.nav_work.setStyleSheet("background:#EFF6FF;color:#2563EB;border-color:#BFDBFE;" if index == 0 else "")
        self.nav_rules.setStyleSheet("background:#EFF6FF;color:#2563EB;border-color:#BFDBFE;" if index == 1 else "")

    def _add_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{stamp}] {message}")
        self._log_lines += 1
        self.log_count_label.setText(f"{self._log_lines} 条记录")

    def _queue_log(self, message: str) -> None:
        self._pending_logs.append(message)
        if len(self._pending_logs) >= 50:
            self._flush_queued_logs()

    def _flush_queued_logs(self) -> None:
        if not self._pending_logs:
            return
        lines = self._pending_logs[:]
        self._pending_logs.clear()
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText("\n".join(f"[{stamp}] {line}" for line in lines))
        self._log_lines += len(lines)
        self.log_count_label.setText(f"{self._log_lines} 条记录")

    def _toggle_logs(self) -> None:
        visible = not self.log_panel.isVisible()
        self.log_panel.setVisible(visible)
        self.log_toggle.setText("隐藏运行日志  ▾" if visible else "显示运行日志  ▸")

    def _add_root(self) -> None:
        path = self.path_input.text().strip().strip('"')
        if not path:
            self._set_alert("请输入 SMB / UNC 或本地目录路径。", "warning")
            return
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.isdir(path):
            self._set_alert(f"目录不可访问：{path}。请检查 SMB 权限、网络连接和路径拼写。", "danger")
            self._add_log(f"添加目录失败：{path}")
            return
        normalized = os.path.normpath(path)
        existing = {self.root_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.root_list.count())}
        if os.path.normcase(normalized) in {os.path.normcase(x) for x in existing}:
            self._set_alert("该目录已经添加。", "warning")
            return
        item = QListWidgetItem(normalized)
        item.setData(Qt.ItemDataRole.UserRole, normalized)
        item.setToolTip(normalized)
        self.root_list.addItem(item)
        self.path_input.clear()
        self._save_settings()
        self._set_alert(f"已添加扫描目录：{normalized}", "success")
        self._add_log(f"添加扫描目录：{normalized}")

    def _browse_root(self) -> None:
        start = self.path_input.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "选择扫描目录", start)
        if path:
            self.path_input.setText(path)
            self._add_root()

    def _remove_roots(self) -> None:
        for item in self.root_list.selectedItems():
            self.root_list.takeItem(self.root_list.row(item))
        self._save_settings()

    def _set_alert(self, text: str, kind: str = "info") -> None:
        self.alert.setText(text)
        styles = {
            "info": "color:#1D4ED8;background:#EFF6FF;border:1px solid #BFDBFE;",
            "success": "color:#15803D;background:#F0FDF4;border:1px solid #BBF7D0;",
            "warning": "color:#B45309;background:#FFFBEB;border:1px solid #FDE68A;",
            "danger": "color:#B91C1C;background:#FEF2F2;border:1px solid #FECACA;",
        }
        self.alert.setStyleSheet(styles.get(kind, styles["info"]) + "border-radius:8px;padding:10px 12px;")
        if kind in ("success", "danger"):
            glow = QGraphicsDropShadowEffect(self.alert)
            glow.setBlurRadius(17)
            glow.setOffset(0, 0)
            glow.setColor(QColor("#16A34A" if kind == "success" else "#DC2626"))
            self.alert.setGraphicsEffect(glow)
        else:
            self.alert.setGraphicsEffect(None)

    def _shake_window(self) -> None:
        base = self.pos()
        animation = QPropertyAnimation(self, b"pos", self)
        animation.setDuration(260)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(base)
        animation.setKeyValueAt(0.20, base + QPoint(6, 0))
        animation.setKeyValueAt(0.40, base + QPoint(-6, 0))
        animation.setKeyValueAt(0.60, base + QPoint(4, 0))
        animation.setKeyValueAt(0.80, base + QPoint(-3, 0))
        animation.setEndValue(base)
        self._shake_animation = animation
        animation.start()

    def _start_scan(self) -> None:
        if self._busy:
            return
        roots = [self.root_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.root_list.count())]
        if not roots:
            self._set_alert("请先添加至少一个扫描目录。可直接粘贴 SMB 路径，例如 \\\\192.168.0.152\\share。", "warning")
            return
        enabled_rules: set[str] = set()
        if self.ds_checkbox.isChecked():
            enabled_rules.add("ds_store")
        if self.apple_checkbox.isChecked():
            enabled_rules.add("appledouble")
        if self.windows_cache_checkbox.isChecked():
            enabled_rules.add("windows_cache")
        if self.explorer_cache_checkbox.isChecked():
            enabled_rules.add("explorer_cache")
        if self.android_cache_checkbox.isChecked():
            enabled_rules.add("android_cache")
        if not enabled_rules:
            self._set_alert("至少启用一项识别规则。", "warning")
            return

        # 新扫描清空旧结果；之后按批次追加，用户不必等整个 NAS 扫完。
        self.model.set_rows([])
        self._scanning = True
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)
        self.confirm_panel.setVisible(False)
        self.scanned_stat[1].setText("0")
        self.found_stat[1].setText("0")
        self.selected_stat[1].setText("0")
        self.result_count.setText("正在扫描，候选文件会实时出现…")
        self._busy = True
        self._set_busy_ui(True, "正在扫描目录…")
        self.progress.setRange(0, 0)
        self.progress_label.setText("正在扫描")
        self._add_log("开始扫描：" + "；".join(roots))
        self.scan_worker = ScanWorker(roots, enabled_rules)
        self.scan_worker.batch.connect(self._scan_batch)
        self.scan_worker.progress.connect(self._scan_progress)
        self.scan_worker.completed.connect(self._scan_completed)
        self.scan_worker.start()

    def _scan_batch(self, rows: list[dict[str, Any]]) -> None:
        self.model.append_rows(rows)
        found = self.model.rowCount()
        selected = len(self.model.selected_records())
        self.found_stat[1].setText(f"{found:,}")
        self.selected_stat[1].setText(f"{selected:,}")
        self.result_count.setText(f"扫描中 · 已发现 {found:,} 个候选 · 默认勾选 {selected:,} 个")

    def _scan_progress(self, scanned: int, found: int, current: str) -> None:
        self.scanned_stat[1].setText(f"{scanned:,}")
        self.found_stat[1].setText(f"{found:,}")
        self.progress_label.setText(f"已扫描 {scanned:,} 项 · 发现 {found:,} 个")
        self.statusBar().showMessage(f"正在检查：{current}")

    def _scan_completed(self, summary: dict[str, Any]) -> None:
        self._flush_queued_logs()
        self._scanning = False
        self._busy = False
        self._set_busy_ui(False, "扫描完成")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.progress_label.setText("扫描完成")
        self.scanned_stat[1].setText(f"{summary['scanned']:,}")
        found = self.model.rowCount()
        selected = len(self.model.selected_records())
        self.found_stat[1].setText(f"{found:,}")
        self.selected_stat[1].setText(f"{selected:,}")
        self.result_count.setText(f"候选 {found:,} 个 · 当前勾选 {selected:,} 个")
        self.confirm_panel.setVisible(False)
        msg = f"扫描完成：检查 {summary['scanned']:,} 项，发现 {found:,} 个高置信度候选，已默认勾选 {selected:,} 个，用时 {summary['elapsed']:.1f} 秒。"
        if summary["cancelled"]:
            msg = "扫描已取消。" + msg
        if summary["errors"]:
            msg += f" 另有 {len(summary['errors'])} 个读取/目录错误，请查看运行日志。"
        if summary["skipped_reparse"]:
            msg += f" 已安全跳过 {summary['skipped_reparse']} 个链接或重解析点。"
        if summary["uncertain_count"]:
            msg += f" 另有 {summary['uncertain_count']} 个疑似文件未通过内容验证，已跳过。"
        self._set_alert(msg, "success" if not summary["errors"] else "warning")
        self._add_log(msg)
        for error in summary["errors"][:500]:
            self._queue_log(error)
        if len(summary["errors"]) > 500:
            self._queue_log(f"其余 {len(summary['errors']) - 500} 条错误未逐条显示，避免日志过长。")
        for path in summary.get("uncertain_paths", []):
            self._queue_log(f"已跳过未通过文件头/配对验证的项目：{path}")
        if summary.get("uncertain_count", 0) > len(summary.get("uncertain_paths", [])):
            self._queue_log(f"其余 {summary['uncertain_count'] - len(summary['uncertain_paths'])} 个疑似项目未逐条写入日志。")
        self._flush_queued_logs()

    def _update_selection_summary(self) -> None:
        selected = len(self.model.selected_records())
        self.selected_stat[1].setText(f"{selected:,}")
        if self._scanning:
            self.result_count.setText(f"扫描中 · 已发现 {self.model.rowCount():,} 个候选 · 当前勾选 {selected:,} 个")
        elif self.model.rows:
            self.result_count.setText(f"候选 {self.model.rowCount():,} 个 · 当前勾选 {selected:,} 个")
        self.delete_btn.setEnabled(selected > 0 and not self._busy)
        if selected:
            total_bytes = sum(row["size"] for row in self.model.selected_records())
            self.delete_btn.setText(f"删除已勾选项目（{selected}）")
            self.confirm_text.setText(f"已选择 {selected:,} 个候选文件，总大小约 {format_size(total_bytes)}。执行前会重新计算 SHA-256 并验证文件类型；内容有变化的文件会被拦截，失败项会保留供重试。")
        else:
            self.delete_btn.setText("删除已勾选项目")

    def _show_delete_confirmation(self) -> None:
        selected = self.model.selected_records()
        if not selected:
            return
        total = sum(row["size"] for row in selected)
        self.confirm_text.setText(
            f"即将删除 {len(selected):,} 个已勾选的高置信度元数据文件（{format_size(total)}）。\n"
            "删除前会重新计算 SHA-256，并再次验证路径、文件类型和文件头。与扫描时内容不同的文件不会删除。此操作不可通过本工具撤销。"
        )
        self.confirm_panel.setVisible(True)
        self.confirm_panel.setFocus()

    def _confirm_delete(self) -> None:
        selected = self.model.selected_records()
        if not selected or self._busy:
            return
        self.confirm_panel.setVisible(False)
        self._busy = True
        self._set_busy_ui(True, "正在复核并删除…")
        self.progress.setRange(0, len(selected))
        self.progress.setValue(0)
        self.progress_label.setText(f"0 / {len(selected)}")
        self._add_log(f"开始删除任务：{len(selected)} 个文件。")
        self.delete_worker = DeleteWorker(selected)
        self.delete_worker.progress.connect(self._delete_progress)
        self.delete_worker.log.connect(self._queue_log)
        self.delete_worker.completed.connect(self._delete_completed)
        self.delete_worker.start()

    def _delete_progress(self, current: int, total: int, path: str) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(current)
        self.progress_label.setText(f"{current:,} / {total:,}")
        self.statusBar().showMessage(f"正在处理：{path}")

    def _delete_completed(self, results: list[dict[str, Any]]) -> None:
        self._flush_queued_logs()
        self.model.apply_delete_results(results)
        self._busy = False
        self._set_busy_ui(False, "任务完成")
        deleted = sum(1 for item in results if item["status"] == "已删除")
        blocked = sum(1 for item in results if item["status"] == "已拦截")
        failed = sum(1 for item in results if item["status"] == "删除失败")
        cancelled = sum(1 for item in results if item["status"] == "已取消")
        message = f"删除任务完成：成功 {deleted} 个，内容/安全复核拦截 {blocked} 个，权限或占用失败 {failed} 个，取消未处理 {cancelled} 个。"
        if blocked:
            from collections import Counter
            reasons = Counter(item["message"] for item in results if item["status"] == "已拦截")
            reason_text = "；".join(f"{reason}（{count}）" for reason, count in reasons.most_common(3))
            message += " 拦截原因：" + reason_text
        if failed:
            from collections import Counter
            reasons = Counter(item["message"] for item in results if item["status"] == "删除失败")
            reason_text = "；".join(f"{reason}（{count}）" for reason, count in reasons.most_common(2))
            message += " 失败原因：" + reason_text
        self._set_alert(message, "success" if not blocked and not failed and not cancelled else "warning")
        self._add_log(message)
        if self.sound_checkbox.isChecked():
            play_synthesized_feedback(success=(blocked == 0 and failed == 0 and cancelled == 0 and deleted > 0))
        if blocked or failed:
            self._shake_window()
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.progress_label.setText("任务完成")
        self.statusBar().showMessage(message)
        self._update_selection_summary()

    def _set_busy_ui(self, busy: bool, text: str) -> None:
        self.scan_btn.setEnabled(not busy)
        self.scan_btn.setText("开始扫描" if not busy else "任务进行中")
        self.add_path_btn.setEnabled(not busy)
        self.browse_btn.setEnabled(not busy)
        self.remove_root_btn.setEnabled(not busy)
        self.ds_checkbox.setEnabled(not busy)
        self.apple_checkbox.setEnabled(not busy)
        self.windows_cache_checkbox.setEnabled(not busy)
        self.explorer_cache_checkbox.setEnabled(not busy)
        self.android_cache_checkbox.setEnabled(not busy)
        self.sound_checkbox.setEnabled(not busy)
        self.select_safe_btn.setEnabled(not busy)
        self.clear_selection_btn.setEnabled(not busy)
        self.export_btn.setEnabled(not busy)
        self.cancel_btn.setVisible(busy)
        self.cancel_btn.setEnabled(busy)
        if not busy:
            self.cancel_btn.setText("取消当前任务")
        self.progress_label.setText(text)
        self.statusBar().showMessage(text)
        self._update_selection_summary()

    def _cancel_task(self) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self._add_log("已请求取消扫描；正在等待当前目录操作结束。")
        if self.delete_worker and self.delete_worker.isRunning():
            self.delete_worker.cancel()
            self._add_log("已请求取消删除任务；正在停止后续文件处理。")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("正在停止…")

    def _export_report(self) -> None:
        if not self.model.rows:
            self._set_alert("当前没有检测结果可导出。", "warning")
            return
        default_name = f"NAS清理检测报告_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "导出检测报告", os.path.join(os.path.expanduser("~"), "Desktop", default_name), "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                writer.writerow(["状态", "规则", "文件名", "大小（字节）", "完整路径", "识别依据", "是否可删除", "是否勾选"])
                for row in self.model.rows:
                    writer.writerow([row.get("state"), row.get("rule"), row.get("name"), row.get("size"), row.get("path"), row.get("reason"), row.get("eligible"), row.get("selected")])
            self._set_alert(f"报告已导出：{path}", "success")
            self._add_log(f"导出 CSV 报告：{path}")
        except OSError as exc:
            self._set_alert(f"导出失败：{exc}", "danger")
            self._add_log(f"导出失败：{exc}")

    def _save_settings(self) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("roots", [self.root_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.root_list.count())])
        self.settings.setValue("include_ds_store", self.ds_checkbox.isChecked())
        self.settings.setValue("include_appledouble", self.apple_checkbox.isChecked())
        self.settings.setValue("include_windows_cache", self.windows_cache_checkbox.isChecked())
        self.settings.setValue("include_explorer_cache", self.explorer_cache_checkbox.isChecked())
        self.settings.setValue("include_android_cache", self.android_cache_checkbox.isChecked())
        self.settings.setValue("sound_enabled", self.sound_checkbox.isChecked())

    def _restore_settings(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        roots = self.settings.value("roots", [])
        if isinstance(roots, str):
            roots = [roots]
        for root in roots:
            if root:
                item = QListWidgetItem(str(root))
                item.setData(Qt.ItemDataRole.UserRole, str(root))
                item.setToolTip(str(root))
                self.root_list.addItem(item)
        self.ds_checkbox.setChecked(self.settings.value("include_ds_store", True, type=bool))
        self.apple_checkbox.setChecked(self.settings.value("include_appledouble", True, type=bool))
        self.windows_cache_checkbox.setChecked(self.settings.value("include_windows_cache", False, type=bool))
        self.explorer_cache_checkbox.setChecked(self.settings.value("include_explorer_cache", False, type=bool))
        self.android_cache_checkbox.setChecked(self.settings.value("include_android_cache", False, type=bool))
        self.sound_checkbox.setChecked(self.settings.value("sound_enabled", False, type=bool))

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._busy:
            self._set_alert("当前任务仍在运行。请先取消并等待任务安全停止后再退出。", "warning")
            event.ignore()
            return
        self._save_settings()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Qwejay")
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#334155"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#EFF6FF"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1D4ED8"))
    app.setPalette(palette)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
