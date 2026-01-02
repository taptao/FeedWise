"""HTML 解析工具."""

import re

from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """
    将 HTML 转换为纯文本.

    Args:
        html: HTML 内容

    Returns:
        提取的纯文本内容
    """
    if not html:
        return ""

    # 使用 BeautifulSoup 解析
    soup = BeautifulSoup(html, "lxml")

    # 移除 script 和 style 标签
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # 获取文本
    text = soup.get_text(separator="\n")

    # 清理多余空白
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    text = "\n".join(lines)

    # 合并连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_first_image(html: str) -> str | None:
    """
    提取 HTML 中的第一张图片 URL.

    Args:
        html: HTML 内容

    Returns:
        图片 URL 或 None
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    img = soup.find("img")

    if img and img.get("src"):
        src = img["src"]
        # 确保是字符串
        if isinstance(src, list):
            src = src[0] if src else None
        return src if src else None

    return None


def count_words(text: str) -> int:
    """
    统计文本字数.

    对于中文，按字符计数；对于英文，按单词计数。
    """
    if not text:
        return 0

    # 统计中文字符
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))

    # 统计英文单词
    english_text = re.sub(r"[\u4e00-\u9fff]", " ", text)
    english_words = len(english_text.split())

    return chinese_chars + english_words


def estimate_reading_time(text: str, wpm: int = 200) -> int:
    """
    估算阅读时间（分钟）.

    Args:
        text: 文本内容
        wpm: 每分钟阅读字数，默认 200

    Returns:
        阅读时间（分钟），最小 1
    """
    word_count = count_words(text)
    minutes = max(1, round(word_count / wpm))
    return minutes

