import pytest

from radler import build_wheels
from radler._cli import main


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
        ("go_binary", "radler-no-such-go", "Go executable not found"),
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
