# ddfupd_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================
# * DDFUPD.msa - Update DDF factors directly after previous MACRO run
# *==============================================================================


from __future__ import annotations

import logging

from gamspy import Loop, Sum
from gamspy.math import Min

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def ddfupd_msa() -> str:
    code = r"""
* initialize Y
  TM_DDF_Y(MR(R),T(T_1)) = 1;
  TM_DDF_Y(MR(R),PP) = ((TM_GDPGOAL(R,PP)/TM_GDP(R,PP))**.7) * PAR_Y(R,PP)/SUM(T_1(T),PAR_Y(R,T));
  DISPLAY TM_DDF_Y;

* normalize to base year
  TM_DDF_DM(R,T,DM)$TM_DEM(R,T,DM) = 1;
  LOOP(T_1(TT),TM_DDF_DM(R,T,DM)$TM_DEM(R,TT,DM) = TM_DEM(R,T,DM) / TM_DEM(R,TT,DM));
  LOOP(T_1(TT),TM_DDF_SP(R,T,DM)$PAR_MC(R,TT,DM) = PAR_MC(R,T,DM) / PAR_MC(R,TT,DM));

* estimate DDF factors
  OPTION CLEAR=TM_DDF;
  TM_F2(R,T,DM)$TM_DDF_SP(R,T,DM) = TM_DDF_DM(R,T,DM) / (TM_DDF_Y(R,T) * TM_DDF_SP(R,T,DM) ** (-TM_ESUB(R)));
  TM_DDF(R,PP(T+1),DM)$TM_F2(R,T,DM) = 100 * (1 - (TM_F2(R,PP,DM)/TM_F2(R,T,DM))**((TM_RHO(R)-1)/(NYPER(T)*TM_RHO(R))));

* update growth indicators
  TM_GROWV(R,T) = TM_GROWV(R,T) + (TM_GR(R,T) - PAR_GRGDP(R,T));
  TM_GROWV(R,TLAST) = TM_GR(R,TLAST);

* update other parameters depending on DDFs or growth
  TM_AEEIV(MR,T,DM) = TM_DDF(MR,T,DM) / 100;
  TM_DFACTCURR(R,T) = 1 - (TM_KPVS(R)/TM_KGDP(R) - TM_DEPR(R)/100 - TM_GROWV(R,T)/100);
  TM_IV0(R)         = TM_K0(R) * (TM_DEPR(R) + SUM(T_1(T),TM_GROWV(R,T)))/100;
  TM_C0(R)          = TM_GDP0(R) - TM_IV0(R);

  LOOP(PP(T+1),
    TM_AEEIFAC(MR,PP,DM) = TM_AEEIFAC(MR,T,DM) * (1 - TM_AEEIV(MR,PP,DM)) ** NYPER(T);
    TM_DFACT(R,PP)       = TM_DFACT(R,T) * TM_DFACTCURR(R,T) ** NYPER(T);
    TM_L(R,PP)           = TM_L(R,T) * (1+TM_GROWV(R,T)/100) ** NYPER(T);
  );

* Arbitrary multiplier on utility in last time period.
  TM_DFACT(MR(R),TLAST)$(TM_ARBM NE 1) = TM_DFACT(R,TLAST) *
      (1-MIN(.999,TM_DFACTCURR(R,TLAST))**(NYPER(TLAST)*TM_ARBM)) /
      (1-MIN(.999,TM_DFACTCURR(R,TLAST))**(NYPER(TLAST) * 1 ));

  VAR_INV.FX(MR,T(T_1))  = TM_IV0(MR);
"""

    return code


