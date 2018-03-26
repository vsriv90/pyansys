"""
Used v150/ansys/customize/user/ResRd.F to help build this interface

"""
import struct
import os
import numpy as np
import warnings
import logging
import ctypes
from ctypes import c_int64

import vtkInterface
from pyansys import _parsefull
from pyansys import _rstHelper
from pyansys import _parser
from pyansys.elements import valid_types
AxisRotation = vtkInterface.common.AxisRotation
try:
    import vtk
    vtkloaded = True
except BaseException:
    warnings.warn('Cannot load vtk\nWill be unable to display results.')
    vtkloaded = False

# Create logger
log = logging.getLogger(__name__)
log.setLevel('DEBUG')

np.seterr(divide='ignore', invalid='ignore')


def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


# Pointer information from ansys interface manual
# =============================================================================
# Individual element index table
e_table = ['ptrEMS', 'ptrENF', 'ptrENS', 'ptrENG', 'ptrEGR', 'ptrEEL',
           'ptrEPL', 'ptrECR', 'ptrETH', 'ptrEUL', 'ptrEFX', 'ptrELF',
           'ptrEMN', 'ptrECD', 'ptrENL', 'ptrEHC', 'ptrEPT', 'ptrESF',
           'ptrEDI', 'ptrETB', 'ptrECT', 'ptrEXY', 'ptrEBA', 'ptrESV',
           'ptrMNL']

"""
ptrEMS - pointer to misc. data
ptrENF - pointer to nodal forces
ptrENS - pointer to nodal stresses
ptrENG - pointer to volume and energies
ptrEGR - pointer to nodal gradients
ptrEEL - pointer to elastic strains
ptrEPL - pointer to plastic strains
ptrECR - pointer to creep strains
ptrETH - pointer to thermal strains
ptrEUL - pointer to euler angles
ptrEFX - pointer to nodal fluxes
ptrELF - pointer to local forces
ptrEMN - pointer to misc. non-sum values
ptrECD - pointer to element current densities
ptrENL - pointer to nodal nonlinear data
ptrEHC - pointer to calculated heat generations
ptrEPT - pointer to element temperatures
ptrESF - pointer to element surface stresses
ptrEDI - pointer to diffusion strains
ptrETB - pointer to ETABLE items(post1 only)
ptrECT - pointer to contact data
ptrEXY - pointer to integration point locations
ptrEBA - pointer to back stresses
ptrESV - pointer to state variables
ptrMNL - pointer to material nonlinear record
"""

SOLUTION_HEADER_KEYS = ['pv3num', 'nelm', 'nnod', 'mask', 'itime',
                        'iter', 'ncumit', 'nrf', 'cs_LSC', 'nmast',
                        'ptrNSL', 'ptrESL', 'ptrRF', 'ptrMST', 'ptrBC',
                        'rxtrap', 'mode', 'isym', 'kcmplx', 'numdof',
                        'DOFS', 'DOFS', 'DOFS', 'DOFS', 'DOFS',
                        'DOFS', 'DOFS', 'DOFS', 'DOFS', 'DOFS',
                        'DOFS', 'DOFS', 'DOFS', 'DOFS', 'DOFS',
                        'DOFS', 'DOFS', 'DOFS', 'DOFS', 'DOFS',
                        'DOFS', 'DOFS', 'DOFS', 'DOFS', 'DOFS',
                        'DOFS', 'DOFS', 'DOFS', 'DOFS', 'DOFS',
                        'title', 'title', 'title', 'title', 'title',
                        'title', 'title', 'title', 'title', 'title',
                        'title', 'title', 'title', 'title', 'title',
                        'title', 'title', 'title', 'title', 'title',
                        'stitle', 'stitle', 'stitle', 'stitle', 'stitle',
                        'stitle', 'stitle', 'stitle', 'stitle', 'stitle',
                        'stitle', 'stitle', 'stitle', 'stitle', 'stitle',
                        'stitle', 'stitle', 'stitle', 'stitle', 'stitle',
                        'dbmtim', 'dbmdat', 'dbfncl', 'soltim', 'soldat',
                        'ptrOND', 'ptrOEL', 'nfldof', 'ptrEXA', 'ptrEXT',
                        'ptrEXAl', 'ptrEXAh', 'ptrEXTl', 'ptrEXTh', 'ptrNSLl',
                        'ptrNSLh', 'ptrRFl', 'ptrRFh', 'ptrMSTl', 'ptrMSTh',
                        'ptrBCl', 'ptrBCh', 'ptrTRFl', 'ptrTRFh', 'ptrONDl',
                        'ptrONDh', 'ptrOELl', 'ptrOELh', 'ptrESLl', 'ptrESLh',
                        'ptrOSLl', 'ptrOSLh', '0', '0', '0',
                        'PrinKey', 'numvdof', 'numadof', '0', '0',
                        'ptrVSLl', 'ptrVSLh', 'ptrASLl', 'ptrASLh', '0',
                        '0', '0', '0', 'numRotCmp', '0',
                        'ptrRCMl', 'ptrRCMh', 'nNodStr', '0', 'ptrNDSTRl',
                        'ptrNDSTRh', 'AvailData', 'geomID', 'ptrGEOl', 'ptrGEOh']

GEOMETRY_HEADER_KEYS = ['__unused', 'maxety', 'maxrl', 'nnod', 'nelm',
                        'maxcsy', 'ptrETY', 'ptrREL', 'ptrLOC', 'ptrCSY',
                        'ptrEID', 'maxsec', 'secsiz', 'maxmat', 'matsiz',
                        'ptrMAS', 'csysiz', 'elmsiz', 'etysiz', 'rlsiz',
                        'ptrETYl', 'ptrETYh', 'ptrRELl', 'ptrRELh', 'ptrCSYl',
                        'ptrCSYh', 'ptrLOCl', 'ptrLOCh', 'ptrEIDl', 'ptrEIDh',
                        'ptrMASl', 'ptrMASh', 'ptrSECl', 'ptrSECh', 'ptrMATl',
                        'ptrMATh', 'ptrCNTl', 'ptrCNTh', 'ptrNODl', 'ptrNODh',
                        'ptrELMl', 'ptrELMh', 'Glbnnod', 'ptrGNODl', 'ptrGNODh',
                        'maxn', 'NodesUpd',  'lenbac', 'maxcomp', 'compsiz',
                        'ptrCOMPl', 'ptrCOMPh']

