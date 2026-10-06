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

from gamspy import Domain, Number, Ord, Sum
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
        eqobjels_rpt_GP(
            g=self.tc,
            config=config,
            micro=micro,
            if_mi_agc_defined=if_mi_agc_defined,
        )


def eqobjels_rpt_GP(
    g: TimesModelClass,
    config: EqobjelsRptConfig,
    micro: str,
    if_mi_agc_defined: bool,
) -> None:
    cc = config

    # *V0.5a 980729 control the inner sums according to the years in the periods

    # $IF DEFINED MI_AGC
    mi_agc_term = (
        Sum(
            g.MiDmas[g.r, g.Com, g.c].where[g.mi_dope[g.r, g.t, g.c]],
            Sum(
                g.Rcj[g.r, g.c, g.j, g.bd],
                g.VAR_ELAST.l[g.r, g.t, g.c, g.s, g.j, g.bd]
                * g.mi_agc[g.r, g.t, g.Com, g.c, g.j, g.bd],
            ),
        )
        if if_mi_agc_defined
        else Number(0)
    )

    cc.arg1.where[Sum(g.Rcj[g.r, g.c, "1", g.Bdneq], 1)] = cc.arg3 * Sum(
        Domain(g.Rdcur[g.r, g.cur], g.Bdneq[g.bd]),
        g.bdsig[g.bd]
        # *V0.5b 980824 - correct ORD adjustment
        * Sum(
            Domain(g.Periodyr[g.t, cc.arg2], g.ComTs[g.r, g.c, g.s]).where[
                g.com_elast[g.r, g.t, g.c, g.s, g.bd]
            ],
            g.com_bprice[g.r, g.t, g.c, g.s, g.cur]
            * (
                Sum(
                    g.Rcj[g.r, g.c, g.j, g.bd],
                    g.VAR_ELAST.l[g.r, g.t, g.c, g.s, g.j, g.bd]
                    * (
                        (
                            1
                            - g.bdsig[g.bd]
                            * (Ord(g.j) - 0.5)
                            * g.com_voc[g.r, g.t, g.c, g.bd]
                            / g.com_step[g.r, g.c, g.bd]
                        )
                        ** (1 / g.com_elast[g.r, g.t, g.c, g.s, g.bd])
                    ),
                ).where[~g.com_elastx[g.r, g.t, g.c, g.bd]]
                + Sum(
                    g.RtcShed[g.r, g.t, g.c, g.bd, g.jj[g.age]],
                    Sum(
                        Domain(
                            g.Rcj[g.r, g.c, g.j, g.bd],
                            g.span[
                                g.age
                                + ceil(
                                    (Ord(g.j) - 0.5)
                                    * g.com_voc[g.r, g.t, g.c, g.bd]
                                    / g.com_step[g.r, g.c, g.bd]
                                    * 100
                                    - Ord(g.age)
                                )
                            ],
                        ),
                        (
                            g.shaped[g.bd, g.jj, g.span]
                            * (
                                (
                                    1
                                    - g.bdsig[g.bd]
                                    * (Ord(g.j) - 0.5)
                                    * g.com_voc[g.r, g.t, g.c, g.bd]
                                    / g.com_step[g.r, g.c, g.bd]
                                )
                                / g.shaped[g.bd, "1", g.span]
                            )
                            ** (1 / Max(1e-3, g.shape[g.jj, g.span]))
                        )
                        ** (1 / g.com_elast[g.r, g.t, g.c, g.s, g.bd])
                        * g.VAR_ELAST.l[g.r, g.t, g.c, g.s, g.j, g.bd],
                    ),
                )
                + mi_agc_term
            ),
        ),
    )

    # $IFI NOT %MICRO%==YES $EXIT
    if micro.upper() != "YES":
        return

    # * NLP utility loss
    cc.arg1.where[g.rd_nlp[g.r, g.c]] = cc.arg3 * Sum(
        g.Rdcur[g.r, g.cur],
        Sum(
            Domain(g.Periodyr[g.t, cc.arg2], g.ComTs[g.r, g.c, g.s]).where[
                g.com_bprice[g.r, g.t, g.c, g.s, g.cur].where[g.mi_elasp[g.r, g.t, g.c]]
            ],
            -g.com_fr[g.r, g.t, g.c, g.s]
            * g.mi_ccons[g.r, g.t, g.c]
            * (
                (g.VAR_DEM.l[g.r, g.t, g.c] ** g.mi_elasp[g.r, g.t, g.c]).where[
                    g.rd_nlp[g.r, g.c] == 1
                ]
                + (
                    (
                        Sum(
                            g.MiDmas[g.r, g.c, g.Com],
                            g.rd_shar[g.r, g.t, g.c, g.Com]
                            ** (1 / g.mi_esub[g.r, g.t, g.c])
                            * (
                                g.com_agg[g.r, g.t, g.Com, g.c]
                                * g.VAR_DEM.l[g.r, g.t, g.Com]
                            )
                            ** g.mi_rho[g.r, g.t, g.c],
                        )
                        ** (1 / g.mi_rho[g.r, g.t, g.c])
                    )
                    ** g.mi_elasp[g.r, g.t, g.c]
                ).where[g.rd_nlp[g.r, g.c] > 2]
                - g.ddf_qref[g.r, g.t, g.c] ** g.mi_elasp[g.r, g.t, g.c]
            ).where[g.rd_nlp[g.r, g.c] > 0],
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
