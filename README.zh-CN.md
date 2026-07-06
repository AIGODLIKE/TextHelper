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


## 近期更新

### 2.0.0

- **多行字符上限**：默认 20,000 字；可在偏好设置中自行调整（256–50,000，Blender 硬上限 50,000）。侧边栏显示「当前 / 上限」。
- **扩展合规**：undo/redo 处理器按需注册；横排/竖排文本统一执行字符上限；使用官方 `blender --command extension build` 打包。
- **添加文本**：改用低级 API 创建 FONT 曲线，不再包装 `bpy.ops.object.text_add`。
- **Manifest**：扩展标签改为 `User Interface`。
- 自 **1.9.17** 以来的累积改进（顶栏工具条、字体搜索/收藏/筛选、HUD 滑条内联编辑、多选批量编辑、主题自适应 HUD、日/繁 i18n，以及 1.9.99 前的各项修复）——详见下方 1.9.x 条目。

### 1.9.x（1.8.x–1.9.x 历史）

- **1.9.86** — 字重合并：PostScript 前缀统一 GenYo 等中英双族名；支持 B/EL 等缩写字重后缀
- **1.9.85** — 偏好设置：字重合并方式（OpenType 族名 / 文件名），修复同族名未合并为多字重
- **1.9.84** — 字体选择器：「隐藏不支持」改为分帧筛选，先出列表再逐步剔除
- **1.9.29** — 字体收藏与筛选（收藏/多字重/可变字体）；顶栏刷新仅图标
- **1.9.27** — 字重标签保留文件名原名（Normal、Roman 等），不再统一显示为 Regular
- **1.9.25** — 顶栏多语言补全；浮动工具栏开关移到预设前；字体/字重 Popover 悬停预览
- **1.9.24** — 顶栏：字号/字距等滑条合并为一行并右对齐；缩短按钮宽度
- **1.9.23** — 顶栏：置于活跃工具设置之后；字体列表「仅显示支持字体」；大小写三键切换；字号/字距/行高/切变滑条；删除线位置
- **1.9.22** — 顶栏置于工具设置之后；字体/字重用 Popover 文本列表（无缩略图）
- **1.9.21** — 修复顶栏工具条：通过视口 Header 注入绘制
- **1.9.20** — 3D 视口顶栏工具条：不开启浮动 HUD 时也可使用排版控件
- **1.9.19** — 修复 HUD 撤销后文本不刷新；滑条直接写 RNA 以正确记录撤销
- **1.9.18** — 多选文本批量调整格式；浮动工具栏操作支持撤销
- **1.9.17** — 视口 HUD 删除线滑条日文标签缩短为「取消位置」
- **1.9.16** — 视口 HUD 删除线滑条英文标签缩短为「Strike Pos」
- **1.9.6** — 刷新图标悬停显示说明；点击后提示「字体信息已刷新」
- **1.9.5** — 视口字体选择器刷新改为第 3 位图标按钮，带悬停与按下反馈
- **1.9.4** — 视口字体选择器、字体菜单与偏好设置中新增可见的 **「强制刷新预览」** 按钮
- **1.9.3** — 修复手动替换字体文件后预览全部失效；刷新按钮现会清除加载失败缓存并重建缩略图
- **1.9.2** — 添加文本时文本框尺寸与偏移量默认为 0
- **1.9.1** — 扩展商店合规：补全 maintainer 邮箱、移除 bl_info、预览缓存初始化更安全、msgbus/load_post 按需注册
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
