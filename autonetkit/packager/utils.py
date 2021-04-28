import os

from autonetkit.render.types import RenderedFileEntry


def write_rendered_to_file(entry: RenderedFileEntry, base_dir: str) -> None:
    """

    @param entry:
    @param base_dir:
    """
    if entry.path:
        path = os.path.join(base_dir, entry.path)
    else:
        path = base_dir

    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    filename = os.path.join(path, entry.filename)
    with open(filename, "w") as fh:
        fh.write(entry.body)
