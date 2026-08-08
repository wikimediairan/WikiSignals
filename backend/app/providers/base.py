from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class SeriesPoint:
    period_start: date
    value: float
    dimensions: dict[str, Any] = field(default_factory=dict)


@dataclass
class SeriesResult:
    metric_id: str
    points: list[SeriesPoint]
    source: str
    raw: Any = None


class DataProvider(ABC):
    name: str

    @abstractmethod
    async def close(self) -> None: ...
