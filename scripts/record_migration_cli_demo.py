"""Record the migration CLI demo without a video encoder.

The script runs the real offline commands, renders their terminal output with
Pillow, and writes an animated GIF. It is the local fallback when VHS cannot
use the installed ffmpeg binary.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1100
HEIGHT = 720
BACKGROUND = "#1e1e2e"
PANEL = "#181825"
TEXT = "#cdd6f4"
MUTED = "#6c7086"
PROMPT = "#a6e3a1"
BLUE = "#89b4fa"
FONT_SIZE = 14
LINE_HEIGHT = 19
MAX_LINES = 32
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def load_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Use the macOS terminal font when present, with a portable fallback."""
    menlo = Path("/System/Library/Fonts/Menlo.ttc")
    if menlo.is_file():
        return ImageFont.truetype(str(menlo), FONT_SIZE)
    return ImageFont.load_default(size=FONT_SIZE)


def run_command(root: Path, args: list[str], environment: dict[str, str]) -> str:
    """Run one CLI command and return the exact printable output."""
    completed = subprocess.run(
        [sys.executable, "-m", "cloudwright_cli", *args],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    return ANSI.sub("", completed.stdout + completed.stderr).rstrip()


def wrap_lines(lines: list[str]) -> list[str]:
    """Wrap plain lines while keeping Rich table borders intact."""
    wrapped: list[str] = []
    for line in lines:
        if any(character in line for character in "┏┓┗┛┃┠┨┯┷┳┻━─╭╮╰╯│"):
            wrapped.append(line[:116])
            continue
        wrapped.extend(textwrap.wrap(line, width=110, replace_whitespace=False) or [""])
    return wrapped[-MAX_LINES:]


def terminal_frame(lines: list[str], duration_ms: int, font) -> tuple[Image.Image, int]:
    """Render one terminal screen."""
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, WIDTH - 18, HEIGHT - 18), radius=14, fill=PANEL, outline="#313244", width=2)
    for index, color in enumerate(("#f38ba8", "#f9e2af", "#a6e3a1")):
        x = 42 + index * 20
        draw.ellipse((x, 38, x + 10, 48), fill=color)
    draw.text((WIDTH // 2, 43), "cloudwright migration · offline", font=font, fill=MUTED, anchor="mm")
    draw.line((30, 66, WIDTH - 30, 66), fill="#313244", width=1)

    y = 84
    for line in wrap_lines(lines):
        color = TEXT
        if line.startswith("#"):
            color = BLUE
        elif line.startswith("$"):
            color = PROMPT
        draw.text((42, y), line, font=font, fill=color)
        y += LINE_HEIGHT
    return image.quantize(colors=128, method=Image.Quantize.MEDIANCUT), duration_ms


def typing_frames(prefix: list[str], command: str, font) -> list[tuple[Image.Image, int]]:
    """Render a short command typing sequence."""
    frames: list[tuple[Image.Image, int]] = []
    for end in range(0, len(command) + 12, 12):
        frames.append(terminal_frame([*prefix, f"$ {command[:end]}"], 100, font))
    return frames


def write_gif(frames: list[tuple[Image.Image, int]], output: Path) -> None:
    """Write terminal frames as an animated GIF."""
    images = [image for image, _ in frames]
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
    parser.add_argument("--out", default="examples/cloudwright-migration-cli-demo.gif")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = (root / args.out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    (root / "tmp").mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment.pop("ANTHROPIC_API_KEY", None)
    environment.pop("OPENAI_API_KEY", None)
    font = load_font()

    with tempfile.TemporaryDirectory(prefix="migration-cli-gif-", dir=root / "tmp") as temp_dir:
        assessment = Path(temp_dir) / "assessment.yaml"
        assessment_arg = str(assessment.relative_to(root))
        project_path = "examples/migrations/ph-telco-project.yaml"
        evidence_path = "examples/migrations/ph-telco-evidence.yaml"
        plan_output = run_command(
            root,
            ["migrate", "plan", project_path, "-o", assessment_arg],
            environment,
        )
        verify_output = run_command(
            root,
            ["migrate", "verify", project_path, evidence_path],
            environment,
        )

    plan_comment = "# Build dependency-ordered waves and explicit migration costs"
    plan_command = f"cloudwright migrate plan {project_path} -o assessment.yaml"
    verify_comment = "# Recorded evidence decides whether the migration can close"
    verify_command = f"cloudwright migrate verify {project_path} {evidence_path}"

    frames: list[tuple[Image.Image, int]] = [terminal_frame([plan_comment, "$ "], 700, font)]
    frames.extend(typing_frames([plan_comment], plan_command, font))
    frames.append(terminal_frame([plan_comment, f"$ {plan_command}", *plan_output.splitlines()], 3_200, font))
    frames.append(terminal_frame([verify_comment, "$ "], 700, font))
    frames.extend(typing_frames([verify_comment], verify_command, font))
    frames.append(
        terminal_frame(
            [verify_comment, f"$ {verify_command}", *verify_output.splitlines()],
            3_600,
            font,
        )
    )
    write_gif(frames, output)
    print(f"Wrote {output} with {len(frames)} frames ({output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
