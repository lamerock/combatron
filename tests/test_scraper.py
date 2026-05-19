from combatron_reader import scraper
from combatron_reader.models import Chapter
import unittest
from unittest.mock import patch

class ScraperTests(unittest.TestCase):
    def test_discover_chapters_parses_and_sorts_labels(self) -> None:
        html_text = """
        <html>
          <body>
            <div class="sidebar">
              <a href="/search/label/Chapter%202%20Issue%20No.%20011">Chapter 2 Issue No. 011</a>
              <a href="/search/label/Chapter%201%20Issue%20No.%200067">Chapter 1 Issue No. 067</a>
              <a href="/search/label/announcement">announcement</a>
            </div>
          </body>
        </html>
        """

        with patch.object(scraper, "_fetch_text", return_value=html_text):
            chapters = scraper.discover_chapters()

        self.assertEqual([chapter.title for chapter in chapters], ["Chapter 1 Issue No. 067", "Chapter 2 Issue No. 011"])
        self.assertTrue(chapters[0].url.endswith("Chapter%201%20Issue%20No.%200067"))

    def test_fetch_chapter_pages_extracts_images(self) -> None:
        html_text = """
        <html>
          <body>
            <div class="post-body">
              <img src="https://blogger.googleusercontent.com/img/a/page-1.jpg" />
              <img src="https://blogger.googleusercontent.com/img/a/page-2.jpg" />
            </div>
          </body>
        </html>
        """

        with patch.object(scraper, "_fetch_text", return_value=html_text):
            chapter_pages = scraper.fetch_chapter_pages(Chapter(title="Chapter 1 Issue No. 001", url="https://example.test/chapter"))

        self.assertEqual(chapter_pages.chapter.title, "Chapter 1 Issue No. 001")
        self.assertEqual(
            chapter_pages.image_urls,
            (
                "https://blogger.googleusercontent.com/img/a/page-1.jpg",
                "https://blogger.googleusercontent.com/img/a/page-2.jpg",
            ),
        )

    def test_fetch_chapter_pages_prefers_linked_high_resolution_image(self) -> None:
        html_text = """
        <html>
          <body>
            <div class="post-body">
              <a href="https://blogger.googleusercontent.com/img/high-res/page-1.jpg">
                <img src="https://blogger.googleusercontent.com/img/thumb/page-1.jpg" />
              </a>
            </div>
          </body>
        </html>
        """

        with patch.object(scraper, "_fetch_text", return_value=html_text):
            chapter_pages = scraper.fetch_chapter_pages(Chapter(title="Chapter 1 Issue No. 002", url="https://example.test/chapter-2"))

        self.assertEqual(chapter_pages.image_urls, ("https://blogger.googleusercontent.com/img/high-res/page-1.jpg",))

    def test_fetch_chapter_pages_keeps_multiple_images_inside_single_wrapper_link(self) -> None:
        html_text = """
        <html>
          <body>
            <div class="post-body">
              <a href="https://blogger.googleusercontent.com/img/high-res/cover.jpg">
                <img src="https://blogger.googleusercontent.com/img/a/page-1.jpg" />
                <img src="https://blogger.googleusercontent.com/img/a/page-2.jpg" />
                <img src="https://blogger.googleusercontent.com/img/a/page-3.jpg" />
              </a>
            </div>
          </body>
        </html>
        """

        with patch.object(scraper, "_fetch_text", return_value=html_text):
            chapter_pages = scraper.fetch_chapter_pages(Chapter(title="Chapter 1 Issue No. 002", url="https://example.test/chapter-2"))

        self.assertEqual(
            chapter_pages.image_urls,
            (
                "https://blogger.googleusercontent.com/img/a/page-1.jpg",
                "https://blogger.googleusercontent.com/img/a/page-2.jpg",
                "https://blogger.googleusercontent.com/img/a/page-3.jpg",
            ),
        )

    def test_fetch_chapter_pages_normalizes_blogger_size_variant(self) -> None:
        html_text = """
        <html>
          <body>
            <div class="post-body">
              <img src="https://blogger.googleusercontent.com/img/b/abc/s1600-h/resized_Combi1.jpg" />
            </div>
          </body>
        </html>
        """

        with patch.object(scraper, "_fetch_text", return_value=html_text):
            chapter_pages = scraper.fetch_chapter_pages(Chapter(title="Chapter 1 Issue No. 004", url="https://example.test/chapter-4"))

        self.assertEqual(chapter_pages.image_urls, ("https://blogger.googleusercontent.com/img/b/abc/s0/resized_Combi1.jpg",))

    def test_fetch_chapter_pages_excludes_blogger_editor_icon(self) -> None:
        html_text = """
        <html>
          <body>
            <div class="post-body">
              <img src="https://resources.blogblog.com/img/icon18_edit_allbkg.gif" />
            </div>
          </body>
        </html>
        """

        with patch.object(scraper, "_fetch_text", return_value=html_text):
            chapter_pages = scraper.fetch_chapter_pages(Chapter(title="Chapter 1 Issue No. 003", url="https://example.test/chapter-3"))

        self.assertEqual(chapter_pages.image_urls, ())


if __name__ == "__main__":
    unittest.main()


def test_discover_chapters_parses_and_sorts_labels(monkeypatch):
    html_text = """
    <html>
      <body>
        <div class="sidebar">
          <a href="/search/label/Chapter%202%20Issue%20No.%20011">Chapter 2 Issue No. 011</a>
          <a href="/search/label/Chapter%201%20Issue%20No.%200067">Chapter 1 Issue No. 067</a>
          <a href="/search/label/announcement">announcement</a>
        </div>
      </body>
    </html>
    """

    monkeypatch.setattr(scraper, "_fetch_text", lambda url: html_text)

    chapters = scraper.discover_chapters()

    assert [chapter.title for chapter in chapters] == ["Chapter 1 Issue No. 067", "Chapter 2 Issue No. 011"]
    assert chapters[0].url.endswith("Chapter%201%20Issue%20No.%200067")


def test_fetch_chapter_pages_extracts_images(monkeypatch):
    html_text = """
    <html>
      <body>
        <div class="post-body">
          <img src="https://blogger.googleusercontent.com/img/a/page-1.jpg" />
          <img src="https://blogger.googleusercontent.com/img/a/page-2.jpg" />
        </div>
      </body>
    </html>
    """

    monkeypatch.setattr(scraper, "_fetch_text", lambda url: html_text)

    chapter_pages = scraper.fetch_chapter_pages(Chapter(title="Chapter 1 Issue No. 001", url="https://example.test/chapter"))

    assert chapter_pages.chapter.title == "Chapter 1 Issue No. 001"
    assert chapter_pages.image_urls == (
        "https://blogger.googleusercontent.com/img/a/page-1.jpg",
        "https://blogger.googleusercontent.com/img/a/page-2.jpg",
    )