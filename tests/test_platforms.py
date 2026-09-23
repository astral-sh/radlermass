import pytest

from radlermass._platforms import macos_tag


@pytest.mark.parametrize(
    ("go_version", "amd64", "arm64"),
    [
        ("go1.20", "10_13", "11_0"),
        ("go1.26.2", "12_0", "12_0"),
        ("go1.27rc1", "13_0", "13_0"),
        ("go1.26.2-custom", "12_0", "12_0"),
    ],
)
def test_macos_tag(go_version, amd64, arm64):
    """Use the Go release's macOS minimum, with an arm64 floor of 11.0."""
    assert macos_tag(go_version, "x86_64") == f"macosx_{amd64}_x86_64"
    assert macos_tag(go_version, "arm64") == f"macosx_{arm64}_arm64"


def test_unknown_go_version():
    """Reject Go versions absent from the macOS version map."""
    with pytest.raises(ValueError, match="Unknown macOS minimum"):
        macos_tag("go1.28.0", "arm64")
