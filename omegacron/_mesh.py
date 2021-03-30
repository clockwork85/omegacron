import collections

import numpy as np


class CellBlock(collections.namedtuple("CellBlock", ["type", "data"])):
    def __repr__(self):
        return f"<meshio CellBlock, type: {self.type},"
        f"num cells: {len(self.data)}>"


class Mesh:
    def __init__(
        self,
        points,
        cells,
        point_data=None,
        cell_data=None,
        field_data=None,
        point_sets=None,
        cell_sets=None,
        gmsh_periodic=None,
        info=None,
    ):
        self.points = np.asarray(points)
        if isinstance(cells, dict):
            # Let's not deprecate this for now.
            # import warnings
            # warnings.warn(
            #     "cell dictionaries are deprecated,
            #      use list of tuples, e.g., "
            #     '[("triangle", [[0, 1, 2], ...])]',
            #     DeprecationWarning,
            # )
            # old dict, deprecated
            self.cells = [
                CellBlock(cell_type, np.asarray(data))
                for cell_type, data in cells.items()
            ]
        else:
            self.cells = [
                CellBlock(cell_type, np.asarray(data)) for cell_type,
                data in cells
            ]
        self.point_data = {} if point_data is None else point_data
        self.cell_data = {} if cell_data is None else cell_data
        self.field_data = {} if field_data is None else field_data
        self.point_sets = {} if point_sets is None else point_sets
        self.cell_sets = {} if cell_sets is None else cell_sets
        self.gmsh_periodic = gmsh_periodic
        self.info = info

        for key, data in self.cell_data.items():
            assert len(data) == len(cells), (
                "Incompatible cell data. "
                f"{len(cells)} cell blocks, but '{key}'"
                f"has {len(data)} blocks."
            )

    def __repr__(self):
        lines = ["<meshio format mesh object>",
                 f"  Number of points: {len(self.points)}"]
        if len(self.cells) > 0:
            lines.append("  Number of cells:")
            for tpe, elems in self.cells:
                lines.append(f"    {tpe}: {len(elems)}")
        else:
            lines.append("  No cells.")

        if self.point_sets:
            names = ", ".join(self.point_sets.keys())
            lines.append(f"  Point sets: {names}")

        if self.cell_sets:
            names = ", ".join(self.cell_sets.keys())
            lines.append(f"  Cell sets: {names}")

        if self.point_data:
            names = ", ".join(self.point_data.keys())
            lines.append(f"  Point data: {names}")

        if self.cell_data:
            names = ", ".join(self.cell_data.keys())
            lines.append(f"  Cell data: {names}")

        return "\n".join(lines)
