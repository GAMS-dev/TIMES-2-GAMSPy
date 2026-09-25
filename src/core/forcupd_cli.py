# forcupd_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging

from core.coef_ext_cli import coef_ext_cli_slope

logger = logging.getLogger(__name__)


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
