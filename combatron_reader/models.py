from dataclasses import dataclass


@dataclass(frozen=True)
class Chapter:
    title: str
    url: str


@dataclass(frozen=True)
class ChapterPages:
    chapter: Chapter
    image_urls: tuple[str, ...]
