"""全文提取器."""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel
from trafilatura import extract, fetch_url
from trafilatura.settings import use_config


class FullTextResult(BaseModel):
    """全文抓取结果."""

    success: bool
    content: str | None = None  # 纯文本版本
    content_html: str | None = None  # HTML 版本
    word_count: int = 0
    error: str | None = None


class FullTextExtractor:
    """使用 trafilatura 提取网页全文."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=4)
        # 配置 trafilatura
        self._config = use_config()
        # 注入模拟浏览器的 User-Agent 以规避简单的 403
        self._config.set(
            "DEFAULT",
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

    async def fetch(self, url: str) -> FullTextResult:
        """
        抓取指定 URL 的全文.

        trafilatura 是同步库，这里用线程池包装成异步。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._fetch_sync,
            url,
        )

    def _fetch_sync(self, url: str) -> FullTextResult:
        """同步抓取全文."""
        try:
            # 下载页面
            downloaded = fetch_url(url, config=self._config)
            if not downloaded:
                return FullTextResult(
                    success=False,
                    error="下载页面失败 (可能由于 403 或网络限制)",
                )

            # 提取 HTML 格式正文
            html_content = extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                include_images=True,
                include_links=True,
                output_format="html",
                favor_precision=False,
            )

            # 提取纯文本版本（用于 AI 分析）
            text_content = extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                output_format="txt",
                favor_precision=False,
            )

            if not html_content and not text_content:
                return FullTextResult(
                    success=False,
                    error="无法从页面内容中提取正文",
                )

            # 清理 HTML 内容
            if html_content:
                html_content = self._clean_html(html_content)

            # 清理纯文本
            if text_content:
                text_content = self._clean_text(text_content)

            return FullTextResult(
                success=True,
                content=text_content,
                content_html=html_content,
                word_count=len(text_content) if text_content else 0,
            )

        except Exception as e:
            return FullTextResult(
                success=False,
                error=str(e),
            )

    def _clean_html(self, html: str) -> str:
        """清理 HTML 内容."""
        # 移除多余空白
        html = re.sub(r"\n\s*\n", "\n\n", html)
        # 移除空标签
        html = re.sub(r"<(\w+)>\s*</\1>", "", html)
        return html.strip()

    def _clean_text(self, text: str) -> str:
        """清理纯文本内容."""
        # 移除多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 移除行首尾空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # 移除常见的无效字符
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text.strip()

    async def fetch_multiple(self, urls: list[str]) -> list[FullTextResult]:
        """批量抓取多个 URL."""
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)
