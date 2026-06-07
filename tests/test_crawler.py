import unittest

import crawler


LANDING_PAGE_HTML = """
<div class="body jMainRegion region_book">
  <div class="table_of_contents">
    <a href="/books-search/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/1/">1</a>
  </div>
</div>
"""


LESSON_PAGE_HTML = """
<div class="body jMainRegion region_chapter region_lifestudy">
  <div>
    <p align="center"><a name="cont2"></a><h1 class="title">Salvation in God’s plan</h1></p>
    <p align="center"><a name="cont"></a><h2 class="head2">Text</h2></p>
    <p>&nbsp; This lesson book covers the subject of God’s full salvation.</p>
  </div>
</div>
<div class="page-preloader jRazorPreloader"></div>
"""


NEXT_LINK_HTML = """
<div class="item center jNavigator">
  <div>
    les. 1
    <a href="/books-search/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/2/">
      <i class="triangle-right"></i>
    </a>
  </div>
</div>
"""


class CrawlerTests(unittest.TestCase):
    def test_normalize_lesson_url(self) -> None:
        url = crawler.normalize_lesson_url(
            "https://bibleread.online/books-search/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/1/"
        )
        self.assertEqual(
            url,
            "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/1/",
        )

    def test_extract_first_lesson_url(self) -> None:
        url = crawler.extract_first_lesson_url(
            LANDING_PAGE_HTML,
            "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/",
        )
        self.assertEqual(
            url,
            "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/1/",
        )

    def test_extract_next_url(self) -> None:
        url = crawler.extract_next_url(
            NEXT_LINK_HTML,
            "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/1/",
        )
        self.assertEqual(
            url,
            "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/2/",
        )

    def test_render_lesson_front_matter_and_body(self) -> None:
        lesson = crawler.render_lesson(
            LESSON_PAGE_HTML,
            "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/1/",
        )
        self.assertIn("Title: Salvation in God’s plan", lesson.markdown)
        self.assertIn("Lesson: 1", lesson.markdown)
        self.assertIn("# Salvation in God’s plan", lesson.markdown)
        self.assertIn("## Text", lesson.markdown)
        self.assertIn("This lesson book covers the subject of God’s full salvation.", lesson.markdown)


if __name__ == "__main__":
    unittest.main()