RESULT_HEADER_KEYS = ['fun12', 'maxn', 'nnod', 'resmax', 'numdof',
                      'maxe', 'nelm', 'kan', 'nsets', 'ptrend',
                      'ptrDSIl', 'ptrTIMl', 'ptrLSPl', 'ptrELMl', 'ptrNODl',
                      'ptrGEOl', 'ptrCYCl', 'CMSflg', 'csEls', 'units',
                      'nSector', 'csCord', 'ptrEnd8', 'ptrEnd8', 'fsiflag',
                      'pmeth', 'noffst', 'eoffst', 'nTrans', 'ptrTRANl',
                      'PrecKey', 'csNds', 'cpxrst', 'extopt', 'nlgeom',
                      'AvailData', 'mmass', 'kPerturb', 'XfemKey', 'rstsprs',
                      'ptrDSIh', 'ptrTIMh', 'ptrLSPh', 'ptrCYCh', 'ptrELMh',
                      'ptrNODh', 'ptrGEOh', 'ptrTRANh', 'Glbnnod', 'ptrGNODl',
                      'ptrGNODh', 'qrDmpKy', 'MSUPkey', 'PSDkey', 'cycMSUPkey',
                      'XfemCrkPropTech']


# element types with stress outputs
validENS = [45, 92, 95, 181, 185, 186, 187]


class FullReader(object):
    """
    Stores the results of an ANSYS full file.

    Parameters
    ----------
    filename : str
        Filename of the full file to read.

    Examples
    --------
    >>> full = FullReader('file.rst')

    """

    def __init__(self, filename):
        """
        Loads full header on initialization

        See ANSYS programmer's reference manual full header section for
        definitions of each header.

        """

        # check if file exists
        if not os.path.isfile(filename):
            raise Exception('{:s} not found'.format(filename))

        self.filename = filename
        self.header = _parsefull.ReturnHeader(filename)

        # Check if lumped (item 11)
        if self.header[11]:
            raise Exception(
                "Unable to read a lumped mass matrix.  Terminating.")

        # Check if arrays are unsymmetric (item 14)
        if self.header[14]:
            raise Exception(
                "Unable to read an unsymmetric mass/stiffness matrix.")

    def LoadKM(self, as_sparse=True, sort=False):
        """
        Load and construct mass and stiffness matrices from an ANSYS full file.

        Parameters
        ----------
        as_sparse : bool, optional
            Outputs the mass and stiffness matrices as scipy csc sparse arrays
            when True by default.

        sort : bool, optional
            Rearranges the k and m matrices such that the rows correspond to
            to the sorted rows and columns in dor_ref.  Also sorts dor_ref.

        Returns
        -------
        dof_ref : (n x 2) np.int32 array
            This array contains the node and degree corresponding to each row
            and column in the mass and stiffness matrices.  In a 3 DOF
            analysis the dof intergers will correspond to:
            0 - x
            1 - y
            2 - z
            Sort these values by node number and DOF by enabling the sort
            parameter

        k : (n x n) np.float or scipy.csc array
            Stiffness array

        m : (n x n) np.float or scipy.csc array
            Mass array
        """
        if not os.path.isfile(self.filename):
            raise Exception('%s not found' % self.filename)

        # see if
        if as_sparse:
            try:
                from scipy.sparse import csc_matrix, coo_matrix
            except BaseException:
                raise Exception('Unable to load scipy, matricies will be full')
                as_sparse = False

        # Get header details
        neqn = self.header[2]  # Number of equations
        ntermK = self.header[9]  # number of terms in stiffness matrix
        ptrSTF = self.header[19]  # Location of stiffness matrix
        ptrMAS = self.header[27]  # Location in file to mass matrix
        # nNodes = self.header[33]  # Number of nodes considered by assembly
        ntermM = self.header[34]  # number of terms in mass matrix
        ptrDOF = self.header[36]  # pointer to DOF info

        # DOF information
        ptrDOF = self.header[36]  # pointer to DOF info
        with open(self.filename, 'rb') as f:
            ReadTable(f, skip=True)  # standard header
            ReadTable(f, skip=True)  # full header
            ReadTable(f, skip=True)  # number of degrees of freedom
            neqv = ReadTable(f)  # Nodal equivalence table

            f.seek(ptrDOF*4)
            ndof = ReadTable(f)
            const = ReadTable(f)

        # dof_ref = np.vstack((ndof, neqv)).T  # stack these references
        dof_ref = [ndof, neqv]

        # Read k and m blocks (see help(ReadArray) for block description)
        if ntermK:
            krow, kcol, kdata = _rstHelper.ReadArray(self.filename,
                                                     ptrSTF,
                                                     ntermK,
                                                     neqn,
                                                     const)
        else:
            warnings.warn('Missing stiffness matrix')
            kdata = None

        if ntermM:
            mrow, mcol, mdata = _rstHelper.ReadArray(self.filename,
                                                     ptrMAS,
                                                     ntermM,
                                                     neqn,
                                                     const)
        else:
            warnings.warn('Missing mass matrix')
            mdata = None

        # remove constrained entries
        if np.any(const < 0):
            if kdata is not None:
                remove = np.nonzero(const < 0)[0]
                mask = ~np.logical_or(np.in1d(krow, remove), np.in1d(kcol, remove))
                krow = krow[mask]
                kcol = kcol[mask]
                kdata = kdata[mask]

            if mdata is not None:
                mask = ~np.logical_or(np.in1d(mrow, remove), np.in1d(mcol, remove))
                mrow = mrow[mask]
                mcol = mcol[mask]
                mdata = mdata[mask]

        dof_ref, index, nref, dref = _rstHelper.SortNodalEqlv(neqn, neqv, ndof)
        if sort:  # make sorting the same as ANSYS rdfull would output
            # resort to make in upper triangle
            krow = index[krow]
            kcol = index[kcol]
            krow, kcol = np.sort(np.vstack((krow, kcol)), 0)

            mrow = index[mrow]
            mcol = index[mcol]
            mrow, mcol = np.sort(np.vstack((mrow, mcol)), 0)
        else:
            dof_ref = np.vstack((nref, dref)).T

        # store data for later reference
        if kdata is not None:
            self.krow = krow
            self.kcol = kcol
            self.kdata = kdata
        if mdata is not None:
            self.mrow = mrow
            self.mcol = mcol
            self.mdata = mdata

        # output as a sparse matrix
        if as_sparse:

            if kdata is not None:
                k = coo_matrix((neqn,) * 2)
                k.data = kdata  # data has to be set first
                k.row = krow
                k.col = kcol

                # convert to csc matrix (generally faster for sparse solvers)
                k = csc_matrix(k)
            else:
                k = None

            if mdata is not None:
                m = coo_matrix((neqn,) * 2)
                m.data = mdata
                m.row = mrow
                m.col = mcol

                # convert to csc matrix (generally faster for sparse solvers)
                m = csc_matrix(m)
            else:
                m = None

        else:
            if kdata is not None:
                k = np.zeros((neqn,) * 2)
                k[krow, kcol] = kdata
            else:
                k = None

            if mdata is not None:
                m = np.zeros((neqn,) * 2)
                m[mrow, mcol] = mdata
            else:
                m = None

        # store if constrained and number of degrees of freedom per node
        self.const = const < 0
        self.ndof = ndof

        return dof_ref, k, m


