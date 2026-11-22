# FileTidy 文件净理

<p align="center">
  <strong>保守识别系统元数据 · 先预览，再删除</strong><br>
  专为 NAS（SMB/UNC 共享）及本地磁盘打造的轻量级安全清理工具
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.2.2-blue">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="PySide6" src="https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey">
</p>

---

## 📖 软件简介

在日常跨平台访问 NAS（如群晖、威联通等）或共享文件夹时，macOS、Windows 和 Android 系统会自动残留大量元数据与缩略图缓存文件（如 `.DS_Store`、`._*`、`Thumbs.db` 等）。

**FileTidy 文件净理** 基于 **Python + PySide6** 开发，采用**极度保守的识别与清理策略**：
- **不依赖宽泛扩展名**：拒绝“一刀切”清理 `.tmp`、`.log`、`.bak` 等可能包含用户数据或程序配置的文件。
- **文件名 + 文件头魔数双重校验**：只将精确匹配文件命名模式且通过二进制文件头验证的元数据列为候选项。
- **针对 SMB 网络环境优化的 SHA-256 复核**：扫描阶段即计算文件完整 SHA-256 内容指纹，删除前重新计算比对，不依赖在 SMB 协议下可能不稳定的 inode 或纳秒级时间戳，兼顾安全性与跨平台兼容性。

---

## ✨ 核心特性

- **直连 SMB / UNC 路径**：无需映射为本地网络驱动器，直接输入 `\\192.168.0.152\share` 即可扫描与清理（已针对 Windows 下裸 UNC 共享根路径边界判断做兼容处理）。
- **实时流式结果展示**：后台多线程扫描，发现的候选项按批次实时推送至界面列表，无需等待整个大型存储卷扫描完毕。
- **严格的删除前五重校验**：
  1. **根目录边界检查**：确保目标路径严格位于原扫描目录内。
  2. **保护目录拦截**：严禁触碰回收站及系统核心元数据目录。
  3. **父目录链防替换校验**：删除前逐级检查扫描根目录及父目录，防止操作期间目录被替换为符号链接或重解析点（Reparse Point）。
  4. **文件特征与内容指纹复核**：重新核对文件类型、大小、修改状态以及完整 **SHA-256** 哈希，扫描后发生过变更的文件会被自动拦截保护。
  5. **二次特征验证**：删除前再次执行规则与文件头校验。
- **灵活的筛选与重试**：支持按关键字搜索文件名/路径，按状态筛选（待清理、已勾选、可重试、已删除、异常），因权限或文件占用删除失败的项目可保留供排查后直接重试。
- **操作可追溯**：内置折叠式运行日志面板，支持一键导出带 BOM 的 `CSV` 检测/清理报告（可直接用 Excel 打开）。
- **单文件零外部资源依赖**：所有图标均通过内存 SVG 矢量渲染，声音提示（Windows 平台可选，默认关闭）通过标准库 `wave` 动态合成。

---

## 🛡️ 支持识别的文件规则

| 规则名称 | 默认状态 | 识别依据（必须同时满足） | 说明与注意事项 |
| :--- | :---: | :--- | :--- |
| **macOS `.DS_Store`** | ✅ 开启 | 文件名为 `.DS_Store` + 文件头前 4 字节为 `Bud1` | 清理 Finder 文件夹视图元数据；同名非 Finder 文件会自动跳过。 |
| **macOS AppleDouble (`._*`)** | ✅ 开启 | `._` 开头 + 文件头为 `00 05 16 07` + 同目录存在对应原文件 | 清理资源分叉/扩展属性文件。**注意：删除会丢失原文件携带的 macOS 扩展属性/标签。** |
| **Windows 旧式缩略图缓存** | ⬜ 关闭 | 文件名为 `Thumbs.db` 或 `ehthumbs.db` + OLE/CFB 文件头 (`D0 CF 11 E0 A1 B1 1A E1`) | 仅匹配通过二进制头验证的旧版文件夹缩略图缓存。 |
| **Windows Explorer 缓存** | ⬜ 关闭 | 精确匹配 `thumbcache_*.db` / `iconcache_*.db` + 数据库文件头为 `CMMM`（索引 `*_idx.db` 含 `IMMM`） | 涵盖 Vista 至 Win11 的资源管理器缓存；删除后系统在需要时会重新生成。 |
| **Android THUMBDATA 缓存** | ⬜ 关闭 | 位于 `.thumbnails` 目录内 + 文件名符合 `.thumbdataN-数字` / `.thumbdataN--数字` | 仅清理缩略图索引文件，**不会扫描或删除同目录下的 JPG/PNG 缩略图**。 |

---

## 🔒 安全边界与跳过策略

为避免误删系统数据或重要文件，以下目录与文件在扫描和删除阶段均会被**强制跳过或拦截**：

- **自动跳过的保护目录**：
  - 群晖元数据与回收站：`@eaDir`、`#recycle`
  - Windows 系统目录：`$RECYCLE.BIN`、`System Volume Information`
  - macOS / Linux 系统目录：`lost+found`、`.Trash`、`.Trashes`、`.Trash-*`、`.Spotlight-V100`、`.fseventsd`、`.TemporaryItems`
- **绝对跳过的链接类型**：符号链接（Symlink）及 Windows 重解析点（Reparse Point）。
- **永不识别的文件类型**：`.tmp`、`.log`、`.bak`、`.old`、`desktop.ini`、Office/LibreOffice 锁文件、普通隐藏文件、文档、照片、视频或整个文件夹。

---

## 🚀 快速开始

### 环境要求

- Python **3.10** 或更高版本
- 操作系统：Windows（完整支持 UNC 路径及可选音频提示）、macOS / Linux（需挂载 SMB 或扫描本地目录）

### 安装与运行

1. 克隆仓库并进入项目目录：
   ```bash
   git clone https://github.com/Qwejay/FileTidy.git
   cd FileTidy
   ```

2. 安装依赖（仅需 `PySide6`）：
   ```bash
   pip install PySide6
   ```

3. 启动程序：
   ```bash
   python main.py
   ```

### （可选）打包为独立可执行文件

如需在 Windows 上打包为免 Python 环境的 `.exe` 程序，可使用 PyInstaller：

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name "FileTidy" main.py
```

---

## 📝 使用流程

1. **添加扫描目录**：粘贴本地路径或 SMB/UNC 路径（如 `\\192.168.0.152\files`），或点击「浏览…」选择目录。
2. **确认识别规则**：默认仅开启高置信度的 `.DS_Store` 和 `._*` 规则，可按需勾选其他缓存规则（悬停规则名称可查看详细安全提示）。
3. **开始扫描（只读预览）**：点击「开始扫描」，右侧表格将实时输出命中结果；通过严格验证的候选项会默认勾选。
4. **人工核对与清理**：
   - 可通过顶部搜索框和状态下拉菜单筛选查看结果，取消勾选不想清理的项目。
   - 点击「删除已勾选项目」，在展开的二次确认面板中核对文件数量与总大小后，点击「确认删除所选文件」。
5. **查看日志与导出报告**：点击底部「显示运行日志」查看跳过/拦截/失败详情，或点击「导出报告」保存为 CSV 表格。

---

## ⚠️ 注意事项

- 本工具执行删除操作时使用的是底层直接删除（`os.remove`），**不会将文件移入系统回收站**，删除后无法通过本工具撤销。请在点击最终「确认删除所选文件」前仔细核对清单。
- 如果通过 SMB 访问 NAS 出现「删除失败」，请检查当前网络账户对该共享文件夹是否拥有写入/删除权限，或检查文件是否正被其他客户端占用。

---

```