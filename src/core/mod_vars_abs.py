# mod_vars_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================*
# * MOD_VARS.EXT EXTENSION VARIABLES
# * called from MAINDRV.MOD
# *==================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Equation, Set, UniverseAlias, Variable

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsAbs(GamsClass):
    """Translation unit for mod_vars.abs."""

    # Instance attributes
    module_name: str = "mod_vars_abs"
    gams_source: str = "mod_vars.abs"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        var = self.env.var

        g.set_variable(
            name=f"{var}_BSPRS",
            var=Variable(
                m,
                name=f"{var}_BSPRS",
                type="Positive",
                domain=[g.r, g.year, g.t, g.p, g.c, g.s, g.lA, *self.env.swd_GP],
                description="Balancing services",
            ),
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  POSITIVE VARIABLES
  {self.env.var}_COMLV(CLVT,R,YEAR,C,S{self.env.swd})   Commodity levels
  {self.env.var}_RLD(R,T,S,ITEM{self.env.swd})          Reserve-defining load levels
  ;
""",
        )

        bs_equations: tuple[tuple[str, list[Alias | Set | UniverseAlias], str], ...] = (
            (
                "EQ_BS00",
                [g.r, g.t, g.c, g.s, g.allsow],
                "Overall demands for balancing services",
            ),
            (
                "EQ_BS01",
                [g.r, g.year, g.c, g.s, g.item, g.lA, g.allsow],
                "Max and Diff over stochastic & determistic demand",
            ),
            (
                "EQ_BS02",
                [g.r, g.t, g.s, g.item, g.allsow],
                "Load levels by process category",
            ),
            (
                "EQ_BS03",
                [g.r, g.t, g.c, g.s, g.allsow],
                "Stochastic demand for balancing services",
            ),
            (
                "EQ_BS04",
                [g.r, g.t, g.c, g.s, g.p, g.allsow],
                "Deterministic demand for balancing services",
            ),
            (
                "EQ_BS05",
                [g.r, g.year, g.t, g.p, g.tsl, g.lA, g.s, g.allsow],
                "Minimum online - offline times",
            ),
            (
                "EQ_BS07",
                [g.r, g.year, g.t, g.p, g.s, g.bd, g.allsow],
                "Ramping constraints",
            ),
            (
                "EQ_BS09",
                [g.r, g.year, g.t, g.p, g.s, g.lA, g.allsow],
                "Capacity margin constraints - positive",
            ),
            (
                "EQ_BS10",
                [g.r, g.year, g.t, g.p, g.s, g.allsow],
                "Capacity margin constraints - negative",
            ),
            (
                "EQ_BS11",
                [g.r, g.year, g.t, g.p, g.c, g.s, g.bd, g.allsow],
                "Limits for spinning reserve by type",
            ),
            (
                "EQ_BS18",
                [g.r, g.year, g.t, g.p, g.s, g.bd, g.allsow],
                "Lower limits for non-spinning reserve by type",
            ),
            (
                "EQ_BS19",
                [g.r, g.year, g.t, g.p, g.c, g.s, g.bd, g.allsow],
                "Upper limits for non-spinning reserve by type",
            ),
            (
                "EQ_BS22",
                [g.r, g.year, g.t, g.p, g.s, g.allsow],
                "Limit for positive reserve from storage",
            ),
            (
                "EQ_BS23",
                [g.r, g.year, g.t, g.p, g.s, g.allsow],
                "Limit for negative reserve from storage",
            ),
            (
                "EQ_BS24",
                [g.r, g.year, g.t, g.p, g.s, g.allsow],
                "Limits for negative reserve from end-use",
            ),
            (
                "EQ_BS25",
                [g.r, g.year, g.t, g.p, g.s, g.allsow],
                "Limits for positive reserve from end-use",
            ),
            (
                "EQ_BS26",
                [g.r, g.t, g.p, g.c, g.s, g.allsow],
                "Bounds for process reserves",
            ),
            ("EQ_BS27", [g.r, g.year, g.t, g.p, g.s, g.allsow], "Maintenance 1"),
            ("EQ_BS28", [g.r, g.year, g.t, g.p, g.s, g.allsow], "Maintenance 2"),
        )
        for name, domain, description in bs_equations:
            g.set_equation(
                name=name,
                eq=Equation(m, name=name, domain=domain, description=description),
            )

        self.tc.enqueue(
            self.mod_vars_abs_exec,
            var=self.env.var,
            sow=self.env.sow,
        )

        if self.env.obmac.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* Spines macros
$ macro Z_COMLV VAS_COMLV
$ macro Z_BSPRS VAS_BSPRS
""",
            )

    def mod_vars_abs_exec(
        self: ModVarsAbs,
        var: str,
        sow: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Set minimum exogenous demand
  BS_CAPACT(R)$(NOT BS_CAPACT(R)) = MAX(0,SMAX(RP_STD(R,P)$GR_GENMAP(R,P,'SI'),PRC_CAPACT(R,P)));
  BS_CAPACT(R)$(NOT BS_CAPACT(R)) = MAX(0,SMAX(BS_SUPP(RP_STD(R,P)),PRC_CAPACT(R,P)));
  {var}_COMLV.LO('DET',RTCS_VARC(R,T,C,S){sow}) $= BS_RTCS('EXOGEN',R,T,C,S)*BS_CAPACT(R);
  RPT_OPT('RATE','1')$(RPT_OPT('RATE','1')<=0)=SMAX(R,BS_CAPACT(R))$(RPT_OPT('RATE','1')=0);

* Set bounds on reserve flows
  BS_BNDPRS(RTP,C,S,BDNEQ)$=BS_BNDPRS(RTP,C,S,'FX');
  BS_BNDPRS(RTP,C,S,'N')$SUM(BDNEQ$BS_BNDPRS(RTP,C,S,BDNEQ),1) = 1;
  LOOP((L(BDUPX),BD)$(BDSIG(L)*BDSIG(BD)<0),
  {var}_bsprs.LO(r,t,t,p,c,s,l{sow})$(RTP(R,T,P)$BS_COMTS(R,C,S)) $= BS_BNDPRS(R,T,P,C,S,BD);
  {var}_bsprs.UP(r,t,t,p,c,s,l{sow})$(RTP(R,T,P)$BS_COMTS(R,C,S)) $= BS_BNDPRS(R,T,P,C,S,L));
""",
        )
