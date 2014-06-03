# -*- coding: utf-8 -*-
"""
Created on Fri May 30 16:22:29 2014

Author: Josef Perktold
License: BSD-3

"""

from statsmodels.compat.python import StringIO

import numpy as np
from numpy.testing import assert_allclose, assert_equal
from nose import SkipTest

import pandas as pd
import patsy

from statsmodels.discrete.discrete_model import Poisson
import statsmodels.base._constraints as monkey

from .results import results_poisson_constrained as results

ss='''\
agecat	smokes	deaths	pyears
1	1	32	52407
2	1	104	43248
3	1	206	28612
4	1	186	12663
5	1	102	5317
1	0	2	18790
2	0	12	10673
3	0	28	5710
4	0	28	2585
5	0	31	1462'''

data = pd.read_csv(StringIO(ss), delimiter='\t')
data['logpyears'] = np.log(data['pyears'])


class CheckPoissonConstrainedMixin(object):

    def test_basic(self):
        res1 = self.res1
        res2 = self.res2
        assert_allclose(res1[0], res2.params[self.idx], rtol=1e-6)
        assert_allclose(res1[1], res2.bse[self.idx], rtol=1e-6)

    def test_basic_method(self):
        if hasattr(self, 'res1m'):
            res1 = (self.res1m if not hasattr(self.res1m, '_results')
                               else self.res1m._results)
            res2 = self.res2
            assert_allclose(res1.params, res2.params[self.idx], rtol=1e-6)
            assert_allclose(res1.bse, res2.bse[self.idx], rtol=1e-6)

            tvalues = res2.params_table[self.idx, 2]
            assert_allclose(res1.tvalues, tvalues, rtol=1e-6)
            pvalues = res2.params_table[self.idx, 3]
            # note most pvalues are very small
            # examples so far agree at 8 or more decimal, but rtol is stricter
            assert_allclose(res1.pvalues, pvalues, rtol=5e-5)

            ci_low = res2.params_table[self.idx, 4]
            ci_upp = res2.params_table[self.idx, 5]
            ci = np.column_stack((ci_low, ci_upp))
            # note most pvalues are very small
            # examples so far agree at 8 or more decimal, but rtol is stricter
            assert_allclose(res1.conf_int(), ci, rtol=5e-5)

            #other
            assert_allclose(res1.llf, res2.ll, rtol=1e-6)
            assert_equal(res1.df_model, res2.df_m)
            # Stata doesn't have df_resid
            df_r = res2.N - res2.df_m - 1
            assert_equal(res1.df_resid, df_r)
        else:
            raise SkipTest("not available yet")

    def test_other(self):
        # some results may not be valid or available for all models
        if hasattr(self, 'res1m'):
            res1 = self.res1m
            res2 = self.res2

            if hasattr(res2, 'll_0'):
                assert_allclose(res1.llnull, res2.ll_0, rtol=1e-6)
            else:
                import warnings
                message = 'test: ll_0 not available, llnull=%6.4F' % res1.llnull
                warnings.warn(message)

        else:
            raise SkipTest("not available yet")


