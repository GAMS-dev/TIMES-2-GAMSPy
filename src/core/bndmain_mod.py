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

from core.bnd_act_mod import bnd_act_mod
from core.bnd_cum_mod import bnd_cum_mod
from core.bnd_elas_mod import bnd_elas_mod
from core.bnd_flo_mod import bnd_flo_mod
from core.bnd_macro_tm import bnd_macro_tm
from core.bnd_set_mod import bnd_set_mod
from core.bnd_stg_mod import bnd_stg_mod
from core.bnd_ucw_mod import bnd_ucw_mod
from core.dynslite_vda import dynslite_vda_bounds

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        var = self.env.var

        self.tc.enqueue(
            self.exec_bndmain_mod,
            arg1=self.arg1,
            arg2=self.arg2,
            var=var,
            swd=self.env.swd,
            sow=self.env.sow,
            swt=self.env.swt,
            r_t=self.env.r_t,
            dflbl=self.env.dflbl,
            stages=self.env.stages,
            timesed=self.env.timesed,
            reduce=self.env.reduce,
            mx=self.env.mx,
            pgprim=self.env.pgprim,
            eotime=self.env.eotime,
            cufscal=self.env.cufscal,
            cucscal=self.env.cucscal,
            macro=self.env.macro,
            var_uc=self.env.var_uc,
            rts=self.env.rts,
            model_name=self.env.model_name,
            bnd_ucw_defined={
                f"{var}_UC": self.tc.defined(f"{var}_UC"),
                f"{var}_UCR": self.tc.defined(f"{var}_UCR"),
                f"{var}_UCT": self.tc.defined(f"{var}_UCT"),
                f"{var}_UCRT": self.tc.defined(f"{var}_UCRT"),
                f"{var}_UCTS": self.tc.defined(f"{var}_UCTS"),
                f"{var}_UCRTS": self.tc.defined(f"{var}_UCRTS"),
            },
            stochastic_symbols_declared={
                "S_NCAP_BND": self.tc.defined("S_NCAP_BND"),
                "S_CAP_BND": self.tc.defined("S_CAP_BND"),
                "S_COM_BNDNET": self.tc.defined("S_COM_BNDNET"),
                "S_COM_BNDPRD": self.tc.defined("S_COM_BNDPRD"),
            },
        )

    def exec_bndmain_mod(
        self: BndmainMod,
        arg1: str,
        arg2: str,
        var: str,
        swd: str,
        sow: str,
        swt: str,
        r_t: str,
        stages: str,
        timesed: str,
        reduce: str,
        mx: str,
        pgprim: str,
        eotime: str,
        cufscal: str,
        cucscal: str,
        macro: str,
        var_uc: str,
        dflbl: str,
        rts: str,
        model_name: str,
        bnd_ucw_defined: dict[str, bool],
        stochastic_symbols_declared: dict[str, bool],
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=bndmain_mod(
                arg1=arg1,
                arg2=arg2,
                var=var,
                swd=swd,
                sow=sow,
                swt=swt,
                r_t=r_t,
                stages=stages,
                timesed=timesed,
                reduce=reduce,
                dflbl=dflbl,
                mx=mx,
                pgprim=pgprim,
                eotime=eotime,
                cufscal=cufscal,
                cucscal=cucscal,
                macro=macro,
                var_uc=var_uc,
                rts=rts,
                model_name=model_name,
                bnd_ucw_defined=bnd_ucw_defined,
                stochastic_symbols_declared=stochastic_symbols_declared,
            ),
        )