def ResultReader(filename):
    """
    Reads a binary ANSYS result file.

    Parameters
    ----------
    filename : string
        Filename of the ANSYS binary result file.

    """
    # determine if file is a result file
    standard_header = ReadStandardHeader(filename)
    if standard_header['file format'] != 12:
        raise Exception('Binary file is not a result file.')

    # determine if cyclic
    with open(filename, 'rb') as f:
        f.seek(103 * 4)
        result_header = ParseHeader(ReadTable(f), RESULT_HEADER_KEYS)

    if result_header['nSector'] == 1:
        log.debug('Initializing standard result')
        return Result(filename)
    else:
        log.debug('Initializing cyclic result')
        return CyclicResult(filename)


class Result(object):
    """
    Reads a binary ANSYS result file.

    Parameters
    ----------
    filename : string
        Filename of the ANSYS binary result file.

    """
    def __init__(self, filename):
        """
        Loads basic result information from result file and initializes result
        object.

        """
        # Store filename result header items
        self.filename = filename
        self.resultheader = GetResultInfo(filename)

        # Get the total number of results and log it
        self.nsets = len(self.resultheader['rpointers'])
        string = 'There are {:d} results in this file'.format(self.nsets)
        log.debug(string)

        # Get indices to resort nodal and element results
        self.sidx = np.argsort(self.resultheader['neqv'])
        self.sidx_elem = np.argsort(self.resultheader['eeqv'])

        # Store node numbering in ANSYS
        self.nnum = self.resultheader['neqv'][self.sidx]
        self.enum = self.resultheader['eeqv'][self.sidx_elem]

        # Store time values for later retrival
        self.GetTimeValues()

        # store geometry for later retrival
        self.StoreGeometry()

    def Plot(self):
        """ plots result geometry """
        self.grid.Plot()

    # def ResultsProperties(self):
    #     """
    #     Logs results available in the result file and returns a dictionary
    #     of available results

    #     Logging must be enabled for the results of the check to be shown in the
    #     console.

    #     Returns
    #     -------
    #     result_check : dict
    #         Dictionary indicating the availability of results.

    #     """

    #     # check number of results
    #     log.debug(
    #         'There are {:d} results in this file'.format(
    #             self.nsets))

    #     if self.resultheader['nSector'] > 1:
    #         log.debug('Contains results from a cyclic analysis with:')
    #         log.debug('\t{:d} sectors'.format(self.resultheader['nSector']))

    #     return {'Number of Results': self.nsets}

    def PlotNodalSolution(self, rnum, comp='norm', as_abs=False, label='',
                          colormap=None, flipscalars=None, cpos=None, screenshot=None,
                          interactive=True):
        """
        Plots a nodal result.

        Parameters
        ----------
        rnum : int
            Cumulative result number.  Zero based indexing.

        comp : str, optional
            Display component to display.  Options are 'x', 'y', 'z', and
            'norm', corresponding to the x directin, y direction, z direction,
            and the combined direction (x**2 + y**2 + z**2)**0.5

        as_abs : bool, optional
            Displays the absolute value of the result.

        label : str, optional
            Annotation string to add to scalar bar in plot.

        colormap : str, optional
           Colormap string.  See available matplotlib colormaps.

        flipscalars : bool, optional
            Flip direction of colormap.

        cpos : list, optional
            List of camera position, focal point, and view up.  Plot first, then
            output the camera position and save it.

        screenshot : str, optional
            Setting this to a filename will save a screenshot of the plot before
            closing the figure.

        interactive : bool, optional
            Default True.  Setting this to False makes the plot generate in the
            background.  Useful when generating plots in a batch mode automatically.

        Returns
        -------
        cpos : list
            Camera position from vtk render window.

        """
        if not vtkloaded:
            raise Exception('Cannot plot without VTK')

        # Load result from file
        nnum, result = self.NodalSolution(rnum)

        # Process result
        if comp == 'x':
            d = result[:, 0]
            stitle = 'X {:s}\n'.format(label)

        elif comp == 'y':
            d = result[:, 1]
            stitle = 'Y {:s}\n'.format(label)

        elif comp == 'z':
            d = result[:, 2]
            stitle = 'Z {:s}\n'.format(label)

        else:
            # Normalize displacement
            d = result[:, :3]
            d = (d * d).sum(1)**0.5

            stitle = 'Normalized\n%s\n' % label

        if as_abs:
            d = np.abs(d)

        # sometimes there are less nodes in the result than in the geometry
        if nnum.size != self.geometry['nnum'].size:
            scalars = np.empty(self.geometry['nnum'].size)
            scalars[:] = np.nan
            mask = np.in1d(self.geometry['nnum'], nnum)
            scalars[mask] = d
            d = scalars

        # for cyclic models
        return self.PlotPointScalars(rnum, d, stitle, colormap, flipscalars,
                                     screenshot, cpos, interactive)

    def GetTimeValues(self):
        """
        Returns table of time values for results.  For a modal analysis, this
        corresponds to the frequencies of each mode.

        Returns
        -------
        tvalues : np.float64 array
            Table of time values for results.  For a modal analysis, this
            corresponds to the frequencies of each mode.

        """
        endian = self.resultheader['endian']
        ptrTIMl = self.resultheader['ptrTIMl']

        # Load values if not already stored
        if not hasattr(self, 'tvalues'):

            # Seek to start of time result table
            f = open(self.filename, 'rb')

            f.seek(ptrTIMl * 4 + 8)
            self.tvalues = np.fromfile(f, endian + 'd', self.nsets)

            f.close()

        return self.tvalues

    def NodalSolution(self, rnum):
        """
        Returns the DOF solution for each node in the global Cartesian
        coordinate system.

        Parameters
        ----------
        rnum : interger
            Cumulative result number.  Zero based indexing.

        sort : bool, optional
            Resorts the results so that the results correspond to the sorted
            node numbering (self.nnum) (default).  If left unsorted, results
            correspond to the nodal equivalence array self.resultheader['neqv']

        Returns
        -------
        nnum : int np.ndarray
            Node numbers associated with the results.

        result : float np.ndarray
            Result is (nnod x numdof), or number of nodes by degrees of freedom

        """
        # Get info from result header
        endian = self.resultheader['endian']
        numdof = self.resultheader['numdof']
        nnod = self.resultheader['nnod']
        rpointers = self.resultheader['rpointers']

        # Check if result is available
        if rnum > self.nsets - 1:
            raise Exception(
                'There are only {:d} results in the result file.'.format(
                    self.nsets))

        # Read a result
        with open(self.filename, 'rb') as f:

            # Seek to result table and to get pointer to DOF results of result table
            f.seek((rpointers[rnum] + 12) * 4)  # item 11
            ptrNSLl = np.fromfile(f, endian + 'i', 1)[0]

            # Seek and read DOF results
            f.seek((rpointers[rnum] + ptrNSLl + 2) * 4)
            nitems = nnod * numdof
            result = np.fromfile(f, endian + 'd', nitems)

            f.close()

        # Reshape to number of degrees of freedom
        r = result.reshape((-1, numdof))

        # Reorder based on sorted indexing
        r = r.take(self.sidx, 0)

        # ansys writes the results in the nodal coordinate system.
        # Convert this to the global coordinate system  (in degrees)
        angles = self.geometry['nodes'][self.insolution, 3:].T
        theta_xy, theta_yz, theta_zx = angles

        if np.any(theta_xy):
            vtkInterface.common.AxisRotation(r, theta_xy, inplace=True, axis='z')

        if np.any(theta_yz):  # untested (!)
            vtkInterface.common.AxisRotation(r, theta_yz, inplace=True, axis='x')

        if np.any(theta_zx):  # untested (!)
            vtkInterface.common.AxisRotation(r, theta_zx, inplace=True, axis='y')

        # also include nodes in output
        return self.nnum, r

    def StoreGeometry(self):
        """ Stores the geometry from the result file """
        # read in the geometry from the result file
        with open(self.filename, 'rb') as f:

            # read geometry header
            f.seek(self.resultheader['ptrGEO']*4)
            table = ReadTable(f)
            geometry_header = ParseHeader(table, GEOMETRY_HEADER_KEYS)
            self.geometry_header = geometry_header

            # Node information
            nnod = geometry_header['nnod']
            nnum = np.empty(nnod, np.int32)
            nloc = np.empty((nnod, 6), np.float)
            _rstHelper.LoadNodes(self.filename, geometry_header['ptrLOC'],
                                 nnod, nloc, nnum)

            # Element Information
            nelm = geometry_header['nelm']
            maxety = geometry_header['maxety']

            # pointer to the element type index table
            f.seek((geometry_header['ptrETY'] + 2) * 4)
            e_type_table = np.fromfile(
                f, self.resultheader['endian'] + 'i', maxety)

            # store information for each element type
            # make these arrays large so you can reference a value via element
            # type numbering

            # number of nodes for this element type
            nodelm = np.empty(10000, np.int32)

            # number of nodes per element having nodal forces
            nodfor = np.empty(10000, np.int32)

            # number of nodes per element having nodal stresses
            nodstr = np.empty(10000, np.int32)
            etype_ID = np.empty(maxety, np.int32)
            ekey = []
            for i in range(maxety):
                f.seek((geometry_header['ptrETY'] + e_type_table[i] + 2) * 4)
                einfo = np.fromfile(f, self.resultheader['endian'] + 'i', 2)
                etype_ref = einfo[0]
                etype_ID[i] = einfo[1]
                ekey.append(einfo)

                f.seek((geometry_header['ptrETY'] + e_type_table[i] + 2 + 60) * 4)
                nodelm[etype_ref] = np.fromfile(
                    f, self.resultheader['endian'] + 'i', 1)

                f.seek((geometry_header['ptrETY'] + e_type_table[i] + 2 + 62) * 4)
                nodfor[etype_ref] = np.fromfile(
                    f, self.resultheader['endian'] + 'i', 1)

                f.seek((geometry_header['ptrETY'] + e_type_table[i] + 2 + 93) * 4)
                nodstr[etype_ref] = np.fromfile(
                    f, self.resultheader['endian'] + 'i', 1)

            # store element table data
            self.element_table = {'nodelm': nodelm,
                                  'nodfor': nodfor,
                                  'nodstr': nodstr}

            # get the element description table
            f.seek((geometry_header['ptrEID'] + 2) * 4)
            e_disp_table = np.empty(nelm, np.int32)
            e_disp_table[:] = np.fromfile(
                f, self.resultheader['endian'] + 'i8', nelm)

            # get pointer to start of element table and adjust element pointers
            ptr = geometry_header['ptrEID'] + e_disp_table[0]
            e_disp_table -= e_disp_table[0]

        # The following is stored for each element
        # mat     - material reference number
        # type    - element type number
        # real    - real constant reference number
        # secnum  - section number
        # esys    - element coordinate system
        # death   - death flat (1 live, 0 dead)
        # solidm  - solid model reference
        # shape   - coded shape key
        # elnum   - element number
        # baseeid - base element number
        # NODES   - node numbers defining the element

        # allocate memory for this (a maximum of 21 points per element)
        etype = np.empty(nelm, np.int32)

        elem = np.empty((nelm, 20), np.int32)
        elem[:] = -1

        # load elements
        _rstHelper.LoadElements(self.filename, ptr, nelm, e_disp_table, elem,
                                etype)
        enum = self.resultheader['eeqv']

        # store geometry dictionary
        self.geometry = {'nnum': nnum,
                         'nodes': nloc,
                         'etype': etype,
                         'elem': elem,
                         'enum': enum,
                         'ekey': np.asarray(ekey, ctypes.c_int64),
                         'e_rcon': np.ones_like(enum)}

        # store the reference array
        # Allow quadradic and null unallowed
        result = _parser.Parse(self.geometry, False, valid_types, True)
        cells, offset, cell_type, self.numref, _, _, _ = result

        # catch -1
        cells[cells == -1] = 0
        cells[cells >= nnum.size] = 0

        # remove nodes that are not in the solution (?)

        # -- or --

        # identify nodes that are actually in the solution
        self.insolution = np.in1d(self.geometry['nnum'], self.resultheader['neqv'])

        # Create vtk object if vtk installed
        if vtkloaded:
            element_type = np.zeros_like(etype)
            for key, typekey in ekey:
                element_type[etype == key] = typekey

            nodes = nloc[:, :3]
            self.quadgrid = vtkInterface.UnstructuredGrid(offset, cells,
                                                          cell_type, nodes)
            self.quadgrid.AddCellScalars(enum, 'ANSYS_elem_num')
            self.quadgrid.AddPointScalars(nnum, 'ANSYSnodenum')
            self.quadgrid.AddCellScalars(element_type, 'Element Type')
            self.grid = self.quadgrid.LinearGridCopy()

    def ElementSolutionHeader(self, rnum):
        """ Get element solution header information """
        # Get the header information from the header dictionary
        # endian = self.resultheader['endian']
        rpointers = self.resultheader['rpointers']
        nelm = self.resultheader['nelm']
        nodstr = self.element_table['nodstr']
        etype = self.geometry['etype']

        # Check if result is available
        if rnum > self.nsets - 1:
            raise Exception(
                'There are only {:d} results in the result file.'.format(
                    self.nsets))

        # Read a result
        with open(self.filename, 'rb') as f:
            f.seek((rpointers[rnum]) * 4)  # item 20
            solution_header = ParseHeader(ReadTable(f), SOLUTION_HEADER_KEYS)

            # key to extrapolate integration
            # = 0 - move
            # = 1 - extrapolate unless active
            # non-linear
            # = 2 - extrapolate always
            # print(rxtrap)
            if solution_header['rxtrap'] == 0:
                warnings.warn('Strains and stresses are being evaluated at ' +
                              'gauss points and not extrapolated')

            # 64-bit pointer to element solution
            if not solution_header['ptrESL']:
                f.close()
                raise Exception('No element solution in result set %d\n' % (rnum + 1) +
                                'Try running with "MXPAND,,,,YES"')

            # Seek to element result header
            element_rst_ptr = rpointers[rnum] + solution_header['ptrESL']
            f.seek(element_rst_ptr * 4)
            ele_ind_table = ReadTable(f, 'i8', nelm) + element_rst_ptr

            # Each element header contains 25 records for the individual
            # results.  Get the location of the nodal stress
            table_index = e_table.index('ptrENS')

            # boundary conditions
            # ptr = rpointers[rnum] + solution_header['ptrBC']
            # f.seek(ptr*4)
            # table = ReadTable(f, 'i')

        return table_index, ele_ind_table, nodstr, etype

    def NodalStress(self, rnum):
        """
        Equivalent ANSYS command: PRNSOL, S

        Retrives the component stresses for each node in the solution.

        The order of the results corresponds to the sorted node numbering.

        This algorithm, like ANSYS, computes the nodal stress by averaging the
        stress for each element at each node.  Due to the discontinunities
        across elements, stresses will vary based on the element they are
        evaluated from.

        Parameters
        ----------
        rnum : interger
            Result set to load using zero based indexing.

        Returns
        -------
        nodenum : numpy.ndarray
            Node numbers of the result.

        stress : numpy.ndarray
            Stresses at Sx Sy Sz Sxy Syz Sxz averaged at each corner node.
            For the corresponding node numbers, see
            where result is the result object.

        Notes
        -----
        Nodes without a stress value will be NAN.

        """
        # element header
        table_index, ele_ind_table, nodstr, etype = self.ElementSolutionHeader(rnum)

        if self.resultheader['rstsprs'] != 0:
            nitem = 6
        else:
            nitem = 11

        # certain element types do not output stress
        elemtype = self.grid.GetCellScalars('Element Type')
        validmask = np.in1d(elemtype, validENS).astype(np.int32)

        assert ele_ind_table.size == self.grid.GetNumberOfCells()
        data, ncount = _rstHelper.ReadNodalValues(self.filename,
                                                  table_index,
                                                  self.grid.celltypes,
                                                  ele_ind_table + 2,
                                                  self.grid.offset,
                                                  self.grid.cells,
                                                  nitem,
                                                  validmask.astype(np.int32),
                                                  self.grid.GetNumberOfPoints(),
                                                  nodstr,
                                                  etype)

        if nitem != 6:
            data = data[:, :6]

        nnum = self.grid.GetPointScalars('ANSYSnodenum')
        stress = data/ncount.reshape(-1, 1)

        return nnum, stress

    def ElementStress(self, rnum):
        """
        Equivalent ANSYS command: PRESOL, S

        Retrives the component stresses for each node in the solution.

        This algorithm, like ANSYS, computes the nodal stress by averaging the
        stress for each element at each node.  Due to the discontinuities
        across elements, stresses at nodes will vary based on the element
        they are evaluated from.

        Parameters
        ----------
        rnum : interger
            Result set to load using zero based indexing.

        Returns
        -------
        element_stress : list
            Stresses at each element for each node for Sx Sy Sz Sxy Syz Sxz.

        enum : np.ndarray
            ANSYS element numbers corresponding to each element.

        enode : list
            Node numbers corresponding to each element's stress results.  One
            list entry for each element

        """
        header = self.ElementSolutionHeader(rnum)
        table_index, ele_ind_table, nodstr, etype = header

        # certain element types do not output stress
        elemtype = self.grid.GetCellScalars('Element Type')
        validmask = np.in1d(elemtype, validENS).astype(np.int32)

        # ele_ind_table = ele_ind_table  # [validmask]
        etype = etype.astype(c_int64)

        # load in raw results
        nnode = nodstr[etype]
        nelemnode = nnode.sum()
        ver = float(self.resultheader['verstring'])

        # bitmask
        # bitmask = bin(int(hex(self.resultheader['rstsprs']), base=16)).lstrip('0b')
        # description maybe in resucm.inc

        if ver >= 14.5:
            if self.resultheader['rstsprs'] != 0:
                nitem = 6
            else:
                nitem = 11
            ele_data_arr = np.empty((nelemnode, nitem), np.float32)
            ele_data_arr[:] = np.nan
            _rstHelper.ReadElementStress(self.filename, table_index,
                                         ele_ind_table + 2,
                                         nodstr.astype(c_int64),
                                         etype,
                                         ele_data_arr,
                                         # self.edge_idx,
                                         nitem, validmask)
            if nitem != 6:
                ele_data_arr = ele_data_arr[:, :6]

        else:
            raise Exception('Not implemented for this version of ANSYS')
            # ele_data_arr = np.empty((nelemnode, 6), np.float64)
            # _rstHelper.ReadElementStressDouble(self.filename, table_index,
            #                                    ele_ind_table,
            #                                    nodstr.astype(c_int64),
            #                                    etype,
            #                                    ele_data_arr,
            #                                    self.edge_idx.astype(c_int64))

        splitind = np.cumsum(nnode)
        element_stress = np.split(ele_data_arr, splitind[:-1])

        # reorder list using sorted indices
        enum = self.grid.GetCellScalars('ANSYS_elem_num')
        sidx = np.argsort(enum)
        element_stress = [element_stress[i] for i in sidx]

        elem = self.geometry['elem']
        enode = []
        for i in sidx:
            enode.append(elem[i, :nnode[i]])

        # Get element numbers
        elemnum = self.geometry['enum'][self.sidx_elem]

        return element_stress, elemnum, enode

    def PrincipalNodalStress(self, rnum):
        """
        Computes the principal component stresses for each node in the
        solution.

        Parameters
        ----------
        rnum : interger
            Result set to load using zero based indexing.

        Returns
        -------
        nodenum : numpy.ndarray
            Node numbers of the result.

        pstress : numpy.ndarray
            Principal stresses, stress intensity, and equivalant stress.
            [sigma1, sigma2, sigma3, sint, seqv]

        Notes
        -----
        ANSYS equivalant of:
        PRNSOL, S, PRIN

        which returns:
        S1, S2, S3 principal stresses, SINT stress intensity, and SEQV
        equivalent stress.

        """
        # get component stress
        nodenum, stress = self.NodalStress(rnum)

        # compute principle stress
        if stress.dtype != np.float32:
            stress = stress.astype(np.float32)

        pstress, isnan = _rstHelper.ComputePrincipalStress(stress)
        pstress[isnan] = np.nan
        return nodenum, pstress

    def PlotPrincipalNodalStress(self, rnum, stype, colormap=None, flipscalars=None,
                                 cpos=None, screenshot=None, interactive=True):
        """
        Plot the principal stress at each node in the solution.

        Parameters
        ----------
        rnum : interger
            Result set using zero based indexing.

        stype : string
            Stress type to plot.  S1, S2, S3 principal stresses, SINT stress
            intensity, and SEQV equivalent stress.

            Stress type must be a string from the following list:

            ['S1', 'S2', 'S3', 'SINT', 'SEQV']

        colormap : str, optional
           Colormap string.  See available matplotlib colormaps.  Only applicable for
           when displaying scalars.  Defaults None (rainbow).  Requires matplotlib.

        flipscalars : bool, optional
            Flip direction of colormap.

        cpos : list, optional
            List of camera position, focal point, and view up.  Plot first, then
            output the camera position and save it.

        screenshot : str, optional
            Setting this to a filename will save a screenshot of the plot before
            closing the figure.  Default None.

        interactive : bool, optional
            Default True.  Setting this to False makes the plot generate in the
            background.  Useful when generating plots in a batch mode automatically.

        Returns
        -------
        cpos : list
            VTK camera position.

        stress : np.ndarray
            Array used to plot stress.

        """
        stress = self.PrincipleStressForPlotting(rnum, stype)

        # Generate plot
        stitle = 'Nodal Stress\n{:s}\n'.format(stype)
        cpos = self.PlotPointScalars(rnum, stress, stitle, colormap, flipscalars,
                                     screenshot, cpos, interactive)

        return cpos, stress

    def PlotPointScalars(self, rnum, scalars, stitle, colormap, flipscalars,
                         screenshot, cpos, interactive):
        """
        Plot a result

        Parameters
        ----------
        rnum : int
            Cumulative result number.

        scalars : np.ndarray
            Node scalars to plot.

        stitle : str
            Title of the scalar bar.

        colormap : str
            See matplotlib colormaps:
            matplotlib.org/examples/color/colormaps_reference.html

        flipscalars : bool
            Reverses the direction of the colormap.

        screenshot : str
            When a filename, saves screenshot to disk.

        cpos : list
            3x3 list describing the camera position.  Obtain it by getting the output
            of PlotPointScalars first.

        interactive : bool
            Allows user to interact with the plot when True.  Default True.

        grid : vtkInterface PolyData or UnstructuredGrid, optional
            Uses self.grid by default.  When specified, uses this grid instead.

        Returns
        -------
        cpos : list
            Camera position.
        """
        if hasattr(self, 'nsector'):
            grid = self.sector
            scalars = scalars[self.mas_ind]
            stitle += '\nMaster Sector\n'
        else:
            grid = self.grid

        if colormap is None and flipscalars is None:
            flipscalars = True

        # Plot off screen when not interactive
        plobj = vtkInterface.PlotClass(off_screen=not(interactive))
        plobj.AddMesh(grid, scalars=scalars, stitle=stitle, colormap=colormap,
                      flipscalars=flipscalars)

        # NAN/missing data are white
        plobj.mapper.GetLookupTable().SetNanColor(1, 1, 1, 1)

        if cpos:
            plobj.SetCameraPosition(cpos)

        plobj.AddText(self.TextResultTable(rnum), fontsize=20)
        if screenshot:
            cpos = plobj.Plot(autoclose=False, interactive=interactive)
            plobj.TakeScreenShot(screenshot)
            plobj.Close()
        else:
            cpos = plobj.Plot(interactive=interactive)

        return cpos

    def TextResultTable(self, rnum):
        """ Returns a text result table for plotting """
        ls_table = self.resultheader['ls_table']
        timevalue = self.GetTimeValues()[rnum]
        text = 'Cumulative Index: {:3d}\n'.format(ls_table[rnum, 2])
        text += 'Loadstep:         {:3d}\n'.format(ls_table[rnum, 0])
        text += 'Substep:          {:3d}\n'.format(ls_table[rnum, 1])
        text += 'Time Value:     {:10.4f}'.format(timevalue)

        return text

    def PrincipleStressForPlotting(self, rnum, stype):
        """
        returns stress used to plot

        """
        stress_types = ['S1', 'S2', 'S3', 'SINT', 'SEQV']
        if stype.upper() not in stress_types:
            raise Exception('Stress type not in \n' + str(stress_types))

        sidx = stress_types.index(stype)

        # don't display elements that can't store stress (!)
        # etype = self.grid.GetCellScalars('Element Type')
        # valid = (np.in1d(etype, validENS)).nonzero()[0]
        # grid = self.grid.ExtractSelectionCells(valid)
        # grid = self.grid

        # Populate with nodal stress at edge nodes
        # nodenum = grid.GetPointScalars('ANSYSnodenum')
        # stress_nnum, edge_stress = self.PrincipalNodalStress(rnum)
        # temp_arr = np.zeros((nodenum.max() + 1, 5))
        # temp_arr[stress_nnum] = edge_stress

        # find matching edge nodes
        # return temp_arr[nodenum, sidx]

        _, stress = self.PrincipalNodalStress(rnum)
        return stress[:, sidx]

    def PlotNodalStress(self, rnum, stype, colormap=None, flipscalars=None,
                        cpos=None, screenshot=None, interactive=True):
        """
        Plots the stresses at each node in the solution.

        The order of the results corresponds to the sorted node numbering.
        This algorthim, like ANSYS, computes the node stress by averaging the
        stress for each element at each node.  Due to the discontinunities
        across elements, stresses will vary based on the element they are
        evaluated from.

        Parameters
        ----------
        rnum : interger
            Result set using zero based indexing.

        stype : string
            Stress type from the following list: [Sx Sy Sz Sxy Syz Sxz]

        colormap : str, optional
           Colormap string.  See available matplotlib colormaps.

        flipscalars : bool, optional
            Flip direction of colormap.

        cpos : list, optional
            List of camera position, focal point, and view up.  Plot first, then
            output the camera position and save it.

        screenshot : str, optional
            Setting this to a filename will save a screenshot of the plot before
            closing the figure.

        interactive : bool, optional
            Default True.  Setting this to False makes the plot generate in the
            background.  Useful when generating plots in a batch mode automatically.

        Returns
        -------
        cpos : list
            3 x 3 vtk camera position.
        """

        stress_types = ['sx', 'sy', 'sz', 'sxy', 'syz', 'sxz', 'seqv']
        stype = stype.lower()
        if stype not in stress_types:
            raise Exception('Stress type not in: \n' + str(stress_types))

        sidx = stress_types.index(stype)

        # don't display elements that can't store stress
        # etype = self.grid.GetCellScalars('Element Type')
        # valid = (np.in1d(etype, validENS)).nonzero()[0]
        # grid = self.grid.ExtractSelectionCells(valid)
        # grid = self.grid  # bypassed for now

        # Populate with nodal stress at edge nodes
        # nodenum = self.grid.GetPointScalars('ANSYSnodenum')
        nnum, stress = self.NodalStress(rnum)
        stress = stress[:, sidx]

        stitle = 'Nodal Stress\n{:s}'.format(stype.capitalize())
        cpos = self.PlotPointScalars(rnum, stress, stitle, colormap, flipscalars,
                                     screenshot, cpos, interactive)

        return cpos

    def SaveAsVTK(self, filename, binary=True):
        """
        Appends all results to an unstructured grid and writes it to disk.

        The file extension will select the type of writer to use.  '.vtk' will
        use the legacy writer, while '.vtu' will select the VTK XML writer.

        Parameters
        ----------
        filename : str
            Filename of grid to be written.  The file extension will select the
            type of writer to use.  '.vtk' will use the legacy writer, while
            '.vtu' will select the VTK XML writer.

        binary : bool, optional
            Writes as a binary file by default.  Set to False to write ASCII

        Notes
        -----
        Binary files write much faster than ASCII, but binary files written on
        one system may not be readable on other systems.  Binary can only be
        selected for the legacy writer.
        """
        # Copy grid as to not write results to original object
        grid = self.grid.Copy()

        for i in range(self.nsets):
            # Nodal results
            val = self.NodalSolution(i)
            grid.AddPointScalars(val, 'NodalSolution{:03d}'.format(i))

            # Populate with nodal stress at edge nodes
            nodenum = self.grid.GetPointScalars('ANSYSnodenum')
            stress_nnum, edge_stress = self.NodalStress(i)
            temp_arr = np.zeros((nodenum.max() + 1, 6))
            temp_arr[stress_nnum] = edge_stress
            stress = temp_arr[nodenum]

            grid.AddPointScalars(stress, 'NodalStress{:03d}'.format(i))

        grid.Write(filename)

    def GetNodalResult(self, i, sort=None):
        warnings.warn('GetNodalResult is depreciated.  Use NodalSolution instead')
        return self.NodalSolution(i)

    def WriteTables(self, filename):
        """ Write binary tables to ASCII.  Assumes int32  """
        rawresult = open(self.filename, 'rb')
        with open(filename, 'w') as f:
            while True:
                try:
                    table = ReadTable(rawresult)
                    f.write('*** %d ***\n' % len(table))
                    for item in table:
                        f.write(str(item) + '\n')
                    f.write('\n\n')
                except:
                    break
        rawresult.close()


