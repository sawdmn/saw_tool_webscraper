#!/usr/bin/env python3
"""
Headless browser webscraper using Playwright.
Designed for Claude Code integration.
"""

import argparse
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def scrape_page(url, selector=None, wait_time=2000, screenshot_path=None):
    """
    Scrape a webpage using Playwright headless browser.

    Args:
        url: Target URL to scrape
        selector: CSS selector for elements to extract (optional)
        wait_time: Time to wait for page load in milliseconds
        screenshot_path: Path to save screenshot (optional)

    Returns:
        dict: Scraped data with metadata
    """
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to URL
            print(f"Loading: {url}", file=sys.stderr)
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for dynamic content
            page.wait_for_timeout(wait_time)

            # Take screenshot if requested
            if screenshot_path:
                page.screenshot(path=screenshot_path)
                print(f"Screenshot saved: {screenshot_path}", file=sys.stderr)

            # Get page content
            html_content = page.content()
            page_title = page.title()

            # Extract elements if selector provided
            elements = []
            if selector:
                try:
                    elements_handles = page.query_selector_all(selector)
                    print(f"Found {len(elements_handles)} elements matching '{selector}'", file=sys.stderr)

                    for element in elements_handles:
                        elements.append({
                            "text": element.inner_text(),
                            "html": element.inner_html()
                        })
                except Exception as e:
                    print(f"Warning: Could not extract elements: {e}", file=sys.stderr)

            # Prepare result
            result = {
                "url": url,
                "title": page_title,
                "success": True,
                "html_length": len(html_content),
                "elements_found": len(elements)
            }

            if selector:
                result["selector"] = selector
                result["elements"] = elements
            else:
                result["html"] = html_content

            return result

        except PlaywrightTimeout:
            return {
                "url": url,
                "success": False,
                "error": "Page load timeout (30s)"
            }
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
        finally:
            browser.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Headless browser webscraper with Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scraping
  python scraper.py --url "https://example.com" --output result.json

  # With selector
  python scraper.py --url "https://example.com" --selector ".item" --output items.json

  # With screenshot
  python scraper.py --url "https://example.com" --output result.json --screenshot debug.png
        """
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Target URL to scrape"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path"
    )

    parser.add_argument(
        "--selector",
        help="CSS selector for elements to extract (optional)"
    )

    parser.add_argument(
        "--wait",
        type=int,
        default=2000,
        help="Wait time in milliseconds (default: 2000)"
    )

    parser.add_argument(
        "--screenshot",
        help="Save screenshot to this path (optional)"
    )

    args = parser.parse_args()

    # Scrape
    print(f"Starting scrape...", file=sys.stderr)
    result = scrape_page(
        url=args.url,
        selector=args.selector,
        wait_time=args.wait,
        screenshot_path=args.screenshot
    )

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if result["success"]:
        print(f"✓ Success! Output saved to: {output_path}", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"✗ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
