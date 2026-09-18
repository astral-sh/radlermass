import base64
import csv
import hashlib
import io
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest
from packaging.metadata import parse_email
from packaging.utils import parse_wheel_filename

from radler import build_wheels

pytestmark = pytest.mark.usefixtures("go_environment")

STEM = "radler_test_cli-1.2.3rc1"


@pytest.fixture(
    params=[
        pytest.param("manylinux_2_17_x86_64", id="linux-amd64"),
        pytest.param("manylinux_2_17_aarch64", id="linux-arm64"),
        pytest.param("musllinux_1_2_x86_64", id="linux-amd64-musl"),
        pytest.param("musllinux_1_2_aarch64", id="linux-arm64-musl"),
        pytest.param("macosx_*_x86_64", id="darwin-amd64"),
        pytest.param("macosx_*_arm64", id="darwin-arm64"),
        pytest.param("win_amd64", id="windows-amd64"),
        pytest.param("win_arm64", id="windows-arm64"),
    ]
)
def wheel(request, wheels):
    [path] = [path for path in wheels if path.match(f"*-{request.param}.whl")]
    with zipfile.ZipFile(path) as archive:
        yield archive


def test_builds_all_platforms(wheels):
    """Build eight wheels when no platforms are specified."""
    assert len(wheels) == 8


def test_wheel_layout(wheel):
    """Put the native executable in .data/scripts with executable permissions.

    The wheel filename uses a normalized name and version with py3-none tags.
    Only the executable and the three required dist-info files are included.
    """
    name, version, _, tags = parse_wheel_filename(Path(wheel.filename).name)
    assert name == "radler-test-cli"
    assert str(version) == "1.2.3rc1"
    [tag] = tags
    assert tag.interpreter == "py3"
    assert tag.abi == "none"

    script = f"{STEM}.data/scripts/hello-radler"
    if tag.platform.startswith("win_"):
        script += ".exe"
    assert set(wheel.namelist()) == {
        script,
        f"{STEM}.dist-info/METADATA",
        f"{STEM}.dist-info/WHEEL",
        f"{STEM}.dist-info/RECORD",
    }
    info = wheel.getinfo(script)
    assert info.create_system == 3
    assert stat.S_ISREG(info.external_attr >> 16)
    assert stat.S_IMODE(info.external_attr >> 16) == 0o755


def test_wheel_metadata(wheel, go_module):
    """Preserve supplied metadata and README contents in each wheel.

    Omit Requires-Python and Requires-Dist, and match the WHEEL tag to the
    filename.
    """
    metadata, unparsed = parse_email(wheel.read(f"{STEM}.dist-info/METADATA"))
    assert not unparsed
    assert metadata == {
        "metadata_version": "2.1",
        "name": "Radler_Test--CLI",
        "version": "1.2.3rc1",
        "summary": "A compiled command — Grüße!",
        "author": "Zoë Example",
        "author_email": "test@example.com",
        "license": "MIT",
        "home_page": "https://example.com",
        "description_content_type": "text/markdown",
        "description": (go_module / "README.md").read_text(encoding="utf-8"),
    }

    _, _, _, tags = parse_wheel_filename(Path(wheel.filename).name)
    [tag] = tags
    wheel_metadata = Parser().parsestr(
        wheel.read(f"{STEM}.dist-info/WHEEL").decode("ascii")
    )
    assert dict(wheel_metadata.items()) == {
        "Wheel-Version": "1.0",
        "Generator": "radler",
        "Root-Is-Purelib": "false",
        "Tag": str(tag),
    }


@pytest.mark.parametrize("readme", ["README.md", "# Inline README\n\nGrüße!\n"])
def test_inline_readme(tmp_path, go_module, readme):
    """Embed README strings verbatim, including strings naming an existing file.

    Omit the Summary header when no description is supplied.
    """
    [path] = build_wheels(
        go_module,
        package_path="cmd/hello",
        platforms=["linux-amd64"],
        output_dir=tmp_path,
        readme=readme,
    )
    with zipfile.ZipFile(path) as wheel:
        metadata, _ = parse_email(wheel.read("hello-0.1.0.dist-info/METADATA"))
    assert metadata["description"] == readme
    assert metadata["description_content_type"] == "text/markdown"
    assert "summary" not in metadata


