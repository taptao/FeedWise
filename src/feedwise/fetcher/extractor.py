"""全文提取器."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel
from trafilatura import extract, fetch_url


class FullTextResult(BaseModel):
    """全文抓取结果."""

    success: bool
    content: str | None = None
    word_count: int = 0
    error: str | None = None


class FullTextExtractor:
    """使用 trafilatura 提取网页全文."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=4)

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
            downloaded = fetch_url(url)
            if not downloaded:
                return FullTextResult(
                    success=False,
                    error="下载页面失败",
                )

            # 提取正文
            text = extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                output_format="txt",
                favor_precision=True,
            )

            if not text:
                return FullTextResult(
                    success=False,
                    error="无法提取正文内容",
                )

            return FullTextResult(
                success=True,
                content=text,
                word_count=len(text),
            )

        except Exception as e:
            return FullTextResult(
                success=False,
                error=str(e),
            )

    async def fetch_multiple(self, urls: list[str]) -> list[FullTextResult]:
        """批量抓取多个 URL."""
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

