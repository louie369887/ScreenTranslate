# 屏幕翻译 (Screen Translator)

基于腾讯混元 Hy-MT2-1.8B 翻译模型的 Windows 屏幕实时翻译工具。支持截图 OCR 识别 + 本地离线翻译 / API 翻译。

## 功能特点

- **截图翻译**：快捷键呼出截图窗口，支持区域框选、窗口选择、全屏翻译
- **实时重翻**：画面变化后自动重新识别并翻译（如滚动网页）
- **本地离线翻译**：使用 Hy-MT2-1.8B GGUF 模型，无需联网
- **API 翻译**：支持 OpenAI 兼容接口（DeepSeek、OpenAI、Ollama、vLLM 等）
- **离线 OCR**：内置 RapidOCR，支持中英文识别，无需联网
- **系统托盘**：关闭窗口后最小化到后台，快捷键随时唤起
- **翻译历史**：自动保存翻译记录，支持搜索和管理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

如果需要 GPU 加速（CUDA），先安装对应版本的 llama-cpp-python：

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

### 2. 下载模型

**方式一：使用 modelscope（推荐国内用户）**

```bash
pip install modelscope
modelscope download --model Tencent-Hunyuan/Hy-MT2-1.8B-GGUF --local_dir models
```

**方式二：使用 huggingface-cli**

```bash
pip install huggingface_hub
huggingface-cli download tencent/Hy-MT2-1.8B-GGUF --local-dir models
```

推荐下载 Q4_K_M 量化版本（约1.1GB），文件名类似 `Hy-MT2-1.8B-Q4_K_M.gguf`。

### 3. 启动

```bash
python main.py
```

或双击 `run.bat`。

## 使用方法

1. 启动后会看到设置界面，在 **翻译服务** 页选择本地模型路径（.gguf 文件）或配置 API
2. 点击 **加载模型** 等待加载完成（首次约需30秒到几分钟，取决于硬件）
3. 按快捷键（默认 `Ctrl+Alt+S`）呼出截图窗口
4. **区域模式**：拖拽框选要翻译的区域，点击「翻译」
5. **窗口模式**：切换到「窗口」标签，鼠标移动到目标窗口上单击，点击「翻译」
6. **全屏模式**：切换到「全屏」标签，直接点击「翻译」
7. 翻译结果会以浮窗显示在选区附近，滚动页面停下后会自动重新翻译

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Alt+S` | 截图翻译（区域/窗口） |
| `Ctrl+Alt+F` | 全屏翻译 |
| `Esc` | 取消截图 / 关闭翻译结果 |

## 设置说明

### 常规

- **主题**：浅色 / 深色 / 跟随系统
- **目标语言**：翻译的目标语种（默认简体中文）
- **默认框选模式**：区域 / 窗口 / 全屏
- **关闭主窗口时最小化到托盘**

### 翻译服务

- **本地模型**：选择 .gguf 文件，设置 GPU 层数、上下文长度、推理参数
- **API 接口**：配置 OpenAI 兼容 API（Base URL、API Key、模型名）
- 预置 DeepSeek / OpenAI / Ollama / vLLM 快捷配置

### OCR 识别

- **图像放大倍数**：画面较小时自动放大以提高识别率
- **智能合并段落**：将识别出的文字行智能合并为段落
- **最低置信度**：过滤低质量识别结果

### 实时翻译

- **检测间隔**：多久检测一次画面变化（默认 500ms）
- **稳定判定时间**：画面停止变化后多久触发翻译（默认 800ms）
- **变化灵敏度**：数值越小越灵敏

### 显示

- **结果窗口透明度**：40% - 100%
- **翻译结果字号**：10px - 32px
- **始终置顶**：翻译结果窗口是否置顶显示
- **自动复制译文**：翻译完成后自动复制到剪贴板

## 模型参数

Hy-MT2-1.8B 推荐推理参数（已内置默认值）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| temperature | 0.7 | 生成温度 |
| top_p | 0.6 | 核采样概率 |
| top_k | 20 | 顶部采样数 |
| repeat_penalty | 1.05 | 重复惩罚 |
| max_tokens | 2048 | 最大生成长度 |
| n_ctx | 4096 | 上下文长度 |

## 文件结构

```
屏幕翻译/
├── main.py                 # 程序入口
├── run.bat                 # 快捷启动
├── requirements.txt        # 依赖列表
├── app/
│   ├── config.py           # 配置管理
│   ├── core/
│   │   ├── win_tools.py    # Windows API (窗口枚举/自启动)
│   │   ├── capture.py      # 屏幕捕获与图像比较
│   │   ├── hotkeys.py      # 全局热键
│   │   └── pipeline.py     # 翻译调度管线
│   ├── ocr/
│   │   └── engine.py       # RapidOCR 封装
│   ├── translate/
│   │   ├── local_llm.py    # llama.cpp 本地推理
│   │   ├── openai_api.py   # OpenAI 兼容 API
│   │   └── service.py      # 翻译服务管理
│   └── ui/
│       ├── theme.py        # 主题样式
│       ├── icons.py        # 图标生成
│       ├── overlay.py      # 截图遮罩窗口
│       ├── result_window.py # 翻译结果浮窗
│       ├── history_widget.py # 历史记录页面
│       └── main_window.py  # 设置主窗口
```

## 常见问题

**Q: 启动后没有反应？**
A: 检查 Python 版本 >= 3.9，确认 PySide6 安装正确。查看 `app.log` 日志。

**Q: 全局热键不生效？**
A: 可能需要管理员权限运行。右键 `run.bat` → 以管理员身份运行。

**Q: 模型加载失败？**
A: 确认已安装 `llama-cpp-python`，GGUF 文件路径正确。CPU 模式无需额外配置。

**Q: OCR 识别不准？**
A: 尝试在 OCR 设置中调高「图像放大倍数」，确保截图区域清晰。

**Q: 如何使用 GPU 加速？**
A: 安装 CUDA 版 llama-cpp-python，在模型设置中设置 GPU 卸载层数 > 0。

## 技术栈

- **UI 框架**: PySide6 (Qt6)
- **屏幕捕获**: mss
- **OCR**: RapidOCR (ONNX Runtime, 离线)
- **本地推理**: llama-cpp-python + Hy-MT2-1.8B GGUF
- **API 翻译**: requests (OpenAI 兼容接口)
- **全局热键**: keyboard

## 许可

MIT License
