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

from gamspy import Number, Smin, SpecialValues, sparse

from core.base_class import GamsClass
from core.bnd_act_mod import bnd_act_mod_GP
from core.bnd_cum_mod import bnd_cum_mod_GP
from core.bnd_elas_mod import bnd_elas_mod_GP
from core.bnd_flo_mod import bnd_flo_mod_GP
from core.bnd_macro_tm import bnd_macro_tm_GP
from core.bnd_set_mod import bnd_set_mod_GP
from core.bnd_stg_mod import bnd_stg_mod_GP
from core.bnd_ucw_mod import bnd_ucw_mod_GP
from core.dynslite_vda import dynslite_vda_bounds_GP

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SowGPType
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

        if self.arg2 == "0":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=f"$CLEAR {var}_IRE {var}_UPS {var}_UDP {var}_UPT {var}_SCAP",
            )

        self.tc.enqueue(
            self.exec_bndmain_mod,
            arg1=self.arg1,
            arg2=self.arg2,
            var=var,
            swd_GP=self.env.swd_GP,
            sow_GP=self.env.sow_GP,
            swt_GP=self.env.swt_GP,
            r_t_GP=self.env.r_t_GP,
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
            rts=self.env.rts(),
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
        swd_GP: tuple[Set | Alias] | tuple[()],
        sow_GP: SowGPType,
        swt_GP: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        r_t_GP: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        stages: str,
        timesed: str,
        reduce: str,
        mx: str,
        pgprim: str,
        eotime: int,
        cufscal: int,
        cucscal: int,
        macro: str,
        var_uc: str,
        dflbl: str,
        rts: str,
        model_name: str,
        bnd_ucw_defined: dict[str, bool],
        stochastic_symbols_declared: dict[str, bool],
    ) -> None:
        """Native translation of bndmain.mod, enqueued from :meth:`compile`."""
        bndmain_mod_GP(
            g=self.tc,
            module=self,
            arg1=arg1,
            arg2=arg2,
            var=var,
            swd_GP=swd_GP,
            sow_GP=sow_GP,
            swt_GP=swt_GP,
            r_t_GP=r_t_GP,
            dflbl=dflbl,
            stages=stages,
            timesed=timesed,
            reduce=reduce,
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
        )


