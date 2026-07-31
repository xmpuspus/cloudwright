"""Record the Smart Canvas demo against a running cloudwright web server.

Usage:
    python scripts/record_smart_canvas.py [--url URL] [--out PATH]

Prereqs:
    - Web server running on the URL (default http://localhost:8765)
    - playwright + chromium installed in the active venv
    - ffmpeg on PATH

What it does:
    1. Drives a Chromium session through the Smart Canvas flow (chat prompt,
       diagram tab, catalog drawer, add resource, edit node, validate standards).
    2. Saves the captured webm.
    3. Converts to GIF with two-pass palette optimization.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

DEFAULT_URL = "http://localhost:8765"
DEFAULT_OUT = Path("examples/cloudwright-smart-canvas-demo.gif")
VIDEO_W = 1280
VIDEO_H = 720
GIF_W = 1100
GIF_H = 620
GIF_FPS = 12


def wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit(f"Server at {url} not responding after {timeout}s")


def linger(page: Page, ms: int) -> None:
    page.wait_for_timeout(ms)


def drive_demo(page: Page) -> None:
    page.goto(DEFAULT_URL)
    page.wait_for_selector('[placeholder="Describe your architecture..."]', timeout=15_000)
    linger(page, 1000)

    # 1. Type and submit the prompt (deliberately phrased to match a high-confidence
    #    template so the recording does not require an LLM API key).
    chat_input = page.locator('[placeholder="Describe your architecture..."]')
    chat_input.fill("three-tier web app with rds and alb on aws")
    linger(page, 800)
    page.get_by_role("button", name="Send").click()

    # 2. Wait for the diagram + catalog drawer to render.
    page.wait_for_selector('button:has-text("Download Terraform")', timeout=30_000)
    linger(page, 1500)

    # 3. Open the catalog drawer, then make sure we're on the Resources tab.
    #    The drawer is closed on load, so it never covers the diagram.
    page.get_by_role("button", name="Add Resource").click()
    linger(page, 900)
    page.locator('button:has-text("resources")').first.click()
    linger(page, 800)

    # 4. Search for "cache" and click an ElastiCache card to add a resource.
    search = page.locator('input[placeholder="Search the catalog"]')
    search.fill("cache")
    linger(page, 1000)
    elasticache_card = page.locator('button:has-text("Amazon ElastiCache")').first
    elasticache_card.click()
    linger(page, 2000)

    # 5. The side panel should auto-open for the freshly added node — edit the label.
    label_input = page.locator("#resource-label").first
    try:
        label_input.wait_for(timeout=4_000)
        label_input.click()
        label_input.press("Control+A")
        label_input.fill("Session cache")
        linger(page, 900)
    except PlaywrightTimeoutError:
        pass

    description_input = page.locator("#resource-description").first
    try:
        description_input.wait_for(timeout=2_000)
        description_input.click()
        description_input.fill("Read-through cache in front of RDS")
        linger(page, 1000)
    except PlaywrightTimeoutError:
        pass

    # 6. Close side panel so the canvas is visible again.
    try:
        page.get_by_role("button", name="Close panel").click(timeout=2_000)
        linger(page, 700)
    except PlaywrightTimeoutError:
        pass

    # 7. Switch to Standards tab and validate.
    try:
        page.locator('button:has-text("standards")').first.click(timeout=3_000)
        linger(page, 800)
        page.get_by_role("button", name="Check Standards").click(timeout=3_000)
        linger(page, 3000)
    except PlaywrightTimeoutError:
        pass

    # 8. Switch to Cost tab to show the cost breakdown.
    try:
        page.locator('button:has-text("cost")').first.click(timeout=2_000)
        linger(page, 1500)
    except PlaywrightTimeoutError:
        pass

    # 9. Back to diagram for the closing frame.
    try:
        page.locator('button:has-text("diagram")').first.click(timeout=2_000)
        linger(page, 1500)
    except PlaywrightTimeoutError:
        pass


def convert_webm_to_gif(webm: Path, gif: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not on PATH")
    palette = webm.with_suffix(".palette.png")
    vf_palette = (
        f"fps={GIF_FPS},scale={GIF_W}:{GIF_H}:flags=lanczos,palettegen=stats_mode=diff"
    )
    vf_use = (
        f"fps={GIF_FPS},scale={GIF_W}:{GIF_H}:flags=lanczos[x];"
        f"[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(webm), "-vf", vf_palette, str(palette)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(webm), "-i", str(palette),
            "-lavfi", vf_use,
            str(gif),
        ],
        check=True,
        capture_output=True,
    )
    palette.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--keep-webm", action="store_true")
    args = parser.parse_args()

    out_gif = Path(args.out).resolve()
    out_gif.parent.mkdir(parents=True, exist_ok=True)

    wait_for_server(args.url)

    video_dir = out_gif.parent / "_recording"
    video_dir.mkdir(exist_ok=True)
    # Clear stale webms
    for old in video_dir.glob("*.webm"):
        old.unlink()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": VIDEO_W, "height": VIDEO_H},
            record_video_dir=str(video_dir),
            record_video_size={"width": VIDEO_W, "height": VIDEO_H},
        )
        page = context.new_page()
        try:
            drive_demo(page)
        finally:
            page.close()
            context.close()
            browser.close()

    webms = sorted(video_dir.glob("*.webm"))
    if not webms:
        print("No webm produced — recording failed", file=sys.stderr)
        return 1
    webm = webms[-1]
    print(f"Recorded {webm} ({webm.stat().st_size:,} bytes)")
    convert_webm_to_gif(webm, out_gif)
    if not args.keep_webm:
        for w in webms:
            w.unlink()
        try:
            video_dir.rmdir()
        except OSError:
            pass
    print(f"Wrote {out_gif} ({out_gif.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
