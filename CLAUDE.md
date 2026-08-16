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

## Collaboration Notes

- **Langue de communication** : Toujours communiquer et répondre en français
- Les commentaires et documentation peuvent rester en français pour cohérence avec la codebase
