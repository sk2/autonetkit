from typing import NamedTuple, Optional


class RenderedFileEntry(NamedTuple):
    body: str
    path: Optional[str]
    filename: str
