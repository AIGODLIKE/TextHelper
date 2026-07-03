# 请务必在Blender 5.2以上版本运行

# Text Helper 文本助手

这是一个能够让你像喝水那样编辑3D文本的Blender工具。
你想要的**多行文本输入**、**字体实时预览**、**无效字体排除**、**字族字重选择**、**横竖排版一键切换**、**极致舒适的UI**等现在全部都在这里！

<img width="2560" height="1380" alt="image" src="https://github.com/user-attachments/assets/b7cd58c7-2943-4c40-840e-67e30e1009b1" />

---

## 亮点功能

### 文本输入

https://github.com/user-attachments/assets/b7d06527-94dc-4f77-ae7a-d5b3cc7e12ba

- 多行 **textbox**（需要Blender 5.2+）
- 换行=Shift+Enter | 确认=Enter

### 字体

https://github.com/user-attachments/assets/adf5a290-0b00-45e4-88f3-e48734f28172



- **实时预览**：实时预览字体/字重效果，支持当前输入内容用作预览（也可以使用字体名称或者自定义字符串）
- **实时生效**：悬停时实时更换字体/字重
- **无效字体排除**：支持根据输入内容**自动匹配**支持的字体（小提示，当输入内容变为“□”时,可以直接展开字体库修复，超级好用啊~）
- **字重合并**：支持同族字体字重合并
- 浏览本地 `.ttf` / `.otf`；可选悬停实时预览
- **多系统支持**：扫描 **系统字体**（Windows / macOS / Linux）


- 横排 / **竖排** 模式，列顺序（从右到左 / 从左到右）
- 粘贴、清空（需 clipboard 权限）
- 竖排半角字符提示与一键转全角

### 视口浮动工具栏（HUD）

- 可拖拽，显示在选中文字附近
- 样式预设、**GPU 字体选择器**、粗体 / 斜体 / 下划线 / 删除线
- 大小写、对齐、间距滑条（字号、字距、词距、行高、倾斜等）
- 双击空白区域进入 / 退出文字编辑模式

### 字体

- 扫描 **系统字体**（Windows / macOS / Linux）
- 搜索、排序、书写系统筛选、**字重选择器**、缩略图预览
- 浏览本地 `.ttf` / `.otf`；可选悬停实时预览

### 其他

- 简体中文界面（随 Blender 语言自动切换）
- 繁体中文界面（`zh_Hant`）
- 日文界面（`ja_JP`）
- 可自定义 HUD 强调色与缩放

---

## 安装

### 扩展平台（推荐）

1. 从 [Releases](https://github.com/AIGODLIKE/TextHelper/releases) 下载 `TextHelper-1.8.5.zip`（发布后），或本地构建（见下）。
2. Blender：**编辑 → 偏好设置 → 获取扩展 → 从磁盘安装…**
3. 选择 zip，启用 **Text Helper**。

### 手动 / 开发

1. 将本仓库克隆到扩展目录，例如：  
   `%APPDATA%\Blender Foundation\Blender\5.2\extensions\user_default\TextHelper`
2. 重启 Blender 或刷新扩展。

### 本地打包（官方）

在 `TextHelper` 插件目录下执行：

```bash
blender --command extension validate
blender --command extension build
```

生成：`TextHelper-1.8.5.zip`

上级 `DATA` 目录中的 `_build_texthelper_zip.py` 可用于快速本地复制；提交 Extension Store 请使用 Blender CLI 生成的 zip。

---

## 近期更新（1.8.x）

- **1.8.5** — 更新字体预览默认示例文字
- **1.8.4** — 繁体中文界面（`zh_Hant`），用语对齐 Blender 繁体（如 視圖區）
- **1.8.2** — Operator poll 与 i18n 合规修复
- **1.8.0** — JSON 多语言（简中、日文）、字重选择器、N 面板布局优化

---

见 `blender_manifest.toml`：

| 权限 | 用途 |
|------|------|
| **files** | 从磁盘加载字体；缓存预览缩略图 |
| **clipboard** | 向文本对象粘贴内容 |

不访问网络。

---

## 使用

1. 添加或选中 **文字（Font）** 对象。
2. 在 3D 视图侧边栏打开 **Text Helper** 标签。
3. 输入或粘贴文字；点击面板标题栏叠加图标开关浮动工具栏。
4. 在 HUD 上打开 **Font** 使用视口字体选择器，或用工具栏调整格式。

偏好设置：**编辑 → 偏好设置 → 插件 → Text Helper**。

---

## 系统要求

- Blender **5.2.0** 及以上
- 侧边栏多行 textbox 需要 Blender **5.2+**

---

## 链接

- [问题反馈](https://github.com/AIGODLIKE/TextHelper/issues)
- [English README](README.md)

---

## 许可证

本插件为自由软件，遵循 **GNU General Public License v3.0 或更高版本**。详见 [LICENSE](LICENSE)。