def bndmain_mod_GP(
    *,
    g: TimesModelClass,
    module: GamsClass,
    arg1: str = "",
    arg2: str = "",
    var: str,
    swd_GP: tuple[Set | Alias] | tuple[()],
    sow_GP: SowGPType,
    swt_GP: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    r_t_GP: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
    stages: str,
    timesed: str,
    reduce: str,
    mx: str,
    pgprim: str,
    eotime: int,
    cufscal: int,
    cucscal: int,
    macro: str,
    var_uc: str,
    dflbl: str,
    rts: str,
    model_name: str,
    bnd_ucw_defined: dict[str, bool],
    stochastic_symbols_declared: dict[str, bool],
) -> None:
    """Native translation of bndmain.mod."""
    r, t, p, c, s, j, bd = g.r, g.t, g.p, g.c, g.s, g.j, g.bd

    # -----------------------------------------------------------------------
    # elastic demands step curve
    # -----------------------------------------------------------------------
    VAR_ELAST = g.get_variable(f"{var}_ELAST")
    VAR_ELAST.up[r, t, c, s, j, bd, *swd_GP] = SpecialValues.POSINF
    if timesed == "YES":
        bnd_elas_mod_GP(g=g, stages=stages, var=var, mx=mx, sow_GP=sow_GP)

    # -----------------------------------------------------------------------
    # limit on total activity capacity when not vintaged
    # -----------------------------------------------------------------------
    bnd_act_mod_GP(g=g, var=var, stages=stages, swd=swd_GP, swt=swt_GP, r_t=r_t_GP)

    # -----------------------------------------------------------------------
    # limit on the flow variable when not vintaged
    # -----------------------------------------------------------------------
    bnd_flo_mod_GP(
        g=g,
        stages=stages,
        reduce=reduce,
        var=var,
        swd=swd_GP,
        swt=swt_GP,
        dflbl=dflbl,
    )

    # -----------------------------------------------------------------------
    # limit on storage
    # -----------------------------------------------------------------------
    bnd_stg_mod_GP(
        g=g,
        var=var,
        arg1="SIN",
        arg2="IN",
        arg3=0,
        swd=swd_GP,
        pgprim=pgprim,
        stages=stages,
    )
    bnd_stg_mod_GP(
        g=g,
        var=var,
        arg1="SOUT",
        arg2="OUT",
        arg3=SpecialValues.NEGINF,
        swd=swd_GP,
        pgprim=pgprim,
        stages=stages,
    )

    # -----------------------------------------------------------------------
    # limit on total installation of new capacity
    # -----------------------------------------------------------------------
    # $ IF %STAGES%==YES  $SETLOCAL SWT '$SW_T(T%SOW%)'
    swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()] = (
        (g.SwT[t, *sow_GP],) if stages == "YES" else swt_GP
    )
    swt_cond: ImplicitSet | Number = swt[0] if swt else Number(1)  # type: ignore[assignment]

    # prevent new investment if turned off explicitly by the user
    g.ncap_bnd[g.RtpOff, "UP"] = SpecialValues.EPS
    g.ncap_bnd[g.Rtp[r, t, p], "LO"].where[
        g.ncap_bnd[g.Rtp, "UP"] * g.ncap_bnd[g.Rtp, "LO"]
    ] = Smin(g.Bdneq, g.ncap_bnd[g.Rtp, g.Bdneq])

    bnd_set_mod_GP(
        g=g,
        variable_name=f"{var}_NCAP",
        bound_param_name="NCAP_BND",
        primary_domain=(r, t, p),
        control_domain=(*r_t_GP, p),
        swd=swd_GP,
        sow=sow_GP,
        stages=stages,
        extra_condition=g.Rp[r, p] * swt_cond,
        stochastic_symbol_declared=stochastic_symbols_declared.get("S_NCAP_BND", False),
    )

    # -----------------------------------------------------------------------
    # limit on total installed capacity
    # -----------------------------------------------------------------------
    g.cap_bnd[g.Rtp[g.RtpVarp], "LO"].where[g.cap_bnd[g.Rtp, "UP"]] = Smin(
        g.Bdneq, g.cap_bnd[g.Rtp, g.Bdneq]
    )

    bnd_set_mod_GP(
        g=g,
        variable_name=f"{var}_CAP",
        bound_param_name="CAP_BND",
        primary_domain=(r, t, p),
        control_domain=(g.Rtp[*r_t_GP, p],),
        swd=swd_GP,
        sow=sow_GP,
        stages=stages,
        extra_condition=swt_cond,
        stochastic_symbol_declared=stochastic_symbols_declared.get("S_CAP_BND", False),
    )

    # -----------------------------------------------------------------------
    # limit on commodities
    # -----------------------------------------------------------------------
    bnd_set_mod_GP(
        g=g,
        variable_name=f"{var}_COMNET",
        bound_param_name="COM_BNDNET",
        primary_domain=(r, t, c, s),
        control_domain=(g.RtcsVarc[*r_t_GP, c, s],),
        swd=swd_GP,
        sow=sow_GP,
        stages=stages,
        extra_condition=swt_cond,
        stochastic_symbol_declared=stochastic_symbols_declared.get(
            "S_COM_BNDNET", False
        ),
    )
    bnd_set_mod_GP(
        g=g,
        variable_name=f"{var}_COMPRD",
        bound_param_name="COM_BNDPRD",
        primary_domain=(r, t, c, s),
        control_domain=(g.RtcsVarc[*r_t_GP, c, s],),
        swd=swd_GP,
        sow=sow_GP,
        stages=stages,
        extra_condition=swt_cond,
        stochastic_symbol_declared=stochastic_symbols_declared.get(
            "S_COM_BNDPRD", False
        ),
    )

    VAR_COMPRD = g.get_variable(f"{var}_COMPRD")
    VAR_COMPRD.fx[g.RtcsVarc[r, t, c, s], *sow_GP].where[
        (~g.RhsComprd[r, t, c, s]).where[g.RcsComprd[r, t, c, s, "FX"]]
    ] = SpecialValues.EPS

    # -----------------------------------------------------------------------
    # bounds for cumulative variables
    # -----------------------------------------------------------------------
    if arg2 == "0":
        bnd_cum_mod_GP(
            g=g,
            arg1=g.comvar,
            stages=stages,
            eotime=eotime,
            var=var,
            sow=sow_GP,
            cufscal=cufscal,
            cucscal=cucscal,
            macro=macro,
        )

    # -----------------------------------------------------------------------
    # bounds for user constraint slacks
    # -----------------------------------------------------------------------
    if var_uc == "YES":
        bnd_ucw_mod_GP(
            g=g,
            arg1=swt_cond,
            var=var,
            stages=stages,
            swd_GP=swd_GP,
            sow_GP=sow_GP,
            defined_symbols=bnd_ucw_defined,
        )

    # -----------------------------------------------------------------------
    # bounds for OBJ components
    # -----------------------------------------------------------------------
    if macro != "YES":
        VAR_OBJ = g.get_variable(f"{var}_OBJ")
        g.UcTsSum[g.r, g.ucn[g.obv], g.s] = False
        VAR_OBJ.lo[g.r, g.obv[g.ucn], g.cur, *sow_GP].where[g.uc_rhs[g.ucn, "N"]] = (
            SpecialValues.NEGINF
        )
        VAR_OBJ.lo[g.r, g.obv[g.ucn], g.cur, *sow_GP] = sparse(g.uc_rhs[g.ucn, "LO"])
        VAR_OBJ.up[g.r, g.obv[g.ucn], g.cur, *sow_GP] = sparse(g.uc_rhs[g.ucn, "UP"])
        VAR_OBJ.lo[g.r, g.obv[g.ucn], g.cur, *sow_GP].where[
            g.uc_rhsr[g.r, g.ucn, "N"]
        ] = SpecialValues.NEGINF
        VAR_OBJ.lo[g.r, g.obv[g.ucn], g.cur, *sow_GP] = sparse(
            g.uc_rhsr[g.r, g.ucn, "LO"]
        )
        VAR_OBJ.up[g.r, g.obv[g.ucn], g.cur, *sow_GP] = sparse(
            g.uc_rhsr[g.r, g.ucn, "UP"]
        )

    # -----------------------------------------------------------------------
    # bounds for TIMES-MACRO
    # -----------------------------------------------------------------------
    if macro == "YES":
        bnd_macro_tm_GP(g=g)

    # -----------------------------------------------------------------------
    # Fix timeslices turned off in projected periods
    # -----------------------------------------------------------------------
    if rts != "S":
        dynslite_vda_bounds_GP(
            g=g,
            module=module,
            swd_GP=swd_GP,
            stages=stages,
            model_name=model_name,
            var=var,
            var_uc_yes=(var_uc == "YES"),
        )
