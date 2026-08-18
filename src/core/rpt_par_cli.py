# rpt_par_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * RPT_PAR.cli - Extension for Climate Module
# * %1-%2 - none or LOOP(SOW, ) for stochastics
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Card, Domain, For, Loop, Smin, Sum, sparse
from gamspy.math import Max, abs, diag, log

if TYPE_CHECKING:
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def rpt_par_cli_GP(g: TimesModelClass) -> None:
    """Calculate Reporting parameters for Climate Module.

    ``%1``/``%2`` are the ``LOOP(SOW,`` / ``);`` pair that both call sites wrap the
    whole file in, so the caller owns the ``gp.Loop(g.Sow)`` context and this
    function only emits its body.
    """
    t, ll, cmq, item, u2, Sow = g.t, g.ll, g.cmq, g.item, g.u2, g.Sow
    CmVar, CmBox, CmBuck = g.CmVar, g.CmBox, g.CmBuck
    CmEmis, CmOfor, CmTkind, CmHists = g.CmEmis, g.CmOfor, g.CmTkind, g.CmHists
    CmAtmap, CmBoxmap, CmForcmap, CmRebox = (
        g.CmAtmap,
        g.CmBoxmap,
        g.CmForcmap,
        g.CmRebox,
    )
    Miyr1, Superyr = g.Miyr1, g.Superyr
    cm_const, cm_exoforc, cm_led, cm_linfor = (
        g.cm_const,
        g.cm_exoforc,
        g.cm_led,
        g.cm_linfor,
    )
    cm_phi, cm_ppm, cm_rr, cm_sig, cm_sig1, cm_stat0 = (
        g.cm_phi,
        g.cm_ppm,
        g.cm_rr,
        g.cm_sig,
        g.cm_sig1,
        g.cm_stat0,
    )
    cm_deltat, cm_dt_forc, cm_maxc_m, cm_result = (
        g.cm_deltat,
        g.cm_dt_forc,
        g.cm_maxc_m,
        g.cm_result,
    )
    cm_smaxc_m, cm_sresult = g.cm_smaxc_m, g.cm_sresult
    attlvl, cnt, f, first_val, last_val = g.attlvl, g.cnt, g.f, g.first_val, g.last_val
    my_array, my_f, my_fil2, vallvl, z = g.my_array, g.my_f, g.my_fil2, g.vallvl, g.z

    VAR_CLIBOX, VAR_CLITOT = g.VAR_CLIBOX, g.VAR_CLITOT
    EQ_CLIMAX, EQ_CLITOT = g.eq_climax, g.eq_clitot

    cm_result.setRecords(None)
    cm_maxc_m.setRecords(None)
    # *-----------------------------------------------------------------------------
    # * Calculate incremental radiative forcing in each year
    my_array.setRecords(None)
    my_f[...] = (
        Sum(
            CmBoxmap["CO2-GTC", CmVar, CmBox].where[
                cm_phi["CO2-GTC", CmBox, "CO2-GTC"]
            ],
            cm_stat0[CmVar, CmBox],
        )
        / cm_const["CO2-PREIND"]
    )
    vallvl[...] = cm_const["GAMMA"] / log(2)
    # Card accepts a Variable at run time; only its annotation is narrower.
    z[...] = Smin(t, g.m[t] - g.cm_calib).where[
        Card(VAR_CLIBOX)  # type: ignore[arg-type, index]
    ]
    with Loop(ll.where[z.where[cm_led[ll]]]):
        cnt[...] = Max(1, cm_led[ll])
        attlvl[...] = (
            Sum(
                CmBoxmap["CO2-GTC", CmVar, CmBox].where[
                    cm_phi["CO2-GTC", CmBox, "CO2-GTC"]
                ],
                VAR_CLIBOX.l[CmVar, CmBox, ll],
            )
            / cm_const["CO2-PREIND"]
        )
        z[...] = (attlvl - my_f) / cnt
        with For(f, start=0, end=cnt - 1):
            my_array[ll - f] = vallvl * log(attlvl - f * z) + cm_exoforc[ll - f]
        my_f[...] = attlvl
    cm_result["FORC+CO2", "CM-FORC", ll].where[cm_led[ll]] = (
        my_array[ll] - cm_exoforc[ll]
    )
    # *-----------------------------------------------------------------------------
    # * Calculate radiative forcing from other emissions in each year
    with Loop(Superyr[t, ll].where[cm_led[ll]]):
        cm_result[CmOfor, "CM-FORC", ll] = Sum(
            CmForcmap[CmOfor, CmEmis],
            cm_linfor[ll, CmEmis, "FX"]
            + cm_linfor[ll, CmEmis, "N"]
            / cm_ppm[CmEmis]
            * Sum(
                CmBoxmap[CmEmis, CmVar, CmBox].where[cm_phi[CmEmis, CmBox, CmEmis]],
                VAR_CLIBOX.l[CmVar, CmBox, ll],
            ),
        ) + Sum(
            CmForcmap[CmTkind[CmOfor], CmVar].where[
                (~CmEmis[CmVar]).where[CmTkind[CmVar]]
            ],
            VAR_CLITOT.l[CmOfor, ll],
        )
    with Loop(Miyr1[t]):
        first_val[...] = Sum(
            CmForcmap[CmOfor, CmEmis],
            cm_linfor[t, CmEmis, "FX"]
            + cm_linfor[t, CmEmis, "N"]
            / cm_ppm[CmEmis]
            * Sum(
                CmBoxmap[CmEmis, CmVar, CmBox].where[cm_phi[CmEmis, CmBox, CmEmis]],
                cm_stat0[CmVar, CmBox],
            ),
        ) + Sum(
            CmForcmap[CmTkind, CmVar].where[(~CmEmis[CmVar]).where[CmTkind[CmVar]]],
            VAR_CLITOT.l[CmTkind, t],
        )
    with Loop(ll.where[cm_led[ll]]):
        cnt[...] = Max(1, cm_led[ll])
        last_val[...] = Sum(
            CmForcmap[CmOfor, CmTkind[CmVar]], cm_result[CmOfor, "CM-FORC", ll]
        )
        with For(f, start=0, end=cnt - 1):
            my_f[...] = f / cnt
            my_fil2[ll - f] = my_f * first_val + (1 - my_f) * last_val
        first_val[...] = last_val
    my_array[ll].where[my_array[ll]] = my_array[ll] + my_fil2[ll]
    # *-----------------------------------------------------------------------------
    cm_dt_forc[ll] = my_array[ll]
    # *-----------------------------------------------------------------------------
    # * Calculate the ith powers of SIG, i=1...Z, where Z = LEAD(T)
    # * First intialize CM_DD to the identity matrix, CM_EE to zero
    with Loop(Domain(CmVar["FORCING"], ll).where[cm_led[ll]]):
        z[...] = cm_led[ll]
        cm_rr.setRecords(None)
        cm_rr["1", CmBuck, CmBox] = diag(CmBuck, CmBox)
        with For(f, start=0, end=z - 1):
            cm_rr["2", CmBox, "LO"] = (
                cm_rr["2", CmBox, "LO"] + my_array[ll - f] * cm_rr["1", CmBox, "ATM"]
            )
            cm_rr["1", CmBuck, CmBox] = Sum(
                cmq.where[CmBox[cmq]],
                cm_rr["1", CmBuck, cmq] * cm_sig[Sow, cmq, CmBox],
            )
        # * Calculate temperature changes
        cm_deltat[ll, CmBox] = (
            cm_rr["1", CmBox, "ATM"] * cm_deltat[ll - cm_led[ll], "ATM"]
            + cm_rr["1", CmBox, "LO"] * cm_deltat[ll - cm_led[ll], "LO"]
            + cm_rr["2", CmBox, "LO"] * cm_sig1[Sow]
            + (
                cm_rr["1", CmBox, "ATM"] * cm_stat0["FORCING", "ATM"]
                + cm_rr["1", CmBox, "LO"] * cm_stat0["FORCING", "LO"]
            ).where[Miyr1[ll]]
        )
    # *-----------------------------------------------------------------------------
    # * Shadow price of total and maximum constraints
    cm_maxc_m[CmVar, t] = sparse(abs(EQ_CLITOT.m[CmVar, t, t]))
    cm_maxc_m[CmVar, ll] = sparse(
        Max(cm_maxc_m[CmVar, ll], abs(EQ_CLIMAX.m[ll, CmVar])).where[
            EQ_CLIMAX.m[ll, CmVar]
        ]
    )

    # *-----------------------------------------------------------------------------
    # * Collect all basic results
    cm_result[CmVar, "CM-EMIS", ll].where[CmEmis[CmVar]] = sparse(
        VAR_CLITOT.l[CmVar, ll]
    )
    cm_result[CmVar, "CM-FORC", ll].where[~CmEmis[CmVar]] = sparse(
        VAR_CLITOT.l[CmVar, ll]
    )
    cm_result[CmVar, cmq, ll] = sparse(
        Sum(CmRebox[cmq, CmBox], VAR_CLIBOX.l[CmVar, CmBox, ll])
    )
    with Loop(CmAtmap[CmEmis, CmHists]):
        cm_result[CmHists, "CM-PPX", ll].where[cm_led[ll]] = (
            Sum(
                CmBoxmap[CmEmis, CmVar, CmBox].where[cm_phi[CmEmis, CmBox, CmEmis]],
                VAR_CLIBOX.l[CmVar, CmBox, ll],
            )
            / cm_ppm[CmEmis]
        )
    cm_result["FORC+TOT", "CM-FORC", ll].where[cm_led[ll]] = sparse(cm_dt_forc[ll])
    cm_result["DELTA+ATM", "CM-DT", ll] = sparse(cm_deltat[ll, "ATM"])
    cm_result["DELTA+LO", "CM-DT", ll] = sparse(cm_deltat[ll, "LO"])
    cm_sresult[Sow, item, u2, ll] = sparse(cm_result[item, u2, ll])
    cm_smaxc_m[Sow, item, ll] = sparse(cm_maxc_m[item, ll])


