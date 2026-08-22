from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    id: str
    name: str
    kind: Literal["rss", "gdelt", "weather", "telegram_web"] = "rss"
    url: HttpUrl
    endpoint: HttpUrl | None = None
    channel: str | None = None
    language: str = "fa"
    categories: list[str] = Field(default_factory=list)
    trust_score: int = Field(ge=0, le=100, default=70)
    enabled: bool = True


class NewsItem(BaseModel):
    id: str
    source_id: str
    title: str
    url: HttpUrl
    summary: str = ""
    published_at: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: str = "general"
    trust_score: int = Field(ge=0, le=100, default=70)
    country: str = "IR"
    language: str = "fa"


class ContentDraft(BaseModel):
    item_id: str
    title: str
    body: str
    style: str
    with_image: bool = False
    source_url: HttpUrl
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScoredItem(BaseModel):
    item: NewsItem
    freshness: float = Field(ge=0, le=100)
    relevance: float = Field(ge=0, le=100)
    public_need: float = Field(ge=0, le=100)
    credibility: float = Field(ge=0, le=100)
    engagement: float = Field(ge=0, le=100)
    uniqueness: float = Field(ge=0, le=100)
    status: Literal["candidate", "selected", "rejected"] = "candidate"

    @property
    def total(self) -> float:
        score = (
            0.20 * self.freshness
            + 0.20 * self.relevance
            + 0.15 * self.public_need
            + 0.20 * self.credibility
            + 0.15 * self.engagement
            + 0.10 * self.uniqueness
        )
        return round(score, 2)
