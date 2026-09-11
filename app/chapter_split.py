"""
Night-Night Kiss (晚安吻) - 章节切分模块
支持中英文章节自动识别，智能分段
"""

import re


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 章节匹配模式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 中文书籍模式（原有逻辑，不变） ──
CHAPTER_PATTERNS = [
    # 第一章 / 第1章 / 第一百二十三章
    re.compile(
        r"^[ \s]*第[零一二三四五六七八九十百千万\d]+[章节回集话期卷篇幕]"
        r"[ \s]*(.*)",
        re.MULTILINE,
    ),
    # 纯数字编号: 1. 疯狂年代 / 1、引言（要求包含中文字符）
    re.compile(
        r"^[ \s]*(\d{1,4})[.、．]\s*.*[\u4e00-\u9fff]",
        re.MULTILINE,
    ),
    # 序章 / 前言 / 后记 / 附录 / 引子 / 楔子 / 尾声 / 番外
    re.compile(
        r"^[ \s]*(序章?|前言|序言|引言|楔子|引子|后记|结语|尾声|附录|番外|终章|尾声|尾声)",
        re.MULTILINE,
    ),
]

# ── 英文书籍模式（独立逻辑） ──
ENGLISH_PATTERNS = [
    # Chapter 1 / CHAPTER I / Chapter One / CHAPTER II. / Chapter 1: Title
    re.compile(
        r"^[ \s]*(?:Chapter|CHAPTER)\s+[\dIVXLCDMoneTwoThreFouFivSiSevEigNi]+"
        r"[.\s]*(?:[:.\-]\s*\S.*)?$",
        re.MULTILINE | re.IGNORECASE,
    ),
    # BOOK I / BOOK II（必须单独成行，排除目录和描述句）
    re.compile(
        r"^[ \s]*(?:BOOK|Book)\s+[IVXLCDM]+[.\s]*$",
        re.MULTILINE,
    ),
    # 纯罗马数字章节号: I / II / III / IV / V / VI / VII / VIII / IX / X ...
    # 要求：整行只有罗马数字字符，且至少 2 个字符或为单个 I/V/X
    re.compile(
        r"^[ \s]*(?:II?I{0,2}|IV|VI{0,3}|IX|XI{0,3}|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)[ \s]*$",
        re.MULTILINE,
    ),
    # Part / Volume
    re.compile(
        r"^[ \s]*(?:Part|PART|Volume|VOLUME)\s+[\dIVXLCDM]+[ \s]*$",
        re.MULTILINE | re.IGNORECASE,
    ),
    # Prologue / Epilogue / Preface / Introduction / Foreword
    re.compile(
        r"^[ \s]*(?:Prologue|PROLOGUE|Epilogue|EPILOGUE|Preface|PREFACE"
        r"|Introduction|INTRODUCTION|Foreword|FOREWORD)[ \s]*$",
        re.MULTILINE | re.IGNORECASE,
    ),
]


def _is_mostly_english(lines: list[str]) -> bool:
    """判断文本是否主要为英文（取前 200 行采样）"""
    sample = "\n".join(lines[:200])
    alpha_chars = [c for c in sample if c.isalpha()]
    if not alpha_chars:
        return False
    english_chars = [c for c in alpha_chars if c.isascii()]
    return len(english_chars) / len(alpha_chars) > 0.8


def _find_chapters(lines: list[str], patterns: list) -> list[tuple]:
    """用指定模式集扫描行，返回 [(行号, 标题), ...]"""
    headings = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            continue
        for pattern in patterns:
            if pattern.match(stripped):
                headings.append((i, stripped))
                break
    return headings


def _filter_toc(headings: list[tuple], lines: list[str]) -> list[tuple]:
    """过滤目录条目：如果某标题前后 10 行内有 >=3 个其他标题，视为目录区域"""
    valid = []
    for idx, (line_no, title) in enumerate(headings):
        nearby = sum(
            1 for other_idx, (other_line, _) in enumerate(headings)
            if other_idx != idx and abs(other_line - line_no) < 10
        )
        if nearby >= 3:
            continue
        # 计算内容长度
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        ch_text = "\n".join(lines[line_no:end]).strip()
        if len(ch_text) >= 50:
            valid.append((line_no, title))
    return valid


