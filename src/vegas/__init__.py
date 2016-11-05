""" Introduction
--------------------
This package provides tools for estimating multidimensional
integrals numerically using an enhanced version of
the adaptive Monte Carlo |vegas| algorithm (G. P. Lepage,
J. Comput. Phys. 27(1978) 192).

A |vegas| code generally involves two objects, one representing
the integrand and the other representing an integration
operator for a particular multidimensional volume. A typical
code sequence for a D-dimensional integral has the structure::

    # create the integrand
    def f(x):
        ... compute the integrand at point x[d] d=0,1...D-1
        ...

    # create an integrator for volume with
    # xl0 <= x[0] <= xu0, xl1 <= x[1] <= xu1 ...
    integration_region = [[xl0, xu0], [xl1, xu1], ...]
    integrator = vegas.Integrator(integration_region)

    # do the integral and print out the result
    result = integrator(f, nitn=10, neval=10000)
    print(result)

The algorithm iteratively adapts to the integrand over
``nitn`` iterations, each of which uses at most ``neval``
integrand samples to generate a Monte Carlo estimate of
the integral. The final result is the weighted average
of the results from all iterations. Increase ``neval``
to increase the precision of the result. Typically
``nitn`` is between 10 and 20. ``neval`` can be
1000s to millions, or more, depending upon
the integrand and the precision desired.

The integrator remembers how it adapted to ``f(x)``
and uses this information as its starting point if it is reapplied
to ``f(x)`` or applied to some other function ``g(x)``.
An integrator's state can be archived for future applications
using Python's :mod:`pickle` module.

See the extensive Tutorial in the first section of the |vegas| documentation.
"""

# Created by G. Peter Lepage (Cornell University) in 12/2013.
# Copyright (c) 2013-14 G. Peter Lepage.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version (see <http://www.gnu.org/licenses/>).
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from ._vegas import RAvg, RAvgArray, RAvgDict
from ._vegas import AdaptiveMap, Integrator, BatchIntegrand
from ._vegas import reporter, batchintegrand
from ._vegas import MPIintegrand
from ._version import version as __version__
# legacy names:
from ._vegas import vecintegrand, VecIntegrand

import gvar as _gvar
import numpy

