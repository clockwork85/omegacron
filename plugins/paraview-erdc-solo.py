import numpy as np
from paraview.util.vtkAlgorithm import (
    VTKPythonAlgorithmBase,
    smdomain,
    smhint,
    smproperty,
    smproxy,
)

from vtkmodules.numpy_interface import dataset_adapter as dsa
from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid
import collections
# import sys
# import meshio
# import meshiah

# paraview_plugin_version = meshiah.__version__
# vtk_to_meshio_type = meshio.vtk._vtk.vtk_to_meshio_type
# meshio_to_vtk_type = meshio.vtk._vtk.meshio_to_vtk_type
# list(meshio._helpers.reader_map.keys())
# erdc_input_filetypes = list(meshiah._helpers.reader_map.keys())
erdc_input_filetypes = ['erdc']
# erdc_extensions = [ext[1:] for ext in meshiah.extension_to_filetype.keys()]
erdc_extensions = ['2dm', '3dm']
erdc_input_filetypes = ["automatic"] + erdc_input_filetypes

print(f"Erdc input filetypes : {erdc_input_filetypes}")


def vtk_type_from_erdc(erdc_type):
    if erdc_type == "triangle":
        return 5
    elif erdc_type == "tetrahedron":
        return 10
    else:
        return -1


@smproxy.reader(
    name="erdc reader",
    extensions=erdc_extensions,
    file_description="erdc supported files",
    support_reload=False,
)
class ERDCReader(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(
            self, nInputPorts=0, nOutputPorts=1,
            outputType="vtkUnstructuredGrid"
        )
        self._filename = None
        self._file_format = None

    @smproperty.stringvector(name="FileName")
    @smdomain.filelist()
    @smhint.filechooser(
        extensions=erdc_extensions, file_description="Erdc supported files"
    )
    def SetFileName(self, filename):
        if self._filename != filename:
            self._filename = filename
            self.Modified()

    @smproperty.stringvector(name="StringInfo", information_only="1")
    def GetStrings(self):
        return erdc_input_filetypes

    @smproperty.stringvector(name="FileFormat", number_of_elements="1")
    @smdomain.xml(
        """
        <StringListDomain name="list">
            <RequiredProperties>
                <Property name="StringInfo" function="StringInfo"/>
            </RequiredProperties>
        </StringListDomain>
        """
    )
    def SetFileFormat(self, file_format):
        # Automatically deduce input format
        if file_format == "automatic":
            file_format = None

        if self._file_format != file_format:
            self._file_format = file_format
            self.Modified()

    def RequestData(self, request, inInfoVec, outInfoVec):
        output = dsa.WrapDataObject(vtkUnstructuredGrid.GetData(outInfoVec))

        # Use meshio to read the mesh
        # mesh = meshiah.read(self._filename, self._file_format)
        print(f"Opening mesh: {self._filename}")
        with open(self._filename) as ifile:
            points = []
            facets = []
            cells = []
            mats = []
            for line in ifile.readlines():
                strip = line.strip()
                split = strip.split()

                if split[0] == "ND":
                    # Vertex
                    points.append([float(x) for x in split[2:]])
                elif split[0] == "E3T":
                    # Triangle
                    data = [int(x) for x in split[2:]]
                    facets.append(data[0:3])
                    mats.append(data[3])
                elif split[0] == "E4T":
                    # Tetrahedron
                    data = [int(x) for x in split[2:]]
                    facets.append(data[0:4])
                    mats.append(data[4])
                else:
                    continue

        points_np = np.array(points)
        cells_np = np.array(facets)
        mats_np = np.array(mats, dtype=np.int32)

        if cells_np.shape[1] == 3:
            cells.append(["triangle", cells_np-1])
        elif cells_np.shape[1] == 4:
            cells.append(["tetrahedron", cells_np-1])
        else:
            logging.warning(
                "ERDC writer only support triangles and tetrahedrons at this time"
                "Skipping {} polygons with {} nodes".format(cells_np.shape[0],
                                                            cells_np.shape[1])
            )
        cell_data = {}
        cell_data['Region'] = []
        cell_data['Region'].append(mats_np)

        # Points
        # if points.shape[1] == 2:
        #    points = np.hstack([points, np.zeros((len(points), 1))])
        output.SetPoints(points_np)

        # CellBlock, adapted from test/legacy_writer.py
        cell_types = np.array([], dtype=np.ubyte)
        cell_offsets = np.array([], dtype=int)
        cell_conn = np.array([], dtype=int)
        # triangle - vtk type = 5
        # tetrahedron - vtk type = 10

        for erdc_type, data in cells:
            vtk_type = vtk_type_from_erdc(erdc_type)
            ncells, npoints = data.shape
            cell_types = np.hstack(
                [cell_types, np.full(ncells, vtk_type, dtype=np.ubyte)]
            )
            offsets = len(cell_conn) + (1 + npoints) * np.arange(ncells,
                                                                 dtype=int)
            cell_offsets = np.hstack([cell_offsets, offsets])
            conn = np.hstack(
                [npoints * np.ones((ncells, 1), dtype=int), data]
            ).flatten()
            cell_conn = np.hstack([cell_conn, conn])
        print(f"cell_types: \n {cell_types}")
        print(f"cell_offsets: \n {cell_offsets}")
        print(f"cell_conn: \n {cell_conn}")
        output.SetCells(cell_types, cell_offsets, cell_conn)

        # Point data
#        for name, array in mesh.point_data.items():
#            output.PointData.append(array, name)

        # Cell data
        for name, data in cell_data.items():
            array = np.concatenate(data)
            output.CellData.append(array, name)

        # Field data
#        for name, array in mesh.field_data.items():
#            output.FieldData.append(array, name)

        return 1


@ smproxy.writer(
    name="erdc Writer",
    extensions=erdc_extensions,
    file_description="erdc supported files",
    support_reload=False,
)
@ smproperty.input(name="Input", port_index=0)
@ smdomain.datatype(dataTypes=["vtkUnstructuredGrid"],
                    composite_data_supported=False)
class ERDCWriter(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(
            self, nInputPorts=1, nOutputPorts=0,
            inputType="vtkUnstructuredGrid"
        )
        self._filename = None

    @ smproperty.stringvector(name="FileName", panel_visibility="never")
    @ smdomain.filelist()
    def SetFileName(self, filename):
        if self._filename != filename:
            self._filename = filename
            self.Modified()

    def RequestData(self, request, inInfoVec, outInfoVec):
        mesh = dsa.WrapDataObject(vtkUnstructuredGrid.GetData(inInfoVec[0]))

        # Read points
        points = np.asarray(mesh.GetPoints())

        # Read cells
        # Adapted from test/legacy_reader.py
        cell_conn = mesh.GetCells()
        cell_offsets = mesh.GetCellLocations()
        cell_types = mesh.GetCellTypes()
        cells_dict = {}
        for vtk_cell_type in np.unique(cell_types):
            offsets = cell_offsets[cell_types == vtk_cell_type]
            ncells = len(offsets)
            npoints = cell_conn[offsets[0]]
            array = np.empty((ncells, npoints), dtype=int)
            for i in range(npoints):
                array[:, i] = cell_conn[offsets + i + 1]
            cells_dict[vtk_to_meshio_type[vtk_cell_type]] = array
        cells = [meshio.CellBlock(key, cells_dict[key]) for key in cells_dict]

        # Read point and field data
        # Adapted from test/legacy_reader.py
        def _read_data(data):
            out = {}
            for i in range(data.VTKObject.GetNumberOfArrays()):
                name = data.VTKObject.GetArrayName(i)
                array = np.asarray(data.GetArray(i))
                out[name] = array
            return out

        point_data = _read_data(mesh.GetPointData())
        field_data = _read_data(mesh.GetFieldData())

        # Read cell data
        cell_data_flattened = _read_data(mesh.GetCellData())
        cell_data = {}
        for name, array in cell_data_flattened.items():
            cell_data[name] = []
            for cell_type in cells_dict:
                vtk_cell_type = meshio_to_vtk_type[cell_type]
                mask_cell_type = cell_types == vtk_cell_type
                cell_data[name].append(array[mask_cell_type])

        # Use meshiah to write mesh
        meshio.write_point_cells(
            self._filename,
            points,
            cells,
            point_data=point_data,
            cell_data=cell_data,
            field_data=field_data,
        )
        return 1

    def Write(self):
        self.Modified()
        self.Update()


def test_ERDCReader(fname):
    reader = ERDCReader()
    reader.SetFileName(fname)
    reader.Update()
    assert reader.GetOutputDataObject(0).GetNumberOfCells() > 0


if __name__ == '__main__':
    test_ERDCReader('tmp/Scenario1.2dm')
    print(f"Test passed for reading 2dm")
    test_ERDCReader('tmp/Scenario1.3dm')
    print(f"Test passed for reading 3dm")
