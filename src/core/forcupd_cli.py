# forcupd_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging

from gamspy import Loop, Sum
from gamspy.math import Max, log, sqrt

from core.coef_ext_cli import coef_ext_cli_slope, coef_ext_cli_slope_GP
from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def forcupd_cli_GP(g: TimesModelClass) -> None:
    ch4_pre = 700
    n2o_pre = 270
    fofo = (
        0.47
        * log(
            1.0
            + 2.01e-05 * ((g.f * g.z) ** 0.75)
            + 5.31e-15 * g.f * ((g.f * g.z) ** 1.52)
        )
        - g.my_sum
    )

    with Loop(g.CmAtmap[g.CmEmis, g.CmHists]):
        g.cm_result[g.CmHists, g.ll].where[g.cm_led[g.ll]] = (
            Sum(
                g.CmBoxmap[g.CmEmis, g.CmVar, g.CmBox].where[
                    g.cm_phi[g.CmEmis, g.CmBox, g.CmEmis]
                ],
                g.VAR_CLIBOX.l[g.CmVar, g.CmBox, g.ll],
            )
            / g.cm_ppm[g.CmEmis]
        )
    g.f[...] = ch4_pre
    g.z[...] = n2o_pre
    g.my_sum[...] = 0.0
    g.my_sum[...] = fofo
    with Loop(g.ll.where[g.cm_led[g.ll]]):
        # *...methane
        g.f[...] = Max(1.0, g.cm_result["CH4-PPB", g.ll] - 0.5)
        g.z[...] = n2o_pre
        g.first_val[...] = 0.036 * (sqrt(g.f) - sqrt(ch4_pre)) - fofo
        g.f[...] = g.f + 1.0
        g.last_val[...] = 0.036 * (sqrt(g.f) - sqrt(ch4_pre)) - fofo
        g.z[...] = g.last_val - g.first_val
        g.last_val[...] = (g.first_val + g.last_val) / 2.0
        g.cm_linfor[g.ll, "CH4-PPB", "N"] = g.z
        g.cm_linfor[g.ll, "CH4-PPB", "FX"] = g.last_val - g.z * (g.f - 0.5)
        # *...nitrous
        g.f[...] = ch4_pre
        g.z[...] = Max(1.0, g.cm_result["N2O-PPB", g.ll] - 0.5)
        g.first_val[...] = 0.12 * (sqrt(g.z) - sqrt(n2o_pre)) - fofo
        g.z[...] = g.z + 1.0
        g.last_val[...] = 0.12 * (sqrt(g.z) - sqrt(n2o_pre)) - fofo
        g.f[...] = g.last_val - g.first_val
        g.last_val[...] = (g.first_val + g.last_val) / 2.0
        g.cm_linfor[g.ll, "N2O-PPB", "N"] = g.f
        g.cm_linfor[g.ll, "N2O-PPB", "FX"] = g.last_val - g.f * (g.z - 0.5)
    # * carbon
    g.cm_linfor[g.ll, "CO2-PPM", g.Bdneq].where[g.cm_led[g.ll]] = g.cm_result[
        "CO2-PPM", g.ll
    ]

    coef_ext_cli_slope_GP(g=g)


def forcupd_cli() -> str:
    ch4_pre = "700"
    n2o_pre = "270"
    fofo = "(0.47*LOG(1 + 2.01E-5*(F*Z)**0.75 + 5.31E-15*F*(F*Z)**1.52)-MY_SUM)"

    return_str = rf"""
LOOP(CM_ATMAP(CM_EMIS,CM_HISTS), CM_RESULT(CM_HISTS,LL)$CM_LED(LL) =
SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$CM_PHI(CM_EMIS,CM_BOX,CM_EMIS),VAR_CLIBOX.L(CM_VAR,CM_BOX,LL))/CM_PPM(CM_EMIS));
F={ch4_pre}; Z={n2o_pre}; MY_SUM=0; MY_SUM={fofo};
LOOP(LL$CM_LED(LL),
*...methane
F = MAX(1,CM_RESULT('CH4-PPB',LL)-.5); Z = {n2o_pre};
FIRST_VAL = .036*(SQRT(F)-SQRT({ch4_pre})) - {fofo}; F=F+1;
LAST_VAL  = .036*(SQRT(F)-SQRT({ch4_pre})) - {fofo};
Z=LAST_VAL-FIRST_VAL; LAST_VAL=(FIRST_VAL+LAST_VAL)/2;
CM_LINFOR(LL,'CH4-PPB','N') = Z;
CM_LINFOR(LL,'CH4-PPB','FX') = LAST_VAL-Z*(F-0.5);
*...nitrous
F = {ch4_pre}; Z = MAX(1,CM_RESULT('N2O-PPB',LL)-.5);
FIRST_VAL = 0.12*(SQRT(Z)-SQRT({n2o_pre})) - {fofo}; Z=Z+1;
LAST_VAL  = 0.12*(SQRT(Z)-SQRT({n2o_pre})) - {fofo};
F=LAST_VAL-FIRST_VAL; LAST_VAL=(FIRST_VAL+LAST_VAL)/2;
CM_LINFOR(LL,'N2O-PPB','N') = F;
CM_LINFOR(LL,'N2O-PPB','FX') = LAST_VAL-F*(Z-0.5);
);
* carbon
CM_LINFOR(LL,'CO2-PPM',BDNEQ)$CM_LED(LL) = CM_RESULT('CO2-PPM',LL);
"""

    return_str += coef_ext_cli_slope()

    return return_str
