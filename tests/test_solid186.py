import os

import pytest
import numpy as np
import pyansys
from pyansys import examples

try:
    __file__
except NameError:
    __file__ = '/home/alex/afrl/python/source/pyansys/tests/test_solid186.py'


test_path = os.path.dirname(os.path.abspath(__file__))
testfiles_path = os.path.join(test_path, 'testfiles', 'solid186')


@pytest.fixture(scope='module')
def result():
    return pyansys.read_binary(examples.rstfile)


@pytest.fixture(scope='module')
def archive():
    return pyansys.Archive(examples.hexarchivefile)


def test_geometry_elements(result, archive):
    r_elem = result.geometry['elem'][result.sidx_elem]
    assert np.allclose(r_elem, archive.elem)


def test_geometry_nodes(result, archive):
    assert np.allclose(result.geometry['nodes'][:, :3], archive.nodes)


def test_geometry_nodenum(result, archive):
    assert np.allclose(result.geometry['nnum'], archive.nnum)


def test_results_displacement(result):
    textfile = os.path.join(testfiles_path, 'prnsol_u.txt')
    nnum, r_values = result.nodal_solution(0)
    a_values = np.loadtxt(textfile, skiprows=2)[:, 1:4]
    assert np.allclose(r_values, a_values)


def test_results_stress(result):
    _, r_values = result.nodal_stress(0)
    textfile = os.path.join(testfiles_path, 'prnsol_s.txt')
    a_values = np.loadtxt(textfile, skiprows=2)[:, 1:]

    # ignore nan
    nanmask = ~np.isnan(r_values).any(1)
    assert np.allclose(r_values[nanmask], a_values, atol=1E-1)


def test_results_pstress(result):
    r_nnum, r_values = result.principal_nodal_stress(0)
    textfile = os.path.join(testfiles_path, 'prnsol_s_prin.txt')
    a_values = np.loadtxt(textfile, skiprows=2)[:, 1:]

    # ignore nan
    nanmask = ~np.isnan(r_values).any(1)
    assert np.allclose(r_values[nanmask], a_values, atol=100)
