# Night-Night Kiss 晚安吻

伴我入睡，文字和月光。

## 功能特性

- **双模式播放**：播客模式（沉浸式背景 + 滚动字幕）与听书模式（纯文本阅读）
- **智能章节切分**：上传 TXT 自动识别章节，支持长文本分段合成
- **TTS 引擎管理**：网页内一键启动/关闭 GPT-SoVITS 引擎，无需手动操作
- **声音模型上传**：支持上传 GPT/SoVITS 权重和参考音频，在线配置
- **音频缓存**：合成结果自动缓存，切换声音模型时自动清理
- **局域网二维码**：扫码即可在手机端访问，随时随地听书
- **阅读进度**：自动保存阅读进度，支持历史记录和续听

## 快速开始

### 环境要求

- Python 3.10+
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 语音合成引擎（可选）

### 安装运行

1. 克隆或下载本项目
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 双击 `run.bat`（Windows）或 `run.command`（Mac）启动程序
4. 浏览器会自动打开 http://localhost:5200

### 配置 TTS 引擎

> 没有 TTS 引擎时程序仍可运行，但无法进行语音合成。

1. 下载 [GPT-SoVITS 整合包](https://github.com/RVC-Boss/GPT-SoVITS/releases)
2. 解压到任意目录（如 `D:\GPT-SoVITS`）
3. 在网页「配置」页面：
   - 填写「引擎目录」路径（如 `D:\GPT-SoVITS`）
   - 点击「自动检测」可自动查找
   - 点击「启动引擎」即可运行
4. 上传声音模型文件（.pth/.ckpt）和参考音频（3~15秒 .wav）
5. 填写「参考音频文本」（参考音频里说了什么）

### 开始使用

1. 在「配置」页面上传 TXT 书籍
2. 在「书架」选择书籍
3. 选择「播客模式」或「听书模式」开始听书
4. 点击右上角二维码图标，手机扫码可在移动端访问

## 目录结构

```
night-kiss/
├── run.bat             ← Windows 启动脚本
├── run.command         ← Mac 启动脚本
├── requirements.txt    ← Python 依赖
├── app/
│   ├── server.py       ← 后端主程序
│   ├── chapter_split.py← 章节切分
│   └── web/            ← 前端（静态文件）
│       ├── index.html
│       ├── style.css
│       └── app.js
└── data/               ← 用户数据（自动创建）
    ├── voice/          ← 声音模型
    ├── books/          ← 上传的书籍
    ├── background.jpg  ← 播客背景图
    ├── books.json      ← 书籍元数据
    ├── progress.json   ← 阅读进度
    └── engine_config.json ← 引擎配置
```

## 数据说明

- 所有用户数据保存在 `data/` 目录下，只要该目录不被删除，数据就不会丢失
- 可以将整个 `night-kiss` 文件夹拷贝到其他电脑上直接使用
- `data/` 目录下的文件已被 `.gitignore` 忽略，不会被提交到 Git

## 技术栈

- **后端**：Flask + requests
- **前端**：原生 HTML/CSS/JavaScript（无框架依赖）
- **TTS 引擎**：[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) v4
- **二维码**：Python qrcode 库（服务端生成）

## 许可证

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE) 授权。

允许个人学习、修改和非商业使用，禁止用于商业盈利目的。
