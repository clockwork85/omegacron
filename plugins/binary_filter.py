#!/usr/bin/env python

from paraview.util.vtkAlgorithm import *
import struct


@smproxy.filter()
@smproperty.input(name="Flux Reader")
@smdomain.datatype(dataTypes=["vtkUnstructuredGrid"], composite_data_supported=False)
class FluxReader(VTKPythonAlgorithmBase):
    def __init__(self):
        super().__init__(nInputPorts=1, nOutputPorts=1,
                         outputType='vtkUnstructuredGrid')
        self._filename = ""
        self._numlights = None
        self._bindata = None

    @smproperty.intvector(name="Number of Lights", default_values=1249)
    def SetNumLights(self, numLights):
        if numLights != self._numlights:
            self._numlights = numLights
            self.Modified()

    def GetNumLights(self):
        return self._numlights

    @smproperty.stringvector(name="Flux File")
    @smdomain.filelist()
    @smhint.filechooser(extensions="bin", file_description="Flux file to read in")
    def SetFileName(self, fname):
        if fname != self._filename:
            self._filename = fname
            self.Modified()

    def GetFileName(self):
        return self._filename

    def RequestDataObject(self, request, inInfo, outInfo):
        inData = self.GetInputData(inInfo, 0, 0)
        outData = self.GetOutputData(outInfo, 0)
        assert inData is not None
        # if outData is not None or (not outData.IsA(inData.GetClassName())):
        outData = inData.NewInstance()
        outInfo.GetInformationObject(0).Set(outData.DATA_OBJECT(), outData)
        return super().RequestDataObject(request, inInfo, outInfo)

    def RequestData(self, request, inInfo, outInfo):
        from vtkmodules.numpy_interface import dataset_adapter as dsa
        from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid
        import vtk
        inData = self.GetInputData(inInfo, 0, 0)
        # outData = self.GetOutputData(outInfo, 0)
        output = dsa.WrapDataObject(vtkUnstructuredGrid.GetData(outInfo, 0))
        output.ShallowCopy(inData)
        # output = dsa.WrapDataObject(vtkUnstructuredGrid.GetData(outData, 0))
        data = self._read_flux_file()
        data_vtk = vtk.vtkDoubleArray()
        data_vtk.SetNumberOfValues(len(data))
        data_vtk.SetName('FluxData')
        for i, val in enumerate(data):
            data_vtk.InsertValue(i, val[0]/self._numlights)
        output.GetCellData().AddArray(data_vtk)
        return 1

    def _read_flux_file(self):
        f = open(self._filename, 'rb')
        number_of_lights = int.from_bytes(f.read(4), byteorder='little')
        assert(number_of_lights == self._numlights)
        num_doubles = int.from_bytes(f.read(4), byteorder='little')
        self._bindata = [struct.unpack('d', f.read(8))
                         for i in range(num_doubles)]
        return self._bindata