class CyclicResult(Result):
    """ adds cyclic functionality to the result reader in pyansys """

    def __init__(self, filename):
        """ Initializes object """
        super(CyclicResult, self).__init__(filename)

        # sanity check
        if self.resultheader['nSector'] == 1:
            raise Exception('Result is not a cyclic model')

        # Add cyclic properties
        self.AddCyclicProperties()

    def AddCyclicProperties(self, tol=1E-5):
        """
        Adds cyclic properties to result object

        Makes the assumption that all the cyclic nodes are within tol
        """
        if self.resultheader['csCord'] != 1:
            warnings.warn('Cyclic coordinate system %d' % self.resultheader['csCord'])
            # raise Exception('Can only read cyclic models with CSYS 1 (for now)')

        # idenfity the sector based on number of elements in master sector
        mask = self.quadgrid.GetCellScalars('ANSYS_elem_num') <= self.resultheader['csEls']
        self.master_cell_mask = mask
        self.sector = self.grid.ExtractSelectionCells(np.nonzero(mask)[0])

        # Store the indices of the master and duplicate nodes
        mask = self.nnum <= self.resultheader['csNds']
        self.master_node_mask = mask
        nnod_sector = mask.sum()
        self.mas_ind = np.arange(nnod_sector)
        self.dup_ind = np.arange(nnod_sector, self.nnum.size)

        # store cyclic node numbers
        self.cyc_nnum = self.nnum[self.mas_ind]

        # get cyclic nodes relative to vtk indexing
        # self.cyc_ind = np.in1d(self.nnum, cyc_nodes).nonzero()[0]

        # create full rotor
        self.nsector = self.resultheader['nSector']

        # Create rotor of sectors
        if vtkloaded:
            self.rotor = []
            rang = 360.0 / self.nsector
            for i in range(self.nsector):

                # Transform mesh
                sector = self.sector.Copy()
                sector.RotateZ(rang * i)
                self.rotor.append(sector)

    def NodalSolution(self, rnum, phase=0, full_rotor=False, as_complex=False):
        """
        Returns the DOF solution for each node in the global cartesian coordinate system.

        Parameters
        ----------
        rnum : interger
            Cumulative result number.  Zero based indexing.

        phase : float, optional
            Phase to rotate sector result.

        full_rotor : bool, optional
            Expands the single sector solution for the full rotor.  Sectors are rotated
            counter-clockwise about the axis of rotation.  Default False.

        as_complex : bool, optional
            Returns result as a complex number, otherwise as the real part rotated by
            phase.  Default False.

        Returns
        -------
        nnum : np.ndarray
            Node numbers of master sector.

        result : np.ndarray
            Result is (nnod x numdof), nnod is the number of nodes in a sector
            and numdof is the number of degrees of freedom.  When full_rotor is True
            the array will be (nSector x nnod x numdof).

        Notes
        -----
        Node numbers correspond to self.cyc_nnum, where self is this result
        object

        """
        # get the nodal result
        nnum, r = super(CyclicResult, self).NodalSolution(rnum)
        nnum = nnum[self.mas_ind]  # only concerned with the master sector

        # master and duplicate sector solutions
        u_mas = r[self.mas_ind]
        u_dup = r[self.dup_ind]

        if as_complex:
            sector_r = u_mas + u_dup*1j
        else:  # convert to real
            sector_r = u_mas*np.cos(phase) - u_dup*np.sin(phase)

        # just return single sector
        if not full_rotor:
            return nnum, sector_r

        # otherwise rotate results (CYC, 1 only)
        sectors = []
        angles = np.linspace(0, 2*np.pi, self.nsector + 1)[:-1]
        for angle in angles:
            sectors.append(AxisRotation(sector_r, angle, deg=False, axis='z'))

        return nnum, np.asarray(sectors)

    def PlotRotor(self):
        vtkInterface.PlotGrids(self.rotor, range(len(self.rotor)))

    # def PlotNodalSolution(self, **kwargs):
        # __doc__ += .__doc__
        
        