def _detect_structure(lines: list[str], max_heading_len: int = 50) -> list[tuple]:
    """
    结构分析自适应检测章节边界。
    不依赖任何固定模式，而是分析文本结构找出“短标题 + 空行分隔 + 后接长内容 + 全文均匀分布”的行。
    """
    if len(lines) < 50:
        return []

    # ── 第一步：找出所有候选标题行 ──
    candidates = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > max_heading_len:
            continue
        # 跳过纯数字行（页码等）
        if re.match(r'^[\d\s\.\-]+$', stripped):
            continue
        # 跳过以小数/标点结尾的行（说明是段落中的断行，不是标题）
        if stripped[-1] in ',.;:)]\'"' or stripped[-1].islower():
            continue
        # 跳过包含括号的行（通常是引用/注释）
        if '(' in stripped and ')' in stripped:
            continue
        # 跳过像句子的行（包含多个单词且含有动词特征）
        words = stripped.split()
        if len(words) > 6:
            continue
        # 跳过以冒号/破折号结尾的行（通常是叙述句）
        if stripped.endswith(':') or stripped.endswith('--') or stripped.endswith('—'):
            continue
        # 前面必须有空行（段落分隔）
        if i < 2:
            continue
        prev_blank = not lines[i-1].strip()
        if not prev_blank:
            continue
        # 后面必须有空行（段落分隔）
        if i + 1 >= len(lines):
            continue
        next_blank = not lines[i+1].strip()
        if not next_blank:
            continue
        # 后面 100 行内必须有实质内容（>= 500 字符）
        following = "\n".join(lines[i+1:min(i+100, len(lines))])
        if len(following.strip()) < 500:
            continue
        candidates.append(i)

    if len(candidates) < 3:
        return []

    # ── 第二步：过滤目录区域（密集出现的候选行） ──
    filtered = []
    for idx, line_no in enumerate(candidates):
        nearby = sum(
            1 for other in candidates
            if other != line_no and abs(other - line_no) < 10
        )
        if nearby < 3:
            filtered.append(line_no)

    if len(filtered) < 3:
        return []

    # ── 第三步：检查分布均匀性 ──
    gaps = [filtered[i+1] - filtered[i] for i in range(len(filtered)-1)]
    if not gaps:
        return []
    avg_gap = sum(gaps) / len(gaps)
    # 如果平均间距太小（< 30行），可能是误判
    if avg_gap < 30:
        return []
    # 过滤掉间距异常小的（可能是同一章节内的子标题）
    final = [filtered[0]]
    for line_no in filtered[1:]:
        if line_no - final[-1] >= avg_gap * 0.5:
            final.append(line_no)

    if len(final) < 3:
        return []

    # ── 第四步：构建标题 ──
    result = []
    for line_no in final:
        title = lines[line_no].strip()
        result.append((line_no, title))

    return result


def _build_chapters(
    headings: list[tuple], lines: list[str], text: str
) -> list[dict]:
    """从过滤后的标题列表构建章节"""
    chapters = []
    for idx, (line_no, title) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        ch_text = "\n".join(lines[line_no:end]).strip()
        if ch_text:
            chapters.append({"title": title, "text": ch_text})

    # 第一章之前有内容，作为「前言」
    if headings and headings[0][0] > 0:
        pre_text = "\n".join(lines[:headings[0][0]]).strip()
        if len(pre_text) > 20:
            chapters.insert(0, {"title": "前言", "text": pre_text})

    return chapters if chapters else [{"title": "全文", "text": text}]


def split_chapters(filepath: str, min_chars: int = 3000) -> list[dict]:
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

    # 先用中文模式扫描
    headings = _find_chapters(lines, CHAPTER_PATTERNS)

    # 中文模式无结果且文本主要为英文，改用英文模式
    if not headings and _is_mostly_english(lines):
        headings = _find_chapters(lines, ENGLISH_PATTERNS)

    # ── 情况 A: 检测到章节标记 ──
    if headings:
        valid = _filter_toc(headings, lines)
        if valid:
            return _build_chapters(valid, lines, text)
        # 目录过滤后无有效章节，用原始标题列表
        return _build_chapters(headings, lines, text)

    # ── 情况 B: 无章节标记 → 结构分析自适应检测 ──
    structural = _detect_structure(lines)
    if structural and len(structural) >= 5:
        return _build_chapters(structural, lines, text)

    # ── 情况 C: 完全无结构 → 按段落智能分组 ──
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
# 合成分段（将长文本按句子边界拆为 ≤ max_chars 的段）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def split_into_segments(text: str, max_chars: int = 300) -> list[str]:
    """
    将一段文本按句子边界拆分为多个片段，每个片段不超过 max_chars 个字符。
    用于合成时控制单次请求的文本长度。
    """
    if not text or not text.strip():
        return []
    if len(text) <= max_chars:
        return [text.strip()]

    sentences = re.split(r'(?<=[。！？!?\n])', text)
    sentences = [s for s in sentences if s.strip()]

    segments = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) <= max_chars:
            current += sent
        else:
            if current.strip():
                segments.append(current.strip())
            if len(sent) > max_chars:
                for i in range(0, len(sent), max_chars):
                    chunk = sent[i:i + max_chars].strip()
                    if chunk:
                        segments.append(chunk)
                current = ""
            else:
                current = sent
    if current.strip():
        segments.append(current.strip())
    return segments


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
