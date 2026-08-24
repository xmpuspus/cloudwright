"""Record the migration proof project against a running Cloudwright server.

Usage:
    python3 scripts/record_migration_demo.py [--url URL] [--out PATH]

The recording uses only the packaged migration project and local HTTP API. It
does not call a model, change infrastructure, or connect to a cloud account.
"""

from __future__ import annotations

import argparse
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

DEFAULT_URL = "http://localhost:8765"
DEFAULT_OUT = Path("examples/cloudwright-migration-web-demo.gif")
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
GIF_WIDTH = 1100
GIF_HEIGHT = 620


def wait_for_server(url: str, timeout: float = 30.0) -> None:
    """Wait until the local server accepts HTTP requests."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit(f"Server at {url} did not respond after {timeout} seconds")


def capture_frame(page: Page, duration_ms: int) -> tuple[Image.Image, int]:
    """Capture and resize one timed browser frame."""
    screenshot = page.screenshot(type="png")
    image = Image.open(BytesIO(screenshot)).convert("RGB")
    image = image.resize((GIF_WIDTH, GIF_HEIGHT), Image.Resampling.LANCZOS)
    image = image.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    return image, duration_ms


def drive_demo(page: Page, url: str) -> list[tuple[Image.Image, int]]:
    """Open the migration view, run the proof project, and collect timed frames."""
    frames: list[tuple[Image.Image, int]] = []
    page.goto(url, wait_until="networkidle")
    page.get_by_role("tab", name="migration").click()
    page.wait_for_timeout(300)
    frames.append(capture_frame(page, 1_800))

    action = page.get_by_role("button", name="Run PH telco proof project")
    action.hover()
    frames.append(capture_frame(page, 500))
    action.click()
    page.get_by_role("heading", name="Ready to close").wait_for(timeout=15_000)
    page.wait_for_timeout(300)
    frames.append(capture_frame(page, 2_800))

    panel = page.locator("#panel-migration")
    for scroll_top in (180, 360, 540, 720, 900, 1080):
        panel.evaluate("(element, top) => element.scrollTo({ top })", scroll_top)
        page.wait_for_timeout(120)
        frames.append(capture_frame(page, 260 if scroll_top < 1080 else 2_500))
    for scroll_top in (840, 600, 360, 0):
        panel.evaluate("(element, top) => element.scrollTo({ top })", scroll_top)
        page.wait_for_timeout(120)
        frames.append(capture_frame(page, 240 if scroll_top else 2_000))
    return frames


def write_gif(frames: list[tuple[Image.Image, int]], output: Path) -> None:
    """Write timed browser frames as an animated GIF."""
    images = [frame for frame, _ in frames]
    durations = [duration for _, duration in frames]
    images[0].save(
        output,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    output_gif = Path(args.out).resolve()
    output_gif.parent.mkdir(parents=True, exist_ok=True)
    wait_for_server(args.url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT},
        )
        page = context.new_page()
        try:
            frames = drive_demo(page, args.url)
        finally:
            page.close()
            context.close()
            browser.close()

    write_gif(frames, output_gif)
    print(f"Wrote {output_gif} with {len(frames)} frames ({output_gif.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
