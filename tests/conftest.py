import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename

from radler import build_wheels


@pytest.fixture(scope="session")
def go_module() -> Path:
    return Path(__file__).parent / "fixtures" / "hello"


@pytest.fixture(scope="session")
def go_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    if shutil.which("go") is None:
        pytest.skip("Go is required for integration tests")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GOTOOLCHAIN", "local")
        patch.setenv("GOPROXY", "off")
        patch.setenv("GOSUMDB", "off")
        patch.setenv("GOWORK", "off")
        patch.setenv("GOFLAGS", "")
        if "GOCACHE" not in os.environ:
            patch.setenv("GOCACHE", str(tmp_path_factory.mktemp("go-cache")))
        yield


@pytest.fixture(scope="session")
def wheels(tmp_path_factory, go_environment, go_module) -> list[Path]:
    return build_wheels(
        go_module,
        name="Radler_Test--CLI",
        version="v1.2.3-rc.1",
        entry_point="hello-radler",
        package_path="cmd/hello",
        output_dir=tmp_path_factory.mktemp("wheels"),
        set_version_var="main.version",
        ldflags="-X 'main.commit=hello world'",
        description="A compiled command — Grüße!",
        author="Zoë Example",
        author_email="test@example.com",
        license_="MIT",
        url="https://example.com",
        readme=Path("README.md"),
    )


@pytest.fixture(scope="session")
def native_wheel(wheels) -> Path:
    compatible = set(sys_tags())
    matches = [
        path for path in wheels if parse_wheel_filename(path.name)[3] & compatible
    ]
    if not matches:
        pytest.skip("No wheel target matches the host platform")
    [wheel] = matches
    return wheel
