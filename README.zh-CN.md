# 请务必在Blender 5.2以上版本运行

# Text Helper 文本助手

这是一个能够让你像喝水那样编辑3D文本的Blender工具。
你想要的**多行文本输入**、**字体实时预览**、**无效字体排除**、**字族字重选择**、**横竖排版一键切换**、**极致舒适的UI**等现在全部都在这里！

<img width="2560" height="1380" alt="image" src="https://github.com/user-attachments/assets/b7cd58c7-2943-4c40-840e-67e30e1009b1" />

---

## 亮点功能

### 多行文本

https://github.com/user-attachments/assets/b7d06527-94dc-4f77-ae7a-d5b3cc7e12ba

<img width="1920" height="1034" alt="Multi-line textinput" src="https://github.com/user-attachments/assets/78887700-2bcb-40a7-a76e-1fc7cc98ee75" />

- 多行文本输入（至少需要Blender 5.2+）
- 换行=Shift+Enter | 确认=Enter

### 字体

https://github.com/user-attachments/assets/adf5a290-0b00-45e4-88f3-e48734f28172

<img width="1920" height="1034" alt="FontSelector" src="https://github.com/user-attachments/assets/435197f9-1233-4d37-a79d-b1412a803869" />

- **实时预览**：实时预览字体/字重效果，支持当前输入内容用作预览（也可以使用字体名称或者自定义字符串）
- **实时生效**：悬停时实时更换字体/字重
- **无效字体排除**：支持根据输入内容**自动匹配**支持的字体（小提示，当输入内容变为“□”时,可以直接展开字体库修复，超级好用啊~）
- **字重合并**：支持同族字体字重合并
- **筛选**：支持按语言、按是否支持、按是否有多个字重进行筛选
- **搜索**：支持搜索字体(暂仅支持英文输入搜索，需要其他语言请先复制粘贴)
- **多系统支持**：扫描 **系统字体**（Windows / macOS / Linux）

### 文本横竖排版

https://github.com/user-attachments/assets/c6e7aafe-1c71-4a4c-872e-7ea1068af498

<img width="1920" height="1034" alt="Horizontal  vertical text modes" src="https://github.com/user-attachments/assets/87920b34-dda8-4bbe-b8af-ce882137bcb4" />


- **横排** / **竖排**:一键转换，竖排模式支持从左到右与从右到左的排布

- **全角修复(对齐修复)**：检测半角字符，一键转为全角，解决字体字符对齐问题(注意：部分字体包含特殊字符可能表现不佳)

https://github.com/user-attachments/assets/b02935a9-20d5-4253-bfa8-67867faa306c

<img width="1920" height="1034" alt="FixFont" src="https://github.com/user-attachments/assets/cc8c8ab1-de71-4907-a78f-6d6798205a0b" />


### 视口浮动工具栏（HUD）

https://github.com/user-attachments/assets/df5342b7-7d49-47f3-ab6a-f1b6f32632e4

<img width="1920" height="1034" alt="TextEdit" src="https://github.com/user-attachments/assets/32b73339-c424-47e8-a28f-6f0b3badc31a" />


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

## 对比

### Blender 原生 vs Text Helper

| | 功能 | Blender 原生 | Text Helper |
|---:|---|:---:|:---:|
| 1 | N 面板多行文本编辑（Blender 5.2+） | ✓ | ✓ |
| 2 | 侧边栏按段落完整预览与编辑 | ✗ | ✓ |
| 3 | 浏览并搜索**系统字体**（不限于当前 .blend 已有字体） | ✗ | ✓ |
| 4 | 悬停**实时预览**字体 / 字重 | ✗ | ✓ |
| 5 | 悬停**实时应用**字体 / 字重 | ✗ | ✓ |
| 6 | 按当前文本内容筛选支持字形的字体 | ✗ | ✓ |
| 7 | 拼音 / 假名辅助字体搜索（中日文） | ✗ | ✓ |
| 8 | 字体收藏、最近使用、字族字重选择 | ✗ | ✓ |
| 9 | 选中文字旁的视口浮动工具栏（HUD） | ✗ | ✓ |
| 10 | 视口顶栏排版工具条 | ✗ | ✓ |
| 11 | 横竖排版一键切换 + 竖排列顺序 | ✗ | ✓ |
| 12 | 竖排 CJK 全角对齐修复 | ✗ | ✓ |
| 13 | 样式预设 + 可内联输入数值的间距滑条 | ✗ | ✓ |
| 14 | 多选文本批量调整格式 | ✗ | ✓ |
| 15 | 字数统计与可配置字符上限 | ✗ | ✓ |
| 16 | 文本工具界面多语言（简中 / 繁中 / 日文） | ✗ | ✓ |
| 17 | 视口内文字编辑模式（EDIT_FONT） | ✓ | ✓ |
| 18 | 无需安装扩展即可使用 | ✓ | ✗ |

### Text Helper 1.9 vs 2.0

| | 改进项 | 1.9.x | 2.0 |
|---:|---|:---:|:---:|
| 1 | **打开字体列表即可立即看到条目**（异步预加载字体目录） | ✗ | ✓ |
| 2 | **非阻塞扫描** — 目录加载时界面仍可操作 | ✗ | ✓ |
| 3 | 筛选 / 搜索结果缓存（再次打开无需全量重扫） | ✗ | ✓ |
| 4 | **「隐藏不支持」分帧逐步剔除**（先出列表，再按帧 refine） | ✗ | ✓ |
| 5 | 字族级字形预检，减少重复逐文件检测 | ✗ | ✓ |
| 6 | 视口**顶栏工具条**（不依赖浮动 HUD 也能排版） | 部分 | ✓ |
| 7 | HUD 滑条：点击输入、拖选、剪贴板快捷键 | ✗ | ✓ |
| 8 | 多选批量编辑并支持撤销 | ✗ | ✓ |
| 9 | HUD 随 Blender 浅/深主题自适应配色 | ✗ | ✓ |
| 10 | 可配置多行字符上限（默认 **20,000** 字） | ✗ | ✓ |
| 11 | OpenType 字重合并偏好（族名 / 文件名） | ✗ | ✓ |
| 12 | 操作符悬停提示完整翻译（日 / 繁） | 部分 | ✓ |
| 13 | 扩展平台规范打包与 handler 按需注册 | 部分 | ✓ |

> **字体列表性能（2.0）：** 打开选择器不再等待完整系统字体扫描或一次性字形审计。目录在后台加载，筛选结果可复用缓存，「隐藏不支持」按帧逐步 refine，因此可以立刻滚动、搜索并选定字体。

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

生成：`TextHelper-2.0.0.zip`

上级 `DATA` 目录中的 `_build_texthelper_zip.py` 可用于快速本地复制；提交 Extension Store 请使用 Blender CLI 生成的 zip。

---

## 已知局限性
- 为提升性能，字体字形匹配会对字符去重，且最多检测 2048 个不同字符。
- 竖排输入：全角修复对不包含全角字形的字体无效
- 竖排输入：全角修复在部分非标准字体的特殊符号表现不佳

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