class TestPoissonConstrained1a(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_noexposure_constraint
        cls.idx = [7, 3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ logpyears + smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data)
        #res1a = mod1a.fit()
        # get start_params, example fails to converge on one py TravisCI
        k_vars = len(mod.exog_names)
        start_params = np.zeros(k_vars)
        start_params[0] = np.log(mod.endog.mean())
        # if we need it, this is desired params
        p = np.array([-3.93478643,  1.37276214,  2.33077032,  2.71338891,
                      2.71338891, 0.57966535,  0.97254074])

        constr = 'C(agecat)[T.4] = C(agecat)[T.5]'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = mod.fit_constrained_(lc.coefs, lc.constants,
                                        start_params=start_params,
                                        fit_kwds={'method':'bfgs'})
        # TODO: Newton fails

        # test method of Poisson, not monkey patched
        cls.res1m = mod.fit_constrained(constr, start_params=start_params,
                                        method='bfgs')


class TestPoissonConstrained1b(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_exposure_constraint
        #cls.idx = [3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical
        cls.idx = [6, 2, 3, 4, 5, 0]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data,
                                   exposure=data['pyears'].values)
                                   #offset=np.log(data['pyears'].values))
        #res1a = mod1a.fit()
        constr = 'C(agecat)[T.4] = C(agecat)[T.5]'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = mod.fit_constrained_(lc.coefs, lc.constants,
                                       fit_kwds={'method':'newton'})
        cls.constraints = lc
        # TODO: bfgs fails
        # test method of Poisson, not monkey patched
        cls.res1m = mod.fit_constrained(constr, method='newton')


class TestPoissonConstrained1c(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_exposure_constraint
        #cls.idx = [3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical
        cls.idx = [6, 2, 3, 4, 5, 0]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data,
                                   offset=np.log(data['pyears'].values))
        #res1a = mod1a.fit()
        constr = 'C(agecat)[T.4] = C(agecat)[T.5]'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = mod.fit_constrained_(lc.coefs, lc.constants,
                                       fit_kwds={'method':'newton'})
        cls.constraints = lc
        # TODO: bfgs fails

        # test method of Poisson, not monkey patched
        cls.res1m = mod.fit_constrained(constr, method='newton')


class TestPoissonNoConstrained(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_exposure_noconstraint
        cls.idx = [6, 2, 3, 4, 5, 0] # 1 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data,
                                   #exposure=data['pyears'].values)
                                   offset=np.log(data['pyears'].values))
        res1 = mod.fit()._results
        cls.res1 = (res1.params, res1.bse)
        cls.res1m = res1


class TestPoissonConstrained2a(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_noexposure_constraint2
        cls.idx = [7, 3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ logpyears + smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data)

        # get start_params, example fails to converge on one py TravisCI
        k_vars = len(mod.exog_names)
        start_params = np.zeros(k_vars)
        start_params[0] = np.log(mod.endog.mean())
        # if we need it, this is desired params
        p = np.array([-9.43762015,  1.52762442,  2.74155711,  3.58730007,
                      4.08730007,  1.15987869,  0.12111539])

        constr = 'C(agecat)[T.5] - C(agecat)[T.4] = 0.5'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = mod.fit_constrained_(lc.coefs, lc.constants,
                                        start_params=start_params,
                                        fit_kwds={'method':'bfgs'})
        # TODO: Newton fails

        # test method of Poisson, not monkey patched
        cls.res1m = mod.fit_constrained(constr, start_params=start_params,
                                        method='bfgs')


class TestPoissonConstrained2b(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_exposure_constraint2
        #cls.idx = [3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical
        cls.idx = [6, 2, 3, 4, 5, 0]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data,
                                   exposure=data['pyears'].values)
                                   #offset=np.log(data['pyears'].values))
        #res1a = mod1a.fit()
        constr = 'C(agecat)[T.5] - C(agecat)[T.4] = 0.5'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = mod.fit_constrained_(lc.coefs, lc.constants,
                                       fit_kwds={'method':'newton'})
        cls.constraints = lc
        # TODO: bfgs fails

        # test method of Poisson, not monkey patched
        cls.res1m = mod.fit_constrained(constr,
                                        fit_kwds={'method':'bfgs'})


class TestPoissonConstrained2c(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):

        cls.res2 = results.results_exposure_constraint2
        #cls.idx = [3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical
        cls.idx = [6, 2, 3, 4, 5, 0]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data,
                                   offset=np.log(data['pyears'].values))

        constr = 'C(agecat)[T.5] - C(agecat)[T.4] = 0.5'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = mod.fit_constrained_(lc.coefs, lc.constants,
                                       fit_kwds={'method':'newton'})
        cls.constraints = lc
        # TODO: bfgs fails

        # test method of Poisson, not monkey patched
        cls.res1m = mod.fit_constrained(constr,
                                        fit_kwds={'method':'bfgs'})


class TestGLMPoissonConstrained1a(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):
        from statsmodels.genmod.generalized_linear_model import GLM
        from statsmodels.genmod import families
        from statsmodels.base._constraints import fit_constrained

        cls.res2 = results.results_noexposure_constraint
        cls.idx = [7, 3, 4, 5, 6, 0, 1]  # 2 is dropped baseline for categorical

        # example without offset
        formula = 'deaths ~ logpyears + smokes + C(agecat)'
        mod = GLM.from_formula(formula, data=data,
                                    family=families.Poisson())
        mod._init_keys.append('family')

        constr = 'C(agecat)[T.4] = C(agecat)[T.5]'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = fit_constrained(mod, lc.coefs, lc.constants)
        cls.constraints = lc
        cls.res1m = mod.fit_constrained(constr)


class TestGLMPoissonConstrained1b(CheckPoissonConstrainedMixin):

    @classmethod
    def setup_class(cls):
        from statsmodels.genmod.generalized_linear_model import GLM
        from statsmodels.genmod import families
        from statsmodels.base._constraints import fit_constrained

        cls.res2 = results.results_exposure_constraint
        cls.idx = [6, 2, 3, 4, 5, 0]  # 2 is dropped baseline for categorical

        # example with offset
        formula = 'deaths ~ smokes + C(agecat)'
        mod = GLM.from_formula(formula, data=data,
                                    family=families.Poisson(),
                                    offset=np.log(data['pyears'].values))
        mod._init_keys.append('family')

        constr = 'C(agecat)[T.4] = C(agecat)[T.5]'
        lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constr)
        cls.res1 = fit_constrained(mod, lc.coefs, lc.constants)
        cls.constraints = lc
        cls.res1m = mod.fit_constrained(constr)._results

    def test_compare_glm_poisson(self):
        res1 = self.res1m
        res2 = self.res2

        formula = 'deaths ~ smokes + C(agecat)'
        mod = Poisson.from_formula(formula, data=data,
                                   exposure=data['pyears'].values)
                                   #offset=np.log(data['pyears'].values))

        constr = 'C(agecat)[T.4] = C(agecat)[T.5]'
        res2 = mod.fit_constrained(constr, start_params=self.res1m.params,
                                        method='newton')

        # we get high precision because we use the params as start_params

        # basic, just as check that we have the same model
        assert_allclose(res1.params, res2.params, rtol=1e-12)
        assert_allclose(res1.bse, res2.bse, rtol=1e-12)

        # check predict, fitted, ...

        predicted = res1.predict()
        assert_allclose(predicted, res2.predict(), rtol=1e-10)
        assert_allclose(res1.mu, predicted, rtol=1e-10)
        assert_allclose(res1.fittedvalues, predicted, rtol=1e-10)
        assert_allclose(res2.predict(linear=True), res2.predict(linear=True),
                        rtol=1e-10)


