"""
Night-Night Kiss (晚安吻) - 后端主程序
本地听书服务，集成 GPT-SoVITS TTS 引擎
"""

import os
import sys
import json
import time
import webbrowser
import threading
from pathlib import Path

import subprocess
import requests
from flask import (
    Flask, request, jsonify, send_file,
    send_from_directory, Response
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 路径配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VOICE_DIR = DATA_DIR / "voice"
BOOKS_DIR = DATA_DIR / "books"
BACKGROUND_FILE = DATA_DIR / "background.jpg"
BOOKS_JSON = DATA_DIR / "books.json"
PROGRESS_JSON = DATA_DIR / "progress.json"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Flask 初始化
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app = Flask(__name__, static_folder=str(Path(__file__).parent / "web"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TTS 引擎配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TTS_CONFIG = {
    "api_url": "http://127.0.0.1:9880/tts",
    "engine_dir": str(BASE_DIR / "engine"),
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 允许的文件类型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE_EXTS = {".pth", ".ckpt", ".pt", ".onnx", ".wav", ".mp3", ".flac"}
TXT_EXTS = {".txt"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

ENGINE_CONFIG_FILE = DATA_DIR / "engine_config.json"


def load_engine_config():
    """加载引擎配置"""
    return load_json(ENGINE_CONFIG_FILE, {
        "api_url": "http://127.0.0.1:9880/tts",
        "engine_dir": str(BASE_DIR / "engine"),
    })


def save_engine_config(cfg):
    """保存引擎配置"""
    save_json(ENGINE_CONFIG_FILE, cfg)


# 权重加载状态
_weights_loaded = False


def load_trained_weights():
    """通过 API 加载用户训练的 GPT 和 SoVITS 权重"""
    global _weights_loaded
    cfg = load_engine_config()
    api_url = cfg.get("api_url", "http://127.0.0.1:9880/tts")
    base_url = api_url.rsplit("/", 1)[0] if "/tts" in api_url else api_url

    gpt_w = cfg.get("gpt_weights", "")
    sovits_w = cfg.get("sovits_weights", "")

    ok = True
    if gpt_w and Path(gpt_w).exists():
        try:
            r = requests.get(f"{base_url}/set_gpt_weights", params={"weights_path": gpt_w}, timeout=30)
            if r.status_code != 200:
                print(f"  [警告] 加载 GPT 权重失败: {r.text}")
                ok = False
            else:
                print(f"  ✓ GPT 权重已加载: {Path(gpt_w).name}")
        except Exception as e:
            print(f"  [警告] 加载 GPT 权重异常: {e}")
            ok = False

    if sovits_w and Path(sovits_w).exists():
        try:
            r = requests.get(f"{base_url}/set_sovits_weights", params={"weights_path": sovits_w}, timeout=30)
            if r.status_code != 200:
                print(f"  [警告] 加载 SoVITS 权重失败: {r.text}")
                ok = False
            else:
                print(f"  ✓ SoVITS 权重已加载: {Path(sovits_w).name}")
        except Exception as e:
            print(f"  [警告] 加载 SoVITS 权重异常: {e}")
            ok = False

    if ok and (gpt_w or sovits_w):
        _weights_loaded = True
    return ok


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ensure_dirs():
    """确保所有数据目录存在"""
    for d in [DATA_DIR, VOICE_DIR, BOOKS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_json(path, default=None):
    """安全加载 JSON 文件"""
    if default is None:
        default = {}
    try:
        p = Path(path)
        if p.exists() and p.stat().st_size > 2:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    """保存 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_text_file(filepath):
    """尝试多种编码读取文本文件"""
    for enc in ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def find_voice_model():
    """查找已上传的参考音频文件"""
    if not VOICE_DIR.exists():
        return None
    for f in VOICE_DIR.iterdir():
        if f.suffix.lower() in {".wav", ".mp3", ".flac"}:
            return str(f)
    return None


def get_tts_engine_status():
    """检测 TTS 引擎是否可用"""
    cfg = load_engine_config()
    api_url = cfg.get("api_url", "http://127.0.0.1:9880/tts")
    base_url = api_url.rsplit("/", 1)[0] if "/tts" in api_url else api_url
    try:
        r = requests.get(base_url + "/", timeout=2)
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 前端页面
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 配置相关 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/config/voice", methods=["GET"])
def get_voice_config():
    """获取当前声音配置"""
    ref_audio = find_voice_model()
    cfg = load_engine_config()
    gpt_w = cfg.get("gpt_weights", "")
    sovits_w = cfg.get("sovits_weights", "")
    return jsonify({
        "gpt_weights": Path(gpt_w).name if gpt_w and Path(gpt_w).exists() else None,
        "sovits_weights": Path(sovits_w).name if sovits_w and Path(sovits_w).exists() else None,
        "ref_audio": Path(ref_audio).name if ref_audio else None,
        "engine_available": get_tts_engine_status(),
    })


@app.route("/api/upload/weights", methods=["POST"])
def upload_weights():
    """上传 GPT 或 SoVITS 权重文件"""
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "未选择文件"}), 400

    model_type = request.form.get("model_type", "")
    if model_type not in ("gpt", "sovits"):
        return jsonify({"error": "请指定 model_type (gpt 或 sovits)"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pth", ".ckpt", ".pt"}:
        return jsonify({"error": f"不支持的格式: {ext}，仅支持 .pth / .ckpt / .pt"}), 400

    # 保存到 voice 目录
    if VOICE_DIR.exists():
        for f in VOICE_DIR.iterdir():
            if f.suffix.lower() in {".pth", ".ckpt", ".pt"}:
                # 只清理同类型的旧文件
                old_type = f.stem.split("_")[0] if "_" in f.stem else ""
                if model_type == "gpt" and "-e" in f.stem:
                    f.unlink()
                elif model_type == "sovits" and "_e" in f.stem:
                    f.unlink()

    filepath = VOICE_DIR / file.filename
    file.save(str(filepath))

    # 更新引擎配置中的权重路径
    cfg = load_engine_config()
    cfg[f"{model_type}_weights"] = str(filepath)
    save_engine_config(cfg)

    # 重置权重加载状态，下次合成时会重新加载
    global _weights_loaded
    _weights_loaded = False

    return jsonify({
        "success": True,
        "model_type": model_type,
        "filename": file.filename,
    })


@app.route("/api/upload/book", methods=["POST"])
def upload_book():
    """上传 TXT 书籍文件"""
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "未选择文件"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in TXT_EXTS:
        return jsonify({"error": "仅支持 .txt 文件"}), 400

    # 保存原始文件
    safe_name = file.filename.replace(" ", "_")
    filepath = BOOKS_DIR / safe_name
    file.save(str(filepath))

    # 读取文本内容
    text = read_text_file(str(filepath))
    if text is None:
        return jsonify({"error": "无法读取文件内容，请确认编码"}), 400

    # 切分章节
    from chapter_split import split_chapters
    chapters = split_chapters(str(filepath))

    # 保存章节 JSON
    book_id = str(int(time.time()))
    book_dir = BOOKS_DIR / book_id
    book_dir.mkdir(exist_ok=True)

    chapters_data = []
    for i, ch in enumerate(chapters):
        chapter_path = book_dir / f"chapter_{i:03d}.txt"
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write(ch["text"])
        chapters_data.append({
            "index": i,
            "title": ch["title"],
            "text": ch["text"],
            "char_count": len(ch["text"]),
            "file": str(chapter_path),
        })

    # 保存书籍元数据
    books = load_json(BOOKS_JSON, [])
    book_entry = {
        "id": book_id,
        "title": request.form.get("title") or Path(file.filename).stem,
        "original_file": safe_name,
        "chapters": chapters_data,
        "chapter_count": len(chapters_data),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    books.append(book_entry)
    save_json(BOOKS_JSON, books)

    return jsonify({
        "success": True,
        "book_id": book_id,
        "title": book_entry["title"],
        "chapter_count": len(chapters_data),
    })


@app.route("/api/upload/background", methods=["POST"])
def upload_background():
    """上传播客背景图片"""
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "未选择文件"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in IMAGE_EXTS:
        return jsonify({"error": f"不支持的图片格式: {ext}"}), 400

    # 保存背景图（统一命名）
    save_path = DATA_DIR / f"background{ext}"
    file.save(str(save_path))

    # 清理其他格式的背景图
    for e in IMAGE_EXTS:
        other = DATA_DIR / f"background{e}"
        if other.exists() and other != save_path:
            other.unlink()

    return jsonify({
        "success": True,
        "filename": save_path.name,
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 书架 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/books", methods=["GET"])
def list_books():
    """获取书架列表"""
    books = load_json(BOOKS_JSON, [])
    result = []
    for b in books:
        result.append({
            "id": b["id"],
            "title": b["title"],
            "chapter_count": b.get("chapter_count", len(b.get("chapters", []))),
            "created_at": b.get("created_at", ""),
        })
    return jsonify(result)


@app.route("/api/books/<book_id>", methods=["GET"])
def get_book(book_id):
    """获取单本书籍详情"""
    books = load_json(BOOKS_JSON, [])
    for b in books:
        if b["id"] == book_id:
            chapters = []
            for ch in b.get("chapters", []):
                chapters.append({
                    "index": ch["index"],
                    "title": ch["title"],
                    "char_count": ch.get("char_count", len(ch.get("text", ""))),
                })
            return jsonify({
                "id": b["id"],
                "title": b["title"],
                "chapters": chapters,
                "chapter_count": b.get("chapter_count", len(chapters)),
                "created_at": b.get("created_at", ""),
            })
    return jsonify({"error": "书籍不存在"}), 404


@app.route("/api/books/<book_id>/chapters/<int:chapter_idx>", methods=["GET"])
def get_chapter(book_id, chapter_idx):
    """获取章节内容"""
    books = load_json(BOOKS_JSON, [])
    for b in books:
        if b["id"] == book_id:
            chapters = b.get("chapters", [])
            if 0 <= chapter_idx < len(chapters):
                ch = chapters[chapter_idx]
                # 尝试从文件读取
                ch_file = ch.get("file", "")
                if ch_file and Path(ch_file).exists():
                    text = read_text_file(ch_file)
                else:
                    text = ch.get("text", "")
                return jsonify({
                    "index": ch["index"],
                    "title": ch["title"],
                    "text": text,
                    "book_title": b["title"],
                })
            return jsonify({"error": "章节不存在"}), 404
    return jsonify({"error": "书籍不存在"}), 404


@app.route("/api/books/<book_id>", methods=["DELETE"])
def delete_book(book_id):
    """删除书籍"""
    books = load_json(BOOKS_JSON, [])
    target = None
    for b in books:
        if b["id"] == book_id:
            target = b
            break
    if not target:
        return jsonify({"error": "书籍不存在"}), 404

    # 删除章节文件夹
    book_dir = BOOKS_DIR / book_id
    if book_dir.exists():
        import shutil
        shutil.rmtree(str(book_dir))

    # 删除上传的原始文件
    original_file = target.get("original_file", "")
    if original_file:
        orig_path = BOOKS_DIR / original_file
        if orig_path.exists():
            orig_path.unlink()

    new_books = [b for b in books if b["id"] != book_id]
    save_json(BOOKS_JSON, new_books)

    # 清理进度
    progress = load_json(PROGRESS_JSON, {})
    progress.pop(book_id, None)
    save_json(PROGRESS_JSON, progress)

    return jsonify({"success": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 进度 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/progress", methods=["GET"])
def get_progress():
    """获取所有阅读进度"""
    return jsonify(load_json(PROGRESS_JSON, {}))


@app.route("/api/progress/<book_id>", methods=["POST"])
def save_progress(book_id):
    """保存阅读进度"""
    data = request.get_json()
    progress = load_json(PROGRESS_JSON, {})
    progress[book_id] = {
        "chapter_index": data.get("chapter_index", 0),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "book_title": data.get("book_title", ""),
        "mode": data.get("mode", "reader"),
    }
    save_json(PROGRESS_JSON, progress)
    return jsonify({"success": True})


@app.route("/api/progress", methods=["DELETE"])
def clear_progress():
    """清空所有阅读进度"""
    save_json(PROGRESS_JSON, {})
    return jsonify({"success": True})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 背景图 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/background/image")
def get_background():
    """获取背景图片"""
    if BACKGROUND_FILE.exists():
        return send_file(str(BACKGROUND_FILE))
    # 查找其他格式
    for ext in IMAGE_EXTS:
        p = DATA_DIR / f"background{ext}"
        if p.exists():
            return send_file(str(p))
    return jsonify({"error": "未设置背景图"}), 404


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 音频合成 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/audio/<book_id>/<int:chapter_idx>", methods=["POST"])
def synthesize_audio(book_id, chapter_idx):
    """调用 TTS 引擎合成章节音频"""
    # 获取章节文本
    books = load_json(BOOKS_JSON, [])
    book = None
    for b in books:
        if b["id"] == book_id:
            book = b
            break
    if book is None:
        return jsonify({"error": "书籍不存在"}), 404

    chapters = book.get("chapters", [])
    if chapter_idx >= len(chapters):
        return jsonify({"error": "章节不存在"}), 404

    ch = chapters[chapter_idx]
    ch_file = ch.get("file", "")
    if ch_file and Path(ch_file).exists():
        text = read_text_file(ch_file)
    else:
        text = ch.get("text", "")

    if not text or not text.strip():
        return jsonify({"error": "章节内容为空"}), 400

    # 检查参考音频
    ref_audio = find_voice_model()
    if not ref_audio:
        return jsonify({"error": "未找到参考音频，请上传一段 3~15 秒的 .wav 音频"}), 400

    # 自动加载训练的权重（首次或引擎重启后）
    if not _weights_loaded:
        load_trained_weights()

    # 调用 GPT-SoVITS api_v2
    cfg = load_engine_config()
    api_url = cfg.get("api_url", TTS_CONFIG["api_url"])
    prompt_text = cfg.get("prompt_text", "")
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": ref_audio,
        "prompt_lang": "zh",
        "prompt_text": prompt_text,
        "top_k": 10,
        "top_p": 0.95,
        "temperature": 0.8,
        "text_split_method": "cut5",
        "batch_size": 1,
        "speed_factor": 1.0,
        "streaming_mode": False,
        "repetition_penalty": 1.35,
        "parallel_infer": True,
    }

    def generate():
        try:
            resp = requests.post(api_url, json=payload, stream=True, timeout=300)
            if resp.status_code == 200:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            else:
                yield b""
        except requests.ConnectionError:
            yield b""
        except Exception:
            yield b""

    def stream_audio():
        audio_data = b""
        for chunk in generate():
            audio_data += chunk

        if not audio_data:
            # TTS 引擎不可用，返回静音占位
            return Response(
                b"",
                status=503,
                mimetype="application/octet-stream",
                headers={
                    "X-Error": "TTS引擎不可用",
                    "X-Message": "请先启动 TTS 引擎，再测试连接",
                }
            )

        return Response(
            audio_data,
            status=200,
            mimetype="audio/wav",
            headers={"Content-Length": str(len(audio_data))},
        )

    return stream_audio()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 引擎配置 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/config/engine", methods=["GET"])
def get_engine_config():
    """获取引擎配置"""
    return jsonify(load_engine_config())


@app.route("/api/config/engine", methods=["POST"])
def set_engine_config():
    """更新引擎配置"""
    data = request.get_json()
    cfg = load_engine_config()
    if "api_url" in data:
        cfg["api_url"] = data["api_url"].strip()
    if "engine_dir" in data:
        cfg["engine_dir"] = data["engine_dir"].strip()
    if "prompt_text" in data:
        cfg["prompt_text"] = data["prompt_text"].strip()
    save_engine_config(cfg)
    return jsonify({"success": True, "config": cfg})


@app.route("/api/engine/test", methods=["POST"])
def test_engine():
    """测试引擎连接"""
    data = request.get_json() or {}
    api_url = data.get("api_url", load_engine_config().get("api_url", ""))
    base_url = api_url.rsplit("/", 1)[0] if "/tts" in api_url else api_url
    try:
        r = requests.get(base_url + "/", timeout=3)
        return jsonify({"success": True, "message": "连接成功"})
    except Exception as e:
        return jsonify({"success": False, "message": f"连接失败: {e}"})


@app.route("/api/engine/auto-detect", methods=["POST"])
def auto_detect_engine():
    """自动检测引擎目录"""
    candidates = [
        BASE_DIR / "engine",
        BASE_DIR / "GPT-SoVITS",
        Path.home() / "GPT-SoVITS",
    ]
    cfg = load_engine_config()
    if cfg.get("engine_dir"):
        candidates.insert(0, Path(cfg["engine_dir"]))

    for d in candidates:
        if d.exists() and (d / "go-webui.py").exists():
            return jsonify({"found": True, "path": str(d)})
        if d.exists() and (d / "api_v2.py").exists():
            return jsonify({"found": True, "path": str(d)})
    return jsonify({"found": False})


@app.route("/api/engine/start", methods=["POST"])
def start_engine():
    """从指定目录启动 TTS 引擎"""
    global _weights_loaded
    _weights_loaded = False  # 重启引擎时重置权重状态
    cfg = load_engine_config()
    engine_dir = Path(cfg.get("engine_dir", ""))

    if not engine_dir.exists():
        return jsonify({"error": "引擎目录不存在，请检查路径"})

    # 优先用 api_v2.py（轻量 API 模式），其次 go-webui.bat
    runtime_python = engine_dir / "runtime" / "python.exe"
    api_v2 = engine_dir / "api_v2.py"

    try:
        if runtime_python.exists() and api_v2.exists():
            # 用引擎自带的 Python 运行 api_v2
            if sys.platform == "win32":
                subprocess.Popen(
                    ["cmd", "/c", "start", "GPT-SoVITS API",
                     str(runtime_python), str(api_v2)],
                    cwd=str(engine_dir),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                subprocess.Popen(
                    [str(runtime_python), str(api_v2)],
                    cwd=str(engine_dir),
                )
            return jsonify({"success": True, "message": "API 引擎启动中，请等待 10~20 秒后测试连接"})

        # 回退到 bat 启动
        bat_file = None
        for name in ["go-webui.bat", "go-api.bat"]:
            if (engine_dir / name).exists():
                bat_file = str(engine_dir / name)
                break

        if not bat_file:
            return jsonify({"error": "未找到 api_v2.py 或启动脚本"})

        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd", "/c", "start", bat_file],
                cwd=str(engine_dir),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            subprocess.Popen(["bash", bat_file], cwd=str(engine_dir))

        return jsonify({"success": True, "message": "引擎启动中，请稍等几秒后测试连接"})
    except Exception as e:
        return jsonify({"error": f"启动失败: {e}"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 系统 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route("/api/status", methods=["GET"])
def system_status():
    """系统状态检查"""
    ref_audio = find_voice_model()
    cfg = load_engine_config()
    has_weights = bool(cfg.get("gpt_weights") or cfg.get("sovits_weights"))
    bg_exists = BACKGROUND_FILE.exists() or any(
        (DATA_DIR / f"background{e}").exists() for e in IMAGE_EXTS
    )
    return jsonify({
        "tts_engine": get_tts_engine_status(),
        "voice_model": has_weights,
        "background": bg_exists,
        "books_count": len(load_json(BOOKS_JSON, [])),
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 启动
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def open_browser():
    """延迟打开浏览器"""
    import time as _t
    _t.sleep(1.5)
    webbrowser.open("http://localhost:5200")


if __name__ == "__main__":
    ensure_dirs()

    print()
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║                                           ║")
    print("  ║     Night-Night Kiss  晚安吻              ║")
    print("  ║     用 AI 的声音，陪你读每一本书           ║")
    print("  ║                                           ║")
    print("  ╚═══════════════════════════════════════════╝")
    print()
    print(f"  地址: http://localhost:5200")
    print(f"  数据: {DATA_DIR}")
    print()

    tts_ok = get_tts_engine_status()
    if tts_ok:
        print("  ✓ TTS 引擎已连接")
    else:
        print("  ✗ TTS 引擎未启动 (可先运行 engine/go-api.bat)")
    print()

    # 自动打开浏览器
    threading.Thread(target=open_browser, daemon=True).start()

    app.run(host="0.0.0.0", port=5200, debug=False)
