from pathlib import Path

from playwright.sync_api import sync_playwright


def export_pdf(html_content: str, output_path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=str(output_path),
            format="Letter",
            print_background=True,
            # Margins set to 0 — let @page CSS rule control all margins
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()
