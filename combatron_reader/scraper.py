from __future__ import annotations

import html
import re
from dataclasses import asdict
from html.parser import HTMLParser
from typing import Iterable
from urllib.request import Request, urlopen

from .models import Chapter, ChapterPages


BASE_URL = "https://projectcombatron.blogspot.com/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CombatronReader/0.1"
EXCLUDED_IMAGE_URLS = {
    "https://resources.blogblog.com/img/icon18_edit_allbkg.gif",
}


class _SidebarLabelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.labels: list[Chapter] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value for key, value in attrs}
        if tag == "a":
            href = attr_map.get("href")
            if href and "/search/label/" in href:
                self._current_href = href
                self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            title = html.unescape("".join(self._current_text)).strip()
            if title:
                self.labels.append(Chapter(title=title, url=self._current_href))
            self._current_href = None
            self._current_text = []


class _ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.image_urls: list[str] = []
        self._post_body_depth = 0
        self._anchor_stack: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value for key, value in attrs}
        class_name = (attr_map.get("class") or "").lower()
        if tag in {"div", "article", "main"}:
            if any(part in class_name for part in ("post-body", "entry-content", "post")):
                self._post_body_depth = max(1, self._post_body_depth + 1)
            elif self._post_body_depth > 0:
                self._post_body_depth += 1
        if tag == "a":
            self._anchor_stack.append(attr_map.get("href"))
        if tag == "img" and self._post_body_depth > 0:
            src = attr_map.get("src") or attr_map.get("data-src") or attr_map.get("data-original")
            linked_href = self._anchor_stack[-1] if self._anchor_stack else None
            candidate = _select_image_candidate(src=src, linked_href=linked_href)
            if candidate and _is_allowed_image_url(candidate):
                self.image_urls.append(candidate)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_stack:
            self._anchor_stack.pop()
        if tag in {"div", "article", "main"} and self._post_body_depth > 0:
            self._post_body_depth -= 1


def _select_image_candidate(src: str | None, linked_href: str | None) -> str | None:
    if not src:
        return linked_href
    if not linked_href or not _looks_like_image(linked_href):
        return src
    src_basename = src.split("?", 1)[0].rsplit("/", 1)[-1].lower()
    link_basename = linked_href.split("?", 1)[0].rsplit("/", 1)[-1].lower()
    if src_basename and src_basename == link_basename:
        return linked_href
    return src


def _looks_like_image(url: str) -> bool:
    return bool(re.search(r"\.(?:jpe?g|png|gif|webp)(?:$|[?#])", url, re.IGNORECASE))


def _normalize_image_url(url: str) -> str:
    normalized = _absolute_url(url)
    if "blogger.googleusercontent.com" in normalized:
        # Some /s1600-h/ style variants return HTML wrappers. /s0/ reliably returns image bytes.
        normalized = re.sub(r"/s\d+(?:-[a-z])?/", "/s0/", normalized, count=1)
    return normalized


def _is_allowed_image_url(url: str) -> bool:
    normalized = _normalize_image_url(url)
    if normalized in EXCLUDED_IMAGE_URLS:
        return False
    return _looks_like_image(normalized) or "blogger.googleusercontent.com" in normalized


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def _absolute_url(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return BASE_URL.rstrip("/") + url
    return BASE_URL.rstrip("/") + "/" + url.lstrip("/")


def _dedupe_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def discover_chapters(source_url: str = BASE_URL) -> list[Chapter]:
    html_text = _fetch_text(source_url)
    parser = _SidebarLabelParser()
    parser.feed(html_text)
    chapters = [
        Chapter(title=chapter.title, url=_absolute_url(chapter.url))
        for chapter in parser.labels
        if chapter.title.lower().startswith("chapter")
    ]
    return _sort_chapters(chapters)


def _sort_chapters(chapters: list[Chapter]) -> list[Chapter]:
    def sort_key(chapter: Chapter) -> tuple[int, int, str]:
        match = re.search(r"Chapter\s+(\d+)\s+Issue\s+No\.\s+(\d+)", chapter.title, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2)), chapter.title.lower()
        return (999, 999, chapter.title.lower())

    return sorted(chapters, key=sort_key)


def fetch_chapter_pages(chapter: Chapter) -> ChapterPages:
    html_text = _fetch_text(chapter.url)
    parser = _ImageParser()
    parser.feed(html_text)
    image_urls = [_normalize_image_url(url) for url in parser.image_urls if _is_allowed_image_url(url)]
    if not image_urls:
        image_urls = _fallback_image_urls(html_text)
    if not image_urls:
        image_urls = _meta_image_urls(html_text)
    return ChapterPages(chapter=chapter, image_urls=_dedupe_preserve_order(image_urls))


def _fallback_image_urls(html_text: str) -> list[str]:
    matches = re.findall(r'https?://[^"\']+\.(?:jpe?g|png|gif|webp)(?:\?[^"\']*)?', html_text, re.IGNORECASE)
    return [_normalize_image_url(match) for match in matches if _is_allowed_image_url(match)]


def _meta_image_urls(html_text: str) -> list[str]:
    matches = re.findall(r"<meta[^>]+property=['\"]og:image['\"][^>]+content=['\"]([^'\"]+)['\"]", html_text, re.IGNORECASE)
    return [_normalize_image_url(match) for match in matches if _is_allowed_image_url(match)]


def to_json_ready(chapters: Iterable[Chapter]) -> list[dict[str, str]]:
    return [asdict(chapter) for chapter in chapters]