def rpt_par_cli(
    *,
    arg1: str = "",
    arg2: str = "",
) -> str:
    """Raw GAMS variant of :func:`rpt_par_cli_GP`.

    A module whose body is ``$BATINCLUDE``d inside GAMS control flow cannot be
    translated to GAMSPy statements until the enclosing block is translated too.
    This variant only serves solve_stc.py, which inlines it into an untranslated
    ``IF(...)``/``LOOP(...)``, and can be removed once that module is translated.
    """
    return rf"""
{arg1}
  OPTION CLEAR=CM_RESULT, CLEAR=CM_MAXC_M;
*-----------------------------------------------------------------------------
* Calculate incremental radiative forcing in each year
  OPTION CLEAR=MY_ARRAY;
  MY_F = SUM(CM_BOXMAP('CO2-GTC',CM_VAR,CM_BOX)$CM_PHI('CO2-GTC',CM_BOX,'CO2-GTC'),CM_STAT0(CM_VAR,CM_BOX))/CM_CONST('CO2-PREIND');
  VALLVL = CM_CONST('GAMMA') / LOG(2);
  Z = SMIN(T,M(T)-CM_CALIB)$CARD(VAR_CLIBOX);
  LOOP(LL$(Z$CM_LED(LL)), CNT = MAX(1,CM_LED(LL));
    ATTLVL = SUM(CM_BOXMAP('CO2-GTC',CM_VAR,CM_BOX)$CM_PHI('CO2-GTC',CM_BOX,'CO2-GTC'),VAR_CLIBOX.L(CM_VAR,CM_BOX,LL))/CM_CONST('CO2-PREIND');
    Z = (ATTLVL - MY_F) / CNT;
    FOR(F = 0 TO CNT-1, MY_ARRAY(LL-F) = VALLVL*LOG(ATTLVL-F*Z)+CM_EXOFORC(LL-F));
    MY_F = ATTLVL;
  );
  CM_RESULT('FORC+CO2','CM-FORC',LL)$CM_LED(LL) = MY_ARRAY(LL)-CM_EXOFORC(LL);
*-----------------------------------------------------------------------------
* Calculate radiative forcing from other emissions in each year
  LOOP(SUPERYR(T,LL)$CM_LED(LL), CM_RESULT(CM_OFOR,'CM-FORC',LL) =
    SUM(CM_FORCMAP(CM_OFOR,CM_EMIS),CM_LINFOR(LL,CM_EMIS,'FX')+CM_LINFOR(LL,CM_EMIS,'N')/CM_PPM(CM_EMIS)*
      SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$CM_PHI(CM_EMIS,CM_BOX,CM_EMIS),VAR_CLIBOX.L(CM_VAR,CM_BOX,LL))) +
    SUM(CM_FORCMAP(CM_TKIND(CM_OFOR),CM_VAR)$((NOT CM_EMIS(CM_VAR))$CM_TKIND(CM_VAR)),VAR_CLITOT.L(CM_OFOR,LL)));
  LOOP(MIYR_1(T), FIRST_VAL =
    SUM(CM_FORCMAP(CM_OFOR,CM_EMIS),CM_LINFOR(T,CM_EMIS,'FX')+CM_LINFOR(T,CM_EMIS,'N')/CM_PPM(CM_EMIS)*
      SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$CM_PHI(CM_EMIS,CM_BOX,CM_EMIS),CM_STAT0(CM_VAR,CM_BOX))) +
    SUM(CM_FORCMAP(CM_TKIND,CM_VAR)$((NOT CM_EMIS(CM_VAR))$CM_TKIND(CM_VAR)),VAR_CLITOT.L(CM_TKIND,T)));
  LOOP(LL$CM_LED(LL), CNT = MAX(1,CM_LED(LL));
    LAST_VAL = SUM(CM_FORCMAP(CM_OFOR,CM_TKIND(CM_VAR)),CM_RESULT(CM_OFOR,'CM-FORC',LL));
    FOR(F = 0 TO CNT-1, MY_F = F/CNT; MY_FIL2(LL-F) = MY_F*FIRST_VAL+(1-MY_F)*LAST_VAL);
    FIRST_VAL = LAST_VAL);
  MY_ARRAY(LL)$MY_ARRAY(LL) = MY_ARRAY(LL) + MY_FIL2(LL);
*-----------------------------------------------------------------------------
  CM_DT_FORC(LL) = MY_ARRAY(LL);
*-----------------------------------------------------------------------------
* Calculate the ith powers of SIG, i=1...Z, where Z = LEAD(T)
* First intialize CM_DD to the identity matrix, CM_EE to zero
  LOOP((CM_VAR('FORCING'),LL)$CM_LED(LL), Z = CM_LED(LL);
    OPTION CLEAR=CM_RR;
    CM_RR('1',CM_BUCK,CM_BOX) = DIAG(CM_BUCK,CM_BOX);
    FOR(F = 0 TO Z-1,
      CM_RR('2',CM_BOX,'LO') = CM_RR('2',CM_BOX,'LO') + MY_ARRAY(LL-F)*CM_RR('1',CM_BOX,'ATM');
      CM_RR('1',CM_BUCK,CM_BOX) = SUM(CM_Q$CM_BOX(CM_Q),CM_RR('1',CM_BUCK,CM_Q)*CM_SIG(SOW,CM_Q,CM_BOX));
    );
* Calculate temperature changes
    CM_DELTAT(LL,CM_BOX) =
                  CM_RR('1',CM_BOX,'ATM') * CM_DELTAT(LL-CM_LED(LL),'ATM') +
                  CM_RR('1',CM_BOX,'LO') * CM_DELTAT(LL-CM_LED(LL),'LO') +
                  CM_RR('2',CM_BOX,'LO') * CM_SIG1(SOW) +
                  (CM_RR('1',CM_BOX,'ATM') * CM_STAT0('FORCING','ATM') +
                   CM_RR('1',CM_BOX,'LO') * CM_STAT0('FORCING','LO'))$MIYR_1(LL);
  );
*-----------------------------------------------------------------------------
* Shadow price of total and maximum constraints
  CM_MAXC_M(CM_VAR,T) $= ABS(EQ_CLITOT.M(CM_VAR,T,T));
  CM_MAXC_M(CM_VAR,LL) $= MAX(CM_MAXC_M(CM_VAR,LL),ABS(EQ_CLIMAX.M(LL,CM_VAR)))$EQ_CLIMAX.M(LL,CM_VAR);

*-----------------------------------------------------------------------------
* Collect all basic results
  CM_RESULT(CM_VAR,'CM-EMIS',LL)$CM_EMIS(CM_VAR) $= VAR_CLITOT.L(CM_VAR,LL);
  CM_RESULT(CM_VAR,'CM-FORC',LL)$(NOT CM_EMIS(CM_VAR)) $= VAR_CLITOT.L(CM_VAR,LL);
  CM_RESULT(CM_VAR,CM_Q,LL) $= SUM(CM_REBOX(CM_Q,CM_BOX),VAR_CLIBOX.L(CM_VAR,CM_BOX,LL));
  LOOP(CM_ATMAP(CM_EMIS,CM_HISTS), CM_RESULT(CM_HISTS,'CM-PPX',LL)$CM_LED(LL) =
    SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$CM_PHI(CM_EMIS,CM_BOX,CM_EMIS),VAR_CLIBOX.L(CM_VAR,CM_BOX,LL))/CM_PPM(CM_EMIS));
  CM_RESULT('FORC+TOT','CM-FORC',LL)$CM_LED(LL) $= CM_DT_FORC(LL);
  CM_RESULT('DELTA+ATM','CM-DT',LL)  $= CM_DELTAT(LL,'ATM');
  CM_RESULT('DELTA+LO','CM-DT',LL)   $= CM_DELTAT(LL,'LO');
  CM_SRESULT(SOW,ITEM,U2,LL)     $= CM_RESULT(ITEM,U2,LL);
  CM_SMAXC_M(SOW,ITEM,LL)        $= CM_MAXC_M(ITEM,LL);
{arg2}
"""