def GetResultInfo(filename):
    """
    Returns pointers used to access results from an ANSYS result file.

    Parameters
    ----------
    filename : string
        Filename of result file.

    Returns
    -------
    resultheader : dictionary
        Result header

    """
    standard_header = ReadStandardHeader(filename)
    endian = standard_header['endian']

    with open(filename, 'rb') as f:
        # Read .RST FILE HEADER
        f.seek(103 * 4)
        header = ParseHeader(ReadTable(f), RESULT_HEADER_KEYS)
        resultheader = merge_two_dicts(header, standard_header)

        # Read nodal equivalence table
        f.seek(resultheader['ptrNOD']*4)
        resultheader['neqv'] = ReadTable(f)

        # Read nodal equivalence table
        f.seek(resultheader['ptrELM']*4)
        resultheader['eeqv'] = ReadTable(f)

        # Read table of pointers to locations of results
        nsets = resultheader['nsets']
        f.seek((resultheader['ptrDSI'] + 2) * 4)  # Start of pointer, then empty, then data

        # Data sets index table. This record contains the record pointers
        # for the beginning of each data set. The first resmax records are
        # the first 32 bits of the index, the second resmax records are
        # the second 32 bits f.seek((ptrDSIl + 0) * 4)
        raw0 = f.read(resultheader['resmax']*4)
        raw1 = f.read(resultheader['resmax']*4)
        subraw0 = [raw0[i*4:(i+1)*4] for i in range(nsets)]
        subraw1 = [raw1[i*4:(i+1)*4] for i in range(nsets)]
        longraw = [subraw0[i] + subraw1[i] for i in range(nsets)]
        longraw = b''.join(longraw)
        rpointers = np.frombuffer(longraw, 'i8')

        assert np.all(rpointers >= 0), 'Data set index table has negative pointers'
        resultheader['rpointers'] = rpointers

        # load harmonic index of each result
        if resultheader['ptrCYC']:
            f.seek((resultheader['ptrCYC'] + 2) * 4)
            resultheader['hindex'] = np.fromfile(f, endian + 'i',
                                                 count=resultheader['nsets'])

        # load step table with columns:
        # [loadstep, substep, and cumulative]
        f.seek((resultheader['ptrLSP'] + 2) * 4)  # Start of pointer, then empty, then data
        table = np.fromfile(f, endian + 'i', count=resultheader['nsets'] * 3)
        resultheader['ls_table'] = table.reshape((-1, 3))

    return resultheader


