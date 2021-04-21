#  File IO for the Meshiah package
import meshiah
import meshio
import numpy as np
import os
import sys


def get_ext(filename):
    """ Gets the extension of the file """
    ext = os.path.splitext(filename)[-1].lower()
    return ext.split('.')[-1]


def read(filename):
    """ Read in Mesh

    This should determine what reader to use to read the meshio
    Reads in the mesh using meshio or erdc reader

    Parameters
    ----------
    :param filename: The name of the mesh file to be read
    :type filename: str

    :returns mesh{2,3}d 
    """

    meshio_extensions = [ext[1:]
                         for ext in meshio.extension_to_filetype.keys()]
    erdc_extensions = ["2dm", "3dm"]

    ext = get_ext(filename)
    print(f" Extension is {ext} ")
    if ext in meshio_extensions:
        mesh = meshio.read(filename)
    elif ext in erdc_extensions:
        if ext == "2dm":
            mesh = read_2dm(filename)
        elif ext == "3dm":
            mesh = read_3dm(filename)
    else:
        print(f"Unable to read file {filename} - It has an unknown extension")
        sys.exit()

    return mesh


def read_2dm(filename):
    """
    Reads a 2dm ERDC file format and returns a Meshio format Mesh object

    :param filename: The name of the 2dm file
    :type filename: str

    :returns mesh2d
    """
    print(f"Reading in 2dm file { filename }")
    points = []
    facets = []
    mats = []

    # Read in the 2dm file line by line
    with open(filename) as ofile:
        for line in ofile.readlines():
            split = line.split()
            if split[0] == "E3T":
                # Triangle
                data = [int(x) for x in split[2:]]
                facets.append(data[0:3])
                mats.append(data[3])
            elif split[0] == "ND":
                # Point
                points.append([float(x) for x in split[2:]])
            else:
                continue
    # Convert mesh parameters for Meshio class
    cells = []
    points = np.array(points)
    facets = np.array(facets)
    mats = np.array(mats, dtype=np.int32)
    cell_data = {}
    cell_data['Region'] = []
    cell_data['Region'].append(mats)
    cells.append(meshio.CellBlock("triangle", facets-1))
    return meshio.Mesh(points, cells, cell_data=cell_data)


def read_3dm(filename):
    """
    Reads a 3dm ERDC file format and returns a Meshio format Mesh object

    :param filename: The name of the 2dm file
    :type filename: str

    :returns mesh3d
    """
    points = []
    tets = []
    mats = []

    with open(filename) as ofile:
        for line in ofile.readlines():
            split = line.split()
            if split[0] == "E4T":
                # Tetrahedron
                data = [int(x) for x in split[2:]]
                tets.append(data[0:3])
                mats.append(data[3])
            elif split[0] == "ND":
                # Point
                points.append([float(x) for x in split[2:]])
            else:
                continue
    # Conversions for meshio format
    cells = []
    points = np.array(points)
    tets = np.array(tets)
    cells.append(meshio.CellBlock("tetrahedra", tets-1))
    mats = np.array(mats, dtype=np.int32)
    cell_data = {}
    cell_data['Region'] = []
    cell_data['Region'].append(mats)

    return meshio.Mesh(points, cells, cell_data=cell_data)


def write():
    return "Mesh Wrote"
