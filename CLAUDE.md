# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RoadCodeLock** is a web scraping project that automates interaction with the French road code quiz website (securite-routiere.gouv.fr). It uses Playwright to automate browser interactions and BeautifulSoup for HTML parsing.

## Technology Stack

- **Language**: Python 3.14+
- **Package Manager**: `uv` (fast, modern Python package manager)
- **Browser Automation**: Playwright (sync API)
- **HTML Parsing**: BeautifulSoup 4
- **Target Website**: https://www.securite-routiere.gouv.fr/les-medias/nos-quiz/je-repasse-le-code

## Development Setup

### Install Dependencies

```bash
uv sync
```

This reads `pyproject.toml` and `uv.lock` to install all dependencies in a virtual environment.

### Run the Scraper

```bash
uv run python src/scraper.py
```

### Verify Installation

```bash
uv pip list
```

This shows installed packages (beautifulsoup4, playwright, etc.).

## Project Structure

```
src/
  scraper.py          # Main scraper script using Playwright sync API
assets/               # Directory for storing assets (currently empty)
pyproject.toml        # Project metadata and dependencies
uv.lock              # Locked dependency versions
```

## Architecture Notes

### scraper.py (src/scraper.py:1-12)

The main scraper uses Playwright's **synchronous API** (`sync_playwright`) to:

1. Launch a Chromium browser in non-headless mode (visible window)
2. Navigate to the French road code quiz page
3. Interact with elements using CSS selectors (e.g., `div#choice-1.choice[role='button']`)
4. Pause for manual interaction (`page.pause()`)
5. Clean up resources

**Key Design Pattern**: Uses a context manager (`with sync_playwright()`) for automatic resource cleanup.

### Dependencies

- **beautifulsoup4**: For parsing and extracting HTML content
- **playwright**: For browser automation (currently using synchronous API only)

## Common Development Tasks

### Run the scraper in interactive mode

The scraper calls `page.pause()` which opens the Playwright Inspector, allowing manual browser interaction while paused.

```bash
uv run python src/scraper.py
```

### Install the Playwright browser

If you encounter browser driver issues:

```bash
playwright install chromium
```

### Explore the target website structure

Use the browser DevTools (F12) or Playwright Inspector to inspect the quiz page and identify element selectors for automation.

## Notes

- The project uses **headless=False**, so the browser window is visible during execution—useful for debugging
- The `page.pause()` call is intentional, allowing manual inspection and interaction
- CSS selectors target quiz choice elements (e.g., `div#choice-1.choice[role='button']`)

## Error Handling Principles

**Only catch specific exceptions when there's a clear reason**

Catch specific exception types ONLY when one of these conditions is true:
1. You need **different behavior** for that specific exception (e.g., retry, return default, exit gracefully)
2. You need to **add context** to the error message (e.g., include filename, parameter value that failed)
3. You need to **pinpoint the failure location** (e.g., separate TypeError from `bytes()` vs from file I/O)

Otherwise, use a general `Exception` catch — the traceback already shows the exact exception type, so being overly specific adds noise without benefit.

**Examples:**

❌ **Bad** — catching TimeoutError just to add context that's already in the traceback:
```python
except TimeoutError as e:
    raise MediaExtractionError("Failed to extract media: timeout") from e
```

✅ **Good** — catching TypeError separately to clarify which operation failed:
```python
except (FileNotFoundError, PermissionError, OSError) as e:
    raise MediaSaveError(f"Failed to save media file: {filename}") from e
except TypeError as e:
    raise MediaSaveError(f"Failed to convert media to bytes: {filename}") from e
```

✅ **Good** — simple and clear when behavior is identical:
```python
except Exception as e:
    cause = getattr(e, "__cause__", e)
    if cause is not None and "Connection closed" in str(cause):
        return local_dataset
    logger.exception("Error during scraping. Restarting...")
    await page.reload()
```

**Note:** Don't catch and `raise` custom exceptions without modification — let them bubble up naturally.

## Collaboration Notes

- **Langue de communication** : Toujours communiquer et répondre en français
- Les commentaires et documentation peuvent rester en français pour cohérence avec la codebase
