import pytest
from packaging.version import Version

from radlermass import build_wheels
from radlermass._cli import main
from radlermass._metadata import Metadata
from radlermass._wheel import write_wheel


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("name", "../evil", "name is invalid"),
        ("version", "invalid", "Invalid version"),
        ("entry_point", "../evil", "command name"),
        ("entry_point", "a\\b", "command name"),
        ("entry_point", "tool.", "command name"),
        ("package_path", "../", "inside the Go module"),
        ("package_path", "go.mod", "package directory not found"),
        ("platforms", ["linux-amd64", "typo"], "Unknown platform"),
        ("platforms", [], "at least one platform"),
        ("description", "hello\nRequires-Dist: injected", "control characters"),
        (
            "set_version_var",
            "main.version -X main.other",
            "Invalid Go version variable",
        ),
        ("build_timeout", 0, "positive, finite"),
        ("build_timeout", float("nan"), "positive, finite"),
        ("go_binary", "radlermass-no-such-go", "Go executable not found"),
    ],
)
def test_invalid_options(tmp_path, go_module, option, value, message):
    """Reject invalid options without creating the output directory."""
    output = tmp_path / "dist"
    with pytest.raises(ValueError, match=message):
        build_wheels(go_module, output_dir=output, **{option: value})
    assert not output.exists()


def test_absolute_package_path_rejected(tmp_path, go_module):
    """Reject absolute package paths, including paths inside the module."""
    with pytest.raises(ValueError, match="relative to the Go module"):
        build_wheels(
            go_module, package_path=str(go_module.resolve()), output_dir=tmp_path
        )
    assert not list(tmp_path.iterdir())


def test_missing_module(tmp_path):
    """Require a go.mod file in the module directory."""
    with pytest.raises(ValueError, match="no go.mod"):
        build_wheels(tmp_path)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "/absolute",
        "C:/absolute",
        "../outside",
        "sboms/../outside",
        "sboms\\outside",
        "sboms/./manifest",
        "sboms//manifest",
        "sboms/",
        "RECORD\x00suffix",
        "METADATA",
        "WHEEL",
        "RECORD",
        "sboms/go.mod.json",
        "RECORD/sub",
        "sboms",
    ],
)
def test_invalid_extra_dist_info_path(tmp_path, name):
    """Reject unsafe paths and collisions with files or directories in the wheel."""
    binary = tmp_path / "hello"
    binary.touch()
    with pytest.raises(ValueError, match=r"\.dist-info file path"):
        write_wheel(
            binary=binary,
            output_dir=tmp_path,
            metadata=Metadata("hello", Version("1")),
            command="hello",
            tag="manylinux_2_17_x86_64",
            timestamp=(1980, 1, 1, 0, 0, 0),
            gomod_json=b"{}",
            extra_dist_info_files={name: b"extra"},
        )


def test_cli_reports_errors(tmp_path, go_module, capsys):
    """Report an empty entry in --platforms on stderr with exit status 1."""
    result = main(
        [
            str(go_module),
            "--output-dir",
            str(tmp_path),
            "--platforms",
            "linux-amd64,",
        ]
    )
    assert result == 1
    captured = capsys.readouterr()
    assert "Unknown platform" in captured.err
    assert not captured.out
    assert not list(tmp_path.iterdir())