def bndmain_mod(
    *,
    arg1: str = "",
    arg2: str = "",
    var: str,
    swd: str,
    sow: str,
    swt: str,
    r_t: str,
    stages: str,
    timesed: str,
    reduce: str,
    mx: str,
    pgprim: str,
    eotime: str,
    cufscal: str,
    cucscal: str,
    macro: str,
    var_uc: str,
    rts: str,
    dflbl: str,
    model_name: str,
    bnd_ucw_defined: dict[str, bool],
    stochastic_symbols_declared: dict[str, bool],
) -> str:
    return rf"""
{rf"$CLEAR {var}_IRE {var}_UPS {var}_UDP {var}_UPT {var}_SCAP" if arg2 == "0" else ""}

*-----------------------------------------------------------------------------
* elastic demands step curve
*-----------------------------------------------------------------------------
{var}_ELAST.UP(R,T,C,S,J,BD {swd}) = INF;
{
        bnd_elas_mod(
            stages=stages,
            var=var,
            mx=mx,
            sow=sow,
        )
        if timesed == "YES"
        else ""
    }

*-----------------------------------------------------------------------------
* limit on total activity capacity when not vintaged
*-----------------------------------------------------------------------------
{
        bnd_act_mod(
            var=var,
            swd=swd,
            swt=f"SW_T(T{swd})$" if stages == "YES" else swt,
            r_t=r_t,
        )
    }

*-----------------------------------------------------------------------------
* limit on the flow variable when not vintaged
*-----------------------------------------------------------------------------
{
        bnd_flo_mod(
            stages=stages,
            reduce=reduce,
            var=var,
            dflbl=dflbl,
            swd=swd,
            swt=f"{swd})$SW_T(T{swd}" if reduce == "YES" and stages == "YES" else swt,
        )
    }

*-----------------------------------------------------------------------------
* limit on storage
*-----------------------------------------------------------------------------
{
        bnd_stg_mod(
            arg1="SIN",
            arg2="IN",
            arg3="0",
            var=var,
            swd=swd,
            pgprim=pgprim,
            stages=stages,
        )
    }
{
        bnd_stg_mod(
            arg1="SOUT",
            arg2="OUT",
            arg3="-INF",
            var=var,
            swd=swd,
            pgprim=pgprim,
            stages=stages,
        )
    }

*-----------------------------------------------------------------------------
* limit on total installation of new capacity
*-----------------------------------------------------------------------------
* prevent new investment if turned off explicitly by the user
NCAP_BND(RTP_OFF,'UP') = EPS;
NCAP_BND(RTP(R,T,P),'LO')$(NCAP_BND(RTP,'UP')$NCAP_BND(RTP,'LO')) = SMIN(BDNEQ,NCAP_BND(RTP,BDNEQ));

{
        bnd_set_mod(
            arg1=f"{var}_NCAP",
            arg2="R,T,P",
            arg3="NCAP_BND",
            arg4=f"{r_t},P",
            arg5=f"$(RP(R,P){f'$SW_T(T{sow})' if stages == 'YES' else swt})",
            arg6="",
            stages=stages,
            swd=swd,
            sow=sow,
            stochastic_symbol_declared=stochastic_symbols_declared.get(
                "S_NCAP_BND", False
            ),
        )
    }

*-----------------------------------------------------------------------------
* limit on total installed capacity
*-----------------------------------------------------------------------------
CAP_BND(RTP(RTP_VARP),'LO')$CAP_BND(RTP,'UP') = SMIN(BDNEQ,CAP_BND(RTP,BDNEQ));

{
        bnd_set_mod(
            arg1=f"{var}_CAP",
            arg2="R,T,P",
            arg3="CAP_BND",
            arg4=f"RTP({r_t},P)",
            arg5=swt,
            arg6="",
            stages=stages,
            swd=swd,
            sow=sow,
            stochastic_symbol_declared=stochastic_symbols_declared.get(
                "S_CAP_BND", False
            ),
        )
    }

*-----------------------------------------------------------------------------
* limit on commodities
*-----------------------------------------------------------------------------
{
        bnd_set_mod(
            arg1=f"{var}_COMNET",
            arg2="R,T,C,S",
            arg3="COM_BNDNET",
            arg4=f"RTCS_VARC({r_t},C,S)",
            arg5=swt,
            arg6="",
            stages=stages,
            swd=swd,
            sow=sow,
            stochastic_symbol_declared=stochastic_symbols_declared.get(
                "S_COM_BNDNET", False
            ),
        )
    }
{
        bnd_set_mod(
            arg1=f"{var}_COMPRD",
            arg2="R,T,C,S",
            arg3="COM_BNDPRD",
            arg4=f"RTCS_VARC({r_t},C,S)",
            arg5=swt,
            arg6="",
            stages=stages,
            swd=swd,
            sow=sow,
            stochastic_symbol_declared=stochastic_symbols_declared.get(
                "S_COM_BNDPRD", False
            ),
        )
    }
{var}_COMPRD.FX(RTCS_VARC(R,T,C,S){
        sow
    })$((NOT RHS_COMPRD(R,T,C,S))$RCS_COMPRD(R,T,C,S,'FX')) = EPS;

*-----------------------------------------------------------------------------
* bounds for cumulative variables
*-----------------------------------------------------------------------------
{
        bnd_cum_mod(
            arg1="COM_VAR",
            stages=stages,
            eotime=eotime,
            var=var,
            sow=sow,
            cufscal=cufscal,
            cucscal=cucscal,
            macro=macro,
        )
        if arg2 == "0"
        else ""
    }

*-----------------------------------------------------------------------------
* bounds for user constraint slacks
*-----------------------------------------------------------------------------
{
        bnd_ucw_mod(
            arg1=swt,
            arg2="",
            var=var,
            stages=stages,
            swd=swd,
            sow=sow,
            defined_symbols=bnd_ucw_defined,
        )
        if var_uc == "YES"
        else ""
    }

*-----------------------------------------------------------------------------
* bounds for OBJ components
*-----------------------------------------------------------------------------
{
        ""
        if macro == "YES"
        else rf'''
UC_TS_SUM(R,UC_N(OBV),S) = NO;
{var}_OBJ.LO(R,OBV(UC_N),CUR {sow})$UC_RHS(UC_N,'N') = -INF;
{var}_OBJ.LO(R,OBV(UC_N),CUR {sow}) $= UC_RHS(UC_N,'LO');
{var}_OBJ.UP(R,OBV(UC_N),CUR {sow}) $= UC_RHS(UC_N,'UP');
{var}_OBJ.LO(R,OBV(UC_N),CUR {sow})$UC_RHSR(R,UC_N,'N') = -INF;
{var}_OBJ.LO(R,OBV(UC_N),CUR {sow}) $= UC_RHSR(R,UC_N,'LO');
{var}_OBJ.UP(R,OBV(UC_N),CUR {sow}) $= UC_RHSR(R,UC_N,'UP');
'''
    }

*-----------------------------------------------------------------------------
* bounds for TIMES-MACRO
*-----------------------------------------------------------------------------
{bnd_macro_tm() if macro == "YES" else ""}

*-----------------------------------------------------------------------------
* Fix timeslices turned off in projected periods
*-----------------------------------------------------------------------------
{
        dynslite_vda_bounds(
            swd=swd,
            stages=stages,
            model_name=model_name,
            var=var,
            var_uc_yes=(var_uc == "YES"),
        )
        if rts != "S"
        else ""
    }
"""
