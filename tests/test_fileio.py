from meshiah import fileio


def test_Read2dm():
    filename = 'tmp/Scenario1.2dm'
    mesh = fileio.read(filename)
    assert len(mesh.points) == 1942
    assert len(mesh.cells[0][1]) == 3743


def test_Read3dm():
    filename = 'tmp/Scenario1.3dm'
    mesh = fileio.read(filename)
    assert len(mesh.points) == 9225
    assert len(mesh.cells[0][1]) == 39034


def test_MeshioType():
    filename = 'tmp/Scenario1.obj'
    mesh = fileio.read(filename)
    assert len(mesh.points) == 1942
    assert len(mesh.cells[0][1]) == 3743
