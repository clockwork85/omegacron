"""Top-level package for omegacron."""

__author__ = """Matthew D. Bray"""
__email__ = 'matthew.d.bray1985@gmail.com'
__version__ = '0.1.0'

from . import (
    dm
)
from ._helpers import extension_to_filetype, read
from ._mesh import CellBlock, Mesh

__all__ = [
    "2dm",
    "3dm",
    "read",
    "Mesh",
    "extension_to_filetype",
    "CellBlock",
    "ReadError",
    "WriteError",
    "__version__"
]
