# saw_tool_webscraper

Headless browser webscraper tool with CLI interface for Claude Code.

## Features

- 🌐 Headless browser scraping with Playwright
- 🎯 JavaScript-heavy websites support
- 📝 JSON output format
- 🔧 CLI interface for easy automation
- 🤖 Designed for Claude Code integration

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Usage

### Basic scraping

```bash
python src/scraper.py --url "https://example.com" --output output.json
```

### With custom selectors

```bash
python src/scraper.py \
  --url "https://example.com" \
  --selector ".module-item" \
  --output modules.json
```

### Options

- `--url` - Target URL (required)
- `--output` - Output JSON file path (required)
- `--selector` - CSS selector for elements to extract (optional)
- `--wait` - Wait time in milliseconds (default: 2000)
- `--screenshot` - Save screenshot for debugging (optional)

## Architecture

```
saw_tool_webscraper/
├── src/
│   ├── scraper.py       # Main scraper logic
│   └── cli.py           # CLI interface
├── tests/               # Test files
├── requirements.txt     # Python dependencies
└── README.md
```

## Example: Extract IT modules

```bash
python src/scraper.py \
  --url "https://www.modulbaukasten.ch/" \
  --output /Users/sascha/Documents/git/saw_notizen-inbox/it-module.json
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/
```

## License

MIT

---

**Repository Type:** `tool`
**Prefix:** `saw_`
**Created:** 2025-01-12
