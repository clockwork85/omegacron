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
import sys
import meshiah
try:
    import meshio
    meshioLib = True
except ImportError:
    meshioLib = False

paraview_plugin_version = meshiah.__version__
erdc_exclusive_input_filetypes = ["dm"]
erdc_exclusive_extensions = ["2dm", "3dm"]

if meshioLib:
    #paraview_plugin_version = meshio.__version__
    vtk_to_meshio_type = meshio.vtk._vtk.vtk_to_meshio_type
    erdc_to_vtk_type = meshio.vtk._vtk.meshio_to_vtk_type
    meshio_input_filetypes = list(meshio._helpers.reader_map.keys())
    meshio_extensions = [ext[1:]
                         for ext in meshio.extension_to_filetype.keys()]
    erdc_extensions = erdc_exclusive_extensions + meshio_extensions
    erdc_input_filetypes = ["automatic"] + \
        meshio_input_filetypes + erdc_exclusive_input_filetypes
    reader_name = 'ERDC-meshio reader'
    description = 'ERDC-meshio supported files'
else:
    vtk_to_erdc_type = {5: "triangle", 10: "tetrahedra"}
    erdc_to_vtk_type = {"triangle": 5, "tetrahedra": 10}
    erdc_input_filetypes = ["automatic"] + erdc_exclusive_input_filetypes
    erdc_extensions = erdc_exclusive_extensions
    reader_name = 'ERDC reader'
    description = 'ERDC supported files'

print(f"ERDC extensions:\n {erdc_extensions}")
print(f"ERDC input filetypes:\n {erdc_input_filetypes}")


def get_erdc_extensions(fname):
    filename = fname.split('.')
    ext = filename[-1]
    if ext in erdc_extensions:
        return ext
    else:
        return None


@smproxy.reader(
    name=reader_name,
    extensions=erdc_extensions,
    file_description=description,
    support_reload=False,
)
class ERDCReader(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(
            self, nInputPorts=0, nOutputPorts=1, outputType="vtkUnstructuredGrid"
        )
        self._filename = None
        self._file_format = None

    @smproperty.stringvector(name="FileName")
    @smdomain.filelist()
    @smhint.filechooser(
        extensions=erdc_extensions, file_description=description
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

        # Determine how to read the mesh
        self._file_format = get_erdc_extensions(self._filename)
        if(self._file_format):
            mesh = meshiah.read_for_paraview(self._filename)
        elif(meshioLib and not self._file_format):
            mesh = meshio.read(self._filename, self._file_format)
            points, cells = mesh.points, mesh.cells
        else:
            print(f"Unable to deduce file format from file: {self._filename}")

        # Points
        if points.shape[1] == 2:
            points = np.hstack([points, np.zeros((len(points), 1))])
        output.SetPoints(points)

        # CellBlock, adapted from test/legacy_writer.py
        cell_types = np.array([], dtype=np.ubyte)
        cell_offsets = np.array([], dtype=int)
        cell_conn = np.array([], dtype=int)
        for meshio_type, data in cells:
            vtk_type = meshio_to_vtk_type[meshio_type]
            ncells, npoints = data.shape
            cell_types = np.hstack(
                [cell_types, np.full(ncells, vtk_type, dtype=np.ubyte)]
            )
            offsets = len(cell_conn) + (1 + npoints) * \
                np.arange(ncells, dtype=int)
            cell_offsets = np.hstack([cell_offsets, offsets])
            conn = np.hstack(
                [npoints * np.ones((ncells, 1), dtype=int), data]
            ).flatten()
            cell_conn = np.hstack([cell_conn, conn])
        output.SetCells(cell_types, cell_offsets, cell_conn)

        # Point data
        for name, array in mesh.point_data.items():
            output.PointData.append(array, name)

        # Cell data
        for name, data in mesh.cell_data.items():
            array = np.concatenate(data)
            output.CellData.append(array, name)

        # Field data
        for name, array in mesh.field_data.items():
            output.FieldData.append(array, name)

        return 1


@smproxy.writer(
    name="meshio Writer",
    extensions=meshio_extensions,
    file_description="meshio-supported files",
    support_reload=False,
)
@smproperty.input(name="Input", port_index=0)
@smdomain.datatype(dataTypes=["vtkUnstructuredGrid"], composite_data_supported=False)
class MeshioWriter(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(
            self, nInputPorts=1, nOutputPorts=0, inputType="vtkUnstructuredGrid"
        )
        self._filename = None

    @smproperty.stringvector(name="FileName", panel_visibility="never")
    @smdomain.filelist()
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

        # Use meshio to write mesh
        meshio.write_points_cells(
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


def test_ERDCReader_Exc(fname):
    reader = ERDCReader()
    reader.SetFileName(fname)
    reader.Update()
    assert reader.GetOutputDataObject(0).GetNumberOfCells() > 0


if __name__ == '__main__':
    test_ERDCReader_Exc('tmp/Scenario1.2dm')
