# ministry_book

Crawler for exporting a bibleread.online lesson book into local markdown files.

## What it does

- Starts from the book landing page for "Lesson Book, Level 1: Salvation - God's Full Salvation"
- Follows the lesson pages in order
- Writes one markdown file per lesson into `output/`
- Uses only the Python standard library

## Files

- `crawler.py`: the crawler and HTML-to-markdown converter
- `output/`: generated markdown files
- `tests/test_crawler.py`: regression tests for the current behavior

## Run

```bash
python3 crawler.py --output-dir output
```

You can override the start URL if needed:

```bash
python3 crawler.py --start-url "https://example.com/" --output-dir output
```

## Test

```bash
python3 -m unittest discover -s tests
```

## Guardrails

The tests lock down the current behavior that matters most:

- landing-page links are normalized to the working lesson URL pattern
- the first lesson URL is discovered correctly from the table of contents
- the next-lesson link is followed correctly
- lesson HTML is rendered into markdown with the current front matter format

If you change the site structure support or the markdown format, update the tests at the same time.