def ddfupd_msa_GP(g: TimesModelClass) -> None:
    # * initialize Y
    g.tm_ddf_y[g.Mr[g.r], g.t[g.t1]] = 1.0
    g.tm_ddf_y[g.Mr[g.r], g.Pp] = (
        ((g.tm_gdpgoal[g.r, g.Pp] / g.tm_gdp[g.r, g.Pp]) ** 0.7)
        * g.par_y[g.r, g.Pp]
        / Sum(g.t1[g.t], g.par_y[g.r, g.t])
    )
    # NOTE: The following print statement is most likely a debug statement and
    # has been commented out for now since .records cannot be used inside a loop.
    # print(g.tm_ddf_y.records)
    # * normalize to base year
    g.tm_ddf_dm[g.r, g.t, g.Dm].where[g.tm_dem[g.r, g.t, g.Dm]] = 1.0
    with Loop(g.t1[g.tt]):
        g.tm_ddf_dm[g.r, g.t, g.Dm].where[g.tm_dem[g.r, g.tt, g.Dm]] = (
            g.tm_dem[g.r, g.t, g.Dm] / g.tm_dem[g.r, g.tt, g.Dm]
        )
    with Loop(g.t1[g.tt]):
        g.tm_ddf_sp[g.r, g.t, g.Dm].where[g.par_mc[g.r, g.tt, g.Dm]] = (
            g.par_mc[g.r, g.t, g.Dm] / g.par_mc[g.r, g.tt, g.Dm]
        )
    # * estimate DDF factors
    g.tm_ddf.setRecords(None)
    g.tm_f2[g.r, g.t, g.Dm].where[g.tm_ddf_sp[g.r, g.t, g.Dm]] = g.tm_ddf_dm[
        g.r, g.t, g.Dm
    ] / (g.tm_ddf_y[g.r, g.t] * (g.tm_ddf_sp[g.r, g.t, g.Dm] ** (-g.tm_esub[g.r])))
    g.tm_ddf[g.r, g.Pp[g.t + 1], g.Dm].where[g.tm_f2[g.r, g.t, g.Dm]] = 100.0 * (
        1.0
        - (
            (g.tm_f2[g.r, g.Pp, g.Dm] / g.tm_f2[g.r, g.t, g.Dm])
            ** ((g.tm_rho[g.r] - 1.0) / (g.nyper[g.t] * g.tm_rho[g.r]))
        )
    )
    # * update growth indicators
    g.tm_growv[g.r, g.t] = g.tm_growv[g.r, g.t] + (
        g.tm_gr[g.r, g.t] - g.par_grgdp[g.r, g.t]
    )
    g.tm_growv[g.r, g.Tlast] = g.tm_gr[g.r, g.Tlast]
    # * update other parameters depending on DDFs or growth
    g.tm_aeeiv[g.Mr, g.t, g.Dm] = g.tm_ddf[g.Mr, g.t, g.Dm] / 100.0
    g.tm_dfactcurr[g.r, g.t] = 1.0 - (
        g.tm_kpvs[g.r] / g.tm_kgdp[g.r]
        - g.tm_depr[g.r] / 100.0
        - g.tm_growv[g.r, g.t] / 100.0
    )
    g.tm_iv0[g.r] = (
        g.tm_k0[g.r] * (g.tm_depr[g.r] + Sum(g.t1[g.t], g.tm_growv[g.r, g.t])) / 100.0
    )
    g.tm_c0[g.r] = g.tm_gdp0[g.r] - g.tm_iv0[g.r]
    with Loop(g.Pp[g.t + 1]):
        g.tm_aeeifac[g.Mr, g.Pp, g.Dm] = g.tm_aeeifac[g.Mr, g.t, g.Dm] * (
            (1.0 - g.tm_aeeiv[g.Mr, g.Pp, g.Dm]) ** g.nyper[g.t]
        )
        g.tm_dfact[g.r, g.Pp] = g.tm_dfact[g.r, g.t] * (
            g.tm_dfactcurr[g.r, g.t] ** g.nyper[g.t]
        )
        g.tm_l[g.r, g.Pp] = g.tm_l[g.r, g.t] * (
            (1.0 + g.tm_growv[g.r, g.t] / 100.0) ** g.nyper[g.t]
        )
    # * Arbitrary multiplier on utility in last time period.
    g.tm_dfact[g.Mr[g.r], g.Tlast].where[(g.tm_arbm != 1.0)] = (
        g.tm_dfact[g.r, g.Tlast]
        * (
            1.0
            - (
                Min(0.999, g.tm_dfactcurr[g.r, g.Tlast])
                ** (g.nyper[g.Tlast] * g.tm_arbm)
            )
        )
        / (1.0 - (Min(0.999, g.tm_dfactcurr[g.r, g.Tlast]) ** (g.nyper[g.Tlast] * 1.0)))
    )
    g.VAR_INV.fx[g.Mr, g.t[g.t1]] = g.tm_iv0[g.Mr]