def test_wheel_record(wheel):
    """Record every wheel member with its SHA-256 digest and byte length.

    RECORD lists itself with an empty hash and size.
    """
    record = f"{STEM}.dist-info/RECORD"
    rows = list(csv.reader(io.StringIO(wheel.read(record).decode("utf-8"))))
    assert len(rows) == len(wheel.namelist())
    records = {member: (digest, size) for member, digest, size in rows}
    assert set(records) == set(wheel.namelist())
    assert records.pop(record) == ("", "")

    for member, (digest, size) in records.items():
        data = wheel.read(member)
        expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        assert size == str(len(data)), member
        assert digest == "sha256=" + expected.decode("ascii"), member


@pytest.mark.parametrize("arch", ["x86_64", "aarch64"])
def test_linux_libc_variants_share_binary(wheels, arch):
    """Use identical binaries for manylinux and musllinux on each architecture."""
    binaries = []
    for libc in ("manylinux_2_17", "musllinux_1_2"):
        [path] = [path for path in wheels if path.name.endswith(f"-{libc}_{arch}.whl")]
        with zipfile.ZipFile(path) as wheel:
            binaries.append(wheel.read(f"{STEM}.data/scripts/hello-radler"))
    assert binaries[0] == binaries[1]


@pytest.fixture(scope="module", params=["pip", "uv"])
def installed_command(request, tmp_path_factory, native_wheel):
    environment = tmp_path_factory.mktemp(f"venv-{request.param}")
    create = [sys.executable, "-m", "venv"]
    if request.param == "uv":
        create.append("--without-pip")
    subprocess.run([*create, str(environment)], check=True, timeout=60)

    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    if request.param == "uv":
        uv = shutil.which("uv")
        assert uv is not None, "uv is required for the installer integration tests"
        command = [uv, "pip", "install", "--python", str(python)]
    else:
        command = [str(python), "-m", "pip", "install"]
    subprocess.run(
        [*command, "--no-index", "--no-deps", str(native_wheel)], check=True, timeout=60
    )
    return scripts / ("hello-radler.exe" if os.name == "nt" else "hello-radler")


