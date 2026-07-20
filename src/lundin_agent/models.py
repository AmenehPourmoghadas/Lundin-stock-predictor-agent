from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str
    published: str
    topic: str
    collector: str

    def to_dict(self) -> dict:
        return asdict(self)
