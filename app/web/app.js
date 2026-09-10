/**
 * Night-Night Kiss (晚安吻) - 前端主逻辑
 * 书架 · 历史阅读 · 配置 · 播放器
 */

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   状态管理
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

const S = {
    currentView: "bookshelf",
    books: [],
    progress: {},
    currentBook: null,
    currentChapter: 0,
    isPlaying: false,
    continuous: false,
    mode: "podcast",       // "podcast" | "reader"
    audioCtx: null,
    audioSource: null,
    audioBuffer: null,
    audioStartTime: 0,
    audioPauseOffset: 0,
    audioDuration: 0,
    progressTimer: null,
    subtitleTimer: null,
    audioAbort: null,      // AbortController for cancelling fetch
    audioRequestId: 0,     // 请求序号，防止过期回调
};

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   工具函数
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

/* 播放器 SVG 图标 */
const ICON_PLAY = `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="7.5 4 20 12 7.5 20"/></svg>`;
const ICON_PAUSE = `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="5.5" y="3.5" width="4.5" height="17" rx="1.5"/><rect x="14" y="3.5" width="4.5" height="17" rx="1.5"/></svg>`;
const ICON_BOOK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`;
const ICON_BOOK_OPEN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`;

function switchView(name) {
    S.currentView = name;
    $$(".view").forEach((v) => (v.style.display = "none"));
    $(`#view-${name}`).style.display = "";
    $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
    if (name === "bookshelf") loadBooks();
    if (name === "history") loadHistory();
    if (name === "settings") loadSettings();
}

function toast(msg, ms) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(el._tid);
    el._tid = setTimeout(() => el.classList.remove("show"), ms || 2200);
}

async function api(path, opts) {
    const res = await fetch(`/api/${path}`, opts);
    return res.json();
}

async function apiUpload(path, file) {
    const fd = new FormData();
    fd.append("file", file);
    return api(path, { method: "POST", body: fd });
}

function fmtDate(s) {
    if (!s) return "";
    return s.slice(0, 10);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   启动
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

document.addEventListener("DOMContentLoaded", async () => {
    // 隐藏启动屏
    setTimeout(() => {
        const sp = $("#splash-screen");
        sp.classList.add("hide");
        setTimeout(() => sp.remove(), 700);
    }, 1400);

    bindEvents();
    await loadBooks();
    loadSettings();

    // 二维码按钮
    $("#btn-qrcode")?.addEventListener("click", async () => {
        const r = await api("local-url");
        if (!r.url) return toast("无法获取局域网地址");
        $("#qrcode-url").textContent = r.url;
        // 显示服务端生成的二维码图片
        const container = $("#qrcode-container");
        container.innerHTML = `<img src="/api/qrcode?t=${Date.now()}" alt="二维码" style="width:100%;height:100%;">`;
        $("#modal-qrcode").style.display = "";
    });
    $("#modal-qrcode .modal-backdrop")?.addEventListener("click", () => {
        $("#modal-qrcode").style.display = "none";
    });
});

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   书架
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function loadBooks() {
    const books = await api("books");
    S.books = Array.isArray(books) ? books : [];
    renderBooks();
}

function renderBooks() {
    const grid = $("#books-grid");
    const empty = $("#books-empty");

    if (!S.books.length) {
        grid.innerHTML = "";
        empty.style.display = "";
        return;
    }
    empty.style.display = "none";

    grid.innerHTML = S.books
        .map(
            (b) => `
        <div class="book-card" data-id="${b.id}">
            <button class="book-delete" data-del="${b.id}" title="删除">✕</button>
            <div class="book-icon">${ICON_BOOK}</div>
            <div class="book-title">${esc(b.title)}</div>
            <div class="book-meta">${b.chapter_count} 章 · ${fmtDate(b.created_at)}</div>
        </div>`
        )
        .join("");

    // 点击书籍 → 打开详情
    grid.querySelectorAll(".book-card").forEach((card) => {
        card.addEventListener("click", (e) => {
            if (e.target.closest(".book-delete")) return;
            openBookModal(card.dataset.id);
        });
    });

    // 删除按钮
    grid.querySelectorAll("[data-del]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            deleteBook(btn.dataset.del);
        });
    });
}

