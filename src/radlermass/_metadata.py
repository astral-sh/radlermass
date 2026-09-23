"""Distribution names, versions, and core metadata."""

import re
from dataclasses import dataclass

from packaging.metadata import RFC822Message
from packaging.utils import canonicalize_name
from packaging.version import Version


def validate_command(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) or name.endswith("."):
        raise ValueError(f"Invalid command name: {name!r}")


@dataclass(frozen=True)
class Metadata:
    name: str
    version: Version
    description: str | None = None
    author: str | None = None
    author_email: str | None = None
    license: str | None = None
    url: str | None = None
    readme: str | None = None

    @property
    def stem(self) -> str:
        name = canonicalize_name(self.name, validate=True).replace("-", "_")
        return f"{name}-{self.version}"

    def render(self) -> bytes:
        # Omit Requires-Python: the wheel installs a native executable directly.
        headers = {
            "Metadata-Version": "2.1",
            "Name": self.name,
            "Version": str(self.version),
            "Summary": self.description,
            "Author": self.author,
            "Author-email": self.author_email,
            "License": self.license,
            "Home-page": self.url,
            "Description-Content-Type": "text/markdown"
            if self.readme is not None
            else None,
        }

        message = RFC822Message()
        for key, value in headers.items():
            if value is not None:
                if any(ord(char) < 32 or ord(char) == 127 for char in value):
                    raise ValueError(f"{key} must not contain control characters")

                message[key] = value

        message.set_payload(self.readme or "")
        return message.as_bytes()
