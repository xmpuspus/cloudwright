"""Screenshot every workspace tab, at three widths, in both themes.

Drives the running web server with Playwright and writes PNGs to an output
directory. Use it as the visual check after any frontend change, and to
regenerate the images under docs/screenshots.

    python3 scripts/_serve_with_mock_llm.py 8799 &
    python3 scripts/ui_screenshots.py --out tmp/shots --base http://127.0.0.1:8799

The prompt below matches a built-in template at high confidence, so the
designer short-circuits the LLM. No API key, no cost, same result every run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROMPT = "three-tier web app with rds and alb on aws"
TABS = ["diagram", "cost", "validate", "compliance", "plan", "review", "export", "spec", "modify"]
VIEWPORTS = {
    "desktop": (1440, 900),
    "laptop": (1180, 800),
    "mobile": (390, 844),
}


def _set_theme(page, theme: str) -> None:
    page.evaluate(
        "t => { localStorage.setItem('cloudwright_theme', t);"
        " document.documentElement.setAttribute('data-theme', t); }",
        theme,
    )


def _design(page, base: str) -> None:
    page.goto(base, wait_until="networkidle")
    page.fill("[placeholder*='Describe']", PROMPT)
    page.get_by_role("button", name="Send").click()
    page.wait_for_function(
        "() => !document.body.innerText.includes('Generating')"
        " && !document.body.innerText.includes('Estimating')"
        " && !document.body.innerText.includes('Finalizing')",
        timeout=60_000,
    )
    page.wait_for_timeout(600)


def capture(base: str, out: Path, themes: list[str], viewports: list[str]) -> int:
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in themes:
            for vp_name in viewports:
                width, height = VIEWPORTS[vp_name]
                ctx = browser.new_context(viewport={"width": width, "height": height})
                page = ctx.new_page()
                page.goto(base)
                _set_theme(page, theme)
                _design(page, base)

                page.screenshot(path=str(out / f"{theme}-{vp_name}-00-chat.png"))
                written += 1

                for tab in TABS:
                    page.get_by_role("tab", name=tab, exact=True).click()
                    page.wait_for_timeout(500)
                    if tab == "validate":
                        page.get_by_role("button", name="Well-Architected").click()
                        page.wait_for_timeout(1200)
                    if tab == "export":
                        page.get_by_role("button", name="Terraform", exact=False).first.click()
                        page.wait_for_timeout(900)
                    if tab == "review":
                        page.get_by_role("button", name="Run review").click()
                        page.wait_for_timeout(1200)
                    page.screenshot(path=str(out / f"{theme}-{vp_name}-{TABS.index(tab) + 1:02d}-{tab}.png"))
                    written += 1

                ctx.close()
        browser.close()
    return written


def readme_shots(base: str, out: Path) -> int:
    """Write the exact filenames the README embeds, plus the legacy aliases."""
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 760})
        page = ctx.new_page()
        page.goto(base)
        _set_theme(page, "light")
        _design(page, base)

        def shot(name: str) -> None:
            nonlocal written
            page.screenshot(path=str(out / name))
            written += 1

        shot("cloudwright-light-1-diagram.png")

        page.get_by_role("tab", name="cost", exact=True).click()
        page.wait_for_timeout(600)
        shot("cloudwright-light-2-cost.png")

        page.get_by_role("tab", name="validate", exact=True).click()
        page.get_by_role("button", name="HIPAA").click()
        page.wait_for_timeout(1500)
        shot("cloudwright-light-3-validate.png")

        page.get_by_role("tab", name="compliance", exact=True).click()
        page.get_by_role("button", name="Run compliance scan").click()
        page.wait_for_timeout(3000)
        shot("cloudwright-compliance-tab.png")

        page.get_by_role("tab", name="plan", exact=True).click()
        page.get_by_role("button", name="Run plan").click()
        page.wait_for_timeout(20000)
        shot("cloudwright-plan-tab.png")

        page.get_by_role("tab", name="diagram", exact=True).click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="Add Resource").click()
        page.wait_for_timeout(1200)
        shot("cloudwright-light-4-canvas.png")

        ctx.close()
        browser.close()

    # Legacy filenames, kept so older external links keep resolving.
    for legacy, current in [
        ("cloudwright-light-1-ecommerce.png", "cloudwright-light-1-diagram.png"),
        ("cloudwright-light-2-analytics.png", "cloudwright-light-2-cost.png"),
        ("cloudwright-light-3-cost.png", "cloudwright-light-2-cost.png"),
        ("cloudwright-light-4-validate.png", "cloudwright-light-3-validate.png"),
    ]:
        (out / legacy).write_bytes((out / current).read_bytes())
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8799")
    parser.add_argument("--out", default="tmp/shots")
    parser.add_argument("--themes", default="light,dark")
    parser.add_argument("--viewports", default="desktop,laptop,mobile")
    parser.add_argument(
        "--readme",
        action="store_true",
        help="write the README filenames into --out instead of the full matrix",
    )
    args = parser.parse_args()

    if args.readme:
        count = readme_shots(args.base, Path(args.out))
    else:
        count = capture(
            args.base,
            Path(args.out),
            args.themes.split(","),
            args.viewports.split(","),
        )
    print(f"wrote {count} screenshots to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