def junk():
    # Singular Matrix in mod1a.fit()

    formula1 = 'deaths ~ smokes + C(agecat)'

    formula2 = 'deaths ~ C(agecat) + C(smokes) : C(agecat)'  # same as Stata default

    mod = Poisson.from_formula(formula2, data=data, exposure=data['pyears'].values)

    res0 = mod.fit()

    constraints = 'C(smokes)[T.1]:C(agecat)[3] = C(smokes)[T.1]:C(agecat)[4]'

    import patsy
    lc = patsy.DesignInfo(mod.exog_names).linear_constraint(constraints)
    R, q = lc.coefs, lc.constants

    resc = mod.fit_constrained(R,q, fit_kwds={'method':'bfgs'})

    # example without offset
    formula1a = 'deaths ~ logpyears + smokes + C(agecat)'
    mod1a = Poisson.from_formula(formula1a, data=data)
    print(mod1a.exog.shape)

    res1a = mod1a.fit()
    lc_1a = patsy.DesignInfo(mod1a.exog_names).linear_constraint('C(agecat)[T.4] = C(agecat)[T.5]')
    resc1a = mod1a.fit_constrained(lc_1a.coefs, lc_1a.constants, fit_kwds={'method':'newton'})
    print(resc1a[0])
    print(resc1a[1])