async function deleteBook(id) {
    if (!confirm("确定要删除这本书吗？")) return;
    await api(`books/${id}`, { method: "DELETE" });
    toast("已删除");
    loadBooks();
}

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   历史阅读
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function loadHistory() {
    const progress = await api("progress");
    S.progress = progress || {};
    renderHistory();
}

function renderHistory() {
    const list = $("#history-list");
    const empty = $("#history-empty");
    const keys = Object.keys(S.progress);

    if (!keys.length) {
        list.innerHTML = "";
        empty.style.display = "";
        return;
    }
    empty.style.display = "none";

    // 按时间倒序
    keys.sort((a, b) => (S.progress[b].timestamp || "").localeCompare(S.progress[a].timestamp || ""));

    list.innerHTML = keys
        .map((id) => {
            const p = S.progress[id];
            return `
            <div class="history-card" data-hid="${id}">
                <div class="h-icon">${ICON_BOOK_OPEN}</div>
                <div class="h-info">
                    <div class="h-title">${esc(p.book_title || id)}</div>
                    <div class="h-meta">上次: 第 ${p.chapter_index + 1} 章 · ${p.mode === "podcast" ? "播客模式" : "听书模式"} · ${p.timestamp || ""}</div>
                    <div class="h-progress-bar"><div class="h-progress-fill" style="width:${p._pct || 0}%"></div></div>
                </div>
            </div>`;
        })
        .join("");

    list.querySelectorAll(".history-card").forEach((card) => {
        card.addEventListener("click", () => resumeFromHistory(card.dataset.hid));
    });
}