def test_installed_command(installed_command, native_wheel):
    """Install the native executable unchanged with both pip and uv.

    Run it without Python or Go on PATH and check the embedded linker values.
    """
    with zipfile.ZipFile(native_wheel) as wheel:
        member = f"{STEM}.data/scripts/{installed_command.name}"
        assert installed_command.read_bytes() == wheel.read(member)
    result = subprocess.run(
        [str(installed_command)],
        env=os.environ | {"PATH": ""},
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert result.stdout == "hello from Go\n1.2.3rc1\nhello world\n"


def test_root_package_is_reproducible(tmp_path, monkeypatch):
    """Build identical root-package wheels with a fixed SOURCE_DATE_EPOCH.

    The archive uses that timestamp and the module directory's name for the
    installed command.
    """
    module = tmp_path / "root-command"
    module.mkdir()
    (module / "go.mod").write_text("module example.com/root\n\ngo 1.20\n")
    (module / "main.go").write_text('package main\nfunc main() { println("root") }\n')
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    [first] = build_wheels(
        module, platforms=["linux-amd64"], output_dir=tmp_path / "one"
    )
    [second] = build_wheels(
        module, platforms=["linux-amd64"], output_dir=tmp_path / "two"
    )
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as wheel:
        assert {info.date_time for info in wheel.infolist()} == {
            (2023, 11, 14, 22, 13, 20)
        }
        assert "root_command-0.1.0.data/scripts/root-command" in wheel.namelist()


def test_library_package_fails(tmp_path, go_module):
    """Reject a library package and leave the output directory empty."""
    with pytest.raises(RuntimeError, match="main package"):
        build_wheels(go_module, platforms=["linux-amd64"], output_dir=tmp_path)
    assert not list(tmp_path.iterdir())


def test_failed_target_does_not_publish_partial_set(tmp_path, go_module):
    """Keep existing wheels unchanged when a later target fails.

    The command has only an amd64 source file, so the arm64 build fails.
    The existing amd64 wheel must remain intact, and the staging directory
    must be removed.
    """
    sentinel = tmp_path / "hello-0.1.0-py3-none-manylinux_2_17_x86_64.whl"
    sentinel.write_bytes(b"previous build")

    with pytest.raises(RuntimeError, match="Go build for linux/arm64 failed"):
        build_wheels(
            go_module,
            name="hello",
            package_path="cmd/amd64-only",
            platforms=["linux-amd64", "linux-arm64"],
            output_dir=tmp_path,
        )
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"previous build"


@pytest.mark.parametrize(
    ("target", "goos", "goarch"),
    [
        ("linux-amd64", "linux", "amd64"),
        ("linux-arm64", "linux", "arm64"),
        ("darwin-amd64", "darwin", "amd64"),
        ("darwin-arm64", "darwin", "arm64"),
        ("windows-amd64", "windows", "amd64"),
        ("windows-arm64", "windows", "arm64"),
    ],
)
def test_compile_environment(tmp_path, go_module, monkeypatch, target, goos, goarch):
    """Override inherited Go settings to build for the selected target.

    Read the binary's build information to check the target, disabled cgo,
    and baseline CPU features.
    """
    monkeypatch.setenv("GOOS", "plan9")
    monkeypatch.setenv("GOARCH", "386")
    monkeypatch.setenv("GOAMD64", "v4")
    monkeypatch.setenv("GOARM64", "v9.5")
    monkeypatch.setenv("CGO_ENABLED", "1")
    [wheel] = build_wheels(
        go_module,
        package_path="cmd/hello",
        platforms=[target],
        output_dir=tmp_path,
    )
    binary = tmp_path / "binary"
    with zipfile.ZipFile(wheel) as archive:
        [script] = [name for name in archive.namelist() if ".data/scripts/" in name]
        binary.write_bytes(archive.read(script))
    result = subprocess.run(
        ["go", "version", "-m", str(binary)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    settings = dict(
        line.removeprefix("\tbuild\t").split("=", 1)
        for line in result.stdout.splitlines()
        if line.startswith("\tbuild\t")
    )
    expected = {"GOOS": goos, "GOARCH": goarch, "CGO_ENABLED": "0"}
    expected.update({"GOAMD64": "v1"} if goarch == "amd64" else {"GOARM64": "v8.0"})
    assert {key: settings[key] for key in expected} == expected


@pytest.mark.parametrize("platform", ["linux-amd64", "darwin-arm64"])
def test_compile_timeout(tmp_path, go_module, platform):
    """Report a real Go subprocess timeout and remove staged output.

    Use a near-zero limit so even a cached build or version query times out.
    """
    with pytest.raises(RuntimeError, match="exceeded 1e-09 seconds") as error:
        build_wheels(
            go_module,
            package_path="cmd/hello",
            platforms=[platform],
            output_dir=tmp_path,
            build_timeout=1e-9,
        )
    assert isinstance(error.value.__cause__, subprocess.TimeoutExpired)
    assert not list(tmp_path.iterdir())


def test_windows_command_suffix(tmp_path, go_module):
    """Preserve an explicit .exe suffix in the Windows command name."""
    [wheel] = build_wheels(
        go_module,
        package_path="cmd/hello",
        name="hello",
        entry_point="hello.exe",
        platforms=["windows-amd64"],
        output_dir=tmp_path,
    )
    with zipfile.ZipFile(wheel) as archive:
        assert "hello-0.1.0.data/scripts/hello.exe" in archive.namelist()


def test_duplicate_platforms(tmp_path, go_module):
    """Produce one wheel when the same platform is requested twice."""
    [wheel] = build_wheels(
        go_module,
        package_path="cmd/hello",
        platforms=["linux-amd64", "linux-amd64"],
        output_dir=tmp_path,
    )
    assert list(tmp_path.iterdir()) == [wheel]


def test_cli(tmp_path, go_module):
    """Build the requested subpackage and read a README file through the CLI."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "radler",
            str(go_module),
            "--package-path",
            "./cmd/hello",
            "--platforms",
            "linux-amd64",
            "--output-dir",
            str(tmp_path),
            "--readme",
            "README.md",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert "Built 1 wheel(s):" in result.stdout
    [path] = tmp_path.glob("*.whl")
    assert path.name == "hello-0.1.0-py3-none-manylinux_2_17_x86_64.whl"
    with zipfile.ZipFile(path) as wheel:
        metadata, _ = parse_email(wheel.read("hello-0.1.0.dist-info/METADATA"))
    assert metadata["description"] == (go_module / "README.md").read_text(
        encoding="utf-8"
    )
    assert "summary" not in metadata
