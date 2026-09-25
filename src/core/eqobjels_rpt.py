# eqobjels_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJELS the objective function flexible demand costs reporting
# *=============================================================================*
# * arg1 - assigned parameter(..arg2..)
# * arg2 - year index (Y_EOH/TT)
# * arg3 - mult or ''
# *-----------------------------------------------------------------------------
# *V0.5a 980729 control the inner sums according to the years in the periods

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Domain, Ord, Sum
from gamspy.math import Max, ceil

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqobjelsRptConfig:
    """Strongly typed data contract for eqobjels.rpt."""

    # %1 - the assigned parameter, already indexed with its %2 year index
    arg1: ImplicitParameter
    # %2 - year index (Y_EOH/TT)
    arg2: Set | Alias
    # %3 - mult or '': multiplier of the whole right hand side
    arg3: ImplicitParameter | Expression | int = 1


class EqobjelsRpt(GamsClass):
    """Translation unit for eqobjels.rpt."""

    # Instance attributes
    module_name: str = "eqobjels_rpt"
    gams_source: str = "eqobjels.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqobjelsRptConfig,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec_eqobjels_rpt,
            config=self.config,
            micro=self.env.micro,
            if_mi_agc_defined=self.tc.defined("MI_AGC"),
        )

    def exec_eqobjels_rpt(
        self: EqobjelsRpt,
        config: EqobjelsRptConfig,
        micro: str,
        if_mi_agc_defined: bool,
    ) -> None:
        g = self.tc
        cc = config

        r, c, t, s, j, jj, bd, age, span, cur, Com = (
            g.r,
            g.c,
            g.t,
            g.s,
            g.j,
            g.jj,
            g.bd,
            g.age,
            g.span,
            g.cur,
            g.Com,
        )
        Bdneq, ComTs, MiDmas, Periodyr, Rcj, Rdcur, RtcShed = (
            g.Bdneq,
            g.ComTs,
            g.MiDmas,
            g.Periodyr,
            g.Rcj,
            g.Rdcur,
            g.RtcShed,
        )
        bdsig, com_bprice, com_elast, com_elastx, com_step, com_voc = (
            g.bdsig,
            g.com_bprice,
            g.com_elast,
            g.com_elastx,
            g.com_step,
            g.com_voc,
        )
        shape, shaped = g.shape, g.shaped
        VAR_ELAST = g.VAR_ELAST

        # *V0.5a 980729 control the inner sums according to the years in the periods

        # The relative demand change of step J, shared by every term below
        step = (Ord(j) - 0.5) * com_voc[r, t, c, bd] / com_step[r, c, bd]

        # Plain (unshaped) elastic demand steps
        els_plain = Sum(
            Rcj[r, c, j, bd],
            VAR_ELAST.l[r, t, c, s, j, bd]
            * ((1 - bdsig[bd] * step) ** (1 / com_elast[r, t, c, s, bd])),
        ).where[~com_elastx[r, t, c, bd]]

        # Shaped elastic demand steps
        els_shaped = Sum(
            RtcShed[r, t, c, bd, jj[age]],
            Sum(
                Domain(
                    Rcj[r, c, j, bd],
                    span[age.lead(ceil(step * 100 - Ord(age)))],
                ),
                (
                    shaped[bd, jj, span]
                    * ((1 - bdsig[bd] * step) / shaped[bd, "1", span])
                    ** (1 / Max(1e-3, shape[jj, span]))
                )
                ** (1 / com_elast[r, t, c, s, bd])
                * VAR_ELAST.l[r, t, c, s, j, bd],
            ),
        )

        els = els_plain + els_shaped

        # $IF DEFINED MI_AGC: integral demand prices of the MICRO extension
        if if_mi_agc_defined:
            els = els + Sum(
                MiDmas[r, Com, c].where[g.mi_dope[r, t, c]],
                Sum(
                    Rcj[r, c, j, bd],
                    VAR_ELAST.l[r, t, c, s, j, bd] * g.mi_agc[r, t, Com, c, j, bd],
                ),
            )

        cc.arg1.where[Sum(Rcj[r, c, "1", Bdneq], 1)] = cc.arg3 * Sum(
            Domain(Rdcur[r, cur], Bdneq[bd]),
            bdsig[bd]
            # *V0.5b 980824 - correct ORD adjustment
            * Sum(
                Domain(Periodyr[t, cc.arg2], ComTs[r, c, s]).where[
                    com_elast[r, t, c, s, bd]
                ],
                com_bprice[r, t, c, s, cur] * els,
            ),
        )

        # $IFI NOT %MICRO%==YES $EXIT
        if micro.upper() != "YES":
            return

        com_agg, com_fr, rd_nlp, rd_shar = g.com_agg, g.com_fr, g.rd_nlp, g.rd_shar
        ddf_qref, mi_ccons, mi_elasp, mi_esub, mi_rho = (
            g.ddf_qref,
            g.mi_ccons,
            g.mi_elasp,
            g.mi_esub,
            g.mi_rho,
        )
        VAR_DEM = g.VAR_DEM

        # * NLP utility loss
        ces = (
            Sum(
                MiDmas[r, c, Com],
                rd_shar[r, t, c, Com] ** (1 / mi_esub[r, t, c])
                * (com_agg[r, t, Com, c] * VAR_DEM.l[r, t, Com]) ** mi_rho[r, t, c],
            )
            ** (1 / mi_rho[r, t, c])
        ) ** mi_elasp[r, t, c]

        utility = (
            (VAR_DEM.l[r, t, c] ** mi_elasp[r, t, c]).where[rd_nlp[r, c] == 1]
            + ces.where[rd_nlp[r, c] > 2]
            - ddf_qref[r, t, c] ** mi_elasp[r, t, c]
        ).where[rd_nlp[r, c] > 0]

        cc.arg1.where[rd_nlp[r, c]] = cc.arg3 * Sum(
            Rdcur[r, cur],
            Sum(
                Domain(Periodyr[t, cc.arg2], ComTs[r, c, s]).where[
                    com_bprice[r, t, c, s, cur] * mi_elasp[r, t, c]
                ],
                -com_fr[r, t, c, s] * mi_ccons[r, t, c] * utility,
            ),
        )