def ReadTable(f, dtype='i', nread=None, skip=False, get_nread=True):
    """ read fortran style table """
    if get_nread:
        n = np.fromfile(f, 'i', 1)
        if not n:
            raise Exception('end of file')

        tablesize = n[0]
        f.seek(4, 1)  # skip padding

    # override
    if nread:
        tablesize = nread

    if skip:
        f.seek((tablesize + 1)*4, 1)
        return
    else:
        if dtype == 'double':
            tablesize //= 2
        table = np.fromfile(f, dtype, tablesize)
    f.seek(4, 1)  # skip padding
    return table


def TwoIntsToLong(intl, inth):
    """ Interpert two ints as one long """
    longint = struct.pack(">I", inth) + struct.pack(">I", intl)
    return struct.unpack('>q', longint)[0]


def Pol2Cart(rho, phi):
    """ Convert cylindrical to cartesian """
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)

    return x, y


def ParseHeader(table, keys):
    """ parses a header from a table """
    header = {}
    for i, key in enumerate(keys):
        header[key] = table[i]

    for key in keys:
        if 'ptr' in key and key[-1] == 'h':
            basekey = key[:-1]
            intl = header[basekey + 'l']
            inth = header[basekey + 'h']
            header[basekey] = TwoIntsToLong(intl, inth)

    return header


