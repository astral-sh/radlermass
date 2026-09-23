# Portions derived from go-to-wheel by Simon Willison (Apache-2.0).
# Modified by Astral Software Inc. for radlermass; see NOTICE.

"""Invoke the Go toolchain in a module directory."""

import math
import os
import shutil
import subprocess
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path

from radlermass._platforms import Target


class Go:
    def __init__(self, module: Path, executable: str, timeout: float) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Build timeout must be a positive, finite number")

        path = shutil.which(executable)
        if path is None:
            raise ValueError(f"Go executable not found: {executable!r}")

        # Resolve before changing the subprocess's working directory to the module.
        self.executable = str(Path(path).absolute())
        self.module = module
        self.timeout = timeout

    def _run(
        self,
        args: list[str],
        *,
        label: str,
        env: dict[str, str] | None = None,
    ) -> str:
        try:
            result = subprocess.run(
                [self.executable, *args],
                cwd=self.module,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"{label} exceeded {self.timeout:g} seconds") from error

        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"{label} failed (exit {result.returncode}):\n{detail}")

        return result.stdout

    @cached_property
    def version(self) -> str:
        """Return the toolchain version selected for this module."""
        return self._run(["env", "GOVERSION"], label="Go version query").strip()

    def gomod_json(self) -> bytes:
        """Return the module's go.mod as UTF-8 JSON without modifying it."""
        return self._run(
            ["mod", "edit", "-json"], label="Go module JSON generation"
        ).encode("utf-8")

    def build(
        self,
        package: str,
        targets: Sequence[Target],
        output_dir: Path,
        ldflags: str,
    ) -> dict[tuple[str, str], Path]:
        """Compile once per GOOS/GOARCH pair, sharing Linux libc variants."""
        binaries: dict[tuple[str, str], Path] = {}
        for target in targets:
            key = (target.goos, target.goarch)
            if key in binaries:
                continue

            binary = output_dir / f"{target.goos}-{target.goarch}.exe"
            env = os.environ | {
                "GOOS": target.goos,
                "GOARCH": target.goarch,
                "CGO_ENABLED": "0",
                # Wheel tags don't encode GOAMD64/GOARM64 feature levels.
                "GOAMD64": "v1",
                "GOARM64": "v8.0",
            }

            self._run(
                [
                    "build",
                    "-trimpath",
                    "-buildmode=exe",
                    f"-ldflags={ldflags}",
                    "-o",
                    str(binary),
                    package,
                ],
                env=env,
                label=f"Go build for {target.goos}/{target.goarch}",
            )
            binaries[key] = binary

        return binaries
