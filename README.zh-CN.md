# 请务必在Blender 5.2以上版本运行

# Text Helper 文本助手

这是一个能够让你像喝水那样编辑3D文本的Blender工具。
你想要的**多行文本输入**、**字体实时预览**、**无效字体排除**、**字族字重选择**、**横竖排版一键切换**、**极致舒适的UI**等现在全部都在这里！

<img width="2560" height="1380" alt="image" src="https://github.com/user-attachments/assets/b7cd58c7-2943-4c40-840e-67e30e1009b1" />

---

## 亮点功能

### 多行文本

https://github.com/user-attachments/assets/b7d06527-94dc-4f77-ae7a-d5b3cc7e12ba

- 多行文本输入（至少需要Blender 5.2+）
- 换行=Shift+Enter | 确认=Enter

### 字体

https://github.com/user-attachments/assets/adf5a290-0b00-45e4-88f3-e48734f28172

- **实时预览**：实时预览字体/字重效果，支持当前输入内容用作预览（也可以使用字体名称或者自定义字符串）
- **实时生效**：悬停时实时更换字体/字重
- **无效字体排除**：支持根据输入内容**自动匹配**支持的字体（小提示，当输入内容变为“□”时,可以直接展开字体库修复，超级好用啊~）
- **字重合并**：支持同族字体字重合并
- **筛选**：支持按语言、按是否支持、按是否有多个字重进行筛选
- **搜索**：支持搜索字体(暂仅支持英文输入搜索，需要其他语言请先复制粘贴)
- **多系统支持**：扫描 **系统字体**（Windows / macOS / Linux）

### 文本横竖排版

https://github.com/user-attachments/assets/c6e7aafe-1c71-4a4c-872e-7ea1068af498

- **横排** / **竖排**:一键转换，竖排模式支持从左到右与从右到左的排布

- **全角修复(对齐修复)**：检测半角字符，一键转为全角，解决字体字符对齐问题(注意：部分字体包含特殊字符可能表现不佳)

https://github.com/user-attachments/assets/b02935a9-20d5-4253-bfa8-67867faa306c

### 视口浮动工具栏（HUD）

https://github.com/user-attachments/assets/df5342b7-7d49-47f3-ab6a-f1b6f32632e4

- 可拖拽，显示在选中文字附近
- 样式预设、**GPU 字体选择器**、粗体 / 斜体 / 下划线 / 删除线
- 大小写、对齐、间距滑条（字号、字距、词距、行高、倾斜等）
- 双击空白区域进入 / 退出文字编辑模式

### 其他

- 简体中文界面（随 Blender 语言自动切换）
- 繁体中文界面（`zh_Hant`）
- 日文界面（`ja_JP`）
- 可自定义 HUD 强调色与缩放

---

## 安装

### 扩展平台（推荐）

1. 从 [Releases](https://github.com/AIGODLIKE/TextHelper/releases) 下载 `TextHelper-X.X.X.zip`，或本地构建（见下）。
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

生成：`TextHelper-1.9.0.zip`

上级 `DATA` 目录中的 `_build_texthelper_zip.py` 可用于快速本地复制；提交 Extension Store 请使用 Blender CLI 生成的 zip。

---

## 近期更新（1.8.x / 1.9.x）

- **1.9.0** — 修复延迟加载字体目录时的崩溃（macOS `UnboundLocalError`）
- **1.8.6** — README 重写，亮点功能说明与演示视频
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
