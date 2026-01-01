"""全文抓取模块."""

from feedwise.fetcher.detector import ContentDetector
from feedwise.fetcher.extractor import FullTextExtractor, FullTextResult

__all__ = [
    "ContentDetector",
    "FullTextExtractor",
    "FullTextResult",
]
