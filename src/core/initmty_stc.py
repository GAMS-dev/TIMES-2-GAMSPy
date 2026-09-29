# initmty_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * INITMTY.stc - Extension for Stochastics
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter, Set

from core.base_class import GamsClass
from core.utils import expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyStc(GamsClass):
    """Translation unit for initmty.stc"""

    # Instance attributes
    module_name: str = "initmty_stc"
    gams_source: str = "initmty.stc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.env.set_global("stages", "YES")

        self.input_control_parameters()
        self.internal_sets_and_parameters()
        self.available_sows_per_period()
        self.stochastic_input_parameters()
        self.internal_work_sets_and_parameters()
        self.reporting()

    def input_control_parameters(self) -> None:
        g = self.tc
        m = self.tc.container

        g.sw_start = Parameter(m, name="SW_START", domain=[g.j])
        g.sw_subs = Parameter(m, name="SW_SUBS", domain=[g.j, g.allsow])
        g.sw_sprob = Parameter(m, name="SW_SPROB", domain=[g.j, g.allsow])
        g.sw_prob = Parameter(m, name="SW_PROB", domain=[g.allsow])
        g.sw_lambda = Parameter(m, name="SW_LAMBDA", records=0)
        # * Predefined UC names for tradeoff analysis
        expand_set(g.ucn, elements=["OBJZ", "OBJ1"])

    def internal_sets_and_parameters(self) -> None:
        g = self.tc
        m = g.container

        g.ww = Alias(m, "WW", alias_with=g.allsow)
        g.SwChild = Set(
            m,
            name="SW_CHILD",
            domain=[g.j, g.ww, g.ww],
            description="Child SOWs of parent SOW at stage J",
        )
        g.SwTree = Set(
            m,
            name="SW_TREE",
            domain=[g.j, g.ww, g.ww],
            description="Finest level SOWs of SOW at stage J",
        )
        g.SwCopy = Set(
            m,
            name="SW_COPY",
            domain=[g.j, g.allsow],
            description="Parent SOW of SOWs to be copied",
        )
        g.SwCpmap = Set(
            m,
            name="SW_CPMAP",
            domain=[g.j, g.ww, g.ww],
            description="Copy map for attributes",
        )
        g.SwTstg = Set(
            m,
            name="SW_TSTG",
            domain=[g.ll, g.j],
            description="Valid stages J for each period T",
        )
        g.SwMap = Set(
            m,
            name="SW_MAP",
            domain=[g.t, g.ww, g.j, g.ww],
            description="Map from internal to original SOW",
        )
        g.SwRev = Set(
            m, name="SW_REV", domain=[g.ww, g.j, g.ww], description="Reverse SOW tree"
        )
        g.Superyr = Set(
            m,
            name="SUPERYR",
            domain=[g.t, g.allyear],
            description="SUpremum PERiod YeaR",
        )
        g.sw_desc = Parameter(
            m,
            name="SW_DESC",
            domain=[g.j, g.allsow],
            description="Number of finest level SOWs",
        )
        g.sw_phase = Parameter(m, name="SW_PHASE", records=0)
        g.sw_parm = Parameter(m, name="SW_PARM", records=0)
        g.sw_norm = Parameter(m, name="SW_NORM", records=1)
        g.doiter = Parameter(m, name="DOITER", records=0)

    def available_sows_per_period(self) -> None:
        g = self.tc
        m = g.container
        j, t, ucn, allyear, allsow = g.j, g.t, g.ucn, g.allyear, g.allsow

        g.SwT = Set(
            m,
            name="SW_T",
            domain=[allyear, allsow],
            description="Which SOWs are available at each period",
        )
        g.SwTsw = Set(
            m,
            name="SW_TSW",
            domain=[allsow, allyear, allsow],
            description="Mapping from finest SOWs to unique SOW at each period",
        )
        g.SwStage = Set(
            m,
            name="SW_STAGE",
            domain=[j, allsow],
            description="Internal SOWs at each stage",
        )
        g.SwUct = Set(m, name="SW_UCT", domain=[ucn, t, allsow])
        g.sw_tprob = Parameter(m, name="SW_TPROB", domain=[t, allsow])

    def stochastic_input_parameters(self: InitmtyStc) -> None:
        g = self.tc
        m = g.container

        r, p, c, j, s, item, allyear = g.r, g.p, g.c, g.j, g.s, g.item, g.allyear
        prc, allsow, bohyear, eohyear = g.prc, g.allsow, g.bohyear, g.eohyear
        bd, comvar, cur, cg, ucn = g.bd, g.comvar, g.cur, g.cg, g.ucn
        reg, com, lim, allreg, ts = g.Reg, g.Com, g.lim, g.allreg, g.ts

        g.s_com_proj = Parameter(
            m,
            name="S_COM_PROJ",
            domain=[reg, allyear, com, j, allsow],
            description="Demand scenario projection",
        )
        g.s_cap_bnd = Parameter(
            m,
            name="S_CAP_BND",
            domain=[reg, allyear, prc, bd, j, allsow],
            description="Bound on total installed capacity",
        )
        g.s_com_cumprd = Parameter(
            m,
            name="S_COM_CUMPRD",
            domain=[r, bohyear, eohyear, c, bd, j, allsow],
            description="Cumulative limit on COMPRD",
        )
        g.s_com_cumnet = Parameter(
            m,
            name="S_COM_CUMNET",
            domain=[r, bohyear, eohyear, c, bd, j, allsow],
            description="Cumulative limit on COMNET",
        )
        g.s_com_tax = Parameter(
            m,
            name="S_COM_TAX",
            domain=[r, allyear, c, s, comvar, cur, j, allsow],
            description="Tax on commodity NET/PRD",
        )
        g.s_flo_cum = Parameter(
            m,
            name="S_FLO_CUM",
            domain=[r, p, c, item, item, bd, j, allsow],
            description="Cumulative limit on FLOW",
        )
        g.s_flo_func = Parameter(
            m,
            name="S_FLO_FUNC",
            domain=[r, allyear, p, cg, cg, j, allsow],
            description="Uncertain multiplier of process transformation",
        )
        g.s_ncap_cost = Parameter(
            m,
            name="S_NCAP_COST",
            domain=[r, allyear, p, j, allsow],
            description="Uncertain multiplier of investment cost",
        )
        g.s_dam_cost = Parameter(
            m,
            name="S_DAM_COST",
            domain=[r, allyear, c, cur, j, allsow],
            description="Damage costs",
        )
        g.s_uc_rhs = Parameter(
            m,
            name="S_UC_RHS",
            domain=[ucn, lim, j, allsow],
            description="RHS of user constraint",
        )
        g.s_uc_rhsr = Parameter(
            m,
            name="S_UC_RHSR",
            domain=[allreg, ucn, lim, j, allsow],
            description="RHS of user constraint",
        )
        g.s_uc_rhst = Parameter(
            m,
            name="S_UC_RHST",
            domain=[ucn, allyear, lim, j, allsow],
            description="RHS of user constraint",
        )
        g.s_uc_rhsrt = Parameter(
            m,
            name="S_UC_RHSRT",
            domain=[allreg, ucn, allyear, lim, j, allsow],
            description="RHS of user constraint",
        )
        g.s_uc_rhsts = Parameter(
            m,
            name="S_UC_RHSTS",
            domain=[ucn, allyear, ts, lim, j, allsow],
            description="RHS of user constraint",
        )
        g.s_uc_rhsrts = Parameter(
            m,
            name="S_UC_RHSRTS",
            domain=[allreg, ucn, allyear, ts, lim, j, allsow],
            description="RHS of user constraint",
        )
        g.s_cm_maxco2c = Parameter(
            m,
            name="S_CM_MAXCO2C",
            domain=[allyear, j, allsow],
            description="Maximum allowable atmospheric CO2 concentration",
        )
        g.s_cm_maxc = Parameter(
            m,
            name="S_CM_MAXC",
            domain=[allyear, item, j, allsow],
            description="Maximum allowable climatic quantity",
        )
        g.s_cm_const = Parameter(
            m,
            name="S_CM_CONST",
            domain=[item, j, allsow],
            description="Climate constants",
        )
        g.s_ucobj = Parameter(
            m,
            name="S_UCOBJ",
            domain=[ucn, allsow],
            description="Weight of UC objective component in tradeoff analysis",
        )
        g.s_ncap_afs = Parameter(
            m,
            name="S_NCAP_AFS",
            domain=[r, allyear, p, s, j, allsow],
            description="Seasonal availability factors",
        )
        g.s_com_fr = Parameter(
            m,
            name="S_COM_FR",
            domain=[r, allyear, c, s, j, allsow],
            description="Commodity fraction multipliers",
        )

    def internal_work_sets_and_parameters(self) -> None:
        g = self.tc
        m = self.tc.container

        g.s_com_cum = Parameter(
            m,
            name="S_COM_CUM",
            domain=[g.r, g.comvar, g.allyear, g.allyear, g.c, g.bd, g.j, g.allsow],
            description="Cumulative limit on COMPRD",
        )
        g.T0 = Set(m, name="T0", domain=[g.ll], description="Augmented periods")
        g.SwT2w = Set(
            m,
            name="SW_T2W",
            domain=[g.ww, g.t, g.ww, g.ll],
            description="Augmented map for SOWs by period",
        )
        g.Rtcsw = Set(
            m,
            name="RTCSW",
            domain=[g.r, g.t, g.c, g.s, g.ww],
            description="Indicator for uncertain timeslice fractions",
        )
        g.Rtpw = Set(
            m,
            name="RTPW",
            domain=[g.r, g.allyear, g.p, g.allsow],
            description="Uncertain SOW by vintage",
        )
        g.RpFfsgg = Set(
            m,
            name="RP_FFSGG",
            domain=[g.r, g.p, g.cg, g.cg],
            description="Uncertain transformation groups",
        )
        g.RpFfsggm = Set(
            m,
            name="RP_FFSGGM",
            domain=[g.r, g.p, g.cg, g.cg, g.comgrp, g.comgrp],
            description="Map of transformation groups",
        )
        g.obj_sic = Parameter(
            m,
            name="OBJ_SIC",
            domain=[g.r, g.t, g.p, g.allsow],
            description="Uncertainty in investments",
        )
        g.suc_l = Parameter(
            m, name="SUC_L", domain=[g.allr, g.ucn], description="Dynamic type LHS"
        )
        g.rtp_safs = Parameter(
            m,
            name="RTP_SAFS",
            domain=[g.r, g.t, g.p, g.s, g.ww],
            description="Uncertain availability factors",
        )
        g.rtcs_sfr = Parameter(
            m,
            name="RTCS_SFR",
            domain=[g.r, g.ll, g.c, g.s, g.ww, g.ts],
            description="Uncertain COM_FR multipliers",
        )
        g.rcs_ssfr = Parameter(
            m,
            name="RCS_SSFR",
            domain=[g.r, g.c, g.s, g.ts, g.ww, g.ll],
            description="Uncertain COM_FR multipliers",
        )

    def reporting(self) -> None:
        g = self.tc
        m = self.tc.container

        ww, allsow, item, allyear, ucn = g.ww, g.allsow, g.item, g.allyear, g.ucn

        g.spar_ucsl = Parameter(m, name="SPAR_UCSL", domain=[ww, ucn, "*", "*", "*"])
        g.cm_sresult = Parameter(
            m,
            name="CM_SRESULT",
            domain=[allsow, item, item, allyear],
            description="Climate Module basic results",
        )
        g.cm_smaxc_m = Parameter(
            m,
            name="CM_SMAXC_M",
            domain=[allsow, item, allyear],
            description="Marginals for max constraints",
        )
