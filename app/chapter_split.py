"""
Night-Night Kiss (晚安吻) - 章节切分模块
支持中英文章节自动识别，智能分段
"""

import re
from pathlib import Path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 章节匹配模式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHAPTER_PATTERNS = [
    # ── 中文 ──
    # 第一章 / 第1章 / 第一百二十三章
    re.compile(
        r"^[ \s]*第[零一二三四五六七八九十百千万\d]+[章节回集话期卷篇幕]"
        r"[ \s]*(.*)",
        re.MULTILINE,
    ),
    # ── 英文 ──
    # Chapter 1 / CHAPTER I / Chapter One
    re.compile(
        r"^[ \s]*(?:Chapter|CHAPTER)\s+[\dIVXLCDMoneTwoThreFouFivSiSevEigNi]+[ \s]*(.*)",
        re.MULTILINE | re.IGNORECASE,
    ),
    # ── 纯数字编号 ──
    # 001 / 1. / 1、
    re.compile(
        r"^[ \s]*(\d{1,4})[.、．]\s*(.+)?",
        re.MULTILINE,
    ),
    # ── Part / Volume ──
    re.compile(
        r"^[ \s]*(?:Part|PART|Volume|VOLUME)\s+[\dIVXLCDM]+[ \s]*(.*)",
        re.MULTILINE | re.IGNORECASE,
    ),
    # ── 序章 / 前言 / 后记 / 附录 / 引子 / 楔子 / 尾声 / 番外 ──
    re.compile(
        r"^[ \s]*(序章?|前言|序言|引言|楔子|引子|后记|结语|尾声|附录|番外|终章|尾声|尾声)",
        re.MULTILINE,
    ),
    # ── Prologue / Epilogue / Preface / Introduction ──
    re.compile(
        r"^[ \s]*(?:Prologue|PROLOGUE|Epilogue|EPILOGUE|Preface|PREFACE"
        r"|Introduction|INTRODUCTION|Foreword|FOREWORD)",
        re.MULTILINE | re.IGNORECASE,
    ),
]

# 中文数字映射
CN_NUMS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000, "万": 10000,
}


def is_chapter_heading(line: str) -> bool:
    """判断一行是否为章节标题"""
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return False
    for pattern in CHAPTER_PATTERNS:
        if pattern.match(stripped):
            return True
    return False


def extract_chapter_title(line: str) -> str:
    """从章节标题行中提取标题文本"""
    stripped = line.strip()
    for pattern in CHAPTER_PATTERNS:
        m = pattern.match(stripped)
        if m:
            # 返回完整标题行
            return stripped
    return stripped


def split_chapters(filepath: str, min_chars: int = 100) -> list[dict]:
    """
    将 TXT 文件切分为章节列表

    Args:
        filepath:   txt 文件路径
        min_chars:  无章节标记时，每段最少字符数

    Returns:
        [{"title": str, "text": str}, ...]
    """
    # ── 读取文件 ──
    text = None
    for enc in ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if text is None:
        return [{"title": "无法读取", "text": ""}]

    text = text.strip()
    if not text:
        return [{"title": "空文件", "text": ""}]

    # ── 逐行扫描，寻找章节标题 ──
    lines = text.split("\n")
    chapter_starts = []  # [(行号, 标题文本), ...]

    for i, line in enumerate(lines):
        if is_chapter_heading(line):
            chapter_starts.append((i, extract_chapter_title(line)))

    # ── 情况 A: 检测到章节标记 ──
    if chapter_starts:
        chapters = []
        for idx, (line_no, title) in enumerate(chapter_starts):
            if idx + 1 < len(chapter_starts):
                end = chapter_starts[idx + 1][0]
            else:
                end = len(lines)

            ch_lines = lines[line_no:end]
            ch_text = "\n".join(ch_lines).strip()

            if ch_text:
                chapters.append({"title": title, "text": ch_text})

        # 如果第一章之前有内容，作为「前言」
        if chapter_starts[0][0] > 0:
            pre_text = "\n".join(lines[: chapter_starts[0][0]]).strip()
            if len(pre_text) > 20:
                chapters.insert(0, {"title": "前言", "text": pre_text})

        return chapters if chapters else [{"title": "全文", "text": text}]

    # ── 情况 B: 无章节标记 → 按段落智能分组 ──
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [{"title": "全文", "text": text}]

    chapters = []
    current_text = ""
    part = 1

    for para in paragraphs:
        current_text += para + "\n\n"
        if len(current_text) >= min_chars:
            chapters.append({"title": f"第 {part} 节", "text": current_text.strip()})
            part += 1
            current_text = ""

    if current_text.strip():
        if chapters and len(current_text.strip()) < min_chars // 2:
            chapters[-1]["text"] += "\n\n" + current_text.strip()
        else:
            chapters.append({
                "title": f"第 {part} 节",
                "text": current_text.strip(),
            })

    return chapters if chapters else [{"title": "全文", "text": text}]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试入口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python chapter_split.py <txt文件路径>")
        sys.exit(1)

    result = split_chapters(sys.argv[1])
    print(f"\n共切分为 {len(result)} 个章节:\n")
    for i, ch in enumerate(result):
        preview = ch["text"][:60].replace("\n", " ")
        print(f"  [{i}] {ch['title']}  ({len(ch['text'])} 字)")
        print(f"      {preview}...")
        print()
