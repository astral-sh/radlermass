"""Command-line interface for radler."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from radler._build import build_wheels
from radler._platforms import TARGETS


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="radler", description="Compile Go commands into Python wheels."
    )

    parser.add_argument("go_dir", help="Go module directory containing go.mod")

    parser.add_argument(
        "--name", help="Distribution name (default: module directory name)"
    )
    parser.add_argument(
        "--version", default="0.1.0", help="Distribution version (PEP 440)"
    )

    parser.add_argument("--output-dir", default="dist", help="Wheel output directory")

    parser.add_argument(
        "--entry-point", help="Installed command name (default: --name)"
    )

    parser.add_argument(
        "--package-path", default=".", help="Package directory within the module"
    )

    parser.add_argument(
        "--platforms",
        help=f"Comma-separated targets (default: all): {', '.join(TARGETS)}",
    )

    parser.add_argument("--go-binary", default="go", help="Go executable path or name")

    parser.add_argument("--description", help="Package summary")
    parser.add_argument("--author", help="Package author")
    parser.add_argument("--author-email", help="Package author email")
    parser.add_argument("--license", dest="license_", help="Package license")
    parser.add_argument("--url", help="Project URL")
    parser.add_argument(
        "--readme", type=Path, help="Markdown README path, relative to the Go module"
    )

    parser.add_argument("--ldflags", help="Additional Go linker flags (after -s -w)")
    parser.add_argument(
        "--set-version-var", help="Go string variable to set to --version"
    )

    parser.add_argument(
        "--build-timeout",
        type=float,
        default=300,
        help="Seconds allowed per Go build (default: 300)",
    )

    args = parser.parse_args(argv)

    if args.platforms is not None:
        args.platforms = [platform.strip() for platform in args.platforms.split(",")]

    try:
        wheels = build_wheels(**vars(args))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"radler: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("radler: interrupted", file=sys.stderr)
        return 130

    print(f"Built {len(wheels)} wheel(s):")
    for wheel in wheels:
        print(f"  {wheel}")

    return 0
