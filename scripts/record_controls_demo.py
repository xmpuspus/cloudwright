"""Record the compliance + plan demo against a running cloudwright web server.

Usage:
    python scripts/record_controls_demo.py [--url URL] [--out PATH]

Prereqs:
    - Web server running on the URL (default http://localhost:8765)
    - playwright + chromium installed in the active venv
    - ffmpeg on PATH

Drives a Chromium session through: design (template-matched prompt, no LLM key
needed) -> Compliance tab (framework chips, run scan, control-mapped posture)
-> Plan tab (run plan, DEPLOYABLE verdict). Saves webm, converts to GIF.
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
DEFAULT_OUT = Path("examples/cloudwright-controls-web-demo.gif")
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
    page.wait_for_selector('input[placeholder="Describe your architecture..."]', timeout=15_000)
    linger(page, 1000)

    chat_input = page.locator('input[placeholder="Describe your architecture..."]')
    chat_input.fill("three-tier web app with rds and alb on aws")
    linger(page, 700)
    page.get_by_role("button", name="Send").click()
    page.wait_for_selector('button:has-text("Download Terraform")', timeout=45_000)
    linger(page, 1500)

    # --- Compliance tab ---
    page.get_by_role("button", name="compliance", exact=True).click()
    linger(page, 1200)
    try:
        page.get_by_role("button", name="Run compliance scan").click(timeout=5_000)
    except PlaywrightTimeoutError:
        pass
    # Wait for the per-framework posture table to render.
    try:
        page.wait_for_selector("text=Scanner:", timeout=90_000)
    except PlaywrightTimeoutError:
        pass
    linger(page, 4500)
    page.mouse.wheel(0, 350)
    linger(page, 2500)

    # --- Plan tab ---
    page.get_by_role("button", name="plan", exact=True).click()
    linger(page, 1200)
    try:
        page.get_by_role("button", name="Run plan").click(timeout=5_000)
    except PlaywrightTimeoutError:
        pass
    try:
        page.wait_for_selector("text=DEPLOYABLE", timeout=90_000)
    except PlaywrightTimeoutError:
        pass
    linger(page, 4500)


def convert_webm_to_gif(webm: Path, gif: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not on PATH")
    palette = webm.with_suffix(".palette.png")
    vf_palette = f"fps={GIF_FPS},scale={GIF_W}:{GIF_H}:flags=lanczos,palettegen=stats_mode=diff"
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
        ["ffmpeg", "-y", "-i", str(webm), "-i", str(palette), "-lavfi", vf_use, str(gif)],
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

    video_dir = out_gif.parent / "_recording_controls"
    video_dir.mkdir(exist_ok=True)
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