class PDFIntegrator(Integrator):
    """ :mod:`vegas` integrator for PDF expectation values.

    ``PDFIntegrator(g)`` is a :mod:`vegas` integrator that evaluates
    expectation values for the multi-dimensional Gaussian distribution
    specified by with ``g``, which is a |GVar| or an array of |GVar|\s or a
    dictionary whose values are |GVar|\s or arrays of |GVar|\s.

    ``PDFIntegrator`` integrates over the entire parameter space of the
    distribution but reexpresses integrals in terms of variables
    that diagonalize ``g``'s covariance matrix and are centered at
    its mean value. This greatly facilitates integration over these
    variables using the :mod:`vegas` module, making integrals over
    10s or more of parameters feasible.

    A simple illustration of ``PDFIntegrator`` is given by the following
    code::

        import vegas
        import gvar as gv

        # multi-dimensional Gaussian distribution
        g = gv.BufferDict()
        g['a'] = gv.gvar([0., 1.], [[1., 0.9], [0.9, 1.]])
        g['b'] = gv.gvar('1(1)')

        # integrator for expectation values in distribution g
        g_expval = vegas.PDFIntegrator(g)

        # adapt integrator to PDF
        warmup = g_expval(neval=1000, nitn=5)

        # want expectation value of [fp, fp**2]
        def f_f2(p):
            fp = p['a'][0] * p['a'][1] + p['b']
            return [fp, fp ** 2]

        # results = <f_f2> in distribution g
        results = g_expval(f_f2, neval=1000, nitn=5, adapt=False)
        print (results.summary())
        print ('results =', results, '\\n')

        # mean and standard deviation of f(p)'s distribution
        fmean = results[0]
        fsdev = gv.sqrt(results[1] - results[0] ** 2)
        print ('f.mean =', fmean, '   f.sdev =', fsdev)
        print ("Gaussian approx'n for f(g) =", f_f2(g)[0])

    where the ``warmup`` calls to the integrator are used to adapt it to
    the PDF, and the final results are in ``results``. Here ``neval`` is
    the (approximate) number of function calls per iteration of the
    :mod:`vegas` algorithm and ``nitn`` is the number of iterations. We
    use the integrator to calculated  the expectation value of ``fp`` and
    ``fp**2``, so we can compute the standard deviation for the
    distribution of ``fp``\s. The output from this code shows that the
    Gaussian approximation (1.0(1.4)) for the mean and standard deviation
    of the ``fp`` distribution is not particularly accurate here
    (correct value is 1.9(2.0)), because of the large uncertainties in
    ``g``::

        itn   integral        average         chi2/dof        Q
        -------------------------------------------------------
          1   0.995(12)       0.995(12)           0.00     1.00
          2   1.014(11)       1.0043(79)          1.39     0.24
          3   1.005(11)       1.0046(65)          1.75     0.10
          4   0.977(13)       0.9978(58)          2.40     0.01
          5   1.004(12)       0.9990(52)          1.94     0.03

        results = [1.904(17) 7.57(17)]

        f.mean = 1.904(17)    f.sdev = 1.986(31)
        Gaussian approx'n for f(g) = 1.0(1.4)

    In general functions being integrated can return a number, or an array of
    numbers, or a dictionary whose values are numbers or arrays of numbers.
    This allows multiple expectation values to be evaluated simultaneously.

    See the documentation with the :mod:`vegas` module for more details on its
    use, and on the attributes and methods associated with integrators.
    The example above sets ``adapt=False`` when  computing final results. This
    gives more reliable error estimates  when ``neval`` is small. Note
    that ``neval`` may need to be much larger (tens or hundreds of
    thousands) for more difficult high-dimension integrals.

    Args:
        g : |GVar|, array of |GVar|\s, or dictionary whose values
            are |GVar|\s or arrays of |GVar|\s that specifies the
            multi-dimensional Gaussian distribution used to construct
            the probability density function.

        limit (positive float): Limits the integrations to a finite
            region of size ``limit`` times the standard deviation on
            either side of the mean. This can be useful if the
            functions being integrated misbehave for large parameter
            values (e.g., ``numpy.exp`` overflows for a large range of
            arguments). Default is ``1e15``.

        scale (positive float): The integration variables are
            rescaled to emphasize parameter values of order
            ``scale`` times the standard deviation. The rescaling
            does not change the value of the integral but it
            can reduce uncertainties in the :mod:`vegas` estimate.
            Default is ``1.0``.

        svdcut (non-negative float or None): If not ``None``, replace
            covariance matrix of ``g`` with a new matrix whose
            small eigenvalues are modified: eigenvalues smaller than
            ``svdcut`` times the maximum eigenvalue ``eig_max`` are
            replaced by ``svdcut*eig_max``. This can ameliorate
            problems caused by roundoff errors when inverting the
            covariance matrix. It increases the uncertainty associated
            with the modified eigenvalues and so is conservative.
            Setting ``svdcut=None`` or ``svdcut=0`` leaves the
            covariance matrix unchanged. Default is ``1e-15``.
    """
    def __init__(self, g, limit=1e15, scale=1., svdcut=1e-15):
        if isinstance(g, _gvar.PDF):
            self.pdf = g
        else:
            self.pdf = _gvar.PDF(g, svdcut=svdcut)
        self.limit = abs(limit)
        self.scale = scale
        # if _have_scipy and limit <= 8.:
        #     limit = scipy.special.ndtr(self.limit)
        #     super(PDFIntegrator, self).__init__(self.pdf.size * [(1. - limit, limit)])
        #     self._expval = self._expval_ndtri
        # else:
        integ_map = self._make_map(self.limit / self.scale)
        super(PDFIntegrator, self).__init__(
            self.pdf.size * [integ_map]
            )
        # limit = numpy.arctan(self.limit / self.scale)
        # super(PDFIntegrator, self).__init__(
        #     self.pdf.size * [(-limit, limit)]
        #     )
        self._expval = self._expval_tan
        self.mpi_rank = 0    # in case mpi is used

    def _make_map(self, limit):
        """ Make vegas grid that is adapted to the pdf. """
        ny = 2000
        y = numpy.random.uniform(0., 1., (ny,1))
        limit = numpy.arctan(limit)
        m = AdaptiveMap([[-limit, limit]], ninc=100)
        theta = numpy.empty(y.shape, float)
        jac = numpy.empty(y.shape[0], float)
        for itn in range(10):
            m.map(y, theta, jac)
            tan_theta = numpy.tan(theta[:, 0])
            x = self.scale * tan_theta
            fx = (tan_theta ** 2 + 1) * numpy.exp(-(x ** 2) / 2.)
            m.add_training_data(y, (jac * fx) ** 2)
            m.adapt(alpha=1.5)
        return numpy.array(m.grid[0])

    def __call__(self, f=None, nopdf=False, mpi=False, _fstd=None, **kargs):
        """ Estimate expectation value of function ``f(p)``.

        Uses module :mod:`vegas` to estimate the integral of
        ``f(p)`` multiplied by the probability density function
        associated with ``g`` (i.e., ``pdf(p)``). The probability
        density function is omitted if ``nopdf=True`` (default
        setting is ``False``). Setting ``mpi=True`` configures vegas
        for multi-processor running using MPI.

        Args:
            f (function): Function ``f(p)`` to integrate. Integral is
                the expectation value of the function with respect
                to the distribution. The function can return a number,
                an array of numbers, or a dictionary whose values are
                numbers or arrays of numbers.

            nopdf (bool): If ``True`` drop the probability density function
                from the integrand (so no longer an expectation value).
                This is useful if one wants to use the optimized
                integrator for something other than a standard
                expectation value. Default is ``False``.

            mpi (bool): If ``True`` configure for use with multiple processors
                and MPI. This option requires module :mod:`mpi4py`. A
                script ``xxx.py`` using an MPI integrator is run
                with ``mpirun``: e.g., ::

                    mpirun -np 4 -output-filename xxx.out python xxx.py

                runs on 4 processors. Setting ``mpi=False`` (default) does
                not support multiple processors. The MPI processor
                rank can be obtained from the ``mpi_rank``
                attribute of the integrator.

        All other keyword arguments are passed on to a :mod:`vegas`
        integrator; see the :mod:`vegas` documentation for further information.
        """
        # N.B. If _fstd is specified then it substitutes for fstd()
        # and the results are returned without modification. This
        # is use by lsqfit.BayesIntegrator.
        if nopdf and f is None and _fstd is None:
            raise ValueError('nopdf==True and f is None --- no integrand')
        if _fstd is None:
            self._buffer = None
            def fstd(p):
                """ convert output to an array """
                fp = [] if f is None else f(p)
                if self._buffer is None:
                    # setup --- only on first call
                    self._is_dict = hasattr(fp, 'keys')
                    if self._is_dict:
                        self._fp = _gvar.BufferDict(fp)
                        self._is_bdict = isinstance(fp, _gvar.BufferDict)
                        bufsize = self._fp.buf.size
                    else:
                        self._is_bdict = False
                        self._fp = numpy.asarray(fp)
                        bufsize = self._fp.size
                    if nopdf:
                        self._buffer = numpy.empty(bufsize, float)
                    else:
                        self._buffer = numpy.empty(bufsize + 1, float)
                        self._buffer[0] = 1.
                if self._is_bdict:
                    self._buffer[(0 if nopdf else 1):] = fp.buf
                elif self._is_dict:
                    self._buffer[(0 if nopdf else 1):] = _gvar.BufferDict(fp).buf
                else:
                    self._buffer[(0 if nopdf else 1):] = numpy.asarray(fp).flat[:]
                return self._buffer
        else:
            fstd = _fstd
        integrand = self._expval(fstd, nopdf)
        if mpi:
            integrand = MPIintegrand(integrand)
            self.mpi_rank = integrand.rank
        else:
            integrand = batchintegrand(integrand)
        results = super(PDFIntegrator, self).__call__(integrand, **kargs)
        if _fstd is not None:
            return results
        else:
            # return output to original format:
            self.norm = None if nopdf else results[0]
            if self._fp.shape is None:
                return _RAvgDictWrapper(self._fp, results, nopdf)
            elif self._fp.shape != ():
                return _RAvgArrayWrapper(self._fp.shape, results, nopdf)
            else:
                return _RAvgWrapper(results, nopdf)

    # def _expval_ndtri(self, f, nopdf):
    #     """ Return integrand using ndtr mapping. """
    #     def ff(theta, nopdf=nopdf):
    #         x = scipy.special.ndtri(theta)
    #         dp = self.pdf.x2dpflat(x) # x.dot(self.vec_sig)
    #         if nopdf:
    #             # must remove built in pdf
    #             pdf = (
    #                 numpy.sqrt(2 * numpy.pi) * numpy.exp((x ** 2) / 2.)
    #                 * self.pdf.pjac[None,:]
    #                 )
    #         else:
    #             pdf = numpy.ones(numpy.shape(x), float)
    #         ans = []
    #         parg = None
    #         for dpi, pdfi in zip(dp, pdf):
    #             p = self.pdf.meanflat + dpi
    #             if parg is None:
    #                 if self.pdf.shape is None:
    #                     if self.pdf.extend:
    #                         parg = ExtendedDict(self.pdf.g, buf=p)
    #                     else:
    #                         parg = BufferDict(self.pdf.g, buf=p)
    #                 else:
    #                     parg = p.reshape(self.pdf.shape)
    #             else:
    #                 if parg.shape is None:
    #                     parg.buf = p
    #                 else:
    #                     parg.flat[:] = p
    #             ans.append(f(parg) * numpy.prod(pdfi))
    #         return numpy.array(ans)
    #     return ff

    def _expval_tan(self, f, nopdf):
        """ Return integrand using the tan mapping. """
        def ff(theta, nopdf=nopdf):
            tan_theta = numpy.tan(theta)
            x = self.scale * tan_theta
            jac = self.scale * (tan_theta ** 2 + 1.)
            if nopdf:
                pdf = jac * self.pdf.pjac[None, :]
            else:
                pdf = jac * numpy.exp(-(x ** 2) / 2.) / numpy.sqrt(2 * numpy.pi)
            dp = self.pdf.x2dpflat(x) # .dot(self.vec_sig))
            ans = []
            parg = None
            for dpi, pdfi in zip(dp, pdf):
                p = self.pdf.meanflat + dpi
                if parg is None:
                    if self.pdf.shape is None:
                        if self.pdf.extend:
                            parg = _gvar.ExtendedDict(self.pdf.g, buf=p)
                        else:
                            parg = _gvar.BufferDict(self.pdf.g, buf=p)
                    else:
                        parg = p.reshape(self.pdf.shape)
                else:
                    if parg.shape is None:
                        parg.buf = p
                    else:
                        parg.flat[:] = p
                ans.append(f(parg) * numpy.prod(pdfi))
            return numpy.array(ans)
        return ff