def ReadStandardHeader(filename):
    """ Reads standard header """
    # f = open(filename, 'rb')
    with open(filename, 'rb') as f:

        endian = '<'
        if np.fromfile(f, dtype='<i', count=1) != 100:

            # Check if big enos
            f.seek(0)
            if np.fromfile(f, dtype='>i', count=1) == 100:
                endian = '>'

            # Otherwise, it's probably not a result file
            else:
                raise Exception('Unable to determine endian type.  ' +
                                'Possibly not an ANSYS binary file')

        f.seek(0)

        header = {}
        header['endian'] = endian
        header['file number'] = ReadTable(f, nread=1, get_nread=False)[0]
        header['file format'] = ReadTable(f, nread=1, get_nread=False)[0]
        int_time = str(ReadTable(f, nread=1, get_nread=False)[0])
        header['time'] = ':'.join([int_time[0:2], int_time[2:4], int_time[4:]])
        int_date = str(ReadTable(f, nread=1, get_nread=False)[0])
        if int_date == '-1':
            header['date'] = ''
        else:
            header['date'] = '/'.join([int_date[0:4], int_date[4:6], int_date[6:]])

        unit_types = {0: 'User Defined',
                      1: 'SI',
                      2: 'CSG',
                      3: 'U.S. Customary units (feet)',
                      4: 'U.S. Customary units (inches)',
                      5: 'MKS',
                      6: 'MPA',
                      7: 'uMKS'}
        header['units'] = unit_types[ReadTable(f, nread=1, get_nread=False)[0]]

        f.seek(11 * 4)
        version = ReadStringFromBinary(f, 1).strip()

        header['verstring'] = version
        header['mainver'] = int(version[:2])
        header['subver'] = int(version[-1])

        # there's something hidden at 12
        f.seek(4, 1)

        # f.seek(13 * 4)
        header['machine'] = ReadStringFromBinary(f, 3).strip()
        header['jobname'] = ReadStringFromBinary(f, 2).strip()
        header['product'] = ReadStringFromBinary(f, 2).strip()
        header['special'] = ReadStringFromBinary(f, 1).strip()
        header['username'] = ReadStringFromBinary(f, 3).strip()

        # Items 23-25 The machine identifier in integer form (three four-character strings)
        # this contains license information
        header['machine_identifier'] = ReadStringFromBinary(f, 3).strip()

        # Item 26 The system record size
        header['system record size'] = ReadTable(f, nread=1, get_nread=False)[0]

        # Item 27 The maximum file length
        # header['file length'] = ReadTable(f, nread=1, get_nread=False)[0]

        # Item 28 The maximum record number
        # header['the maximum record number'] = ReadTable(f, nread=1, get_nread=False)[0]

        # Items 31-38 The Jobname (eight four-character strings)
        f.seek(32*4)
        header['jobname2'] = ReadStringFromBinary(f, 8).strip()

        # Items 41-60 The main analysis title in integer form (20 four-character strings)
        f.seek(42*4)
        header['title'] = ReadStringFromBinary(f, 20).strip()

        # Items 61-80 The first subtitle in integer form (20 four-character strings)
        header['subtitle'] = ReadStringFromBinary(f, 20).strip()

        # Item 95 The split point of the file (0 means the file will not split)
        f.seek(96*4)
        header['split point'] = ReadTable(f, nread=1, get_nread=False)[0]

        # Items 97-98 LONGINT of the maximum file length
        ints = ReadTable(f, nread=2, get_nread=False)
        header['file length'] = TwoIntsToLong(ints[0], ints[1])

    return header


def ReadStringFromBinary(f, n):
    """ Read n 4 character binary strings from a file opend in binary mode """
    string = b''
    for i in range(n):
        string += f.read(4)[::-1]

    try:
        return string.decode('utf')
    except:
        return string
