"""FreshRSS Google Reader API 客户端."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from feedwise.models.article import Article
from feedwise.models.feed import Feed


@dataclass
class FreshRSSConfig:
    """FreshRSS 连接配置."""

    base_url: str
    username: str
    api_password: str


class FreshRSSError(Exception):
    """FreshRSS API 错误."""


class FreshRSSClient:
    """FreshRSS Google Reader API 客户端."""

    def __init__(self, config: FreshRSSConfig) -> None:
        self.config = config
        self._auth_token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """关闭客户端."""
        await self._client.aclose()

    async def authenticate(self) -> str:
        """获取认证 token."""
        url = f"{self.config.base_url}/api/greader.php/accounts/ClientLogin"
        data = {
            "Email": self.config.username,
            "Passwd": self.config.api_password,
        }

        response = await self._client.post(url, data=data)
        response.raise_for_status()

        # 解析响应，格式为 "Auth=xxx"
        for line in response.text.strip().split("\n"):
            if line.startswith("Auth="):
                self._auth_token = line[5:]
                return self._auth_token

        msg = "认证失败：无法获取 Auth token"
        raise FreshRSSError(msg)

    def _get_headers(self) -> dict[str, str]:
        """获取带认证的请求头."""
        if not self._auth_token:
            msg = "未认证，请先调用 authenticate()"
            raise FreshRSSError(msg)
        return {"Authorization": f"GoogleLogin auth={self._auth_token}"}

    async def get_subscriptions(self) -> list[Feed]:
        """获取订阅列表."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/subscription/list"
        params = {"output": "json"}

        response = await self._client.get(
            url,
            params=params,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        data = response.json()
        feeds: list[Feed] = []

        for sub in data.get("subscriptions", []):
            # 提取分类
            categories = sub.get("categories", [])
            category = categories[0].get("label") if categories else None

            feed = Feed(
                id=sub["id"],
                title=sub["title"],
                url=sub["url"],
                site_url=sub.get("htmlUrl"),
                icon_url=sub.get("iconUrl"),
                category=category,
            )
            feeds.append(feed)

        return feeds

    async def get_unread_items(self, count: int = 100) -> list[Article]:
        """获取未读文章."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/stream/contents/user/-/state/com.google/reading-list"
        params = {
            "output": "json",
            "n": count,
            "xt": "user/-/state/com.google/read",  # 排除已读
        }

        response = await self._client.get(
            url,
            params=params,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        data = response.json()
        return self._parse_items(data.get("items", []))

    async def get_all_items(self, count: int = 100) -> list[Article]:
        """获取所有文章（包括已读）."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/stream/contents/user/-/state/com.google/reading-list"
        params = {
            "output": "json",
            "n": count,
        }

        response = await self._client.get(
            url,
            params=params,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        data = response.json()
        return self._parse_items(data.get("items", []))

    def _parse_items(self, items: list[dict[str, Any]]) -> list[Article]:
        """解析文章列表."""
        articles: list[Article] = []

        for item in items:
            # 提取内容
            content_obj = item.get("content") or item.get("summary") or {}
            content = content_obj.get("content", "")

            # 提取链接
            alternates = item.get("alternate", [])
            url = alternates[0].get("href") if alternates else None

            # 提取 feed_id
            origin = item.get("origin", {})
            feed_id = origin.get("streamId", "")

            # 解析时间戳
            published_ts = item.get("published", 0)
            published_at = (
                datetime.fromtimestamp(published_ts) if published_ts else None
            )

            article = Article(
                id=item["id"],
                feed_id=feed_id,
                title=item.get("title", "无标题"),
                author=item.get("author"),
                url=url,
                content=content,
                published_at=published_at,
            )
            articles.append(article)

        return articles

    async def mark_as_read(self, item_id: str) -> bool:
        """标记文章已读."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/edit-tag"
        data = {
            "i": item_id,
            "a": "user/-/state/com.google/read",
        }

        response = await self._client.post(
            url,
            data=data,
            headers=self._get_headers(),
        )
        return response.status_code == 200

    async def mark_as_unread(self, item_id: str) -> bool:
        """标记文章未读."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/edit-tag"
        data = {
            "i": item_id,
            "r": "user/-/state/com.google/read",
        }

        response = await self._client.post(
            url,
            data=data,
            headers=self._get_headers(),
        )
        return response.status_code == 200

    async def mark_as_starred(self, item_id: str) -> bool:
        """标记文章收藏."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/edit-tag"
        data = {
            "i": item_id,
            "a": "user/-/state/com.google/starred",
        }

        response = await self._client.post(
            url,
            data=data,
            headers=self._get_headers(),
        )
        return response.status_code == 200

    async def unmark_starred(self, item_id: str) -> bool:
        """取消文章收藏."""
        url = f"{self.config.base_url}/api/greader.php/reader/api/0/edit-tag"
        data = {
            "i": item_id,
            "r": "user/-/state/com.google/starred",
        }

        response = await self._client.post(
            url,
            data=data,
            headers=self._get_headers(),
        )
        return response.status_code == 200