async function resumeFromHistory(bookId) {
    const p = S.progress[bookId];
    if (!p) return toast("无记录");

    const book = await api(`books/${bookId}`);
    if (book.error) return toast("书籍不存在");

    S.currentBook = book;
    S.currentChapter = p.chapter_index || 0;
    S.mode = p.mode || "reader";
    showPlayer();
    loadChapterContent(bookId, S.currentChapter);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   配置页
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function loadSettings() {
    // 模型权重 & 参考音频状态
    const voice = await api("config/voice");
    const gws = $("#gpt-weights-status");
    const sws = $("#sovits-weights-status");
    const ras = $("#ref-audio-status");
    if (voice.gpt_weights) {
        gws.innerHTML = `<span class="status-dot on"></span>${esc(voice.gpt_weights)}`;
    } else {
        gws.innerHTML = `<span class="status-dot off"></span>未上传 (.ckpt / .pth)`;
    }
    if (voice.sovits_weights) {
        sws.innerHTML = `<span class="status-dot on"></span>${esc(voice.sovits_weights)}`;
    } else {
        sws.innerHTML = `<span class="status-dot off"></span>未上传 (.ckpt / .pth)`;
    }
    if (voice.ref_audio) {
        ras.innerHTML = `<span class="status-dot on"></span>${esc(voice.ref_audio)}`;
    } else {
        ras.innerHTML = `<span class="status-dot off"></span>未上传 (3~15秒 .wav)`;
    }

    // TTS 引擎
    const status = await api("status");
    const ts = $("#tts-status");
    if (status.tts_engine) {
        ts.innerHTML = `<span class="status-dot on"></span>已连接`;
    } else {
        ts.innerHTML = `<span class="status-dot off"></span>未连接`;
    }

    // 加载引擎配置
    const engineCfg = await api("config/engine");
    $("#input-engine-url").value = engineCfg.api_url || "http://127.0.0.1:9880/tts";
    $("#input-engine-dir").value = engineCfg.engine_dir || "";
    $("#input-prompt-text").value = engineCfg.prompt_text || "";

    // 背景图
    const bgImg = new Image();
    bgImg.onload = () => {
        $("#bg-status").innerHTML = `<span class="status-dot on"></span>已设置`;
    };
    bgImg.onerror = () => {
        $("#bg-status").innerHTML = `<span class="status-dot off"></span>未设置`;
    };
    bgImg.src = "/api/background/image?t=" + Date.now();

    // 引擎状态角标
    const es = $("#engine-status");
    es.innerHTML = status.tts_engine
        ? `<span class="status-dot on"></span>引擎就绪`
        : `<span class="status-dot off"></span>引擎离线`;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   文件上传
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function bindUploads() {
    // GPT 权重上传
    $("#input-gpt-weights").addEventListener("change", async (e) => {
        const f = e.target.files[0];
        if (!f) return;
        toast("正在上传 GPT 权重...");
        const fd = new FormData();
        fd.append("file", f);
        fd.append("model_type", "gpt");
        const r = await api("upload/weights", { method: "POST", body: fd });
        if (r.error) toast("错误: " + r.error);
        else {
            toast("GPT 权重已保存 ✓");
            if (r.cache_cleared) toast("已清除旧音频缓存", 1500);
        }
        e.target.value = "";
        loadSettings();
    });

    // SoVITS 权重上传
    $("#input-sovits-weights").addEventListener("change", async (e) => {
        const f = e.target.files[0];
        if (!f) return;
        toast("正在上传 SoVITS 权重...");
        const fd = new FormData();
        fd.append("file", f);
        fd.append("model_type", "sovits");
        const r = await api("upload/weights", { method: "POST", body: fd });
        if (r.error) toast("错误: " + r.error);
        else {
            toast("SoVITS 权重已保存 ✓");
            if (r.cache_cleared) toast("已清除旧音频缓存", 1500);
        }
        e.target.value = "";
        loadSettings();
    });

    // 参考音频上传
    $("#input-ref-audio").addEventListener("change", async (e) => {
        const f = e.target.files[0];
        if (!f) return;
        toast("正在上传参考音频...");
        const r = await apiUpload("upload/voice", f);
        if (r.error) toast("错误: " + r.error);
        else {
            toast("参考音频已保存 ✓");
            if (r.cache_cleared) toast("已清除旧音频缓存", 1500);
        }
        e.target.value = "";
        loadSettings();
    });

    $("#input-book").addEventListener("change", async (e) => {
        const f = e.target.files[0];
        if (!f) return;
        toast("正在上传书籍，请稍候...");
        const r = await apiUpload("upload/book", f);
        if (r.error) toast("错误: " + r.error);
        else toast(`《${r.title}》已加入书架 ✓`);
        e.target.value = "";
        loadBooks();
    });

    $("#input-bg").addEventListener("change", async (e) => {
        const f = e.target.files[0];
        if (!f) return;
        toast("正在上传背景图...");
        const r = await apiUpload("upload/background", f);
        if (r.error) toast("错误: " + r.error);
        else toast("背景图已保存 ✓");
        e.target.value = "";
        loadSettings();
    });
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   书籍详情弹窗
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function openBookModal(bookId) {
    const book = await api(`books/${bookId}`);
    if (book.error) return toast(book.error);

    S.currentBook = book;
    $("#modal-book-title").textContent = book.title;
    $("#modal-book-info").textContent = `共 ${book.chapter_count} 章`;

    const list = $("#modal-chapter-list");
    list.innerHTML = book.chapters
        .map(
            (ch) => `
        <div class="chapter-item" data-ci="${ch.index}">
            <span class="ch-name">${esc(ch.title)}</span>
            <span class="ch-len">${ch.char_count} 字</span>
        </div>`
        )
        .join("");

    list.querySelectorAll(".chapter-item").forEach((el) => {
        el.addEventListener("click", () => {
            S.currentChapter = parseInt(el.dataset.ci);
            S.mode = "reader";
            closeModal();
            showPlayer();
            loadChapterContent(bookId, S.currentChapter);
        });
    });

    // 模式按钮
    $("#btn-podcast").onclick = () => {
        S.currentChapter = 0;
        S.mode = "podcast";
        closeModal();
        showPlayer();
        loadChapterContent(bookId, 0);
    };
    $("#btn-reader").onclick = () => {
        S.currentChapter = 0;
        S.mode = "reader";
        closeModal();
        showPlayer();
        loadChapterContent(bookId, 0);
    };

    // 显示弹窗
    $("#modal-book").style.display = "";
}

function closeModal() {
    $("#modal-book").style.display = "none";
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   播放器
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function showPlayer() {
    const player = $("#player");
    player.style.display = "";

    // 显示对应模式
    $("#player-podcast").style.display = S.mode === "podcast" ? "" : "none";
    $("#player-reader").style.display = S.mode === "reader" ? "" : "none";

    // 播客模式加载背景
    if (S.mode === "podcast") {
        $("#podcast-bg-img").src = "/api/background/image?t=" + Date.now();
    }

    // 填充章节选择器
    fillChapterSelect();
    saveProgress();
}

function fillChapterSelect() {
    const sel = $("#player-chapter-select");
    if (!S.currentBook) return;
    sel.innerHTML = S.currentBook.chapters
        .map((ch) => `<option value="${ch.index}"${ch.index === S.currentChapter ? " selected" : ""}>${esc(ch.title)}</option>`)
        .join("");
}

async function loadChapterContent(bookId, chapterIdx) {
    // 立即停止当前音频和未完成的请求，防止重叠
    stopAudio();
    if (S.audioAbort) {
        S.audioAbort.abort();
        S.audioAbort = null;
    }
    S.audioBuffer = null;

    const data = await api(`books/${bookId}/chapters/${chapterIdx}`);
    if (data.error) return toast(data.error);

    S.currentChapter = chapterIdx;

    // 更新 UI
    $("#player-chapter").textContent = data.title;
    $("#player-chapter-select").value = chapterIdx;

    // 同步章节进度到历史记录
    saveProgress();

    if (S.mode === "podcast") {
        setSubtitle(data.text);
    }
    if (S.mode === "reader") {
        $("#reader-chapter-title").textContent = data.title;
        $("#reader-content").textContent = data.text;
    }

    // 加载音频
    await loadAudio(bookId, chapterIdx);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   音频播放 (Web Audio API)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function loadAudio(bookId, chapterIdx) {
    // 取消之前的请求
    stopAudio();
    if (S.audioAbort) {
        S.audioAbort.abort();
    }
    const controller = new AbortController();
    S.audioAbort = controller;
    const myRequestId = ++S.audioRequestId;

    // 初始化 AudioContext
    if (!S.audioCtx) {
        S.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }

    toast("正在合成音频，请稍候...");

    // 启动合成进度轮询
    let progressTimer = null;
    const startProgressPolling = () => {
        progressTimer = setInterval(async () => {
            try {
                const r = await fetch(`/api/audio/${bookId}/${chapterIdx}/status`);
                const d = await r.json();
                if (d.synthesizing && myRequestId === S.audioRequestId) {
                    toast(`正在合成第 ${d.current}/${d.total} 段...`);
                }
            } catch (_) {}
        }, 2000);
    };
    const stopProgressPolling = () => {
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
    };

    try {
        // 先检查是否已有合成在进行（重入章节时避免重复 POST）
        const statusRes = await fetch(`/api/audio/${bookId}/${chapterIdx}/status`);
        const statusData = await statusRes.json();

        let res;
        if (statusData.synthesizing) {
            // 已有合成在进行，用等待循环轮询（不再另开 progressPolling 避免重复请求）
            toast("正在合成音频，请稍候...");
            for (let i = 0; i < 300; i++) {
                await new Promise(r => setTimeout(r, 1000));
                if (myRequestId !== S.audioRequestId) return;
                const sr = await fetch(`/api/audio/${bookId}/${chapterIdx}/status`);
                const sd = await sr.json();
                if (sd.cached) break;
                if (!sd.synthesizing) break;
                if (sd.current && sd.total) toast(`正在合成第 ${sd.current}/${sd.total} 段...`);
            }
            // 合成完成，取缓存文件
            res = await fetch(`/api/audio/${bookId}/${chapterIdx}`, {
                method: "POST",
                signal: controller.signal,
            });
        } else {
            // 没有进行中的合成，启动进度轮询后正常发起 POST
            startProgressPolling();
            res = await fetch(`/api/audio/${bookId}/${chapterIdx}`, {
                method: "POST",
                signal: controller.signal,
            });
        }

        stopProgressPolling();

        // 检查是否已被新请求取代
        if (myRequestId !== S.audioRequestId) return;

        const fromCache = res.headers.get("X-From-Cache") === "true";

        if (res.status === 503) {
            const raw = res.headers.get("X-Message") || "";
            const msg = raw ? decodeURIComponent(raw) : "TTS 引擎不可用";
            toast(msg, 3500);
            return;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            toast(err.error || "音频合成失败", 3000);
            return;
        }

        const arrayBuf = await res.arrayBuffer();
        // 再次检查是否已被新请求取代
        if (myRequestId !== S.audioRequestId) return;

        S.audioBuffer = await S.audioCtx.decodeAudioData(arrayBuf);
        S.audioDuration = S.audioBuffer.duration;
        S.audioPauseOffset = 0;

        toast(fromCache ? "缓存命中，开始播放" : "开始播放");
        playAudio();
    } catch (err) {
        stopProgressPolling();
        if (err.name === "AbortError") return; // 被取消，忽略
        console.error("Audio error:", err);
        toast("音频加载失败", 3000);
    }
}

function playAudio() {
    if (!S.audioBuffer || !S.audioCtx) return;

    // 先停掉可能还在播放的旧 source
    if (S.audioSource) {
        try {
            S.audioSource.onended = null;
            S.audioSource.stop();
        } catch (_) {}
        S.audioSource = null;
    }

    // 如果已播放完，从头开始
    if (S.audioPauseOffset >= S.audioDuration) {
        S.audioPauseOffset = 0;
    }

    S.audioSource = S.audioCtx.createBufferSource();
    S.audioSource.buffer = S.audioBuffer;
    S.audioSource.connect(S.audioCtx.destination);
    S.audioSource.onended = onTrackEnd;

    const offset = S.audioPauseOffset;
    S.audioSource.start(0, offset);
    S.audioStartTime = S.audioCtx.currentTime - offset;
    S.isPlaying = true;

    $("#btn-play-pause").innerHTML = ICON_PAUSE;
    startProgressTimer();
    if (S.mode === "podcast") startSubtitleTimer();
}

function pauseAudio() {
    if (S.audioSource) {
        S.audioSource.onended = null;
        S.audioSource.stop();
        S.audioSource = null;
    }
    S.audioPauseOffset = S.audioCtx.currentTime - S.audioStartTime;
    S.isPlaying = false;

    $("#btn-play-pause").innerHTML = ICON_PLAY;
    stopProgressTimer();
    stopSubtitleTimer();
}

function stopAudio() {
    if (S.audioSource) {
        try {
            S.audioSource.onended = null;
            S.audioSource.stop();
        } catch (_) {}
        S.audioSource = null;
    }
    S.isPlaying = false;
    S.audioPauseOffset = 0;
    stopProgressTimer();
    stopSubtitleTimer();
}

function onTrackEnd() {
    S.isPlaying = false;
    S.audioPauseOffset = S.audioDuration;
    $("#btn-play-pause").innerHTML = ICON_PLAY;
    stopProgressTimer();
    stopSubtitleTimer();
    $("#player-progress").style.width = "100%";

    if (S.continuous) {
        setTimeout(() => goNextChapter(), 800);
    }
}

function togglePlayPause() {
    if (!S.audioBuffer) return;
    if (S.isPlaying) pauseAudio();
    else playAudio();
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   进度条 & 字幕
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function getCurrentTime() {
    if (!S.isPlaying) return S.audioPauseOffset;
    return S.audioCtx.currentTime - S.audioStartTime;
}

function startProgressTimer() {
    stopProgressTimer();
    S.progressTimer = setInterval(() => {
        const t = getCurrentTime();
        const pct = Math.min((t / S.audioDuration) * 100, 100);
        $("#player-progress").style.width = pct + "%";
    }, 250);
}

function stopProgressTimer() {
    clearInterval(S.progressTimer);
}

function setSubtitle(text) {
    const el = $("#podcast-subtitle");
    if (!text) { el.textContent = ""; return; }

    // 将文本按句子拆分
    const sentences = text.match(/[^。！？！\?\.\n]+[。！？！\?\.\n]?/g) || [text];
    el.innerHTML = sentences.map((s) => `<span class="sub-sentence">${esc(s.trim())}</span>`).join("");
}

function startSubtitleTimer() {
    stopSubtitleTimer();
    const el = $("#podcast-subtitle");
    const sentences = el.querySelectorAll(".sub-sentence");
    if (!sentences.length) return;

    const total = S.audioDuration;
    // 按字符数估算每句时长
    const totalChars = Array.from(sentences).reduce((a, s) => a + s.textContent.length, 0);

    let offset = 0;
    const timings = Array.from(sentences).map((s) => {
        const start = offset;
        offset += (s.textContent.length / totalChars) * total;
        return { el: s, start, end: offset };
    });

    S.subtitleTimer = setInterval(() => {
        const t = getCurrentTime();
        timings.forEach(({ el, start, end }) => {
            if (t >= start && t < end) {
                el.classList.add("active");
                el.scrollIntoView({ behavior: "smooth", block: "center" });
            } else {
                el.classList.remove("active");
            }
        });
    }, 300);
}

function stopSubtitleTimer() {
    clearInterval(S.subtitleTimer);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   章节导航
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function goPrevChapter() {
    if (!S.currentBook || S.currentChapter <= 0) return toast("已经是第一章了");
    S.currentChapter--;
    loadChapterContent(S.currentBook.id, S.currentChapter);
}

function goNextChapter() {
    if (!S.currentBook) return;
    if (S.currentChapter >= S.currentBook.chapters.length - 1) {
        toast("已经是最后一章了");
        return;
    }
    S.currentChapter++;
    loadChapterContent(S.currentBook.id, S.currentChapter);
}

function toggleContinuous() {
    S.continuous = !S.continuous;
    $("#btn-continuous").classList.toggle("active", S.continuous);
    toast(S.continuous ? "连续播放已开启" : "连续播放已关闭");
}

function closePlayer() {
    // 停止音频并取消未完成的合成请求
    stopAudio();
    if (S.audioAbort) {
        S.audioAbort.abort();
        S.audioAbort = null;
    }
    S.audioBuffer = null;
    S.audioPauseOffset = 0;
    $("#player").style.display = "none";
    $("#player-progress").style.width = "0";
    loadBooks();
    loadHistory();
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   引擎配置
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function saveEngineConfig() {
    const apiUrl = $("#input-engine-url").value.trim();
    const engineDir = $("#input-engine-dir").value.trim();
    const promptText = $("#input-prompt-text").value.trim();
    const r = await api("config/engine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_url: apiUrl, engine_dir: engineDir, prompt_text: promptText }),
    });
    if (r.success) toast("引擎配置已保存 ✓");
    else toast("保存失败");
    loadSettings();
}

async function testEngineConnection() {
    const apiUrl = $("#input-engine-url").value.trim();
    toast("正在测试连接...");
    const r = await api("engine/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_url: apiUrl }),
    });
    if (r.success) toast("✓ " + r.message);
    else toast("✗ " + r.message, 3000);
    loadSettings();
}

async function autoDetectEngine() {
    toast("正在检测引擎目录...");
    const r = await api("engine/auto-detect", { method: "POST" });
    if (r.found) {
        $("#input-engine-dir").value = r.path;
        toast("✓ 已找到引擎: " + r.path);
    } else {
        toast("未找到引擎，请手动填写目录路径", 3000);
    }
}

async function startEngineFromUI() {
    toast("正在启动引擎...");
    const r = await api("engine/start", { method: "POST" });
    if (r.success) toast(r.message, 3500);
    else toast("✗ " + (r.error || "启动失败"), 3500);
}

async function stopEngineFromUI() {
    if (!confirm("确定关闭 TTS 引擎？关闭后需手动重新启动。")) return;
    toast("正在关闭引擎...");
    const r = await api("engine/stop", { method: "POST" });
    if (r.success) toast(r.message, 3500);
    else toast("✗ " + (r.error || "关闭失败"), 3500);
    loadSettings();
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   进度保存
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

async function saveProgress() {
    if (!S.currentBook) return;
    await api(`progress/${S.currentBook.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            chapter_index: S.currentChapter,
            book_title: S.currentBook.title,
            mode: S.mode,
        }),
    });
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   事件绑定
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function bindEvents() {
    // 标签栏
    $$(".tab").forEach((t) => t.addEventListener("click", () => switchView(t.dataset.view)));

    // 上传
    bindUploads();

    // 弹窗关闭
    $(".modal-backdrop")?.addEventListener("click", closeModal);

    // 播放器控制
    $("#btn-play-pause").addEventListener("click", togglePlayPause);
    $("#btn-prev").addEventListener("click", goPrevChapter);
    $("#btn-next").addEventListener("click", goNextChapter);
    $("#btn-continuous").addEventListener("click", toggleContinuous);
    $("#btn-close-player").addEventListener("click", closePlayer);

    // 章节选择器
    $("#player-chapter-select").addEventListener("change", (e) => {
        S.currentChapter = parseInt(e.target.value);
        if (S.currentBook) loadChapterContent(S.currentBook.id, S.currentChapter);
    });

    // 进度条点击跳转
    $("#player-progress-bar").addEventListener("click", (e) => {
        if (!S.audioBuffer || !S.audioDuration) return;
        const rect = e.currentTarget.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        const seekTo = pct * S.audioDuration;

        if (S.isPlaying) {
            // 重新定位播放
            if (S.audioSource) {
                try { S.audioSource.onended = null; S.audioSource.stop(); } catch (_) {}
                S.audioSource = null;
            }
            S.audioSource = S.audioCtx.createBufferSource();
            S.audioSource.buffer = S.audioBuffer;
            S.audioSource.connect(S.audioCtx.destination);
            S.audioSource.onended = onTrackEnd;
            S.audioSource.start(0, seekTo);
            S.audioStartTime = S.audioCtx.currentTime - seekTo;
        } else {
            S.audioPauseOffset = seekTo;
        }
        // 更新进度条
        const progressPct = Math.min((seekTo / S.audioDuration) * 100, 100);
        $("#player-progress").style.width = progressPct + "%";
    });

    // 清空历史
    $("#btn-clear-history").addEventListener("click", async () => {
        if (!confirm("确定清空所有阅读记录？")) return;
        await fetch("/api/progress", { method: "DELETE" });
        toast("已清空");
        loadHistory();
    });

    // 引擎配置
    $("#btn-engine-save")?.addEventListener("click", saveEngineConfig);
    $("#btn-engine-test")?.addEventListener("click", testEngineConnection);
    $("#btn-engine-detect")?.addEventListener("click", autoDetectEngine);
    $("#btn-engine-start")?.addEventListener("click", startEngineFromUI);
    $("#btn-engine-stop")?.addEventListener("click", stopEngineFromUI);
}
