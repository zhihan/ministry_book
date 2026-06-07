#!/usr/bin/env python3
"""Crawl a bibleread.online lesson book into local markdown files.

This script is intentionally self-contained: it uses only the Python
standard library so it can run on a clean machine.

Usage:
  python3 crawler.py

By default it starts from the requested lesson-book URL and writes
markdown files into ./output/.
"""

from __future__ import annotations

import argparse
import html as html_lib
import os
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_START_URL = (
    "https://bibleread.online/all-books-by-Watchman-Nee-and-Witness-Lee/"
    "book-lesson-book-level-1-salvationgods-full-salvation-Witness-Lee-read-online/"
)


def fetch(url: str) -> str:
    """Fetch a page with a browser-like user agent."""
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "lesson"


def normalize_lesson_url(url: str) -> str:
    return url.replace("/books-search/", "/all-books-by-Watchman-Nee-and-Witness-Lee/")


def clean_text(text: str) -> str:
    text = html_lib.unescape(text).replace("\xa0", " ").replace("\ufeff", "")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class MarkdownRenderer(HTMLParser):
    """Minimal HTML -> markdown renderer for the lesson body."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.buffer: list[str] = []
        self.current_block: Optional[tuple[str, int]] = None
        self.ignore_depth = 0
        self.list_stack: list[str] = []

    def flush(self) -> None:
        text = clean_text("".join(self.buffer))
        self.buffer = []
        if not text:
            return

        kind, level = self.current_block or ("p", 0)
        if kind == "heading":
            self.parts.append(f"{'#' * level} {text}")
        elif kind == "li":
            prefix = "- "
            if self.list_stack and self.list_stack[-1] == "ol":
                prefix = "1. "
            self.parts.append(f"{prefix}{text}")
        else:
            self.parts.append(text)
        self.current_block = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style"}:
            self.ignore_depth += 1
            return
        if self.ignore_depth:
            return

        if tag in {"h1", "h2", "h3", "h4"}:
            self.flush()
            level = int(tag[1])
            self.current_block = ("heading", level)
            return
        if tag == "li":
            self.flush()
            self.current_block = ("li", 0)
            return
        if tag in {"ul", "ol"}:
            self.list_stack.append(tag)
            return
        if tag == "br":
            self.buffer.append("\n")
            return

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.ignore_depth = max(0, self.ignore_depth - 1)
            return
        if self.ignore_depth:
            return

        if tag in {"h1", "h2", "h3", "h4", "p", "li"}:
            self.flush()
            return
        if tag in {"ul", "ol"} and self.list_stack:
            self.list_stack.pop()
            return
        if tag == "div":
            # Allow nested divs to naturally separate blocks.
            if self.buffer:
                self.flush()

    def handle_data(self, data: str) -> None:
        if self.ignore_depth:
            return
        self.buffer.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self.ignore_depth:
            self.buffer.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.ignore_depth:
            self.buffer.append(f"&#{name};")

    def render(self) -> str:
        self.flush()
        text = "\n\n".join(part for part in self.parts if part.strip())
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def extract_body_html(page_html: str) -> str:
    patterns = [
        r'<div class="body jMainRegion region_chapter region_lifestudy">\s*(.*?)\s*</div>\s*<div class="page-preloader',
        r'<div class="body[^"]*region_lifestudy">\s*(.*?)\s*</div>\s*<div class="page-preloader',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
    raise ValueError("Could not locate lesson body in page HTML")


def extract_first_lesson_url(page_html: str, base_url: str) -> Optional[str]:
    patterns = [
        r'href="([^"]*all-books-by-Watchman-Nee-and-Witness-Lee/[^"]+/1/)"',
        r'href="([^"]+/1/)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return normalize_lesson_url(urljoin(base_url, html_lib.unescape(match.group(1))))
    return None


def extract_page_title(page_html: str) -> str:
    match = re.search(r'<h1 class="title">(.*?)</h1>', page_html, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return "Lesson"
    return clean_text(re.sub(r"<.*?>", "", match.group(1)))


def extract_next_url(page_html: str, base_url: str) -> Optional[str]:
    match = re.search(
        r'href="([^"]+)"[^>]*>\s*<i class="triangle-right"',
        page_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    return normalize_lesson_url(urljoin(base_url, html_lib.unescape(match.group(1))))


def extract_page_number(page_url: str) -> Optional[int]:
    match = re.search(r"/(\d+)/?$", urlparse(page_url).path)
    if not match:
        return None
    return int(match.group(1))


@dataclass
class Lesson:
    number: Optional[int]
    title: str
    url: str
    markdown: str


def render_lesson(page_html: str, url: str) -> Lesson:
    title = extract_page_title(page_html)
    body_html = extract_body_html(page_html)
    renderer = MarkdownRenderer()
    renderer.feed(body_html)
    body_md = renderer.render()

    number = extract_page_number(url)
    header = ["---"]
    header.append(f"Title: {title}")
    header.append(f"Source: {url}")
    if number is not None:
        header.append(f"Lesson: {number}")
    header.extend(["---", ""])
    markdown = "\n".join(header) + body_md
    return Lesson(number=number, title=title, url=url, markdown=markdown)


def write_lesson(output_dir: Path, lesson: Lesson) -> Path:
    prefix = f"{lesson.number:02d}-" if lesson.number is not None else ""
    filename = f"{prefix}{slugify(lesson.title)}.md"
    path = output_dir / filename
    path.write_text(lesson.markdown, encoding="utf-8")
    return path


def crawl(start_url: str, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    saved: list[Path] = []
    url = start_url

    while url and url not in seen:
        seen.add(url)
        page_html = fetch(url)
        try:
            lesson = render_lesson(page_html, url)
        except ValueError:
            next_url = extract_first_lesson_url(page_html, url)
            if not next_url or next_url in seen:
                break
            url = next_url
            continue

        path = write_lesson(output_dir, lesson)
        saved.append(path)
        next_url = extract_next_url(page_html, url)
        if not next_url or next_url in seen:
            break
        url = next_url

    return saved


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument("--output-dir", default="output")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    saved = crawl(args.start_url, output_dir)
    print(f"Saved {len(saved)} markdown file(s) to {output_dir.resolve()}")
    for path in saved[:5]:
        print(f" - {path.name}")
    if len(saved) > 5:
        print(f" - ... {len(saved) - 5} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
