# Text Helper 文本助手

**版本 1.7.1** · 适用于 Blender **5.2+** · [GPL-3.0-or-later](LICENSE)

Text Helper 让 Blender 文本对象更好用：侧边栏多行编辑、视口浮动工具栏、系统字体浏览与实时预览，以及竖排文本工作流。

维护者：**ACGGIT**

---

## 功能概览

### 侧边栏（N 面板）

- 多行 **textbox**（Blender 5.2+），可设置可见行数
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
- 搜索、排序、书写系统筛选、缩略图预览
- 浏览本地 `.ttf` / `.otf`；可选悬停实时预览

### 其他

- 简体中文界面（随 Blender 语言自动切换）
- 可自定义 HUD 强调色与缩放

---

## 安装

### 扩展平台（推荐）

1. 从 [Releases](https://github.com/AIGODLIKE/TextHelper/releases) 下载 `TextHelper-1.7.1.zip`（发布后），或本地构建（见下）。
2. Blender：**编辑 → 偏好设置 → 获取扩展 → 从磁盘安装…**
3. 选择 zip，启用 **Text Helper**。

### 手动 / 开发

1. 将本仓库克隆到扩展目录，例如：  
   `%APPDATA%\Blender Foundation\Blender\5.2\extensions\user_default\TextHelper`
2. 重启 Blender 或刷新扩展。

### 本地打包

在包含 `_build_texthelper_zip.py` 的上级目录执行：

```bash
python _build_texthelper_zip.py
```

生成：`TextHelper-1.7.1.zip`

---

## 权限说明

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
