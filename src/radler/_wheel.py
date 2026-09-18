"""Write wheels containing native executables in the scripts install scheme."""

import base64
import csv
import hashlib
import io
import os
import stat
import time
import zipfile
from pathlib import Path
from typing import BinaryIO

from packaging.tags import Tag

from radler._metadata import Metadata


def wheel_timestamp() -> tuple[int, int, int, int, int, int]:
    """Return a ZIP timestamp from SOURCE_DATE_EPOCH, or 1980-01-01.

    Clamp values before 1980 and reject values after 2107.
    """
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800"))
    if epoch > 4354819199:  # ZIP timestamps end in 2107.
        raise ValueError("SOURCE_DATE_EPOCH is too large for a ZIP timestamp")
    return time.gmtime(max(epoch, 315532800))[:6]


def write_wheel(
    binary: Path,
    output_dir: Path,
    metadata: Metadata,
    command: str,
    tag: str,
    timestamp: tuple[int, int, int, int, int, int],
) -> Path:
    if tag.startswith("win_") and not command.lower().endswith(".exe"):
        command += ".exe"
    stem = metadata.stem
    dist_info = f"{stem}.dist-info"
    wheel_tag = Tag("py3", "none", tag)
    path = output_dir / f"{stem}-{wheel_tag}.whl"
    rows: list[tuple[str, str, str]] = []

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:

        def add(member: str, source: BinaryIO, mode: int) -> None:
            info = zipfile.ZipInfo(member, date_time=timestamp)
            info.create_system = 3  # Unix permissions, even when building on Windows.
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            digest = hashlib.sha256()
            size = 0
            with wheel.open(info, "w", force_zip64=True) as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            encoded = (
                base64.urlsafe_b64encode(digest.digest()).rstrip(b"=").decode("ascii")
            )
            rows.append((member, f"sha256={encoded}", str(size)))

        with binary.open("rb") as source:
            add(f"{stem}.data/scripts/{command}", source, 0o755)
        add(f"{dist_info}/METADATA", io.BytesIO(metadata.render()), 0o644)
        wheel_metadata = (
            "Wheel-Version: 1.0\n"
            "Generator: radler\n"
            "Root-Is-Purelib: false\n"
            f"Tag: {wheel_tag}\n"
        )
        add(f"{dist_info}/WHEEL", io.BytesIO(wheel_metadata.encode("ascii")), 0o644)
        record = f"{dist_info}/RECORD"
        rows.append((record, "", ""))
        contents = io.StringIO(newline="")
        csv.writer(contents, lineterminator="\n").writerows(rows)
        add(record, io.BytesIO(contents.getvalue().encode("utf-8")), 0o644)
    return path
