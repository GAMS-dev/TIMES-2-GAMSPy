# bndmain_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * BNDMAIN.MOD establishes bounds on variables
# *   %1 - mod or v# for the source code to be used
# *   %2 - flag indicating calling phase
# *=============================================================================*
# *GaG Questions/Comments:
# *  - FXs take precedence as are set last!!!
# *  - TS-based bounds:
# *    - individual TS vs at/above limit via s-index
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.bnd_act_mod import BndActMod
from core.bnd_cum_mod import BndCumMod
from core.bnd_elas_mod import BndElasMod
from core.bnd_flo_mod import BndFloMod
from core.bnd_macro_tm import BndMacroTm
from core.bnd_set_mod import BndSetMod
from core.bnd_stg_mod import BndStgMod
from core.bnd_ucw_mod import BndUcwMod
from core.dynslite_vda import DynsliteVda

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndmainMod(GamsClass):
    """Translation unit for bndmain.mod"""

    # Instance attributes
    module_name: str = "bndmain_mod"
    gams_source: str = "bndmain.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.arg2 == "0":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=f"$CLEAR {self.env.var}_IRE {self.env.var}_UPS {self.env.var}_UDP {self.env.var}_UPT {self.env.var}_SCAP",
            )

        # *-----------------------------------------------------------------------------
        # * elastic demands step curve
        # *-----------------------------------------------------------------------------
        self.tc.enqueue(
            self.set_upper_bound_on_var_elast, var=self.env.var, swd=self.env.swd
        )
        if self.env.timesed == "YES":
            self.include(BndElasMod(tc=self.tc, env=self.env))

        # *-----------------------------------------------------------------------------
        # * limit on total activity capacity when not vintaged
        # *-----------------------------------------------------------------------------
        self.include(BndActMod(tc=self.tc, env=self.env))

        # *-----------------------------------------------------------------------------
        # * limit on the flow variable when not vintaged
        # *-----------------------------------------------------------------------------
        self.include(BndFloMod(tc=self.tc, env=self.env))

        # *-----------------------------------------------------------------------------
        # * limit on storage
        # *-----------------------------------------------------------------------------
        self.include(
            BndStgMod(tc=self.tc, env=self.env, arg1="SIN", arg2="IN", arg3="0")
        )
        self.include(
            BndStgMod(tc=self.tc, env=self.env, arg1="SOUT", arg2="OUT", arg3="-INF")
        )

        # *-----------------------------------------------------------------------------
        # * limit on total installation of new capacity
        # *-----------------------------------------------------------------------------
        if self.env.stages == "YES":
            self.env.set_local("swt", f"$SW_T(T{self.env.sow})")

        # * prevent new investment if turned off explicitly by the user
        self.tc.enqueue(self.prevent_new_investment)
        self.include(
            BndSetMod(
                tc=self.tc,
                env=self.env,
                arg1=f"{self.env.var}_NCAP",
                arg2="R,T,P",
                arg3="NCAP_BND",
                arg4=f"{self.env.r_t},P",
                arg5=f"$(RP(R,P){self.env.swt})",
            )
        )

        # *-----------------------------------------------------------------------------
        # * limit on total installed capacity
        # *-----------------------------------------------------------------------------
        self.tc.enqueue(self.limit_on_total_installed_capacity)
        self.include(
            BndSetMod(
                tc=self.tc,
                env=self.env,
                arg1=f"{self.env.var}_CAP",
                arg2="R,T,P",
                arg3="CAP_BND RTP(R,T,P)",
                arg4=f"{self.env.swt}",
            )
        )

        # *-----------------------------------------------------------------------------
        # * limit on commdities
        # *-----------------------------------------------------------------------------
        self.include(
            BndSetMod(
                tc=self.tc,
                env=self.env,
                arg1=f"{self.env.var}_COMNET",
                arg2="R,T,C,S",
                arg3="COM_BNDNET",
                arg4=f"RTCS_VARC({self.env.r_t},C,S)",
                arg5=f"{self.env.swt}",
            )
        )
        self.include(
            BndSetMod(
                tc=self.tc,
                env=self.env,
                arg1=f"{self.env.var}_COMPRD",
                arg2="R,T,C,S",
                arg3="COM_BNDPRD",
                arg4=f"RTCS_VARC({self.env.r_t},C,S)",
                arg5=f"{self.env.swt}",
            )
        )
        self.tc.enqueue(self.limit_on_commodities, var=self.env.var, sow=self.env.sow)

        # *-----------------------------------------------------------------------------
        # * bounds for cumulative variables
        # *-----------------------------------------------------------------------------
        if self.arg2 == "0":
            self.include(BndCumMod(tc=self.tc, env=self.env, arg1="COM_VAR"))

        # *-----------------------------------------------------------------------------
        # * bounds for user constraint slacks
        # *-----------------------------------------------------------------------------
        if self.env.var_uc == "YES":
            self.include(BndUcwMod(tc=self.tc, env=self.env, arg1=f"{self.env.swt}"))
        # *-----------------------------------------------------------------------------
        # $IF %MACRO%==YES $GOTO MACRO

        if not self.env.macro == "YES":
            self.tc.enqueue(
                self.bounds_for_obj_components,
                var=self.env.var,
                sow=self.env.sow,
            )

        # *-----------------------------------------------------------------------------
        # * bounds for TIMES-MACRO
        # *-----------------------------------------------------------------------------
        if self.env.macro == "YES":
            self.include(BndMacroTm(tc=self.tc, env=self.env))
        # *-----------------------------------------------------------------------------
        # * Fix timeslices turned off in projected periods
        if not self.env.rts == "S":
            self.include(DynsliteVda(tc=self.tc, env=self.env, arg1="BOUNDS"))

    def bounds_for_obj_components(self: BndmainMod, var: str, sow: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
        * Bounds for OBJ components
        UC_TS_SUM(R,UC_N(OBV),S) = NO;
        {var}_OBJ.LO(R,OBV(UC_N),CUR {sow})$UC_RHS(UC_N,'N') = -INF;
        {var}_OBJ.LO(R,OBV(UC_N),CUR {sow}) $= UC_RHS(UC_N,'LO');
        {var}_OBJ.UP(R,OBV(UC_N),CUR {sow}) $= UC_RHS(UC_N,'UP');
        {var}_OBJ.LO(R,OBV(UC_N),CUR {sow})$UC_RHSR(R,UC_N,'N') = -INF;
        {var}_OBJ.LO(R,OBV(UC_N),CUR {sow}) $= UC_RHSR(R,UC_N,'LO');
        {var}_OBJ.UP(R,OBV(UC_N),CUR {sow}) $= UC_RHSR(R,UC_N,'UP');
""",
        )

    def set_upper_bound_on_var_elast(self: BndmainMod, var: str, swd: str):
        self.tc.add_gams_code(
            module=self, phase="run", code=f"{var}_ELAST.UP(R,T,C,S,J,BD {swd}) = INF;"
        )

    def prevent_new_investment(self: BndmainMod):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    NCAP_BND(RTP_OFF,'UP') = EPS;
    NCAP_BND(RTP(R,T,P),'LO')$(NCAP_BND(RTP,'UP')$NCAP_BND(RTP,'LO')) = SMIN(BDNEQ,NCAP_BND(RTP,BDNEQ));
""",
        )

    def limit_on_total_installed_capacity(self: BndmainMod):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
CAP_BND(RTP(RTP_VARP),'LO')$CAP_BND(RTP,'UP') = SMIN(BDNEQ,CAP_BND(RTP,BDNEQ));
""",
        )

    def limit_on_commodities(self: BndmainMod, var: str, sow: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"{var}_COMPRD.FX(RTCS_VARC(R,T,C,S){sow})$((NOT RHS_COMPRD(R,T,C,S))$RCS_COMPRD(R,T,C,S,'FX')) = EPS;",
        )
