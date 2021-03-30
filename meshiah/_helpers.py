import pathlib
from typing import List, Optional

from ._exceptions import ReadError, WriteError
from ._files import is_buffer

extension_to_filetype = {}
reader_map = {}
_writer_map = {}


def register(name: str, extensions: List[str], reader, writer_map):
    for ext in extensions:
        extension_to_filetype[ext] = name

    if reader is not None:
        reader_map[name] = reader
    _writer_map.update(writer_map)


def _filetype_from_path(path: pathlib.Path):
    ext = ""
    out = None
    for suffix in reversed(path.suffixes):
        ext = (suffix + ext).lower()
        if ext in extension_to_filetype:
            out = extension_to_filetype[ext]

    if out is None:
        raise ReadError(
            f"Could not deduce file format from extension '{ext}'."
        )
    return out


def read(filename, file_format: Optional[str] = None):
    """Reads an unstructured mesh with added data.
    :param filenames: The files/PathLikes to read from.
    :type filenames: str

    :returns mesh{2,3}d: The mesh data.
    """
    if is_buffer(filename, "r"):
        if file_format == "tetgen":
            raise ReadError(
                "tetgen format is spread across multiple files "
                "and so cannot be read from a buffer"
            )
        msg = f"Unknown file format '{file_format}'"
    else:
        path = pathlib.Path(filename)
        if not path.exists():
            raise ReadError(f"File {filename} not found.")

        if not file_format:
            # deduce file format from extension
            file_format = _filetype_from_path(path)

        msg = f"Unknown file format '{file_format}' of '{filename}'."

    if file_format not in reader_map:
        raise ReadError(msg)

    return reader_map[file_format](filename)