class _RAvgWrapper(_gvar.GVar):
    """ Wrapper for BayesIntegrator GVar result. """
    def __init__(self, results, nopdf=False):
        self.results = results
        ans = results[0] if nopdf else (results[1] / results[0])
        super(_RAvgWrapper, self).__init__(*ans.internaldata)

    def _dof(self):
        return self.results.dof

    dof = property(
        _dof,
        None,
        None,
        "Number of degrees of freedom in weighted average."
        )

    def _Q(self):
        return self.results.Q

    Q = property(
        _Q,
        None,
        None,
        "*Q* or *p-value* of weighted average's *chi**2*.",
        )

    def summary(self, weighted=None):
        return self.results.summary(weighted=weighted)

class _RAvgDictWrapper(_gvar.BufferDict):
    """ Wrapper for BayesIntegrator dictionary result """
    def __init__(self, fp, results, nopdf=False):
        super(_RAvgDictWrapper, self).__init__(fp)
        self.results = results
        self.buf = results if nopdf else (results[1:] / results[0])

    def _dof(self):
        return self.results.dof

    dof = property(
        _dof,
        None,
        None,
        "Number of degrees of freedom in weighted average."
        )

    def _Q(self):
        return self.results.Q

    Q = property(
        _Q,
        None,
        None,
        "*Q* or *p-value* of weighted average's *chi**2*.",
        )

    def summary(self, weighted=None):
        return self.results.summary(weighted=weighted)

class _RAvgArrayWrapper(numpy.ndarray):
    """ Wrapper for BayesIntegrator array result. """
    def __new__(
        subtype, shape, results, nopdf=False,
        dtype=object, buffer=None, offset=0, strides=None, order=None
        ):
        obj = numpy.ndarray.__new__(
            subtype, shape=shape, dtype=object, buffer=buffer, offset=offset,
            strides=strides, order=order
            )
        if buffer is None:
            obj.flat = numpy.array(obj.size * [_gvar.gvar(0,0)])
        obj.results = results
        obj.flat = results if nopdf else (results[1:] / results[0])
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.results = getattr(obj, 'results', None)

    def _dof(self):
        return self.results.dof

    dof = property(
        _dof,
        None,
        None,
        "Number of degrees of freedom in weighted average."
        )

    def _Q(self):
        return self.results.Q

    Q = property(
        _Q,
        None,
        None,
        "*Q* or *p-value* of weighted average's *chi**2*.",
        )

    def summary(self, weighted=None):
        return self.results.summary(weighted=weighted)