def eqobjels_rpt(
    arg1: str,
    arg2: str,
    arg3: str,
    micro: str,
    if_mi_agc_defined: bool,
) -> str:
    """Raw GAMS text of eqobjels.rpt, for callers that are still string based."""
    return rf"""
*V0.5a 980729 control the inner sums according to the years in the periods

  {arg1}$SUM(RCJ(R,C,'1',BDNEQ),1) = {arg3}

    SUM((RDCUR(R,CUR),BDNEQ(BD)), BDSIG(BD) *
*V0.5b 980824 - correct ORD adjustment
      SUM((PERIODYR(T,{
        arg2
    }),COM_TS(R,C,S))$COM_ELAST(R,T,C,S,BD), COM_BPRICE(R,T,C,S,CUR) *
        (SUM(RCJ(R,C,J,BD), VAR_ELAST.L(R,T,C,S,J,BD) *
          ((1-BDSIG(BD)*(ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))**(1/COM_ELAST(R,T,C,S,BD))))$(NOT COM_ELASTX(R,T,C,BD)) +
         SUM(RTC_SHED(R,T,C,BD,JJ(AGE)),
           SUM((RCJ(R,C,J,BD),SPAN(AGE+CEIL((ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD)*100-ORD(AGE)))),
             (SHAPED(BD,JJ,SPAN) *
              ((1-BDSIG(BD)*(ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))/SHAPED(BD,'1',SPAN))**(1/MAX(1E-3,SHAPE(JJ,SPAN)))
             )**(1/COM_ELAST(R,T,C,S,BD)) * VAR_ELAST.L(R,T,C,S,J,BD)))
{
        "+SUM(MI_DMAS(R,COM,C)$MI_DOPE(R,T,C),SUM(RCJ(R,C,J,BD),VAR_ELAST.L(R,T,C,S,J,BD)*MI_AGC(R,T,COM,C,J,BD)))"
        if if_mi_agc_defined
        else ""
    }
        ))
    );
{
        ""
        if micro.upper() != "YES"
        else (
            f'''
* NLP utility loss
  {arg1}$RD_NLP(R,C) = {arg3}
    SUM(RDCUR(R,CUR),
      SUM((PERIODYR(T,{
                arg2
            }),COM_TS(R,C,S))$(COM_BPRICE(R,T,C,S,CUR)$MI_ELASP(R,T,C)), -COM_FR(R,T,C,S) * MI_CCONS(R,T,C) *
          ((VAR_DEM.L(R,T,C)**MI_ELASP(R,T,C))$(RD_NLP(R,C)=1) +
           ((SUM(MI_DMAS(R,C,COM),RD_SHAR(R,T,C,COM)**(1/MI_ESUB(R,T,C))*(COM_AGG(R,T,COM,C)*VAR_DEM.L(R,T,COM))**MI_RHO(R,T,C))**(1/MI_RHO(R,T,C)))**MI_ELASP(R,T,C))$(RD_NLP(R,C)>2) -
           DDF_QREF(R,T,C)**MI_ELASP(R,T,C))$(RD_NLP(R,C)>0))
    );
'''
        )
    }

"""
