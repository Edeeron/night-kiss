# Night-Night Kiss 晚安吻

用 AI 的声音，陪你读每一本书。

## 快速开始

1. 双击 `run.bat`（Windows）或 `run.command`（Mac）启动程序
2. 浏览器会自动打开 http://localhost:5200
3. 在「配置」页面上传声音模型、TXT 书籍和背景图片
4. 在「书架」选择书籍开始听书

## TTS 引擎配置

本程序使用 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 作为语音合成引擎。

1. 下载 GPT-SoVITS 整合包
2. 将整合包内容解压到 `engine/` 目录
3. 先运行 `engine/go-api.bat` 启动 TTS 引擎
4. 再运行 `run.bat` 启动主程序

> 在没有 TTS 引擎的情况下，程序仍可运行，但无法进行语音合成。

## 目录结构

```
night-kiss/
├── run.bat             ← Windows 启动脚本
├── run.command         ← Mac 启动脚本
├── app/
│   ├── server.py       ← 后端主程序
│   ├── chapter_split.py← 章节切分
│   └── web/            ← 前端（静态文件）
│       ├── index.html
│       ├── style.css
│       └── app.js
├── engine/             ← GPT-SoVITS 整合包
│   └── go-api.bat      ← 启动 TTS API
└── data/               ← 用户数据
    ├── voice/          ← 声音模型
    ├── books/          ← 上传的书籍
    ├── background.jpg  ← 播客背景图
    └── progress.json   ← 阅读进度
```

## 数据说明

所有用户数据保存在 `data/` 目录下，只要该目录不被删除，数据就不会丢失。
可以将整个 `night-kiss` 文件夹拷贝到其他电脑上直接使用。
