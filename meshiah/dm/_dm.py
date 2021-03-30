"""
I/O for ERDC 2dm / 3dm file format
"""
import logging

import numpy as np

from .._files import open_file
from .._helpers import register
from .._exceptions import ReadError, WriteError
from .._mesh import CellBlock, Mesh


def read(filename):
    with open_file(filename, "r") as f:
        mesh = read_buffer(f)
    return mesh


def read_buffer(f):
    points = []
    facets = []
    mats = []

    while True:
        line = f.readline()

        if not line:
            # EOF
            break

        strip = line.strip()

        if len(strip) == 0 or strip[0] == "#":
            continue

        split = strip.split()

        if split[0] == "ND":
            # vertex
            points.append([float(x) for x in split[2:]])
        elif split[0] == "E3T":
            # triangle
            data = [int(x) for x in split[2:]]
            facets.append(data[0:3])
            mats.append(data[3])
        elif split[0] == "E4T":
            # tetrahedron
            data = [int(x) for x in split[2:]]
            facets.append(data[0:4])
            mats.append(data[4])
        else:
            continue

    # Convert into numpy arrays
    cells = []
    points = np.array(points)
    facets = np.array(facets)
    if facets.shape[1] == 3:
        cells.append(CellBlock("triangle", facets-1))
    elif facets.shape[1] == 4:
        cells.append(CellBlock("tetra", facets-1))
    else:
        logging.warning(
            "meshio::dm only supports triangles and tetrahedrons. "
            "Skipping {} polygons with {} nodes".format(facets.shape[0],
                                                        facets.shape[1])
        )
    mats = np.array(mats, dtype=np.int32)
    cell_data = {}
    cell_data['Region'] = []
    cell_data['Region'].append(mats)
    return Mesh(points, cells, cell_data=cell_data)


def write(filename, mesh):
    for c in mesh.cells:
        if c.type not in ["triangle", "tetra"]:
            raise WriteError(
                "ERDC .2dm and .3dm files can only contain triangles or"
                "tetrahedrons."
            )
    with open_file(filename, "w") as f:
        f.write(
            "# Created by meshio v{}, {}\n".format(
                __version__, datetime.datetime.now().isoformat()
            )
        )
        for i, p in enumerate(mesh.points):
            f.write("ND {} {} {} {}\n".format(i+1, p[0], p[1], p[1]))

        for _, cell_array in mesh.cells:
            for i, c in cell_array:
                f.write("E3T {} {} {} {} 1\n".format(i+1, c[0], c[1], c[2]))


register("dm", [".2dm", ".3dm"], read, {"dm": write})
