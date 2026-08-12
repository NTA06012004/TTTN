from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SourceRecord:
    entity_type: str
    external_key: str
    source_url: str
    payload: dict[str, Any]


class CrawlerAdapter(ABC):
    code: str
    name: str
    source_type: str
    base_url: str

    @abstractmethod
    def crawl(self, *, year: int | None = None) -> Iterable[SourceRecord]:
        """Trả bản ghi chuẩn hóa; adapter không ghi trực tiếp vào database."""

