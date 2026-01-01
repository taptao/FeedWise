"""内容完整性检测器."""

from typing import ClassVar


class ContentDetector:
    """检测 RSS 内容是否完整，判断是否需要抓取全文."""

    # 常见的截断标记
    TRUNCATION_MARKERS: ClassVar[list[str]] = [
        "...",
        "…",
        "Read more",
        "Continue reading",
        "Read the full article",
        "Click to read more",
        "阅读更多",
        "查看全文",
        "点击阅读",
        "继续阅读",
        "展开全文",
        "[...]",
        "[…]",
    ]

    # 最小内容长度阈值
    MIN_CONTENT_LENGTH = 500

    def needs_full_content(self, title: str, content: str) -> bool:
        """
        判断是否需要抓取全文.

        Args:
            title: 文章标题
            content: 文章纯文本内容

        Returns:
            True 表示需要抓取全文
        """
        if not content:
            return True

        content = content.strip()

        # 规则1：内容太短
        if len(content) < self.MIN_CONTENT_LENGTH:
            return True

        # 规则2：检测截断标记（检查末尾100字符）
        tail = content[-100:].lower() if len(content) > 100 else content.lower()
        for marker in self.TRUNCATION_MARKERS:
            if marker.lower() in tail:
                return True

        # 规则3：内容与标题比例异常（标题很长但内容很短）
        if len(title) > 50 and len(content) < 300:
            return True

        # 规则4：内容只有几段且很短
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        return bool(len(paragraphs) <= 2 and len(content) < 800)

    def estimate_completeness(self, content: str) -> float:
        """
        估算内容完整度 (0-1).

        这是一个启发式估算，用于 UI 展示。
        """
        if not content:
            return 0.0

        content = content.strip()
        length = len(content)

        # 基于长度的基础分数
        if length < 200:
            base_score = 0.2
        elif length < 500:
            base_score = 0.4
        elif length < 1000:
            base_score = 0.6
        elif length < 2000:
            base_score = 0.8
        else:
            base_score = 1.0

        # 检查截断标记，如果有则降分
        tail = content[-100:].lower() if len(content) > 100 else content.lower()
        for marker in self.TRUNCATION_MARKERS:
            if marker.lower() in tail:
                base_score *= 0.5
                break

        return min(1.0, base_score)
