# ppmain_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PPMAIN.MOD oversees all the preprocessor activities
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *   - determination of B/E/D(t)
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import pandas as pd
from gamspy import (
    Alias,
    Card,
    Domain,
    Else,
    ElseIf,
    Expression,
    For,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Product,
    Set,
    Smax,
    Smin,
    SpecialValues,
    Sum,
    While,
    set_options,
    sparse,
)
from gamspy.math import (
    Max,
    Min,
    Round,
    abs,
    ceil,
    exp,
    floor,
    log,
    map_value,
    mod,
    project,
    same_as,
)

from core.base_class import GamsClass
from core.eqflomrk_mod import EqflomrkMod
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.filshape_gms import FilshapeGms
from core.main_ext_mod import include_extension
from core.pp_chp_ier import PpChpIer
from core.pp_chp_mod import PpChpMod
from core.pp_lvlbd_mod import PpLvlbdMod
from core.pp_lvlbr_mod import PpLvlbrMod
from core.pp_lvlfc_mod import PpLvlfcMod, PpLvlfcModConfig
from core.pp_lvlff_mod import PpLvlffMod
from core.pp_lvlfs_mod import PpLvlfsMod
from core.pp_lvlif_mod import PpLvlifMod
from core.pp_lvlpk_mod import PpLvlpkMod
from core.pp_lvlus_mod import PpLvlusConfig, PpLvlusMod
from core.pp_micro_mod import PpMicroMod
from core.pp_off_mod import pp_off_GP
from core.pp_prelv_vda import PpPrelvVda
from core.pp_qafs_mod import PpQafsMod
from core.pp_reduce_red import PpReduceRed
from core.ppmain_tm import PpmainTm
from core.preppm_mod import PreppmMod
from core.prepxtra_mod import PrepxtraMod
from core.timslice_mod import TimsliceMod
from core.utils import resolve_ctst
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from core.utils import SET_OR_ALIAS
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


def tslvl_reset_violations_df(f_val: float, z_val: float) -> pd.DataFrame | None:
    """Commodities/processes defined at non-existing TSLVL."""
    if f_val + z_val == 0:
        return None
    return pd.DataFrame({"F": [int(f_val)], "Z": [int(z_val)]})


def cap_bnd_violations(g: TimesModelClass) -> Set:
    """Inconsistent CAP_BND(UP/FX) defined for process capacity."""

    r, t, p, lA = g.r, g.t, g.p, g.lA
    Rtp, PrcRcap, RpFlo = g.Rtp, g.PrcRcap, g.RpFlo
    f, z, ifq = g.f, g.z, g.ifq

    cap_bnd, rcap_bnd, prc_resid = g.cap_bnd, g.rcap_bnd, g.prc_resid

    violations = Set(g.container, name="violations_r_t_p_cap_bnd", domain=[r, t, p])
    with Loop(
        Domain(Rtp[r, t, p], lA["UP"]).where[
            ((~(cap_bnd[Rtp, lA] > prc_resid[Rtp])).where[cap_bnd[Rtp, lA]])
        ]
    ):
        with If(PrcRcap[r, p]):
            z[...] = 0.0
        with Else():
            z[...] = prc_resid[Rtp]
        with If(z):
            f[...] = cap_bnd[Rtp, lA]
            cap_bnd[Rtp, lA].where[(ifq < 10.0)] = SpecialValues.EPS
            f[...].where[(0.0 ** (ifq + f + Number(1.0).where[RpFlo[r, p]]))] = z
            with If(f < z):
                rcap_bnd[Rtp, "N"] = z
                violations[r, t, p] = True
    return violations


def mi_dmas_topology_violations(g: TimesModelClass) -> Set:
    """Commodity group found in topology violating its integrity."""
    r, c, Com = g.r, g.c, g.Com
    Dem, MiDmas = g.Dem, g.MiDmas

    violations = Set(g.container, name="violations_r_c_com_mi_dmas", domain=[r, c, Com])
    violations[r, c, Com].where[Dem[r, c] & MiDmas[r, c, Com]] = True
    return violations


def ncap_tlife_violations(g: TimesModelClass) -> tuple[Set, Set]:
    """NCAP_TLIFE duration check. NCAP_TLIFE out of feasible range."""
    r, t, p, age = g.r, g.t, g.p, g.age
    Rtp, Rxx, ncap_tlife, life = g.Rtp, g.Rxx, g.ncap_tlife, g.life

    too_short = Set(g.container, name="violations_r_t_p_tlife_short", domain=[r, t, p])
    too_long = Set(g.container, name="violations_r_t_p_tlife_long", domain=[r, t, p])

    with Loop(age.sameAs("1")):
        Rxx.setRecords(None)
        g.putgrp[...] = 0.0
        with Loop(
            Rtp[r, t, p].where[
                ((~(life[age + (ncap_tlife[Rtp] - 0.999)])).where[ncap_tlife[Rtp]])
            ]
        ):
            with If(ncap_tlife[Rtp] < 1.0):
                Rxx[Rtp] = True
                too_short[r, t, p] = True
            with Else():
                too_long[r, t, p] = True

    return too_short, too_long


def diverging_trade_topology_violations(g: TimesModelClass) -> Set:
    """Unsupported diverging trade topology."""

    r, p, c, ie = g.r, g.p, g.c, g.ie
    Com, RpcMarket, TopIre = g.Com, g.RpcMarket, g.TopIre
    RpcIre, IreDist, CgGrp = g.RpcIre, g.IreDist, g.CgGrp
    z = g.z

    violations = Set(
        g.container, name="violations_r_p_c_ie_trade", domain=[r, p, c, ie]
    )
    # * Set the import commodities for marketplaces
    with Loop(RpcMarket[r, p, c, ie].where[(~(Sum(TopIre[r, c, r, Com, p], 1.0)))]):
        # * If only one import and market commodity is involved for (R,P), choose the import:
        z[...] = Sum(RpcIre[r, p, Com, "IMP"], 1.0) + SpecialValues.EPS
        with If(IreDist[r, p]):  # noqa: SIM117
            with If(z > 1.0):
                violations[r, p, c, ie] = True
        with ElseIf(z == 1.0):
            z[...] = Sum(Com.where[RpcMarket[r, p, Com, "EXP"]], 1.0)
        with If(z == 1.0):  # noqa: SIM117
            with Loop(RpcIre[r, p, Com, "IMP"]):
                z[...] = 0.0
                CgGrp[r, p, c, Com] = True
        with If(z):
            CgGrp[r, p, c, c] = True
    return violations


def flow_off_ts_violations(g: TimesModelClass) -> Set:
    """Flow OFF TS level below VARiable TS level."""
    r, p, c, ts, s = g.r, g.p, g.c, g.ts, g.s
    bohyear, eohyear = g.bohyear, g.eohyear
    PrcFoff, Rpc, RpcsVar, RsBelow = g.PrcFoff, g.Rpc, g.RpcsVar, g.RsBelow

    violations = Set(
        g.container,
        name="violations_r_p_c_ts_boh_eoh",
        domain=[r, p, c, ts, bohyear, eohyear],
    )
    with Loop(
        PrcFoff[Rpc[r, p, c], ts, bohyear, eohyear].where[
            Sum(RpcsVar[r, p, c, s].where[RsBelow[r, s, ts]], 1.0)
        ]
    ):
        violations[r, p, c, ts, bohyear, eohyear] = True
    return violations


def ncap_pasti_violations(g: TimesModelClass) -> Set:
    """Delayed Process but PASTInvestment."""
    r, p, pyr = g.r, g.p, g.pyr
    Trackp, ncap_pasti, prc_ymax = g.Trackp, g.ncap_pasti, g.prc_ymax

    violations = Set(g.container, name="violations_ncap_pasti", domain=[r, p])
    violations[r, p].where[
        Trackp[r, p] & Sum(pyr.where[ncap_pasti[r, pyr, p]], 1) & (prc_ymax[r, p] > 0)
    ] = True
    return violations


def com_fr_normalization_violations(g: TimesModelClass) -> Set:
    """COM_FR does not sum to unity (T=first year)."""
    r, t, c = g.r, g.t, g.c
    Trackc, Rtc, com_fr, z = g.Trackc, g.Rtc, g.com_fr, g.z

    violations = Set(g.container, name="violations_r_t_c", domain=[r, t, c])
    with Loop(Trackc[r, c]):
        z[...] = 1.0
        with Loop(  # noqa: SIM117
            Rtc[r, t, c].where[((com_fr[r, t, c, "ANNUAL"] != 1.0).where[z])]
        ):
            with If(abs(com_fr[r, t, c, "ANNUAL"] - 1.0) > 1e-05):
                z[...] = 0.0
                violations[r, t, c] = True
    return violations


def cap_bnd_lo_up_violations(g: TimesModelClass) -> Set:
    """Inconsistent CAP_BND(UP/LO/FX) defined for process capacity."""

    r, t, p = g.r, g.t, g.p
    Rtp, RtpVarp, cap_bnd = g.Rtp, g.RtpVarp, g.cap_bnd

    violations = Set(
        g.container, name="violations_r_t_p_cap_bnd_lo_up", domain=[r, t, p]
    )

    with Loop(
        Rtp[r, t, p].where[
            RtpVarp[r, t, p]
            & (
                (cap_bnd[r, t, p, "LO"] > cap_bnd[r, t, p, "UP"]).where[
                    cap_bnd[r, t, p, "UP"]
                ]
            )
        ]
    ):
        violations[r, t, p] = True
    return violations


class PpmainMod(GamsClass):
    """Translation unit for ppmain.mod."""

    # Instance attributes
    module_name: str = "ppmain_mod"
    gams_source: str = "ppmain.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase: GamsPhase = "init"
        g = self.tc
        m = g.container

        r, t, p, s, c = g.r, g.t, g.p, g.s, g.c

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
* establish the QC error message log file
  FILE QLOG / QA_CHECK.LOG /; QLOG.LW=0;
""",
        )

        g.putout = Parameter(m, name="PUTOUT", records=0)
        g.putgrp = Parameter(m, name="PUTGRP", records=0)
        g.errlev = Parameter(m, name="ERRLEV", records=0)
        # * Additional Declarations in PPMAIN
        g.startoff = Parameter(m, name="STARTOFF", records=0)
        g.endoff = Parameter(m, name="ENDOFF", records=0)
        g.Matprc = Set(m, name="MATPRC", domain=[g.prcgrp], records=["PRV", "PRW"])
        g.NoRvp = Set(m, name="NO_RVP", domain=[r, t, p])
        g.IreDist = Set(m, name="IRE_DIST", domain=[r, p])
        g.RpSgs = Set(m, name="RP_SGS", domain=[r, p])
        g.RpSts = Set(m, name="RP_STS", domain=[r, p])
        g.RpStl = Set(m, name="RP_STL", domain=[r, p, g.tsl, g.lA])
        g.RpsStg = Set(m, name="RPS_STG", domain=[r, p, s])
        g.RpcStg = Set(m, name="RPC_STG", domain=[r, p, c])
        g.RpcStgn = Set(m, name="RPC_STGN", domain=[r, p, c, g.io])
        g.UcDt = Set(m, name="UC_DT", domain=[g.allr, g.ucn])
        g.Rcs = Set(m, name="RCS", domain=[g.Reg, g.Com, g.ts])
        g.RcRc = Set(m, name="RC_RC", domain=[g.allreg, g.Com, g.allreg, g.Com])

        # * Log Warnings
        self.env.set_scoped("tmp", ".")
        if self.env.datagdx == "YES" and self.env.g2x6 == "YES":
            self.env.set_scoped("tmp", "; Input Data have been filtered via GDX")

        # Not relevant in gamspy: $ IF WARNINGS $BATINCLUDE pp_qaput.%1 PUTOUT 0 * 'GAMS Warnings Detected%TMP%'

        self.tc.enqueue(self.phase_one, pgprim=self.env.pgprim)

        # *-----------------------------------------------------------------------------
        # * spread NCAP_PASTI and determine PASTYEAR
        # *-----------------------------------------------------------------------------
        g.Phyr = Set(m, name="PHYR", domain=[g.allyear])
        g.pastsum = Parameter(m, name="PASTSUM", domain=[g.r, g.allyear, g.p])

        self.tc.enqueue(self.phase_two)
        self.add_records_to_universe_item(records=["PASTI"])
        self.tc.enqueue(self.phase_two_two)

        if self.env.obj.upper() == "MOD":
            self.tc.enqueue(self.set_mt_zero)
        self.tc.enqueue(self.phase_three, condition=self.env.oblong.upper() == "YES")

        # Initialize MINYR already here (was in COEF_OBJ.mod)
        g.minyr = Parameter(m, name="MINYR")

        self.tc.enqueue(self.phase_four)

        # Inter/Extrapolate G_OFFTHD if specified
        if self.tc.defined("G_OFFTHD"):
            self.include(
                FilparamGms(
                    tc=self.tc,
                    env=self.env,
                    config=FilparamGmsConfig(
                        src=g.g_offthd,
                        arg2=(),
                        tail1=(),
                        arg4=("", "", "", "", "", ""),
                        arg5=g.year,
                        arg6=g.t,
                        arg9=5,
                    ),
                )
            )

        self.tc.enqueue(self.g_offthd_to_zero)

        # *-----------------------------------------------------------------------------
        # * complete timeslice declarations
        # *-----------------------------------------------------------------------------
        # * Include preprocessing of timeslice attributes
        self.include(TimsliceMod(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_five, botime=self.env.botime)

        # * Check NCAP_PASTI
        self.tc.enqueue(self.check_ncap_pasti)

        # Set the RTP_OFF for all remaining PRC_NOFF ranges
        self.tc.enqueue(self.set_rtp_off)

        # *-----------------------------------------------
        # * interpolation/extrapolation
        # *-----------------------------------------------
        # * Call interpolation subsystem
        self.include(PreppmMod(tc=self.tc, env=self.env))

        if self.env.intext_only.upper() == "YES":
            return

        # initialize timestep control
        # moved symbol declarion to maindrv_mod.py
        g.Subt.setRecords(records=g.t.toList())

        self.tc.enqueue(self.phase_six, ctst=self.env.ctst)

        # * Checks for host processes of refits
        if g.PrcRcap is None:
            g.PrcRcap = Set(m, name="PRC_RCAP")
        self.tc.register_assignment(g.PrcRcap)
        if g.prc_refit is None:
            g.prc_refit = Parameter(m, name="PRC_REFIT")
        self.tc.register_assignment(g.prc_refit)

        self.tc.enqueue(self.phase_seven, ctst=self.env.ctst)

        # override the lead delay on capacity if M2T, if viable period
        if self.env.validate == "YES":
            self.tc.enqueue(self.activate_rtp_cptyr)

        self.tc.register_assignment(g.rcap_bnd)
        self.tc.enqueue(
            self.phase_eight,
            pgprim=self.env.pgprim,
            prc_simv_defined=self.tc.defined("PRC_SIMV"),
        )

        # Extensions after establishing RPCS_VAR and PRC_CAPACT but before levelising
        extensions = {"VDA": PpPrelvVda}
        requested_exts = set(self.env.extend.split())
        include_extension(
            module=self,
            extensions=extensions,
            requested_exts=requested_exts,
            source="ppmain",
        )

        # Make various QA checks for FLO_SHAR
        self.include(PpQafsMod(tc=self.tc, env=self.env))

        # *-----------------------------------------------------------------------------
        # * setup and apply (some) SHAPE/MULTI
        # *-----------------------------------------------------------------------------
        g.maxlife = Parameter(m, name="MAXLIFE")

        self.tc.enqueue(self.phase_nine)

        # Call the SHAPE inter-/extrapolation routine

        self.include(FilshapeGms(tc=self.tc, env=self.env, arg1=g.startoff))

        self.tc.enqueue(self.adjust_shape)

        # *GG* note that multi will take additional parameter NO/YES to do 2nd assignment or not
        # * Call the inter-/extrapolation routine for MULTI
        self.include(
            FilparamGms(
                tc=self.tc,
                env=self.env,
                config=FilparamGmsConfig(
                    src=g.multi,
                    arg2=(g.j,),
                    tail1=(),
                    arg4=("", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Eohyears,
                    arg7=Number(0),  # "NO$"
                ),
            )
        )

        self.tc.enqueue(self.establish_basic_defaults_for_non_ts_attribute)

        g.UcCapflo = Set(m, name="UC_CAPFLO", domain=[g.ucn, g.side, g.r, g.p, g.c])

        self.tc.enqueue(self.phase_eleven)

        # *-----------------------------------------------------------------------------
        # * do the basic initializations that are TS-based, including aggregate/inherit
        # *-----------------------------------------------------------------------------
        # * commodity related attributes
        # *-----------------------------------------------------------------------------
        # * infastructure efficiency
        # * set seasonal fraction for commodity if necessary, G_YRFR('ANNUAL') already = 1
        # * difference between the average calculated demand and the actual shape of the peak
        # * commodity based costs, subsidies and taxes
        # * elastic demands base price, quantity, elasticity and steps

        self.tc.enqueue(self.activate_rtc_net)
        # fmt: off
        batincludes: list[PpLvlfcModConfig] = [
            PpLvlfcModConfig(arg1=g.com_ie,     arg2=(g.c,), arg3=g.ComTs, arg4=(),                 arg5=("0",) * 4, arg6=g.allts, arg7=(g.t,),        arg8=g.Rtc[g.r, g.t, g.c]              ),
            PpLvlfcModConfig(arg1=g.com_fr,     arg2=(g.c,), arg3=g.ComTs, arg4=(),                 arg5=("0",) * 4, arg6=g.allts, arg7=(g.t,),        arg8=g.RtcNet[g.r, g.t, g.c], arg9=True),
            PpLvlfcModConfig(arg1=g.com_pkflx,  arg2=(g.c,), arg3=g.ComTs, arg4=(),                 arg5=("0",) * 4, arg6=g.allts, arg7=(g.t,),        arg8=Number(1)                         ),
            PpLvlfcModConfig(arg1=g.obj_comnt,  arg2=(g.c,), arg3=g.ComTs, arg4=(g.costype,g.cur),  arg5=("0",) * 2, arg6=g.allts, arg7=(g.Datayear,), arg8=g.Rc[g.r, g.c]                    ),
            PpLvlfcModConfig(arg1=g.obj_compd,  arg2=(g.c,), arg3=g.ComTs, arg4=(g.costype,g.cur),  arg5=("0",) * 2, arg6=g.allts, arg7=(g.Datayear,), arg8=g.Rc[g.r, g.c]                    ),
            PpLvlfcModConfig(arg1=g.com_elast,  arg2=(g.c,), arg3=g.ComTs, arg4=(g.bd,),            arg5=("0",) * 3, arg6=g.allts, arg7=(g.Datayear,), arg8=g.Rc[g.r, g.c]                    ),
            PpLvlfcModConfig(arg1=g.com_bprice, arg2=(g.c,), arg3=g.ComTs, arg4=(g.cur,),           arg5=("0",) * 3, arg6=g.allts, arg7=(g.Datayear,), arg8=g.Rc[g.r, g.c]                    ),
            PpLvlfcModConfig(arg1=g.com_bqty,   arg2=(g.c,), arg3=g.ComTs, arg4=(),                 arg5=("0",) * 5, arg6=g.allts, arg7=(),            arg8=g.Rc[g.r, g.c],          arg9=True),
        ]
        # fmt: on
        for pp_lvlfc_config in batincludes:
            self.include(PpLvlfcMod(tc=self.tc, env=self.env, config=pp_lvlfc_config))

        self.tc.enqueue(self.phase_twelve)

        # Split of timeslice based upon level and commodity profile
        if not macro.rtcs_fr.active:
            g.rtcs_fr = Parameter(m, name="RTCS_FR", domain=[g.r, g.t, g.c, g.s, g.s])

        rts_GP = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        self.tc.enqueue(self.phase_thirteen, rts=rts_GP)

        # Preprocess TIMES-Micro
        if self.env.timesed == "YES":
            self.include(PpMicroMod(tc=self.tc, env=self.env, arg1="PRE"))

        self.tc.enqueue(self.phase_fourteen)

        self.include(
            PpLvlbrMod(
                tc=self.tc,
                env=self.env,
                arg1="NCAP_AF",
                arg2="",
                arg3="PRC_TS",
                arg4=",'0','0'",
                arg5="0",
                arg6="1",
            )
        )

        self.tc.enqueue(self.phase_fiveteen)

        self.include(PpLvlpkMod(tc=self.tc, env=self.env, arg1=Number(1)))

        # *-----------------------------------------------------------------------------
        # * flow related attributes
        # *-----------------------------------------------------------------------------
        # * costs, subsidy, taxes, & flow rates
        batincludes = [
            PpLvlfcModConfig(
                arg1=g.flo_cost,
                arg2=(g.p, g.c),
                arg3=g.RpcsVar,
                arg4=(g.cur,),
                arg5=("0",) * 2,
                arg6=g.allts,
                arg7=(g.Datayear,),
                arg8=g.Rpc[g.r, g.p, g.c],
                arg11="N",
            ),
            PpLvlfcModConfig(
                arg1=g.flo_sub,
                arg2=(g.p, g.c),
                arg3=g.RpcsVar,
                arg4=(g.cur,),
                arg5=("0",) * 2,
                arg6=g.allts,
                arg7=(g.Datayear,),
                arg8=g.Rpc[g.r, g.p, g.c],
                arg11="N",
            ),
            PpLvlfcModConfig(
                arg1=g.flo_tax,
                arg2=(g.p, g.c),
                arg3=g.RpcsVar,
                arg4=(g.cur,),
                arg5=("0",) * 2,
                arg6=g.allts,
                arg7=(g.Datayear,),
                arg8=g.Rpc[g.r, g.p, g.c],
                arg11="N",
            ),
            PpLvlfcModConfig(
                arg1=g.flo_pkcoi,
                arg2=(g.p, g.c),
                arg3=g.RpcsVar,
                arg4=(),
                arg5=("0",) * 3,
                arg6=g.allts,
                arg7=(g.t,),
                arg8=g.Rtp[g.r, g.t, g.p],
            ),
            PpLvlfcModConfig(
                arg1=g.flo_bdlvl,
                arg2=(g.p,),
                arg3=g.PrcTs,
                arg4=(g.bd,),
                arg5=("0",) * 2,
                arg6=g.allts,
                arg7=(g.t,),
                arg8=g.Rtp[g.r, g.t, g.p],
                arg10=(g.cg,),
                arg11=Number(1),
                arg12=(~g.c[g.cg]) | g.Actcg[g.cg],
            ),
            PpLvlfcModConfig(
                arg1=g.flo_bdlvl,
                arg2=(g.p, g.c),
                arg3=g.RpcsVar,
                arg4=(g.bd,),
                arg5=("0",) * 2,
                arg6=g.allts,
                arg7=(g.t,),
                arg8=g.Rtp[g.r, g.t, g.p],
                arg11=Number(1),
                arg12=g.Rpc[g.r, g.p, g.c],
            ),
            PpLvlfcModConfig(
                arg1=g.act_flo,
                arg2=(g.p,),
                arg3=g.RpsS1,
                arg4=(),
                arg5=("0",) * 3,
                arg6=g.allts,
                arg7=(g.v,),
                arg8=g.Rtp[g.r, g.v, g.p],
                arg10=(g.c,),
                arg11=Number(0),
                arg12=g.stoa[g.s],
            ),
        ]
        for pp_lvlfc_config in batincludes:
            self.include(PpLvlfcMod(tc=self.tc, env=self.env, config=pp_lvlfc_config))

        self.tc.enqueue(self.phase_sixteen)

        # derive the CHP flow control attributes
        if self.arg1.upper() == "IER":
            self.include(PpChpIer(tc=self.tc, env=self.env, arg1=self.arg1))
        elif self.arg1.upper() == "MOD":
            self.include(PpChpMod(tc=self.tc, env=self.env, arg1=self.arg1))
        else:
            raise FileNotFoundError("No matching pp_chp file found.")

        # *-----------------------------------------------------------------------------
        # * the actual flow control attributes
        # *-----------------------------------------------------------------------------
        # * FLO_ attributes

        # * handle FLO_FUNC and FLO_SUM aggregation/inheritance
        self.include(PpLvlffMod(tc=self.tc, env=self.env))
        self.include(PpLvlfsMod(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_seventeen)

        # handle FLO_SHAR aggregation/inheritance
        self.include(
            PpLvlbrMod(
                tc=self.tc,
                env=self.env,
                arg1="FLO_SHAR",
                arg2=",C,CG",
                arg3="RPCS_VAR",
                arg4="",
                arg5="1",
                arg6="0",
                arg7="C,",
            )
        )
        # preprocessing of FLO_MARK/PRC_MARK
        self.include(EqflomrkMod(tc=self.tc, env=self.env))

        self.tc.enqueue(self.deactivate_rpc_noflo)

        # inter-regional exchange related attributes
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                config=PpLvlfcModConfig(
                    arg1=g.ire_price,
                    arg2=(g.p, g.c),
                    arg3=g.RpcsVar,
                    arg4=(g.allreg, g.ie, g.cur),
                    arg5=(),
                    arg6=g.allts,
                    arg7=(g.Datayear,),
                    arg8=g.RpcIre[g.r, g.p, g.c, g.ie],
                ),
            )
        )
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                config=PpLvlfcModConfig(
                    arg1=g.ire_flosum,
                    arg2=(g.p,),
                    arg3=g.PrcTs,
                    arg4=(g.ie, g.Com, g.io),
                    arg5=(),
                    arg6=g.allts,
                    arg7=(g.t,),
                    arg8=g.Rtp[g.r, g.t, g.p],
                    arg10=(g.c,),
                ),
            )
        )
        # this routine only handles IRE_FLO
        self.include(PpLvlifMod(tc=self.tc, env=self.env, arg1=self.arg1))

        self.tc.enqueue(
            self.phase_eightteen,
            micro=self.env.micro,
            macro=self.env.macro,
            pgprim=self.env.pgprim,
        )

        # process bounds to see if aggregation is necessary
        # fmt: off
        pplvlbd_batincludes = [
            ("ACT_BND",    "P", '', '', '',          "PRC_TS", "RPS_PRCTS", "RTPS_BD", "EPS"),
            ("FLO_FR",     "P", "C,", '', ",''",     "RPCS_VAR", "RPCS_VAR", "UNCD7", "0"),
            ("COM_BNDNET", "C", '', '', ",'',''",    "COM_TS", "RCS_COMTS", "UNCD7"),
            ("COM_BNDPRD", "C", '', '', ",'',''",    "COM_TS", "RCS_COMTS", "UNCD7"),
            ("IRE_BND",    "C", '', 'ALL_R,IE,', '', "COM_TS", "RCS_COMTS", "UNCD7", "EPS"),

        ]
        # fmt: on
        for arg in pplvlbd_batincludes:
            self.include(
                PpLvlbdMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg[0],  # type: ignore[arg-type]
                    arg2=arg[1],  # type: ignore[arg-type]
                    arg3=arg[2],  # type: ignore[arg-type]
                    arg4=arg[3],  # type: ignore[arg-type]
                    arg5=arg[4],  # type: ignore[arg-type]
                    arg6=arg[5],  # type: ignore[arg-type]
                    arg7=arg[6],  # type: ignore[arg-type]
                    arg8=arg[7],  # type: ignore[arg-type]
                    arg9=arg[8] if len(arg) > 8 else "",  # type: ignore[arg-type]
                )
            )

        self.tc.enqueue(self.phase_nineteen, pgprim=self.env.pgprim)

        dam_elast_defined = self.tc.defined("DAM_ELAST")
        obj_eq_lin = self.env.obj.upper() == "LIN"
        self.tc.enqueue(
            self.phase_twenty,
            dam_elast_defined=dam_elast_defined,
            obj_eq_lin=obj_eq_lin,
            pgprim=self.env.pgprim,
        )

        # Levelization of STG_LOSS and STG_SIFT
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                config=PpLvlfcModConfig(
                    arg1=g.stg_loss,
                    arg2=(g.p,),
                    arg3=g.PrcTs,
                    arg4=(),
                    arg5=("0",) * 4,
                    arg6=g.s2,
                    arg7=(g.v,),
                    arg8=g.Rtp[g.r, g.v, g.p].where[
                        ~g.RpsStg[g.r, g.p, g.s].where[g.Trackp[g.r, g.p]]
                    ],
                ),
            )
        )
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                config=PpLvlfcModConfig(
                    arg1=g.stg_sift,
                    arg2=(g.p, g.c),
                    arg3=g.RpcsVar,
                    arg4=(),
                    arg5=("0",) * 3,
                    arg6=g.allts,
                    arg7=(g.t,),
                    arg8=g.Rtp[g.r, g.t, g.p],
                ),
            )
        )

        self.tc.enqueue(self.convert_equilibrium_losses_to_standard_losses)

        # User constraints
        # Default values
        self.include(PrepxtraMod(tc=self.tc, env=self.env, arg1="UCINT"))

        self.tc.enqueue(self.phase_twentyone)

        # Assigning commodities and processes to UC group map sets
        g.UcMapFlo = Set(
            m,
            name="UC_MAP_FLO",
            domain=[g.ucn, g.side, g.allreg, g.prc, g.Com],
            description="Assigning processes to UC_GRP",
        )
        g.UcMapIre = Set(
            m,
            name="UC_MAP_IRE",
            domain=[g.ucn, g.allreg, g.prc, g.Com, g.ie],
            description="Assigning processes to UC_GRP",
        )

        self.tc.enqueue(self.phase_twentytwo)

        # ...Handle UC_FLO/IRE/ACT/COM leveling by aggregation/inheritance
        # fmt: off
        pp_lvlus_batincludes: list[PpLvlusConfig] = [
            PpLvlusConfig(uc_parameter=g.uc_act, arg2=(g.p,), arg3=g.PrcTs, arg4=('0', '0'), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl),
            PpLvlusConfig(uc_parameter=g.uc_flo, arg2=(g.p, g.c), arg3=g.RpcsVar, arg4=('0',), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl, arg9=g.prc_sgl[g.r,g.p], arg10=(g.c,)),
            PpLvlusConfig(uc_parameter=g.uc_ire, arg2=(g.p, g.c), arg3=g.PrcTs, arg4=(), arg5=(g.ie,), arg6=(), arg7=g.p, arg8=g.PrcTsl),
            PpLvlusConfig(uc_parameter=g.uc_com, arg2=(g.c,), arg3=g.ComTs, arg4=(), arg5=(g.ucgrptype,), arg6=(g.comvar,), arg7=g.c, arg8=g.ComTsl),
        ]
        # fmt: on
        for config in pp_lvlus_batincludes:
            self.include(PpLvlusMod(tc=self.tc, env=self.env, config=config))

        self.tc.enqueue(
            self.control_set_for_balance_production_equations,
            validate=self.env.validate == "YES",
        )

        # *----------------------------------------------------------------------------*
        # *GG* V07_1 BLENDing equation
        # *----------------------------------------------------------------------------*
        # *******************************************************************************
        # *GG* V07_2  Create any Combined & Control Sets Needed for BLENDing Execution
        # *******************************************************************************
        g.BleSpe = Set(m, name="BLE_SPE", domain=[g.r, g.Com, g.spe])
        g.BleTp = Set(m, name="BLE_TP", domain=[g.r, g.allyear, "*"])
        g.BleSpeopr = Set(m, name="BLE_SPEOPR", domain=[g.r, g.Com, g.spe, g.Opr])
        g.BleOpr = Set(m, name="BLE_OPR", domain=[g.r, g.Com, g.Com])
        g.BleInp = Set(m, name="BLE_INP", domain=[g.r, g.Com, g.Com])
        g.BleSpeinp = Set(m, name="BLE_SPEINP", domain=[g.r, g.Com, g.spe, g.Com])
        g.BleEnv = Set(m, name="BLE_ENV", domain=[g.r, g.Com, g.Com, g.Opr])
        g.ble_bal = Parameter(m, name="BLE_BAL", domain=[g.r, g.year, g.c, g.c])

        self.tc.enqueue(self.phase_twentythree)

        # Coefficients for BLENDing
        g.opr2 = Alias(m, name="OPR2", alias_with=g.Opr)

        self.tc.enqueue(self.phase_twentyfour)

        self.include(PpReduceRed(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_twentyfive)

        # *----------------------------------------------------------------
        # * MACRO
        # *----------------------------------------------------------------
        if self.env.macro == "YES":
            self.include(PpmainTm(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_twenty_six)

    def control_set_for_balance_production_equations(
        self: PpmainMod, validate: bool
    ) -> None:
        """
        Control set for balance/production equations based on TS-resolution and RHS
        """
        g = self.tc
        r, c, s, lim, t = g.r, g.c, g.s, g.lim, g.t

        g.RcsCombal[r, t, c, s, lim].where[
            g.RtcsVarc[r, t, c, s] & g.ComLim[r, c, lim] & (~g.RhsCombal[r, t, c, s])
        ] = True
        g.RcsCombal[r, t, c, s, lim].where[
            lim.sameAs("FX") & g.RhsCombal[r, t, c, s]
        ] = True
        if validate:
            g.RhsComprd[r, t, c, s].where[g.RtcsVarc[r, t, c, s]] = True
        g.RcsComprd[r, t, c, s, lim].where[
            lim.sameAs("FX") & g.RhsComprd[r, t, c, s]
        ] = True

    def convert_equilibrium_losses_to_standard_losses(self: PpmainMod) -> None:
        """Convert equilibrium losses into standard losses for IPS, and adjust all losses by year fractions"""
        g = self.tc
        g.stg_loss[g.Rtp[g.r, g.v, g.p], g.s[g.tsl]].where[
            (
                (abs(g.stg_loss[g.Rtp, g.s] * 2.0 - 1.0) >= 1.0).where[
                    g.PrcMap[g.r, "STK", g.p]
                ]
            )
        ] = 1.0 - exp(-(abs(g.stg_loss[g.Rtp, g.s])))
        g.stg_loss[g.Rtp[g.r, g.v, g.p], g.s].where[
            (g.stoa[g.s].where[g.stg_loss[g.Rtp, g.s]])
        ] = log(
            exp(g.stg_loss[g.Rtp, g.s] * g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s])
        )
        g.Trackp.setRecords(None)
        g.Trackpc.setRecords(None)

    def deactivate_rpc_noflo(self: PpmainMod) -> None:
        g = self.tc
        g.RpcNoflo[g.Rmkc[g.Rpc]] = False
        # *-----------------------------------------------------------------------------
        # * inter-regional exchange related attributes
        # *-----------------------------------------------------------------------------
        g.putgrp[...] = 0.0

    def activate_rtc_net(self: PpmainMod) -> None:
        g = self.tc
        g.RtcNet[g.Rtc[g.r, g.t, g.c]].where[~(g.ComTsl[g.r, g.c, "ANNUAL"])] = True

    def adjust_shape(self: PpmainMod) -> None:
        g = self.tc
        g.shape["1", g.age].where[(Ord(g.age) <= g.startoff)] = 1.0

        g.shape[g.j, g.age].where[
            ((g.shape[g.j, g.age] == 0.0).where[g.shape[g.j, g.age]])
        ] = 0.0

    def activate_rtp_cptyr(self: PpmainMod) -> None:
        g = self.tc
        g.RtpCptyr[g.r, g.t, g.t, g.p].where[g.Rtp[g.r, g.t, g.p]] = True

    def phase_one(self: PpmainMod, pgprim: str) -> None:
        g = self.tc
        # * Establish set of main currencies by region (for which discount rate provided)
        with Loop(
            Domain(g.r, g.ll[g.bohyear], g.cur).where[g.g_drate[g.r, g.ll, g.cur]]
        ):
            g.Rdcur[g.r, g.cur] = True
        # *-----------------------------------------------------------------------------
        # * establish initial primary looping control sets indicating what region/process/commodities
        # *-----------------------------------------------------------------------------
        # * process/commodities in each region, including inter-regional exchanges
        g.PrcActunt[g.r, g.p, pgprim, g.UnitsAct] = False
        project(source=g.TopIre, target=g.RpcAire)
        g.RpcIre[g.RpcAire, "IMP"] = True
        project(source=g.TopIre, target=g.RpcAire, direction="left")
        g.RpcIre[g.RpcAire, "EXP"] = True
        g.RpcAire.setRecords(None)
        project(source=g.PrcActunt, target=g.PrcAct)
        g.RpIre[g.allr, g.p].where[Sum(g.RpcIre[g.allr, g.p, g.c, g.ie], 1)] = True
        g.Top[g.RpIre[g.r, g.p], g.c, "IN"].where[g.RpcIre[g.r, g.p, g.c, "EXP"]] = (
            False
        )
        g.Top[g.RpIre[g.r, g.p], g.c, "OUT"].where[g.RpcIre[g.r, g.p, g.c, "IMP"]] = (
            False
        )
        g.Top[g.RpgRed[g.PrcAct[g.r, g.p], g.c, g.io]].where[
            (g.ComTmap[g.r, "ENV", g.c] + g.RpIre[g.r, g.p])
        ] = True
        # * process/commodities in each region
        g.Rpc[g.r, g.p, g.c].where[
            (Sum(g.Top[g.r, g.p, g.c, g.io], 1) + Sum(g.RpcIre[g.r, g.p, g.c, g.ie], 1))
        ] = True
        g.Rc[g.r, g.c].where[Sum(g.Rpc[g.r, g.p, g.c], 1)] = True
        g.Rp[g.r, g.p].where[Sum(g.Rpc[g.r, g.p, g.c], 1)] = True
        g.RpFlo[g.Rp].where[~(g.RpIre[g.Rp])] = True

        # * establish PCG, checking for missing ones
        project(source=g.PrcActunt, target=g.RpPg)
        g.RpgRed.setRecords(None)
        g.PrcAct.setRecords(None)
        g.PrcAct[g.Rp].where[~(Sum(g.RpPg[g.Rp, g.cg], 1.0))] = True
        if g.PrcAct.number_records:
            g.Trackpc[g.PrcAct[g.r, g.p], g.c].where[
                (
                    ~(g.ComTmap[g.r, "ENV", g.c] + g.ComTmap[g.r, "FIN", g.c]).where[
                        g.Top[g.r, g.p, g.c, "OUT"]
                    ]
                )
            ] = True
            g.PrcAct[g.Rp].where[(Sum(g.Trackpc[g.Rp, g.c], 1.0) != 1.0)] = False
            g.RpPg[g.Trackpc[g.PrcAct, g.c]] = True
            g.PrcAct.setRecords(None)
            g.Trackpc.setRecords(None)
        # * add groupings by type
        g.ComGmap[g.ComTmap] = True
        # *-----------------------------------------------------------------------------
        # * Establish missing sets for storage processes
        # *  - assumption: stored commodities should be members of the PG
        # *-----------------------------------------------------------------------------
        # * Prohibit special storage commodities
        g.Trackc[g.r, g.c].where[g.ComLim[g.r, g.c, "N"]] = True
        g.Trackc[g.r, pgprim] = True
        # * Defaults for stored commodity
        g.RpSts[g.r, g.p].where[g.PrcMap[g.r, "STS", g.p]] = True
        g.Trackp[g.r, g.p].where[
            (g.PrcMap[g.r, "STG", g.p] + g.PrcMap[g.r, "STK", g.p] + g.RpSts[g.r, g.p])
        ] = True
        g.Trackp[g.r, g.p].where[Sum(g.PrcStgtss[g.r, g.p, g.c], 1.0)] = False
        g.Trackp[g.r, g.p].where[Sum(g.PrcNstts[g.r, g.p, g.s], 1.0)] = False
        g.Trackpc[g.Trackp[g.r, g.p], g.c].where[
            Sum(
                Domain(g.Top[g.r, g.p, g.c, g.io], g.RpPg[g.r, g.p, g.cg]).where[
                    g.ComGmap[g.r, g.cg, g.c]
                ],
                1.0,
            )
        ] = True
        g.Trackpc[g.Trackp[g.r, g.p], g.c].where[
            Sum(g.RpPg[g.r, g.p, g.c].where[~(g.Trackc[g.r, g.c])], 1.0)
        ] = True
        # * Auto-generate missing charge/discharge flow
        g.RpcStgn[g.Top[g.Trackp[g.r, g.p], g.c, g.io]].where[
            Sum(
                Domain(
                    g.ComGmap[g.r, g.ComType[g.cg], g.c], g.Trackpc[g.r, g.p, g.Com]
                ).where[g.ComGmap[g.r, g.cg, g.Com]],
                1.0,
            )
        ] = True
        project(source=g.flo_func, target=g.CgGrp)
        g.RpcStgn[g.Rp, g.c, g.io].where[
            Sum(g.RpcStgn[g.Trackpc[g.Rp, g.Com], g.io], 1)
        ] = False
        with Loop(g.CgGrp[g.Trackp[g.Rp], g.c, g.Com]):
            with If(g.Trackpc[g.Rp, g.c]):
                g.RpcStgn[g.Rp, g.Com, g.io] = False
            with ElseIf(g.Trackpc[g.Rp, g.Com]):
                g.RpcStgn[g.Rp, g.c, g.io] = False
        g.Trackpc[g.Rpc] = sparse(Sum(g.RpcStgn[g.Rpc, g.io], 1))
        # * day-night storage
        with Loop(g.PrcNstts[g.r, g.p, g.s]):
            g.PrcMap[g.r, "STG", g.p] = True
            g.PrcMap[g.r, "NST", g.p] = True
            g.PrcMap[g.r, "STK", g.p] = False
        # * inter-period storage
        g.PrcStgips[g.Trackpc[g.r, g.p, g.c]].where[g.PrcMap[g.r, "STK", g.p]] = True
        with Loop(g.PrcStgips[g.r, g.p, g.c]):
            g.PrcMap[g.r, "STG", g.p] = True
            g.PrcMap[g.r, "STK", g.p] = True
            g.PrcMap[g.r, "NST", g.p] = False
            with If(~(Sum(g.Top[g.r, g.p, g.c, g.io], 1))):
                g.Top[g.r, g.p, g.c, g.io] = True
            with If(~(g.RpSts[g.r, g.p])):
                g.PrcTsl[g.r, g.p, g.tslvl] = g.tslvl.sameAs("ANNUAL")  # type: ignore[assignment]
        # * time-slice storage
        g.PrcStgtss[g.Trackpc[g.r, g.p, g.c]].where[~(g.PrcMap[g.r, "STK", g.p])] = True
        with Loop(g.PrcStgtss[g.r, g.p, g.c]):
            g.PrcMap[g.r, "STG", g.p] = True
            g.PrcMap[g.r, "STS", g.p] = True
            g.PrcMap[g.r, "NST", g.p] = False
            g.PrcMap[g.r, "STK", g.p] = False
            with If(~(Sum(g.Top[g.r, g.p, g.c, g.io], 1))):
                g.Top[g.r, g.p, g.c, g.io] = True
        g.Trackc.setRecords(None)
        g.Trackp.setRecords(None)
        g.Trackpc.setRecords(None)
        g.CgGrp.setRecords(None)
        g.RpcStgn.setRecords(None)
        # * If storage is input- or output-based, define it such
        g.RpcStgn[g.PrcStgtss[g.r, g.p, g.c], g.io].where[
            ~(
                Sum(
                    g.Top[g.r, g.p, g.Com, g.io].where[g.PrcStgtss[g.r, g.p, g.Com]],
                    1.0,
                )
            )
        ] = True
        g.RpcStgn[g.PrcStgips[g.r, g.p, g.c], g.io].where[
            ~(
                Sum(
                    g.Top[g.r, g.p, g.Com, g.io].where[g.PrcStgips[g.r, g.p, g.Com]],
                    1.0,
                )
            )
        ] = True
        g.Top[g.RpcStgn] = True

    def phase_two(self: PpmainMod) -> None:
        g = self.tc
        project(source=g.ncap_pasty, target=g.PrcCap)
        with Loop(
            Domain(g.PrcCap[g.Rp[g.r, g.p]], g.Pastyear[g.ll]).where[
                (g.ncap_pasty[g.r, g.Pastyear, g.p] > 1.0)
            ]
        ):
            g.f[...] = g.ncap_pasty[g.r, g.ll, g.p]
            g.my_f[...] = g.ncap_pasti[g.r, g.ll, g.p] / g.f
            # * for each year within spread build running sum of distributed PASTIs
            with For(g.z, g.f - 1.0, 0.0, direction="downto"):
                g.pastsum[g.r, g.allyear[g.ll - g.z], g.p] = (
                    g.pastsum[g.r, g.allyear, g.p] + g.my_f
                )
            # * since spread this guy, clear original value
            g.ncap_pasti[g.r, g.ll, g.p] = 0.0
        # * add any spread past investments to any provided originally (and not spread)
        g.ncap_pasti[g.r, g.ll, g.p].where[g.pastsum[g.r, g.ll, g.p]] = (
            g.ncap_pasti[g.r, g.ll, g.p] + g.pastsum[g.r, g.ll, g.p]
        )
        # * extend the list of past years
        project(source=g.ncap_pasti, target=g.Pastyear)

    def phase_two_two(self: PpmainMod) -> None:
        g = self.tc
        g.intdefault["PASTI"].where[g.pyr["0"]] = 1.0
        g.pyr["0"] = False
        g.PrcCap.setRecords(None)
        g.pastsum.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * determination of YEAR subsets and period B/E/D
        # *-----------------------------------------------------------------------------
        # * 98/02/23 middle year of period M(T) from *.dd to ppmain.mod
        # * [UR]: duration of period moved from *.dd to ppmain.mod
        g.d[g.Milestonyr] = g.e[g.Milestonyr] - g.b[g.Milestonyr] + 1.0
        g.m[g.Milestonyr] = floor(g.b[g.Milestonyr] + (g.d[g.Milestonyr] - 1.0) / 2.0)

    def set_mt_zero(self: PpmainMod) -> None:
        g = self.tc
        g.m[g.t] = 0.0

    def g_offthd_to_zero(self: PpmainMod) -> None:
        self.tc.g_offthd["0"] = 0.0

    def phase_three(self: PpmainMod, condition: bool) -> None:
        g = self.tc
        if g.altobj.toValue() == 1.0:
            g.altobj[...] = Number(1.0).where[Sum(g.t, g.m[g.t] != g.yearval[g.t])]
        # * establish 1st/last run year
        g.Miyr1[g.t].where[(Ord(g.t) == 1.0)] = True
        if g.altobj.toValue():
            # * If alternate objective, set B and E, D and M:
            g.e[g.t[g.tt - 1]] = floor((g.yearval[g.t] + g.yearval[g.tt]) / 2.0)
            g.b[g.t[g.tt + 1]] = g.e[g.tt] + 1.0
            g.b[g.Miyr1[g.t]].where[(abs(g.b[g.t] - (g.yearval[g.t] - 5.0)) > 5.0)] = (
                g.yearval[g.t]
            )
            g.e[g.t].where[
                (
                    (abs(g.e[g.t] - (g.yearval[g.t] + 15.0)) > 15.0).where[
                        (Ord(g.t) == Card(g.t))
                    ]
                )
            ] = (
                2.0 * g.yearval[g.t]
                - g.b[g.t]
                + 1.0
                - Number(1.0).where[mod(g.yearval[g.t] - g.b[g.t] + 1.0, 5.0)]
            )
            g.d[g.t] = g.e[g.t] - g.b[g.t] + 1.0
            g.m[g.t] = g.yearval[g.t]
        # *V0.5c 980904 - set 1st value to B not milestone itself
        g.miyr_v1[...] = Smin(g.Miyr1, g.b[g.Miyr1])
        g.miyr_vl[...] = Smax(g.t.where[(Ord(g.t) == Card(g.t))], g.e[g.t])
        if condition and (
            (g.miyr_v1 + Sum(g.t, g.e[g.t] + 1.0 - g.b[g.t]) - g.miyr_vl).toValue()
            != 1.0
        ):
            raise Exception("Inconsistent periods - cannot use OBLONG.")

        with Loop(g.Miyr1[g.ll]):
            g.Pastyear[g.ll.lag(g.yearval[g.ll] - g.miyr_v1 + 1)] = True

        # * Set LEADs and LAGs for periods
        g.lead[g.tt[g.t.lead(1, "circular")]] = Max(
            g.m[g.tt] - g.m[g.t], g.m[g.tt] - g.b[g.tt] + 1.0
        )
        g.lagt[g.tt[g.t.lag(1, "circular")]] = Max(
            g.m[g.t] - g.m[g.tt], g.e[g.tt] - g.m[g.tt] + 1.0
        )
        if g.altobj.toValue():
            g.ipd[g.t] = (
                g.lead[g.t]
                + Min(g.e[g.t] - g.m[g.t], g.lead[g.t] - 1.0).where[g.Miyr1[g.t]]
            )
        else:
            g.ipd[g.t] = g.d[g.t]
        g.fpd[g.t] = g.d[g.t]

    def phase_four(self: PpmainMod) -> None:
        g = self.tc
        g.minyr[...] = Min(g.miyr_v1 - 1.0, Smin(g.t, g.m[g.t] - g.ipd[g.t]) + 1.0)
        g.pyr_v1[...] = Min(Smin(g.Pastyear, g.yearval[g.Pastyear]), g.minyr)
        # * Define MIYR_L
        with Loop(g.Miyr1[g.allyear]):
            g.z[...] = g.miyr_vl - g.yearval[g.allyear]
            g.MiyrL[g.allyear + g.z] = True
        # * establish the beginning/end/delta for each MILESTONYR
        # * introduce PASTMILE (PASTYEAR that are not MILESTONYR)
        # * set the past years to self
        g.Pastmile[g.Pastyear].where[
            ((g.yearval[g.Pastyear] <= g.miyr_vl).where[~(g.t[g.Pastyear])])
        ] = True
        g.m[g.Pastmile] = g.yearval[g.Pastmile]
        g.b[g.Pastmile] = g.m[g.Pastmile]
        g.e[g.Pastmile] = g.m[g.Pastmile]
        g.d[g.Pastmile] = 1.0
        # *-----------------------------------------------------------------------------
        # * set EOHYEARS contains all years until MIYR_VL
        g.Eohyears[g.allyear].where[
            ((g.yearval[g.allyear] >= g.minyr) * (g.yearval[g.allyear] <= g.miyr_vl))
        ] = True
        # * create list of all years in each period
        g.Periodyr[g.t, g.Eohyears].where[
            ((g.yearval[g.Eohyears] >= g.b[g.t]) * (g.yearval[g.Eohyears] <= g.e[g.t]))
        ] = True

    def phase_five(self: PpmainMod, botime: int) -> None:
        g = self.tc
        # * Migrate PASTIs defined on Milestonyr if requested
        if g.intdefault["PASTI"].toValue():
            with Loop(g.pyr[g.t[g.ll]].where[(g.m[g.t] > g.b[g.t])]):
                g.Vnt[g.ll - 1, g.t] = True
            with Loop(g.Vnt[g.ll, g.t]):
                g.b[g.ll] = g.m[g.t] - 1.0
                g.e[g.ll] = g.m[g.t]
                g.m[g.ll] = g.b[g.ll]
                g.d[g.ll] = 2.0
                g.Pastyear[g.t] = False
                g.pastsum[g.r, g.t, g.p].where[g.ncap_pasti[g.r, g.t, g.p]] = (
                    g.ncap_pasti[g.r, g.ll, g.p]
                    + g.ncap_pasti[g.r, g.t, g.p]
                    + 1.0
                    - 1.0
                )
                g.coef_rtp[g.r, g.ll, g.p].where[g.pastsum[g.r, g.t, g.p]] = (
                    g.ncap_pasti[g.r, g.t, g.p] / g.pastsum[g.r, g.t, g.p]
                )
                g.ncap_pasti[g.r, g.ll, g.p] = sparse(g.pastsum[g.r, g.t, g.p])
                g.ncap_pasti[g.r, g.t, g.p] = 0.0
                g.pastsum.setRecords(None)
            g.Vnt[g.Pastmile, g.t].where[g.Periodyr[g.t, g.Pastmile]] = True
            project(source=g.Vnt, target=g.Phyr, direction="left")
            g.pyr[g.Phyr] = True
            g.Pastmile[g.Phyr] = True
        # *-----------------------------------------------------------------------------
        # * initialize start/end year for new investments
        # *V0.5c 980904 - use OFF instead of START/END
        # *-----------------------------------------------------------------------------
        g.putgrp[...] = 0.0
        # * Convert START to NOFF
        with Loop(g.Lastll[g.ll].where[Card(g.ncap_start)]):  # type: ignore
            g.z[...] = Card(g.ll) + botime
            g.PrcNoff[g.Rp, "BOH", g.eohyear].where[g.ncap_start[g.Rp]] = False
            g.PrcNoff[g.Rp, "BOH", g.ll + Min(-(1.0), g.ncap_start[g.Rp] - g.z)].where[
                g.ncap_start[g.Rp]
            ] = True
        # * Construct year sets for the active model horizon
        g.prc_ymax.setRecords(None)
        g.uncd1.setRecords(None)
        g.uncd1["BOH"] = True
        g.uncd1[g.year].where[(g.yearval[g.year] <= g.miyr_v1)] = True
        g.prc_ymax[g.Rp[g.r, g.p]] = Max(
            0.0,
            Smax(
                g.PrcNoff[g.r, g.p, g.bohyear[g.uncd1], g.eohyear],
                Ord(g.eohyear) + botime - 2.0,
            ),
        )
        # * Set RTP_OFF for delayed processes
        g.Trackp[g.Rp] = sparse(g.prc_ymax[g.Rp])
        g.RtpOff[g.r, g.t, g.p].where[
            ((g.yearval[g.t] <= g.prc_ymax[g.r, g.p]).where[g.Trackp[g.r, g.p]])
        ] = (g.prc_ymax[g.r, g.p] - g.b[g.t] + 1.0) / g.d[g.t] >= g.g_offthd[g.t]
        g.prc_ymax[g.Trackp[g.r, g.p]] = Smax(g.RtpOff[g.r, g.t, g.p], g.e[g.t])

    def check_ncap_pasti(self: PpmainMod) -> None:
        g = self.tc

        violations = ncap_pasti_violations(g)
        g.pp_qaput_logger.log_violations(
            violations_df=violations.records,
            err_level=1,
            group_desc="Delayed Process but PASTInvestment",
            message_template="WARNING       - Delay is ignored: R={R} P={P}",
        )

        # * the delay is ignored for processes that also carry a legacy PAST investment: PRC_YMAX(R,P) = 0
        g.prc_ymax[g.r, g.p].where[violations[g.r, g.p]] = 0.0

        g.Trackp.setRecords(None)

    def set_rtp_off(self: PpmainMod) -> None:
        g = self.tc
        g.uncd1[g.bohyear] = ~(g.uncd1[g.bohyear])
        with Loop(g.PrcNoff[g.Rp[g.r, g.p], g.bohyear[g.uncd1], g.eohyear]):
            g.Trackp[g.r, g.p] = True
        with Loop(g.Trackp[g.r, g.p]):
            pp_off_GP(g, g.PrcNoff, (g.p,), Number(1), g.RtpOff[g.r, g.t, g.p], 1)
        g.Rtp[g.r, g.t, g.p].where[g.Rp[g.r, g.p]] = Number(1).where[
            (g.yearval[g.t] > g.prc_ymax[g.r, g.p])
        ]
        g.Rtp[g.r, g.pyr, g.p].where[
            (
                g.Rp[g.r, g.p].where[
                    (g.ncap_pasti[g.r, g.pyr, g.p] > 0.0)
                    & g.ncap_pasti[g.r, g.pyr, g.p]
                ]
            )
        ] = True
        g.Rvp[g.Rtp[g.r, g.t, g.p]] = True
        g.Trackp.setRecords(None)

    def phase_six(self: PpmainMod, ctst: Literal["", "**EPS", "**0", "1"]) -> None:
        g = self.tc

        g.RtPp[g.r, g.t] = True
        # * maximum NCAP_ILED+NCAP_TLIFE+NCAP_DLAG+NCAP_DLIFE+NCAP_DELIF
        g.dur_max[...] = Max(
            g.g_tlife,
            Smax(
                g.Rvp[g.r, g.t, g.p],
                g.ncap_iled[g.Rvp]
                + g.ncap_tlife[g.Rvp]
                + g.ncap_dlag[g.Rvp]
                + g.ncap_dlife[g.Rvp]
                + g.ncap_delif[g.Rvp],
            ),
        )
        # * add PASTYEAR to EOHYEARS before 1st period
        g.Eohyears[g.pyr].where[(g.yearval[g.pyr] < g.minyr)] = True
        # * establish EACHYEAR: goes until (MIYR_VL+DUR_MAX)
        g.Eachyear[g.Pastyear] = True
        g.Eachyear[g.allyear].where[
            (
                (g.yearval[g.allyear] >= g.minyr)
                * (g.yearval[g.allyear] <= (g.miyr_vl + g.dur_max))
            )
        ] = True
        # * LATECOSTS
        g.Periodyr[g.t, g.Eachyear].where[
            ((g.e[g.t] == g.miyr_vl) * (g.yearval[g.Eachyear] >= g.miyr_vl))
        ] = True
        # *-----------------------------------------------------------------------------
        # * establish rest of primary looping control sets indicating what region/process/commodities
        # *-----------------------------------------------------------------------------
        # * expand individual commodities in own CG
        g.MiDmas[g.ComGmap[g.Rc, g.c]] = True
        g.MiDmas[g.r, g.c, g.c] = False
        if g.MiDmas.number_records:
            project(source=g.Top, target=g.Dem)
            g.putgrp[...] = 0.0

            mi_dmas_violations = mi_dmas_topology_violations(g=g)
            g.pp_qaput_logger.log_violations(
                violations_df=mi_dmas_violations.records,
                err_level=9,
                group_desc=(
                    "Commodity group found in topology violating its integrity"
                ),
                message_template=(
                    "SEVERE ERROR  - Group removed from topology:   R={R} CG={C}"
                ),
            )

            project(source=g.MiDmas, target=g.Dem, direction="left")
            g.Rc[g.Dem] = False
            g.Rpc[g.r, g.p, g.c].where[g.Dem[g.r, g.c]] = False
            g.MiDmas.setRecords(None)
            g.Dem.setRecords(None)
        g.ComGmap[g.Rc[g.r, g.c], g.c] = True
        g.NrgGmap[g.r, g.nrggrid[g.nrgtype], g.c] = sparse(
            g.NrgTmap[g.r, g.nrgtype, g.c]
        )
        # * UR 02/22/99 PRC_CG is now internally generated
        g.PrcCg[g.Rpc] = True
        g.PrcCg[g.RpPg] = True
        # * Add aggregate commodities into RC
        project(source=g.com_agg, target=g.MiDmas, direction="left")
        project(source=g.ComTmap, target=g.Fin)
        with Loop(
            g.MiDmas[g.r, g.Com, g.c].where[(g.Fin[g.r, g.Com].where[g.Fin[g.r, g.c]])]
        ):
            g.Rc[g.r, g.c] = True
        g.Fin.setRecords(None)
        g.MiDmas.setRecords(None)
        # * determination of capacity related flows - initialization
        g.RpcCapflo[g.Rtp, g.c].where[
            (g.ncap_icom[g.Rtp, g.c] + g.ncap_ocom[g.Rtp, g.c])
        ] = True
        g.RpcCapflo[g.Rtp, g.c] = sparse(
            Sum(g.io.where[g.ncap_com[g.Rtp, g.c, g.io]], 1.0)
        )
        project(source=g.RpcCapflo, target=g.RpcNoflo)
        with Loop(g.RpcNoflo[g.r, g.p, g.c].where[~(g.Rc[g.r, g.c])]):
            g.Rc[g.r, g.c] = True
        # *-----------------------------------------------------------------------------
        # * process/commodity relationships
        # *-----------------------------------------------------------------------------
        # * primary group & commodities in primary group
        g.RpcPg[g.Rpc[g.r, g.p, g.c]].where[
            Sum(g.RpPg[g.r, g.p, g.cg].where[g.ComGmap[g.r, g.cg, g.c]], 1.0)
        ] = True
        g.RpcPg[g.RpIre[g.r, g.p], g.c].where[
            ~(g.RpcIre[g.r, g.p, g.c, "IMP"] + g.RpcIre[g.r, g.p, g.c, "EXP"])
        ] = False
        # * endorse STG level
        g.RpcPg[g.PrcStgtss[g.Rp, g.c]].where[
            Sum(g.PrcTsl[g.Rp, g.tsl].where[(Ord(g.tsl) > 1.0)], 1.0)
        ] = True
        g.RpPgtype[g.Rp[g.r, g.p], g.ComType].where[
            Sum(g.RpcPg[g.r, g.p, g.c].where[g.ComTmap[g.r, g.ComType, g.c]], 1.0)
        ] = True
        g.RpAire[g.RpIre[g.Rp], g.ie].where[
            Sum(g.RpcIre[g.RpcPg[g.Rp, g.c], g.ie], 1.0)
        ] = True
        # * input/output normalized process
        g.RpInout[g.Rp, g.io].where[Sum(g.Top[g.RpcPg[g.Rp, g.c], g.io], 1.0)] = True
        # * determine shadow primary if not provided - for regular processes only (RP_FLO)
        g.Trackp[g.RpFlo[g.Rp]].where[~(Sum(g.PrcSpg[g.Rp, g.comgrp], 1.0))] = True
        with Loop(  # noqa: SIM117
            Domain(g.RpPgtype[g.RpFlo[g.r, g.p], g.cg], g.io).where[
                ~(g.RpInout[g.r, g.p, g.io])
            ]
        ):
            with If(g.Trackp[g.r, g.p]):
                # * set the SPG to the same type as the PG if commodities on the other side with that COM_TYPE
                with If(
                    Sum(
                        g.Top[g.r, g.p, g.c, g.io].where[g.ComGmap[g.r, g.cg, g.c]], 1.0
                    )
                ):
                    g.PrcSpg[g.r, g.p, g.cg] = True
                with Else():
                    # * did not find any commodities with the same type as the PG, so assume energy
                    # * assume material if PRC is material conversion and PGTYPE is DEM
                    with If(
                        Sum(
                            g.Rpc[g.r, g.p, g.c].where[g.ComTmap[g.r, "MAT", g.c]],
                            1.0,
                        ).where[
                            Sum(g.PrcMap[g.r, g.Matprc, g.p], 1.0)
                            & g.RpPgtype[g.r, g.p, "DEM"]
                        ]
                    ):
                        g.PrcSpg[g.r, g.p, "MAT"] = True
                    with Else():
                        g.z[...] = 1.0
                        with Loop(g.PgSmap[g.cg, g.j, g.ComType].where[g.z]):  # noqa: SIM117
                            with If(
                                Sum(
                                    g.Top[g.r, g.p, g.c, g.io].where[
                                        g.ComTmap[g.r, g.ComType, g.c]
                                    ],
                                    1.0,
                                )
                            ):
                                g.z[...] = 0.0
                                g.PrcSpg[g.r, g.p, g.ComType] = True
        # * Add commodities in SPG into RPC_SPG
        with Loop(
            Domain(g.PrcSpg[g.r, g.p, g.cg], g.io).where[~(g.RpInout[g.r, g.p, g.io])]
        ):
            g.RpcSpg[g.r, g.p, g.c].where[
                (g.Top[g.r, g.p, g.c, g.io].where[g.ComGmap[g.r, g.cg, g.c]])
            ] = True
        g.PrcCg[g.PrcSpg] = True
        g.Trackp.setRecords(None)

        # *-----------------------------------------------------------------------------
        # * set level and timeslices for each commodity
        # *   - if individual TS provided and no TSL then use TSs to set TSL
        # *     else set the TS from TSL if none provided
        # *-----------------------------------------------------------------------------

        # * remove invalid levels
        g.Rxx.setRecords(None)
        g.Rxx[g.r, g.tsl, g.r].where[~(Sum(g.Rjlvl[g.j, g.r, g.tsl], 1.0))] = True
        g.f[...] = Card(g.ComTsl)
        g.z[...] = Card(g.PrcTsl)
        g.ComTsl[g.r, g.c, g.tsl - 1].where[g.Rxx[g.r, g.tsl, g.r]] = sparse(
            g.ComTsl[g.r, g.c, g.tsl]
        )
        g.f[...] = Card(g.ComTsl) - g.f
        g.ComTsl[g.r, g.c, g.tsl].where[(g.Rxx[g.r, g.tsl, g.r].where[g.f])] = False
        g.PrcTsl[g.r, g.p, g.tsl - 1].where[g.Rxx[g.r, g.tsl, g.r]] = sparse(
            g.PrcTsl[g.r, g.p, g.tsl]
        )
        g.z[...] = Card(g.PrcTsl) - g.z
        g.PrcTsl[g.r, g.p, g.tsl].where[(g.Rxx[g.r, g.tsl, g.r].where[g.z])] = False

        g.pp_qaput_logger.log_violations(
            violations_df=tslvl_reset_violations_df(g.f.toValue(), g.z.toValue()),
            err_level=1,
            group_desc="Commodities/processes defined at non-existing TSLVL",
            message_template=(
                "WARNING       - Number of COM/PRC resetted to coarser level: {F}/{Z}"
            ),
        )

        # * check for individual TS provided
        g.Trackc[g.Rc] = sparse(Sum(g.ComTs[g.Rc, g.s], 1.0))
        with Loop(
            g.ComTs[g.Rc[g.r, g.c], g.s].where[~(Sum(g.ComTsl[g.Rc, g.tsl], 1.0))]
        ):
            g.ComTsl[g.Rc, g.tsl].where[g.TsGroup[g.r, g.tsl, g.s]] = True
        # * check for excess or missing COM_TS
        with Loop(
            g.ComTsl[g.Trackc[g.r, g.c], g.tslvl].where[
                (
                    Sum(g.TsGroup[g.r, g.tslvl, g.s], 1.0)
                    != Sum(g.ComTs[g.r, g.c, g.s], 1.0)
                )
            ]
        ):
            g.ComTs[g.r, g.c, g.s].where[~(g.TsGroup[g.r, g.tslvl, g.s])] = False
            g.Rcs[g.r, g.c, g.s].where[
                (
                    ~(
                        Sum(
                            g.ComTs[g.r, g.c, g.ts].where[g.RsTree[g.r, g.s, g.ts]], 1.0
                        )
                    ).where[g.g_yrfr[g.r, g.s]]
                )
            ] = True
        g.ComTsl[g.Rc, "ANNUAL"].where[~(Sum(g.ComTsl[g.Rc, g.tsl], 1.0))] = True
        # *GG/UR make sure to init all S
        with Loop(g.ComTsl[g.Rc[g.r, g.c], g.tsl].where[~(g.Trackc[g.Rc])]):
            g.ComTs[g.Rc, g.s].where[g.TsGroup[g.r, g.tsl, g.s]] = True
        # * identify all TS at/above the COM_TSL
        g.RcsComts[g.Rc[g.r, g.c], g.s].where[
            Sum(g.TsMap[g.r, g.s, g.ts].where[g.ComTs[g.Rc, g.ts]], 1.0)
        ] = True
        # * determine the spread of periods/slices for the commodities
        g.Trackc.setRecords(None)
        with Loop(g.ComOff[g.Rc, g.bohyear, g.eohyear]):
            g.Trackc[g.Rc] = True
        g.Rtc[g.r, g.t, g.c].where[g.Rc[g.r, g.c]] = True
        with Loop(g.Trackc[g.r, g.c]):
            # * set the OFF range
            pp_off_GP(g, g.ComOff, (g.c,), Number(1), g.Rtc[g.r, g.t, g.c], 0)
            # * create a variable for VAR_COM for desired timeslices unless period turned off
            g.com_bndprd[g.r, g.t, g.c, g.s, "FX"].where[
                (g.ComTs[g.r, g.c, g.s].where[~(g.Rtc[g.r, g.t, g.c])])
            ] = SpecialValues.EPS
        g.RtcsVarc[g.Rtc[g.r, g.t, g.c], g.s].where[g.ComTs[g.r, g.c, g.s]] = True
        g.Trackc.setRecords(None)

        # * Peaking
        # * a) Time-slices specified on COM_PKTS must be on COM_TSLevel
        # * b) if no COM_PKTS is specified but COM_PEAK given, for all COM_TS
        # *    COM_PKTS will be set and hence peaking equations generated
        # *GG*PK 1st check if COM_PKTS has been specified at different level, then set if not provided at all
        # *UR*PK 1) com_peak is set if at least one com_pkts exists
        # *      2) if com_peak and com_pkts above com_ts => com_pkts is inherited
        # *         if at least one com_pkts below com_ts => com_pkts is aggregated
        # *      3) if com_peak but no com_pkts           => com_pkts for all com_ts

        # * set com_peak when com_pkts
        g.ComPeak[g.r, g.cg].where[Sum(g.ComPkts[g.r, g.cg, g.s], 1.0)] = 1.0
        g.Trackc[g.ComPeak[g.r, g.c]].where[~(Sum(g.ComTsl[g.r, g.c, g.tsl], 1.0))] = (
            True
        )
        with Loop(g.Annual[g.ts[g.tsl]]):
            g.ComTsl[
                g.Trackc[g.r, g.c],
                g.tsl + Smax(g.ComPkts[g.r, g.c, g.s], g.stoal[g.r, g.s]),
            ] = True
        g.Trackc.setRecords(None)
        # * inherit to the COM_TS level if necessary
        g.ComPkts[g.ComPeak[g.r, g.c], g.s].where[
            Sum(g.ComPkts[g.r, g.c, g.ts].where[g.RsTree[g.r, g.s, g.ts]], 1.0)
        ] = Sum(g.ComTsl[g.r, g.c, g.tsl], Ord(g.tsl) == g.stoal[g.r, g.s] + 1.0)
        # * if nothing then set for all
        with Loop(g.ComPeak[g.r, g.cg].where[~(Sum(g.ComPkts[g.r, g.cg, g.s], 1.0))]):
            g.z[...] = Smax(
                g.ComTsl[g.r, g.c, g.tsl].where[g.ComGmap[g.r, g.cg, g.c]],
                g.tslvlnum[g.tsl],
            )
            with Loop(g.tsl.where[(g.tslvlnum[g.tsl] == g.z)]):
                g.ComPkts[g.r, g.cg, g.s].where[g.TsGroup[g.r, g.tsl, g.s]] = True

        # *-----------------------------------------------------------------------------
        # * set level and timeslices for each process
        # *   - if individual TS provided and no TSL then use TSs to set TSL
        # *     else set the TS from TSL if none provided
        # *-----------------------------------------------------------------------------
        with Loop(
            g.PrcTs[g.Rp[g.r, g.p], g.s].where[~(Sum(g.PrcTsl[g.Rp, g.tsl], 1.0))]
        ):
            g.PrcTsl[g.Rp, g.tsl].where[g.TsGroup[g.r, g.tsl, g.s]] = True
        g.PrcTsl[g.Rp, "ANNUAL"].where[~(Sum(g.PrcTsl[g.Rp, g.tsl], 1.0))] = True
        # *GG/UR make sure to init all S
        g.Trackp[g.Rp].where[~(Sum(g.PrcTs[g.Rp, g.s], 1.0))] = True
        with Loop(g.tsl):
            g.PrcTs[g.Trackp[g.r, g.p], g.s].where[
                (g.TsGroup[g.r, g.tsl, g.s].where[g.PrcTsl[g.r, g.p, g.tsl]])
            ] = True
        g.Trackp.setRecords(None)

        # * determine seasons for which a process handling seasonal commodities may need to
        # * be tracked, and identify all the TS above this level
        # *   - RPS_PRCTS corresponds to all levels at/above PRC_TS
        # *   - RPS_S2 corresponds to non-PG flo variables
        # *   - RPS_S1 corresponds to level of EQ_PTRANS

        # * Convert ANNUAL level timeslice storage
        g.RpSgs[g.RpFlo[g.r, g.p]].where[
            (
                g.PrcTsl[g.r, g.p, "ANNUAL"].where[
                    (g.PrcMap[g.r, "STS", g.p] + g.PrcMap[g.r, "NST", g.p])
                ]
            )
        ] = True
        g.RpSgs[g.RpFlo[g.r, g.p]] = sparse(g.PrcMap[g.r, "SGS", g.p])
        g.PrcMap[g.r, "STG", g.p].where[
            ((~Sum(g.Top[g.RpcPg[g.r, g.p, g.c], "IN"], 1.0)).where[g.RpSgs[g.r, g.p]])
        ] = False
        # * All NST operating below ANNUAL level but producing ANNUAL level commodity will be STG:
        g.PrcMap[g.r, "STG", g.p].where[
            (~g.PrcTsl[g.r, g.p, "ANNUAL"]).where[g.PrcMap[g.r, "NST", g.p]]
        ] = True
        g.RpStg[g.Rp[g.r, g.p]] = sparse(g.PrcMap[g.r, "STG", g.p])
        # * identify shadow group timeslice level
        # * For LOAD processes, take the maximum TSLVL
        project(source=g.com_fr, target=g.Dem)
        with Loop(g.ComTsl[g.Dem[g.r, g.c], "ANNUAL"]):
            g.Trackp[g.RpFlo[g.r, g.p]].where[g.RpcPg[g.r, g.p, g.c]] = True
        g.prc_ymax[g.Rp[g.r, g.p]] = Smax(
            Domain(g.RpcSpg[g.r, g.p, g.c], g.ComTsl[g.r, g.c, g.tsl]),
            g.tslvlnum[g.tsl],
        )
        g.prc_ymax[g.Trackp[g.r, g.p]] = Smax(
            Domain(g.Rpc[g.r, g.p, g.c], g.ComTsl[g.r, g.c, g.tsl]), g.tslvlnum[g.tsl]
        )
        g.prc_ymax[g.RpStg] = 0.0
        g.prc_ymax[g.Rp] = Max(
            g.prc_ymax[g.Rp], Smax(g.PrcTsl[g.Rp, g.tsl], g.tslvlnum[g.tsl])
        )
        # * First, get levels for each TS
        with Loop(g.r):
            g.ts_array.setRecords(None)
            g.ts_array[g.s] = sparse(g.rs_tslvl[g.r, g.s])
            g.z[...] = Max(1.0, Smax(g.Rlup[g.r, g.tslvl, g.tsl], g.tslvlnum[g.tsl]))
            # * identify all S at shadow level
            g.RpsS2[g.RpSgs[g.r, g.p], g.s].where[
                (g.ts_array[g.s] == g.prc_ymax[g.r, g.p])
            ] = True
            g.prc_sgl[g.RpFlo[g.r, g.p]] = (
                Min(g.prc_ymax[g.r, g.p] - Number(1.0).where[g.RpStg[g.r, g.p]], g.z)
                - 1.0
            )
            g.prc_ymax[g.RpSgs[g.r, g.p]] = g.prc_sgl[g.r, g.p] + 1.0
            # * save the finer of the PRC_TS and the finest commodity in the shadow primary
            g.RpsS1[g.Rp[g.r, g.p], g.s].where[
                (g.ts_array[g.s] == g.prc_ymax[g.r, g.p])
            ] = True
            g.RpsS2[g.RpsS1[g.r, g.p, g.s]].where[~(g.RpSgs[g.r, g.p])] = True
        # * identify all TS at/above the PRC_TSL
        with Loop(Domain(g.tslvl, g.tsl).where[(Ord(g.tsl) > Ord(g.tslvl))]):
            with If(Ord(g.tsl) == 2.0):
                g.RpsPrcts[g.PrcTs[g.Rp, g.s]] = Number(1.0)  # type:ignore
            g.RpsPrcts[g.Rp[g.r, g.p], g.s].where[
                (g.TsGroup[g.r, g.tslvl, g.s].where[g.PrcTsl[g.Rp, g.tsl]])
            ] = True
        g.RpPgflo[g.Trackp].where[(g.prc_ymax[g.Trackp] > 1.0)] = True

        # *-----------------------------------------------------------------------------
        # * Establish the main control set for generation or not of a VAR_FLO/IRE for
        # *   each commodity involved in a process, and for viable commodity/process timeslices
        # * Take into consideration whether the commodity is turned off for some timeslice
        # * Note: RTPCS_VAR further adjusted at the end of PPMAIN (after optional REDUCE)
        # *-----------------------------------------------------------------------------
        # * Special handling for storage, esp. night storage
        g.RpcStg[g.Rpc[g.RpStg[g.r, g.p], g.c]].where[
            (
                g.PrcStgtss[g.Rpc]
                + g.PrcStgips[g.Rpc]
                + (g.RpcPg[g.Rpc] + g.RpcSpg[g.Rpc]).where[g.PrcMap[g.r, "NST", g.p]]
            )
        ] = True
        g.Trackpc[g.RpcStg[g.r, g.p, g.c]].where[
            (
                (g.Top[g.r, g.p, g.c, "OUT"] + g.PrcNstts[g.r, g.p, "ANNUAL"]).where[
                    g.ComTs[g.r, g.c, "ANNUAL"] & g.PrcMap[g.r, "NST", g.p]
                ]
            )
        ] = True
        g.RpcsVar[g.Rpc[g.RpStg[g.r, g.p], g.c], g.s].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[~(g.Trackpc[g.Rpc])]
                + g.Annual[g.s].where[g.Trackpc[g.Rpc]]
            )
        ] = True
        g.PrcNstts[g.RpStg[g.r, g.p], g.Annual].where[
            ~(Sum(g.Top[g.Trackpc[g.r, g.p, g.c], "IN"], 1.0))
        ] = False
        project(source=g.PrcNstts, target=g.PrcAct)
        g.PrcNstts[g.RpsS2[g.r, g.p, g.s]].where[~(g.PrcAct[g.r, g.p])] = sparse(
            g.PrcMap[g.r, "NST", g.p]
        )
        # * The commodities in the PCG need to be tracked at the PRC_TS-level
        g.Trackp[g.Rp] = ~(g.RpStg[g.Rp])
        g.RpcsVar[g.RpcPg[g.Trackp[g.r, g.p], g.c], g.s].where[
            g.PrcTs[g.r, g.p, g.s]
        ] = True
        # * All non-PCG commodities need to be tracked at the S1/S2-level
        g.RpcsVar[g.RpcSpg[g.Trackp[g.r, g.p], g.c], g.s].where[
            g.RpsS2[g.r, g.p, g.s]
        ] = True
        g.RpcsVar[g.Rpc[g.Trackp[g.r, g.p], g.c], g.s].where[
            (
                g.RpsS1[g.r, g.p, g.s].where[
                    ~(g.RpcPg[g.r, g.p, g.c] + g.RpcSpg[g.r, g.p, g.c])
                ]
            )
        ] = True
        # * Remove timeslices turned off by COM_TS
        g.RpcsVar[g.r, g.p, g.c, g.s].where[g.Rcs[g.r, g.c, g.s]] = False
        g.prc_ymax.setRecords(None)
        g.Rcs.setRecords(None)
        g.PrcAct.setRecords(None)
        g.Trackp.setRecords(None)
        g.Trackpc.setRecords(None)

        # *-----------------------------------------------------------------------------
        # * adjustment of life and construction lead if below threshold
        # *-----------------------------------------------------------------------------
        tlife_too_short, tlife_too_long = ncap_tlife_violations(g)
        g.pp_qaput_logger.log_violations(
            violations_df=tlife_too_short.records,
            err_level=1,
            group_desc="NCAP_TLIFE out of feasible range",
            message_template="WARNING       - Too short, set to 1,   R={R} P={P} V={T}",
        )
        g.pp_qaput_logger.log_violations(
            violations_df=tlife_too_long.records,
            err_level=1,
            group_desc="NCAP_TLIFE out of feasible range",
            message_template=(
                f"WARNING       - No FOM beyond year {Card(g.age)},  R={{R}} P={{P}} V={{T}}"
            ),
        )
        g.ncap_tlife[g.Rxx[g.r, g.v, g.p]] = 1.0

        # * set the technical lifetime if none set
        g.ncap_tlife[g.Rtp].where[~(g.ncap_tlife[g.Rtp])] = g.g_tlife
        # *-----------------------------------------------------------------------------
        g.g_iledno[...] = resolve_ctst((g.g_iledno + 2.0), ctst) - 2.0
        # * Adjust fractional and negative ILED if such exist (only integral ILED can be fully consistent)
        g.coef_iled[g.Rtp].where[g.ncap_iled[g.Rtp]] = Max(
            abs(g.ncap_iled[g.Rtp]), g.coef_iled[g.Rtp]
        )
        g.ncap_iled[g.Rtp[g.r, g.v, g.p]].where[g.ncap_iled[g.Rtp]] = Max(
            SpecialValues.EPS, ceil(g.ncap_iled[g.Rtp] - 0.5)
        ).where[(g.coef_iled[g.Rtp] > Min(g.d[g.v], g.ncap_tlife[g.Rtp]) / g.g_iledno)]
        g.ncap_iled[g.Rtp[g.r, g.Phyr, g.p]] = (
            g.ncap_iled[g.Rtp] + g.coef_rtp[g.Rtp] + SpecialValues.EPS
        )

    def phase_seven(self: PpmainMod, ctst: Literal["", "**EPS", "**0", "1"]) -> None:
        g = self.tc
        g.prc_refit[g.r, g.p, g.prc].where[g.prc_refit[g.r, g.p, g.prc]] = Max(
            abs(Round(g.prc_refit[g.r, g.p, g.prc])),
            Min(
                6.0,
                abs(Max(Round(g.prc_refit[g.r, g.p, g.p]), -1.0) * 2.0),
            ),
        ) * mod(Round(g.prc_refit[g.r, g.p, g.prc]), 2.0)
        with Loop(Domain(g.Rp[g.r, g.prc], g.p).where[g.prc_refit[g.Rp, g.p]]):
            with If(~(g.PrcRcap[g.Rp])):
                g.RtpOff[g.r, g.t, g.p] = True
            with If(g.prc_refit[g.Rp, g.p] < -4.0):
                g.ncap_elife[g.Rtp[g.r, g.t, g.p]].where[
                    (g.ncap_elife[g.Rtp] < 1.0)
                ] = g.ncap_tlife[g.Rtp]
                g.ncap_tlife[g.Rtp[g.r, g.t, g.p]] = Max(
                    g.ncap_tlife[g.r, g.t, g.prc] + g.ncap_iled[g.r, g.t, g.prc] - 1.0,
                    g.ncap_tlife[g.Rtp],
                )
        # *-----------------------------------------------------------------------------
        # * capacity transfer v = year of installation and thus data values where
        # *   v is >= start and <= end and t is within the TLIFEv adjusted for any ILEDv
        # *-----------------------------------------------------------------------------
        # * determine the number of repeated investments
        g.ncap_tlife[g.Rvp].where[
            ((g.ncap_pasti[g.Rvp] == 0.0).where[g.RtpOff[g.Rvp]])
        ] = 1.0
        g.coef_rpti[g.Rtp[g.r, g.Pastmile, g.p]].where[
            g.ncap_pasti[g.r, g.Pastmile, g.p]
        ] = 1.0
        # * If alternate objective, differentiate OBJ1 cases where TLIFE > IPD lead but TLIFE < D
        if g.altobj.toValue():
            g.coef_rpti[g.Rtp[g.r, g.t, g.p]].where[g.ncap_iled[g.r, g.t, g.p]] = Max(
                1.0,
                ceil(
                    (g.d[g.t] - g.ncap_iled[g.r, g.t, g.p])
                    / g.ncap_tlife[g.r, g.t, g.p]
                ),
            )
            g.coef_rpti[g.Rtp[g.r, g.t, g.p]].where[
                (
                    (
                        (
                            Round(g.ncap_tlife[g.r, g.t, g.p])
                            - resolve_ctst(g.ipd[g.t], ctst)
                        )
                        > 0.0
                    ).where[(~(g.ncap_iled[g.r, g.t, g.p]))]
                )
            ] = Max(
                1.0,
                ceil(Max(g.d[g.t], g.ipd[g.t]) / g.ncap_tlife[g.r, g.t, g.p]),
            )
            g.coef_rpti[g.Rtp[g.r, g.t, g.p]].where[(~(g.coef_rpti[g.r, g.t, g.p]))] = (
                Max(1.0, Max(g.d[g.t], g.ipd[g.t]) / g.ncap_tlife[g.r, g.t, g.p])
            )
        else:
            g.coef_rpti[g.Rtp[g.r, g.t, g.p]] = Max(
                1.0,
                ceil(
                    (g.d[g.t] - g.ncap_iled[g.r, g.t, g.p])
                    / g.ncap_tlife[g.r, g.t, g.p]
                ),
            )
        # * Collect all possible period intervals for capacity transfer
        g.Vnt[g.v, g.t].where[(g.m[g.t] >= g.m[g.v])] = True
        g.ykval[g.Vnt[g.v, g.t]] = g.b[g.t] - g.b[g.v]
        if g.altobj.toValue() < 2.0:
            g.RtpCptyr[g.r, g.Vnt[g.v, g.t], g.p].where[
                (
                    (g.b[g.v] + g.ncap_iled[g.r, g.v, g.p] < (g.e[g.t] + 1.0)).where[
                        (
                            g.ncap_iled[g.r, g.v, g.p]
                            + g.coef_rpti[g.r, g.v, g.p] * g.ncap_tlife[g.r, g.v, g.p]
                            > g.ykval[g.v, g.t]
                        )
                        & g.Rtp[g.r, g.v, g.p]
                    ]
                )
            ] = True
        else:
            # * If linearized objective, use relaxed thresholds
            g.ykval[g.Vnt[g.tt, g.t]] = (
                g.b[g.t]
                - g.b[g.tt]
                - (1.0 - mod(g.ipd[g.t], 2.0) + (g.ipd[g.t] - 1.0) / 9.0) / 2.0
            )
            g.f[...] = 0.0
            g.pastsum[g.Rtp[g.r, g.v, g.p]] = (g.ncap_iled[g.r, g.v, g.p] + g.f).where[
                g.ncap_iled[g.r, g.v, g.p]
            ] + g.coef_rpti[g.r, g.v, g.p] * g.ncap_tlife[g.r, g.v, g.p]
            g.RtpCptyr[g.r, g.Vnt[g.v, g.t], g.p].where[
                (
                    (g.pastsum[g.r, g.v, g.p] > g.ykval[g.v, g.t]).where[
                        (g.b[g.v] + g.ncap_iled[g.r, g.v, g.p] < g.e[g.t] + 1.0)
                        & g.Rtp[g.r, g.v, g.p]
                    ]
                )
            ] = True
            g.pastsum.setRecords(None)
        g.ykval.setRecords(None)
        g.coef_rtp.setRecords(None)

    def phase_eight(self: PpmainMod, pgprim: str, prc_simv_defined: bool) -> None:
        g = self.tc
        g.RtpCptyr[g.r, g.Miyr1[g.t], g.t, g.p].where[
            (g.Rtp[g.r, g.t, g.p].where[g.PrcMap[g.r, "STK", g.p]])
        ] = True
        # *-----------------------------------------------------------------------------
        # * Preprocess capacity bounds
        # *-----------------------------------------------------------------------------
        # * Migrate CAP_BND + QA check
        g.Rvp.setRecords(None)
        g.putgrp[...] = 0.0
        g.cap_bnd[g.Rtp, g.Bdneq] = sparse(g.cap_bnd[g.Rtp, "FX"])

        cap_bnd_violations_set = cap_bnd_violations(g)

        g.pp_qaput_logger.log_violations(
            violations_df=cap_bnd_violations_set.records,
            err_level=round(g.ifq.toValue()),
            group_desc="Inconsistent CAP_BND(UP/FX) defined for process capacity",
            message_template=(
                "WARNING       - Bound converted to NCAP_BND,   R.T.P= {R}.{T}.{P}"
                + (" infeasibility detected," if g.ifq.toValue() > 9 else "")
            ),
        )

        # * clear zero / INF CAP_BNDs
        g.Rvp[g.Rtp].where[
            ((g.cap_bnd[g.Rtp, "UP"] == 0.0).where[g.cap_bnd[g.Rtp, "UP"]])
        ] = True
        with Loop(g.t):
            g.ncap_bnd[g.r, g.tt, g.p, "UP"].where[
                (g.RtpCptyr[g.r, g.tt, g.t, g.p].where[g.Rvp[g.r, g.t, g.p]])
            ] = SpecialValues.EPS
        g.Rvp[g.RtpVarp] = False
        g.cap_bnd[g.Rvp, g.bd] = 0.0
        g.cap_bnd[g.Rtp, g.Bdlox].where[map_value(g.cap_bnd[g.Rtp, g.Bdlox])] = 0.0
        # * Check whether both UP and LO bounds (then it pays to have VAR_CAP)
        g.RtpVarp[g.Rtp[g.r, g.t, g.p]].where[
            (g.cap_bnd[g.Rtp, "UP"] * g.cap_bnd[g.Rtp, "LO"])
        ] = True
        g.putgrp[...] = 0.0

        cap_bnd_lo_up_violations_set = cap_bnd_lo_up_violations(g)
        g.pp_qaput_logger.log_violations(
            violations_df=cap_bnd_lo_up_violations_set.records,
            err_level=1,
            group_desc="Inconsistent CAP_BND(UP/LO/FX) defined for process capacity",
            message_template=(
                "WARNING       - Lower bound set equal to upper bound,   "
                "R.T.P= {R}.{T}.{P}"
            ),
        )

        # *-----------------------------------------------------------------------------
        # * turn off RTP/CPTYR if no new investment & installed capacity no longer available
        with Loop(g.Bdupx[g.bd]):
            g.RtpOff[g.Rtp].where[
                ((g.ncap_bnd[g.Rtp, g.bd] == 0.0).where[g.ncap_bnd[g.Rtp, g.bd]])
            ] = True
        g.NoRvp[g.RtpOff[g.r, g.t, g.p]].where[~(g.ncap_pasti[g.r, g.t, g.p])] = True
        with Loop(g.t):
            g.NoRvp[g.r, g.tt, g.p].where[
                (g.RtpCptyr[g.r, g.t, g.tt, g.p].where[~(g.RtpOff[g.r, g.t, g.p])])
            ] = False
        with Loop(g.pyr[g.v]):
            g.NoRvp[g.r, g.t, g.p].where[
                (g.RtpCptyr[g.r, g.v, g.t, g.p].where[g.ncap_pasti[g.r, g.v, g.p]])
            ] = False
        g.Rtp[g.NoRvp] = False
        g.RtpCptyr[g.r, g.t, g.tt, g.p].where[
            ((~g.ncap_pasti[g.r, g.t, g.p]).where[g.RtpOff[g.r, g.t, g.p]])
        ] = False
        g.Rvp.setRecords(None)
        g.NoRvp.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * initialize start/end year for a process & available years
        # *-----------------------------------------------------------------------------
        # *-- Speed up by first tracking RPs with PRC_AOFF
        with Loop(g.PrcAoff[g.Rp[g.r, g.p], g.bohyear, g.eohyear]):
            g.Trackp[g.r, g.p] = True
        g.RtpVara[g.Rtp[g.r, g.t, g.p]].where[~(g.Trackp[g.r, g.p])] = True
        with Loop(g.Trackp[g.r, g.p]):
            g.MyFil[g.t] = True
            # * set the OFF range
            pp_off_GP(g, g.PrcAoff, (g.p,), Number(1), g.MyFil[g.t], 0)
            # * set the periods for which VAR_ACT is OK
            g.RtpVara[g.Rtp[g.r, g.MyFil[g.t], g.p]] = True

        g.Trackp.setRecords(None)

        # *-----------------------------------------------------------------------------
        # * initialize start/end year for a process flows
        # *-----------------------------------------------------------------------------
        # * Initialize start/end year for process commodities
        g.Rtpc[g.Rtp[g.r, g.t, g.p], g.c] = sparse(g.Rpc[g.r, g.p, g.c])
        g.putgrp[...] = 0.0
        # *-- track all RPCs with PRC_FOFF:
        with Loop(g.PrcFoff[g.r, g.p, g.c, g.ts, g.bohyear, g.eohyear]):
            g.Trackpc[g.r, g.p, g.c] = True
        with Loop(g.RpcsVar[g.Trackpc[g.r, g.p, g.c], g.s]):
            g.MyFil[g.t] = False
            # * check for shut-off here or timeslice above
            pp_off_GP(
                g, g.PrcFoff, (g.p, g.c, g.ts), g.TsMap[g.r, g.ts, g.s], g.MyFil[g.t], 1
            )
            # * QC check that shut-off not specified below the VAR level
            g.RtpcsOut[g.RtpVara[g.r, g.MyFil[g.t], g.p], g.c, g.s] = True

        flow_off_ts_violations_set = flow_off_ts_violations(g)
        g.pp_qaput_logger.log_violations(
            violations_df=flow_off_ts_violations_set.records,
            err_level=1,
            group_desc="Flow OFF TS level below VARiable TS level",
            message_template="WARNING       - OFF is ignored:  R={R} P={P} C={C} S={TS}",
        )

        g.Trackpc.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * Add leading milestones into RTP if/when simulated vintages
        if prc_simv_defined:
            with Loop(g.t):
                g.NoRvp[g.r, g.tt - 1, g.p].where[
                    (g.RtpCptyr[g.r, g.tt, g.t, g.p].where[g.PrcSimv[g.r, g.p]])
                ] = True
            g.NoRvp[g.Rtp[g.r, g.t, g.p]] = False
            g.Rtp[g.NoRvp] = True
        # *-----------------------------------------------------------------------------
        # * Remove commodity from PG if PRC_ACTFLO flagged non-interpolated, as bad
        g.RpcPg[g.r, g.p, g.c].where[
            (
                (~g.RpPg[g.r, g.p, g.c]).where[
                    Round(g.prc_actflo[g.r, "0", g.p, g.c] < 0.0)
                ]
            )
        ] = False
        # * Save original non-PG PRC_ACTFLO groups
        g.RpcPg[g.RpcStg] = True
        g.RpStd[g.RpFlo[g.Rp]].where[~(g.RpStg[g.Rp])] = True
        project(source=g.prc_actflo, target=g.RpcAct, direction="left")
        g.RpcAct[g.r, g.p, g.c].where[
            (g.RpcPg[g.r, g.p, g.c] + (~g.Rpc[g.r, g.p, g.c].where[g.RpStd[g.r, g.p]]))
        ] = False
        g.Chp[g.Rp[g.r, g.p]] = sparse(g.PrcMap[g.r, "CHP", g.p])
        # *-----------------------------------------------------------------------------
        # * establishment PRC_CAPACT/ACTFLO from PRC_CAPUNT/ACTUNT/COM_UNIT & determine INOUT(r,p)
        # *-----------------------------------------------------------------------------
        g.prc_capact[g.Rp].where[~(g.prc_capact[g.Rp])] = 1.0
        # * Copy PRC_ACTFLO from PG to individual commodities in PG, allowing reserved word pgprim
        g.prc_actflo[g.Rtp[g.r, g.v, g.p], g.c].where[
            ((~g.prc_actflo[g.Rtp, g.c]).where[g.RpcPg[g.r, g.p, g.c]])
        ] = sparse(Sum(g.RpPg[g.r, g.p, g.cg], g.prc_actflo[g.r, g.v, g.p, g.cg]))
        g.prc_actflo[g.Rtp[g.r, g.v, g.p], g.c].where[
            ((~g.prc_actflo[g.Rtp, g.c]).where[g.RpcPg[g.r, g.p, g.c]])
        ] = sparse(g.prc_actflo[g.Rtp, pgprim])
        g.prc_actflo[g.Rtp[g.r, g.v, g.p], g.c].where[
            ((~g.prc_actflo[g.Rtp, g.c]).where[g.RpcPg[g.r, g.p, g.c]])
        ] = 1.0
        # * RP_PGACT signifies that activity can be substituted for the primary flow
        g.RpPgact[g.RpFlo[g.r, g.p]].where[
            (Sum(g.RpcPg[g.r, g.p, g.c], 1.0) == 1.0)
        ] = True
        g.RpPgact[g.RpIre[g.r, g.p]].where[
            (Sum(g.RpcIre[g.RpcPg[g.r, g.p, g.c], g.ie], 1.0) == 1.0)
        ] = True

    def phase_nine(self: PpmainMod) -> None:
        g = self.tc
        g.maxlife[...] = Smax(g.Rtp, g.ncap_tlife[g.Rtp])
        # * Convert indexes to demand elasticity shape curves to tuples
        with Loop(same_as(g.j, "1")):
            g.RtcShed[
                g.r,
                g.t,
                g.c,
                g.bd,
                g.j + Max(0.0, g.com_elastx[g.r, g.t, g.c, g.bd] - 1.0),
            ].where[g.com_elastx[g.r, g.t, g.c, g.bd]] = True
        g.startoff[...] = (
            ceil(
                Max(
                    g.maxlife,
                    Smax(
                        g.RtcShed[g.r, g.t, g.c, g.bd, g.j],
                        g.com_voc[g.r, g.t, g.c, g.bd],
                    )
                    * 100.0,
                )
            )
            + 1.0
        )

    def establish_basic_defaults_for_non_ts_attribute(self: PpmainMod) -> None:
        g = self.tc

        with Loop(g.j):
            g.z[...] = 1.0
            with Loop(g.ll.where[(g.multi[g.j, g.ll] * g.z)]):
                g.z[...] = 0.0
                g.f[...] = Min(1.0, g.multi[g.j, g.ll])
            with If(~(g.z)):
                g.multi[g.j, g.Eohyears].where[~(g.multi[g.j, g.Eohyears])] = g.f
        g.multi["1", g.Eachyear] = 1.0
        # *-----------------------------------------------------------------------------
        # * establish basic defaults for the non-TS attribute
        # *-----------------------------------------------------------------------------
        # * economic life = technical life if not provided
        g.ncap_elife[g.Rtp].where[~(g.ncap_elife[g.Rtp])] = g.ncap_tlife[g.Rtp]
        # * commodity release always in next year if no time provided but release
        g.ncap_dlife[g.Rtp[g.r, g.t, g.p]].where[
            (
                (~g.ncap_dlife[g.Rtp]).where[
                    Sum(g.Rpc[g.r, g.p, g.c].where[g.ncap_ocom[g.Rtp, g.c]], 1.0)
                ]
            )
        ] = 1.0
        g.ncap_delif[g.Rtp[g.r, g.t, g.p]].where[~(g.ncap_delif[g.Rtp])] = sparse(
            g.ncap_dlife[g.Rtp]
        )
        # * if investment requires commodity and has a leadtime, set commodity time = lead, if not provided
        g.ncap_cled[g.Rtp[g.r, g.t, g.p], g.c].where[
            ((~g.ncap_cled[g.Rtp, g.c]).where[g.ncap_icom[g.Rtp, g.c]])
        ] = g.coef_iled[g.Rtp]
        # * defaults for CHP plants
        g.ncap_bpme[g.Rtp[g.r, g.v, g.p]].where[
            ((~g.ncap_bpme[g.Rtp]).where[g.ncap_cdme[g.Rtp] & g.Chp[g.r, g.p]])
        ] = 1.0
        g.ncap_chpr[g.Rtp[g.r, g.v, g.p], "UP"].where[
            (
                (~(Sum(g.lim.where[g.ncap_chpr[g.Rtp, g.lim]], 1.0))).where[
                    g.Chp[g.r, g.p]
                ]
            )
        ] = 1.0
        # * set default storage efficiency if not provided
        with Loop(
            g.RpStg[g.r, g.p].where[
                (~Sum(g.Rtp[g.r, g.t, g.p].where[g.stg_eff[g.Rtp]], 1.0))
            ]
        ):
            g.stg_eff[g.Rtp[g.r, g.v, g.p]] = 1.0

    def phase_eleven(self: PpmainMod) -> None:
        g = self.tc
        # *-----------------------------------------------------------------------------
        # * determination of capacity-ONLY related flows
        # *-----------------------------------------------------------------------------
        # * Initialize capflo indicators for UC_FLO
        g.UcCapflo[g.ucn, g.side, g.RpcNoflo[g.r, g.p, g.c]].where[
            g.UcAttr[g.r, g.ucn, g.side, "FLO", "CAPFLO"]
        ] = True
        g.RpcNoflo[g.RpcPg] = False
        g.RpcsVar[g.RpcNoflo[g.r, g.p, g.c], g.Annual].where[
            ~(g.Rpc[g.r, g.p, g.c])
        ] = True
        g.Trackpc[g.RpcNoflo] = True
        # * identify those commodities involved ONLY with capacity by eliminating those with flows
        with Loop(g.Trackpc[g.r, g.p, g.c]):
            with If(g.RpIre[g.r, g.p]):
                # * RPC_IRE implies IRE_FLOc so not only capacity related
                g.z[...] = ~(Sum(g.RpcIre[g.r, g.p, g.c, g.ie], 1.0))
                g.z[...].where[g.z] = ~(
                    Sum(
                        Domain(g.Rtpc[g.r, g.t, g.p, g.Com], g.s, g.ie, g.io).where[
                            g.ire_flosum[g.r, g.t, g.p, g.Com, g.s, g.ie, g.c, g.io]
                        ],
                        g.RpcIre[g.r, g.p, g.Com, g.ie],
                    )
                )
            with Else():
                g.z[...] = ~(
                    Sum(
                        g.Rtpc[g.r, g.t, g.p, g.c].where[
                            g.prc_actflo[g.r, g.t, g.p, g.c]
                        ],
                        1.0,
                    )
                )
                # * check for the commodity within flo_func/sum/shar
                g.z[...].where[g.z] = ~(
                    Sum(
                        Domain(g.t, g.cg1, g.cg2, g.s).where[
                            g.flo_func[g.r, g.t, g.p, g.cg1, g.cg2, g.s]
                        ],
                        g.ComGmap[g.r, g.cg1, g.c] + g.ComGmap[g.r, g.cg2, g.c],
                    )
                )
                g.z[...].where[g.z] = ~(
                    Sum(
                        Domain(g.t, g.cg1, g.Com, g.cg2, g.s).where[
                            g.flo_sum[g.r, g.t, g.p, g.cg1, g.Com, g.cg2, g.s]
                        ],
                        g.ComGmap[g.r, g.Com, g.c] + g.ComGmap[g.r, g.cg2, g.c],
                    )
                )
                g.z[...].where[g.z] = ~(
                    Sum(
                        Domain(g.t, g.cg, g.s, g.bd).where[
                            g.flo_shar[g.r, g.t, g.p, g.c, g.cg, g.s, g.bd]
                        ],
                        1.0,
                    )
                )
            with If(~(g.z)):
                g.RpcNoflo[g.r, g.p, g.c] = False

        g.Trackpc.setRecords(None)

    def phase_twelve(self: PpmainMod) -> None:
        g = self.tc
        # * Defaults for infrastructure efficiency and seasonal fraction
        project(source=g.com_ie, target=g.Rcs)
        g.RtcNet.setRecords(None)
        g.RpPgflo.setRecords(None)
        g.com_ie[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[(~(g.Rcs[g.r, g.c, g.s]))] = 1.0
        # *GG* 010406 - sum up COM_FRs below on a seasonal level so RTCS_TSFR set below
        # * Get the timeslices where COM_FR has been given
        g.com_fr[g.r, g.ll, g.c, g.Annual] = 0.0
        project(source=g.com_fr, target=g.Rcs)
        g.Trackc[g.r, g.c] = sparse(Sum(g.Rcs[g.r, g.c, g.s], 1.0))
        g.Rcs[g.Trackc[g.r, g.c], g.s].where[g.g_yrfr[g.r, g.s]] = ~(
            g.Rcs[g.r, g.c, g.s]
        )
        # * Fill all other COM_TS timeslices and finer with default fractions
        g.com_fr[g.Rtc[g.r, g.t, g.c], g.s].where[
            (g.Rcs[g.r, g.c, g.s] * g.ComTs[g.r, g.c, g.s])
        ] = g.g_yrfr[g.r, g.s]
        g.com_fr[g.Rtc[g.r, g.t, g.c], g.ts].where[
            g.Rcs[g.r, g.c, g.ts] * g.TsGroup[g.r, "WEEKLY", g.ts]
        ] = sparse(
            Sum(
                g.RsBelow1[g.r, g.s, g.ts],
                g.com_fr[g.r, g.t, g.c, g.s]
                * (g.g_yrfr[g.r, g.ts] / g.g_yrfr[g.r, g.s]),
            )
        )
        g.com_fr[g.Rtc[g.r, g.t, g.c], g.ts].where[
            g.Rcs[g.r, g.c, g.ts] * g.TsGroup[g.r, "DAYNITE", g.ts]
        ] = sparse(
            Sum(
                g.RsBelow1[g.r, g.s, g.ts],
                g.com_fr[g.r, g.t, g.c, g.s]
                * (g.g_yrfr[g.r, g.ts] / g.g_yrfr[g.r, g.s]),
            )
        )
        # * Sum up COM_FR for all commodities that have it defined
        g.com_fr[g.r, g.t, g.c, g.ts].where[
            g.Trackc[g.r, g.c].where[g.TsGroup[g.r, "WEEKLY", g.ts]]
        ] = sparse(Sum(g.RsBelow1[g.r, g.ts, g.s], g.com_fr[g.r, g.t, g.c, g.s]))
        g.com_fr[g.r, g.t, g.c, g.ts].where[
            g.Trackc[g.r, g.c].where[g.TsGroup[g.r, "SEASON", g.ts]]
        ] = sparse(Sum(g.RsBelow1[g.r, g.ts, g.s], g.com_fr[g.r, g.t, g.c, g.s]))
        g.com_fr[g.r, g.t, g.c, g.s].where[g.norts[g.r, g.t, g.s]] = 0.0
        g.com_fr[g.r, g.t, g.c, g.Annual].where[g.Trackc[g.r, g.c]] = Sum(
            g.RsBelow1[g.r, g.Annual, g.s], g.com_fr[g.r, g.t, g.c, g.s]
        )

        violations = com_fr_normalization_violations(g)
        g.pp_qaput_logger.log_violations(
            violations_df=violations.records,
            err_level=1,
            group_desc="COM_FR does not sum to unity (T=first year)",
            # Use Python's left-align padding (:<13) to recreate the wide gaps!
            message_template="WARNING       - Normalized to 1,   R={R:<12} C={C:<12} (T={T})",
        )

        violations.setRecords(None)

        g.com_fr[g.Rtc[g.r, g.t, g.c], g.s].where[
            ((g.com_fr[g.Rtc, "ANNUAL"] != 1.0).where[g.Trackc[g.r, g.c]])
        ] = g.com_fr[g.Rtc, g.s] / g.com_fr[g.Rtc, "ANNUAL"]
        g.RpPgflo[g.Rp[g.r, g.p]] = sparse(
            Sum(g.RpcPg[g.Rp, g.c].where[g.Trackc[g.r, g.c]], 1.0)
        )
        g.RpPgflo[g.Rp].where[Sum(g.RpsS1[g.PrcTs[g.Rp, g.s]], 1.0)] = False
        g.Rcs.setRecords(None)
        g.Trackc.setRecords(None)

    def phase_thirteen(self: PpmainMod, rts: SET_OR_ALIAS | Expression) -> None:
        g = self.tc
        g.rs_fr[g.RsTree[g.r, g.s, g.ts]] = (
            Number(1.0).where[g.TsMap[g.r, g.s, g.ts]]
            + (g.g_yrfr[g.r, g.s] / g.g_yrfr[g.r, g.ts]).where[
                g.RsBelow[g.r, g.ts, g.s]
            ]
        )
        macro.rtcs_fr.rtcs_frmx_GP(g.Rtc[g.r, g.t, g.c], g.s, g.ts).where[
            (g.RsBelow[g.r, g.ts, g.s].where[g.com_fr[g.Rtc, g.ts]])
        ] = (
            (
                (g.com_fr[g.Rtc, g.s] / g.com_fr[g.Rtc, g.ts]).where[
                    (g.com_fr[g.Rtc, g.ts] > 0.0)
                ]
            )
            / g.rs_fr[g.r, g.s, g.ts]
            - 1.0
        )
        g.com_fr[g.Rtc[g.r, g.t, g.c], rts].where[
            ((~(g.com_fr[g.Rtc, g.s])).where[g.RcsComts[g.r, g.c, g.s]])
        ] = g.g_yrfr[g.r, g.s]
        # *-----------------------------------------------------------------------------
        # * Elastic demands
        # *-----------------------------------------------------------------------------
        project(source=g.com_proj, target=g.Dem)

    def phase_fourteen(self: PpmainMod) -> None:
        g = self.tc
        # * check sign of COM_ELAST and set RCJ after assigning default COM_STEPs
        g.com_elast[g.r, g.t, g.c, g.s, g.Bdneq[g.bd]].where[
            g.com_elast[g.r, g.t, g.c, g.s, g.bd]
        ] = -abs(g.com_elast[g.r, g.t, g.c, g.s, g.bd] - 1.0 + 1.0).where[
            Sum(
                g.Rdcur[g.r, g.cur],
                g.com_bprice[g.r, g.t, g.c, g.s, g.cur] * g.com_voc[g.r, g.t, g.c, g.bd]
                > 0.0,
            )
        ]
        project(source=g.com_elast, target=g.RcAgp)
        g.com_step[g.RcAgp[g.Rc, g.Bdneq]].where[(~(g.com_step[g.Rc, g.Bdneq]))] = Max(
            1.0, g.com_step[g.Rc, "FX"]
        )
        g.Rcj[g.Rc, g.j, g.bd].where[
            ((Ord(g.j) <= g.com_step[g.Rc, g.bd]).where[g.RcAgp[g.Rc, g.bd]])
        ] = 1.0
        g.RcAgp.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * process availability factor
        # *   - apply MULTI (moved to coef_cpt)
        # *   - move up to the appropriate level, if applicable
        # *   - move down to the appropriate level, if applicable
        # *   - set default, if necessary
        # *-----------------------------------------------------------------------------
        # * leveling of availability; set at the PRC_TS level by inheriting from above, if not yet set
        g.putgrp[...] = 0.0
        g.RtpsBd[g.Rtp[g.r, g.v, g.p], g.s, g.bd].where[g.PrcTs[g.r, g.p, g.s]] = (
            sparse(g.ncap_afs[g.Rtp, g.s, g.bd].where[~(g.ncap_af[g.Rtp, g.s, g.bd])])
        )

    def phase_fiveteen(self: PpmainMod) -> None:
        g = self.tc
        g.ncap_af[g.RtpsBd].where[g.ncap_af[g.RtpsBd]] = sparse(g.ncap_afs[g.RtpsBd])
        # * Mark those timeslices that have NCAP_AFs:
        g.Rxx.setRecords(None)
        g.RtpsBd.setRecords(None)

        g.RtpsBd[
            g.r,
            g.ll.lag(
                (Ord(g.ll) * (g.ncap_af[g.r, g.ll, g.p, g.s, g.bd] > 0.0)), "circular"
            ),
            g.p,
            g.s,
            g.Bdupx[g.bd],
        ].where[(g.v[g.ll].where[g.ncap_af[g.r, g.ll, g.p, g.s, g.bd]])] = True
        project(source=g.RtpsBd, target=g.Trackp)
        g.Rxx[g.PrcTs[g.Trackp[g.r, g.p], g.s]] = sparse(
            Sum(g.RtpsBd[g.r, g.Lastll, g.p, g.s, g.Bdupx], 1.0)
        )
        # * Set default if no PRC_TS has NCAP_AFs :
        g.ncap_af[g.Rtp[g.r, g.v, g.p], g.s, "UP"].where[
            (g.PrcTs[g.r, g.p, g.s].where[(~(g.Trackp[g.r, g.p]))])
        ] = 1.0
        g.PrcTs2[g.PrcTs[g.Trackp[g.r, g.p], g.s]] = ~(g.Rxx[g.r, g.p, g.s])
        g.ncap_af[g.Rtp[g.r, g.v, g.p], g.s, "UP"].where[
            (g.PrcTs2[g.r, g.p, g.s].where[g.RpStg[g.r, g.p]])
        ] = SpecialValues.EPS
        g.PrcTs2[g.RpStg, g.s] = False
        # * Make sure to get rid of any remaining PRC_TS for which no NCAP_AF
        g.PrcTs2[g.Rp[g.r, g.p], g.s] = sparse(
            Sum(g.RsBelow[g.r, g.ts, g.s].where[g.PrcTs2[g.Rp, g.ts]], 1.0)
        )
        g.PrcTs[g.PrcTs2] = False
        g.RpcsVar[g.RpcsVar[g.r, g.p, g.c, g.s]].where[g.PrcTs2[g.r, g.p, g.s]] = False
        g.RtpcsOut[g.Rtpc[g.r, g.t, g.p, g.c], g.s].where[g.PrcTs2[g.r, g.p, g.s]] = (
            True
        )
        g.PrcTs2.setRecords(None)
        g.Trackp.setRecords(None)
        g.RtpsBd.setRecords(None)

    def phase_sixteen(self: PpmainMod) -> None:
        g = self.tc
        # *GG*PKCOI defaults to 1
        with Loop(  # noqa: SIM117
            Domain(g.Rpc[g.r, g.p, g.c], g.ComGmap[g.ComPeak[g.r, g.cg], g.c]).where[
                (g.Top[g.Rpc, "IN"] + g.RpcIre[g.Rpc, "EXP"])
            ]
        ):
            with If(
                ~(
                    Sum(
                        Domain(g.Rtp[g.r, g.t, g.p], g.RpcsVar[g.Rpc, g.ts]).where[
                            g.flo_pkcoi[g.Rtp, g.c, g.ts]
                        ],
                        1.0,
                    )
                )
            ):
                g.Trackpc[g.Rpc] = True
        g.Trackpc[g.PrcPkno[g.r, g.p], g.c] = False
        g.flo_pkcoi[g.Rtp[g.r, g.t, g.p], g.c, g.s].where[
            (g.RpcsVar[g.r, g.p, g.c, g.s].where[g.Trackpc[g.r, g.p, g.c]])
        ] = 1.0
        g.Trackpc.setRecords(None)

    def phase_seventeen(self: PpmainMod) -> None:
        g = self.tc
        # * Add FLO_SUM translated from PRC_ACTFLO
        g.ire_flosum[g.Rtp[g.r, g.v, g.p], g.c, g.s, g.ie, g.Com, g.io].where[
            g.RpcPg[g.r, g.p, g.c]
            * g.RpcIre[g.r, g.p, g.c, g.ie]
            * g.RpcsVar[g.r, g.p, g.c, g.s]
            * g.Top[g.r, g.p, g.Com, g.io]
        ] = sparse(
            Sum(
                g.RpcAct[g.RpIre[g.r, g.p], g.Com],
                g.prc_actflo[g.r, g.v, g.p, g.Com]
                * (1.0 / g.prc_actflo[g.r, g.v, g.p, g.c]),
            )
        )

        g.flo_sum[g.Rtp[g.r, g.v, g.p], g.cg, g.c, g.Com, g.s].where[
            (g.RpPg[g.r, g.p, g.cg] * g.RpcPg[g.r, g.p, g.c] * g.PrcTs[g.r, g.p, g.s])
        ] = sparse(
            Sum(
                g.RpcAct[g.RpFlo[g.r, g.p], g.Com],
                g.prc_actflo[g.r, g.v, g.p, g.Com]
                * (1.0 / g.prc_actflo[g.r, g.v, g.p, g.c]),
            )
        )
        g.RpcAct.setRecords(None)

    def phase_eightteen(self: PpmainMod, macro: str, micro: str, pgprim: str) -> None:
        g = self.tc

        # *-----------------------------------------------------------------------------
        # * Preprocess market-based trade
        # *-----------------------------------------------------------------------------
        # * Set endogenous trade indicators
        g.Rxx.setRecords(None)
        with Loop(g.TopIre[g.r, g.c, g.Reg, g.Com, g.p]):
            g.Rxx[g.r, g.c, g.p] = True
            g.RpcIreio[g.Reg, g.p, g.Com, "IMP", "IN"] = True
        g.RpcIreio[g.r, g.p, g.c, "EXP", "IN"].where[g.Rxx[g.r, g.c, g.p]] = True
        g.RpcIreio[g.RpcIre[g.r, g.p, g.c, g.ie], "OUT"].where[
            (~(g.RpcIreio[g.r, g.p, g.c, g.ie, "IN"]))
        ] = True
        g.PrcMap[g.r, "DISTR", g.p].where[g.PrcMap[g.r, "CORR", g.p]] = True
        g.IreDist[g.RpIre[g.r, g.p]].where[g.PrcMap[g.r, "DISTR", g.p]] = True
        # * Define a marketplace whenever imports to several regions, or an intermediate region between two other regions
        with Loop(
            g.Rxx[g.r, g.c, g.p].where[
                (Sum(g.TopIre[g.r, g.c, g.Reg, g.Com, g.p], 1.0) > 1.0)
            ]
        ):
            g.RpcMarket[g.r, g.p, g.c, "EXP"] = True
        g.Rxx[g.r, g.c, g.p].where[g.IreDist[g.r, g.p]] = False
        with Loop(
            g.TopIre[g.Reg, g.Com, g.Rxx[g.r, g.c, g.p]].where[
                (~(Sum(g.com1.where[g.TopIre[g.r, g.c, g.Reg, g.com1, g.p]], 1.0)))
            ]
        ):
            g.RpcMarket[g.r, g.p, g.c, "EXP"] = True
        # * Ensure that over distribution all directly linked regions after first market are also markets
        g.Trackpc[g.IreDist[g.r, g.p], g.c].where[g.RpcMarket[g.r, g.p, g.c, "EXP"]] = (
            True
        )
        with While(Card(g.Trackpc)):  # type: ignore[arg-type]
            g.Rxx.setRecords(None)
            with Loop(  # noqa: SIM117
                Domain(
                    g.Trackpc[g.r, g.p, g.c],
                    g.TopIre[g.r, g.c, g.Reg, g.Com, g.p],
                    g.RpcIre[g.Reg, g.p, g.com1, "EXP"],
                )
            ):
                with If(
                    ~(Sum(g.com2.where[g.TopIre[g.Reg, g.com1, g.r, g.com2, g.p]], 1.0))
                ):
                    g.Rxx[g.Reg, g.p, g.com1] = True
            g.Trackpc.setRecords(None)
            g.Trackpc[g.Rxx[g.r, g.p, g.c]].where[
                (~(g.RpcMarket[g.r, g.p, g.c, "EXP"]))
            ] = True
            g.RpcMarket[g.Trackpc, "EXP"] = True
        g.putgrp[...] = 0.0

        trade_topology_violations = diverging_trade_topology_violations(g)
        g.pp_qaput_logger.log_violations(
            violations_df=trade_topology_violations.records,
            err_level=1,
            group_desc="Unsupported diverging trade topology",
            message_template="WARNING       - Too complex topology:  R={R} P={P}",
        )

        with Loop(g.CgGrp[g.r, g.p, g.c, g.Com]):
            g.RcRc[g.r, g.c, g.r, g.Com] = True
        g.TopIre[g.RcRc[g.r, g.c, g.r, g.Com], g.p].where[
            g.CgGrp[g.r, g.p, g.c, g.Com]
        ] = True
        g.CgGrp.setRecords(None)
        # * Complete the preparation of marketplace
        with Loop(g.TopIre[g.r, g.c, g.r, g.Com, g.p]):
            # * If no IRE_FLO set for marketplace, set default values
            with If(g.IreDist[g.r, g.p]):
                g.ire_flo[g.Rtp[g.r, g.v, g.p], g.c, g.r, g.Com, g.s].where[
                    (
                        (g.ire_flo[g.r, g.v, g.p, g.c, g.r, g.Com, g.s] == 0.0).where[
                            g.RpcsVar[g.r, g.p, g.Com, g.s]
                        ]
                    )
                ] = 1.0
            with Else():
                g.f[...] = Sum(
                    Domain(g.Rtp[g.r, g.t, g.p], g.s).where[
                        g.ire_flo[g.r, g.t, g.p, g.c, g.r, g.Com, g.s]
                    ],
                    1.0,
                )
                with Loop(
                    Domain(g.Reg, g.com1).where[
                        (g.TopIre[g.r, g.c, g.Reg, g.com1, g.p].where[(~(g.f))])
                    ]
                ):
                    g.f[...] = Sum(
                        Domain(g.Rtp[g.r, g.t, g.p], g.s).where[
                            g.ire_flo[g.r, g.t, g.p, g.c, g.Reg, g.com1, g.s]
                        ],
                        1.0,
                    )
                    with If(g.f):
                        g.ire_flo[g.Rtp[g.r, g.v, g.p], g.c, g.r, g.Com, g.s].where[
                            g.RpcsVar[g.r, g.p, g.Com, g.s]
                        ] = g.ire_flo[g.r, g.v, g.p, g.c, g.Reg, g.com1, g.s]
        # * Set standard EQIRE control for all imports other than from marketplace region
        with Loop(  # noqa: SIM117
            g.TopIre[g.r, g.c, g.Reg, g.Com, g.p].where[
                g.RpcMarket[g.r, g.p, g.c, "EXP"]
            ]
        ):
            with If(~(same_as(g.r, g.Reg))):
                g.Trackpc[g.Reg, g.p, g.Com] = True
        g.RpcEqire[g.RpcIre[g.r, g.p, g.c, "IMP"]].where[
            ((~g.Trackpc[g.r, g.p, g.c]).where[g.RpcIreio[g.r, g.p, g.c, "IMP", "IN"]])
        ] = True
        g.Trackpc.setRecords(None)
        # * Set all non-standard EQIRE and MARKET controls
        with Loop(g.TopIre[g.r, g.c, g.r, g.Com, g.p]):
            with If(~(g.RpcEqire[g.r, g.p, g.Com, "IMP"])):
                g.RpcEqire[g.r, g.p, g.c, "EXP"] = True
            with ElseIf(g.RpcMarket[g.r, g.p, g.c, "EXP"]):
                with If(g.IreDist[g.r, g.p]):
                    g.RpcEqire[g.r, g.p, g.c, "EXP"] = True
                with Else():
                    g.RpcMarket[g.r, g.p, g.Com, "IMP"] = True
        g.TopIre[g.r, g.c, g.r, g.Com, g.p].where[g.RpcEqire[g.r, g.p, g.c, "EXP"]] = (
            False
        )
        # * Copy shutdown periods of marketplace to import regions
        with Loop(g.RpcMarket[g.r, g.p, g.c, "EXP"]):
            g.Rtpc[g.Reg, g.t, g.p, g.Com].where[
                (
                    g.TopIre[g.r, g.c, g.Reg, g.Com, g.p].where[
                        (~(g.RtpVara[g.r, g.t, g.p]))
                    ]
                )
            ] = False
        # * Copy shutdown periods of import process to export regions
        with Loop(
            g.TopIre[g.Reg, g.c, g.r, g.Com, g.p].where[
                g.RpcEqire[g.r, g.p, g.Com, "IMP"]
            ]
        ):
            g.Rtpc[g.Reg, g.t, g.p, g.c].where[(~(g.RtpVara[g.r, g.t, g.p]))] = False
        # * Reset RP_AIRE for distr IRE processes
        g.RpAire[g.RpIre[g.r, g.p], "EXP"].where[
            (g.RpAire[g.r, g.p, "IMP"].where[g.IreDist[g.r, g.p]])
        ] = False
        # * Set IRE_FLOSUM for C if activity has IE flow
        g.ire_flosum[g.Rtp[g.r, g.t, g.p], g.c, g.s, g.ie, g.Com, g.io].where[
            (
                g.RpcPg[g.r, g.p, g.c].where[
                    g.RpAire[g.r, g.p, g.ie]
                    & g.ire_flosum[g.Rtp, pgprim, g.s, g.ie, g.Com, g.io]
                ]
            )
        ] = g.ire_flosum[g.Rtp, pgprim, g.s, g.ie, g.Com, g.io] * (
            1.0 / g.prc_actflo[g.Rtp, g.c]
        )
        g.ire_flosum[g.r, g.t, g.p, pgprim, g.s, g.ie, g.Com, g.io] = 0.0
        # *-----------------------------------------------------------------------------
        # * OK inter-regional trade if in topology
        # * Default values for IRE_FLO by LOOP over TOP_IRE
        with Loop(g.TopIre[g.r, g.c, g.Reg, g.Com, g.p]):  # noqa: SIM117
            with If(
                ~(
                    Sum(
                        Domain(g.Rtp[g.r, g.t, g.p], g.s).where[
                            g.ire_flo[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
                        ],
                        1.0,
                    )
                )
            ):
                g.ire_flo[g.Rtp[g.r, g.v, g.p], g.c, g.Reg, g.Com, g.s].where[
                    g.PrcTs[g.Reg, g.p, g.s]
                ] = 1.0
        # *-----------------------------------------------------------------------------
        # * initialize the commodity balance equation type
        # *   - equality (MAT,ENV,FIN)
        # *   - prodution >= consumption (NRG,DEM)
        # *GG* questions about conservation and renewables being =N= balances?
        # *   - ignored for now (with no equations created)
        # *-----------------------------------------------------------------------------
        # * set the sub-sets of commodities
        g.Nrg[g.Rc[g.r, g.c]].where[g.ComTmap[g.r, "NRG", g.c]] = True
        g.Mat[g.Rc[g.r, g.c]].where[g.ComTmap[g.r, "MAT", g.c]] = True
        g.Dem[g.Rc[g.r, g.c]].where[g.ComTmap[g.r, "DEM", g.c]] = True
        g.Env[g.Rc[g.r, g.c]].where[g.ComTmap[g.r, "ENV", g.c]] = True
        g.Fin[g.Rc[g.r, g.c]].where[g.ComTmap[g.r, "FIN", g.c]] = True
        # * free up if conservation or free energy type, unless provided by the user
        g.Trackc[g.Rc] = True
        with Loop(g.lim):
            g.Trackc[g.r, g.c].where[g.ComLim[g.r, g.c, g.lim]] = False
        g.ComLim[g.Trackc[g.Nrg[g.r, g.c]], "UP"].where[
            (g.NrgTmap[g.r, "CONSRV", g.c] + g.NrgTmap[g.r, "FRERENEW", g.c])
        ] = True
        # * set defaults if not provided by user
        g.Trackc[g.r, g.c].where[g.ComLim[g.r, g.c, "UP"]] = False
        g.ComLim[g.Mat[g.Trackc], "FX"] = True
        g.ComLim[g.Fin[g.Trackc], "FX"] = True
        g.Trackc[g.r, g.c].where[g.ComLim[g.r, g.c, "FX"]] = False
        g.ComLim[g.Trackc, "LO"] = True
        g.Trackc.setRecords(None)

        # handle TIMES-MACRO
        if macro.upper() == "YES":
            g.ComLim[g.Rc[g.Dem], g.bd].where[(~(g.ComLim[g.Rc, "N"]))] = ~(
                g.Bdneq[g.bd]
            )
        if micro.upper() == "YES":
            g.ComLim[g.Rc[g.Dem], g.bd].where[(~(g.ComLim[g.Rc, "N"]))] = ~(
                g.Bdneq[g.bd]
            )
        # *-----------------------------------------------------------------------------
        # * establish inter-regional convert attributes
        # *-----------------------------------------------------------------------------
        # * identify regions trading
        project(source=g.TopIre, target=g.Rreg, direction="left")
        g.Rxx.setRecords(None)
        with Loop(g.Rreg[g.allr, g.allreg]):
            g.z[...] = 1.0
            # * if all regions working with same time-slices, set to 1
            # *  assumption is if have one direction then have the other too
            with Loop(g.tslvl.where[g.z]):
                g.z[...].where[g.z] = Product(
                    g.TsGroup[g.allr, g.tslvl, g.s], g.TsGroup[g.allreg, g.tslvl, g.s]
                )
                g.z[...].where[g.z] = Product(
                    g.TsGroup[g.allreg, g.tslvl, g.s], g.TsGroup[g.allr, g.tslvl, g.s]
                )
                with If(g.z):
                    g.Rxx[g.allr, g.s, g.allreg].where[
                        g.TsGroup[g.allr, g.tslvl, g.s]
                    ] = True
        g.Rxx[g.allr, g.s, g.allreg].where[g.Rxx[g.allreg, g.s, g.allr]] = True
        g.ire_tscvt[g.Rxx[g.allr, g.s, g.allreg], g.s].where[
            (~(g.ire_tscvt[g.allr, g.s, g.allreg, g.s]))
        ] = 1.0
        # * for the conversion of traded commodities, set default to 1
        # *  assumption is if have one direction then have the other too
        project(source=g.ire_ccvt, target=g.RcRc)
        g.ire_ccvt[g.RcRc[g.Rc, g.r, g.c]].where[(~(g.ire_ccvt[g.RcRc]))] = (
            1.0 / g.ire_ccvt[g.r, g.c, g.Rc]
        )
        project(source=g.TopIre, target=g.RcRc, direction="left")
        g.ire_ccvt[g.RcRc].where[(~(g.ire_ccvt[g.RcRc]))] = 1.0
        project(source=g.TopIre, target=g.RcRc)
        g.ire_ccvt[g.RcRc].where[(~(g.ire_ccvt[g.RcRc]))] = 1.0
        # *-----------------------------------------------------------------------------
        # * process bounds to see if aggregation is necessary
        # *-----------------------------------------------------------------------------
        g.putgrp[...] = 0.0
        g.Uncd7.setRecords(None)

    def phase_nineteen(self: PpmainMod, pgprim: str) -> None:
        g = self.tc
        # * Add bounds based on rate levels
        g.flo_bdlvl[g.Rtp, g.cg, g.s, g.bd].where[g.flo_bnd[g.Rtp, g.cg, g.s, g.bd]] = (
            0.0
        )
        g.flo_bnd[g.Rtpc[g.r, g.t, g.p, g.c], g.s, g.bd].where[
            (g.RpcsVar[g.r, g.p, g.c, g.s].where[g.flo_bdlvl[g.Rtpc, g.s, g.bd]])
        ] = g.flo_bdlvl[g.Rtpc, g.s, g.bd] * g.g_yrfr[g.r, g.s] * 8760.0
        g.flo_bnd[g.Rtp[g.r, g.t, g.p], g.cg[g.ComType], g.s, g.bd].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    g.RpIre[g.r, g.p] & g.flo_bdlvl[g.Rtp, g.cg, g.s, g.bd]
                ]
            )
        ] = g.flo_bdlvl[g.Rtp, g.cg, g.s, g.bd] * g.g_yrfr[g.r, g.s] * 8760.0
        # *  ACT_BND(RTP(R,T,P),S,BD)$((RP_STG(R,P)->0)$PRC_TS(R,P,S)$FLO_BDLVL(RTP,pgprim,S,BD)) = FLO_BDLVL(RTP,pgprim,S,BD)*G_YRFR(R,S)*8760;
        g.act_bnd[g.Rtp[g.r, g.t, g.p], g.s, g.bd].where[
            (
                (g.RpStg[g.r, g.p]).where[
                    (~g.PrcTs[g.r, g.p, g.s] | Number(0))
                    & g.flo_bdlvl[g.Rtp, pgprim, g.s, g.bd]
                ]
            )
        ] = g.flo_bdlvl[g.Rtp, pgprim, g.s, g.bd] * g.g_yrfr[g.r, g.s] * 8760.0
        # *-----------------------------------------------------------------------------
        # * process cumulative bounds
        # *-----------------------------------------------------------------------------
        # * process flows: UC_CUMFLO
        g.uc_cumflo[
            g.ucn,
            g.r,
            g.p,
            g.c,
            g.bohyear + g.beoh[g.bohyear],
            g.eohyear + g.beoh[g.eohyear],
        ] = sparse(g.uc_cumflo[g.ucn, g.r, g.p, g.c, g.bohyear, g.eohyear])
        g.uc_cumflo[g.ucn, g.r, g.p, g.c, g.bohyear, g.eohyear].where[
            (~(g.ll[g.bohyear] * g.ll[g.eohyear]))
        ] = 0.0
        g.uc_cumflo[
            g.ucn,
            g.r,
            g.p,
            pgprim,
            g.bohyear + g.beoh[g.bohyear],
            g.eohyear + g.beoh[g.eohyear],
        ] = sparse(g.uc_cumact[g.ucn, g.r, g.p, g.bohyear, g.eohyear])
        with Loop(
            Domain(g.ucn, g.Rp, g.c, g.year, g.ll).where[
                g.uc_cumflo[g.ucn, g.Rp, g.c, g.year, g.ll]
            ]
        ):
            g.RpcCumflo[g.Rp, g.c, g.year, g.ll] = True
        # * process flows: FLO_CUM
        g.flo_cum[
            g.r,
            g.p,
            g.c,
            g.bohyear + g.beoh[g.bohyear],
            g.eohyear + g.beoh[g.eohyear],
            g.lA,
        ] = sparse(g.flo_cum[g.r, g.p, g.c, g.bohyear, g.eohyear, g.lA])
        g.flo_cum[g.r, g.p, g.c, g.bohyear, g.eohyear, g.lA].where[
            (~(g.ll[g.bohyear] * g.ll[g.eohyear]))
        ] = 0.0
        g.flo_cum[
            g.r,
            g.p,
            pgprim,
            g.bohyear + g.beoh[g.bohyear],
            g.eohyear + g.beoh[g.eohyear],
            g.lA,
        ] = sparse(g.act_cum[g.r, g.p, g.bohyear, g.eohyear, g.lA])
        g.RpcCumflo[g.Rp, g.c, g.year, g.ll] = sparse(
            Sum(g.lA.where[g.flo_cum[g.Rp, g.c, g.year, g.ll, g.lA]], True)
        )
        g.uc_cumact.setRecords(None)
        g.act_cum.setRecords(None)
        # * commodities: UC_CUMCOM
        g.uc_cumcom[
            g.ucn,
            g.r,
            g.comvar,
            g.c,
            g.bohyear + g.beoh[g.bohyear],
            g.eohyear + g.beoh[g.eohyear],
        ] = sparse(g.uc_cumcom[g.ucn, g.r, g.comvar, g.c, g.bohyear, g.eohyear])
        g.uc_cumcom[g.ucn, g.r, g.comvar, g.c, g.bohyear, g.eohyear].where[
            (~(g.ll[g.bohyear] * g.ll[g.eohyear] * g.Rc[g.r, g.c]))
        ] = 0.0
        with Loop(
            Domain(g.ucn, g.r, g.comvar, g.c, g.year, g.ll).where[
                g.uc_cumcom[g.ucn, g.r, g.comvar, g.c, g.year, g.ll]
            ]
        ):
            g.RcCumcom[g.r, g.comvar, g.year, g.ll, g.c] = True
        # * commodities: COM_CUMNET/COM_CUMPRD
        g.com_cum[
            g.r,
            "NET",
            g.year[g.bohyear + g.beoh[g.bohyear]],
            g.ll[g.eohyear + g.beoh[g.eohyear]],
            g.c,
            g.lA,
        ] = sparse(g.com_cumnet[g.r, g.bohyear, g.eohyear, g.c, g.lA])
        g.com_cum[
            g.r,
            "PRD",
            g.year[g.bohyear + g.beoh[g.bohyear]],
            g.ll[g.eohyear + g.beoh[g.eohyear]],
            g.c,
            g.lA,
        ] = sparse(g.com_cumprd[g.r, g.bohyear, g.eohyear, g.c, g.lA])
        g.com_cumnet.setRecords(None)
        g.com_cumprd.setRecords(None)
        g.RcCumcom[g.r, g.comvar, g.year, g.ll[g.eohyear], g.c] = sparse(
            Sum(g.lA.where[g.com_cum[g.r, g.comvar, g.year, g.ll, g.c, g.lA]], True)
        )
        # *-----------------------------------------------------------------------------
        # * determine if VAR_COMxxx needed on RHS of EQ_COM equations
        # *-----------------------------------------------------------------------------
        # * commodities aggregated by COM_AGG
        with Loop(Domain(g.r, g.t, g.c, g.Com).where[g.com_agg[g.r, g.t, g.c, g.Com]]):
            g.RcAgp[g.ComLim[g.r, g.c, g.lim]] = True
        g.RcAgp[g.r, g.c, g.bd].where[
            (g.ComTmap[g.r, "DEM", g.c].where[g.RcAgp[g.r, g.c, "LO"]])
        ] = ~(g.Bdneq[g.bd])
        g.RcAgp[g.Rc, "FX"].where[g.RcAgp[g.Rc, "N"]] = True
        g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[g.RcAgp[g.r, g.c, "LO"]] = (
            True
        )
        g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[g.RcAgp[g.r, g.c, "FX"]] = (
            True
        )

    def phase_twenty(
        self: PpmainMod, dam_elast_defined: bool, obj_eq_lin: bool, pgprim: str
    ) -> None:
        g = self.tc
        # * commodities involved in DAM comprod
        if dam_elast_defined:
            g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[
                g.dam_elast[g.r, g.c, "N"]
            ] = True
        # * commodities involved in CUM constraints
        with Loop(g.RcCumcom[g.r, "NET", g.allyear, g.ll, g.c]):
            g.RtcNet[g.r, g.t, g.c].where[
                ((g.e[g.t] >= g.yearval[g.allyear]) * (g.b[g.t] <= g.yearval[g.ll]))
            ] = True
            if obj_eq_lin:
                g.RtcNet[g.r, g.t, g.c].where[
                    (
                        (g.m[g.t] + g.lagt[g.t] > g.yearval[g.allyear])
                        * (g.m[g.t] - g.lead[g.t] < g.yearval[g.ll])
                    )
                ] = True
        with Loop(g.RcCumcom[g.r, "PRD", g.allyear, g.ll, g.c]):
            g.RtcPrd[g.r, g.t, g.c].where[
                ((g.e[g.t] >= g.yearval[g.allyear]) * (g.b[g.t] <= g.yearval[g.ll]))
            ] = True
            if obj_eq_lin:
                g.RtcPrd[g.r, g.t, g.c].where[
                    (
                        (g.m[g.t] + g.lagt[g.t] > g.yearval[g.allyear])
                        * (g.m[g.t] - g.lead[g.t] < g.yearval[g.ll])
                    )
                ] = True
        # * check all TS at/above COM_TSL for bounds
        g.RhsCombal[g.RtcsVarc[g.RtcNet, g.s]] = True
        g.com_cstnet[
            g.r,
            g.ll.lag(Ord(g.ll), "circular"),
            g.c,
            g.s.lag(Ord(g.s), "circular"),
            g.cur,
        ].where[
            (
                g.com_cstnet[g.r, g.ll, g.c, g.s, g.cur]
                + g.com_subnet[g.r, g.ll, g.c, g.s, g.cur]
                + g.com_taxnet[g.r, g.ll, g.c, g.s, g.cur]
            )
        ] = SpecialValues.EPS
        with Loop(
            Domain(g.r, g.c, g.s, g.Rdcur[g.r, g.cur]).where[
                g.com_cstnet[g.r, "0", g.c, g.s, g.cur]
            ]
        ):
            g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.ts]] = True
        g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[
            Sum(
                Domain(g.TsMap[g.r, g.ts, g.s], g.bd).where[
                    g.com_bndnet[g.r, g.t, g.c, g.ts, g.bd]
                ],
                abs(g.com_bndnet[g.r, g.t, g.c, g.ts, g.bd])
                != Number(SpecialValues.POSINF).where[g.Bdupx[g.bd]],
            )
        ] = True
        g.RhsComprd[g.RtcsVarc[g.RtcPrd, g.s]] = True
        g.com_cstprd[
            g.r,
            g.ll.lag(Ord(g.ll), "circular"),
            g.c,
            g.s.lag(Ord(g.s), "circular"),
            g.cur,
        ].where[
            (
                g.com_cstprd[g.r, g.ll, g.c, g.s, g.cur]
                + g.com_subprd[g.r, g.ll, g.c, g.s, g.cur]
                + g.com_taxprd[g.r, g.ll, g.c, g.s, g.cur]
            )
        ] = SpecialValues.EPS
        with Loop(
            Domain(g.r, g.c, g.s, g.Rdcur[g.r, g.cur]).where[
                g.com_cstprd[g.r, "0", g.c, g.s, g.cur]
            ]
        ):
            g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.ts]] = True
        g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[
            Sum(
                Domain(g.TsMap[g.r, g.ts, g.s], g.bd).where[
                    g.com_bndprd[g.r, g.t, g.c, g.ts, g.bd]
                ],
                (abs(g.com_bndprd[g.r, g.t, g.c, g.ts, g.bd]) != SpecialValues.POSINF)
                & (
                    g.com_bndprd[g.r, g.t, g.c, g.ts, g.bd]
                    != Number(SpecialValues.NA).where[g.Bdupx[g.bd]]
                ),
            )
        ] = True
        # *-----------------------------------------------------------------------------
        # * Storage
        # *-----------------------------------------------------------------------------
        # * Remove standard flow variables from genuine storage charge/discharge flows
        g.RtpcsOut[g.Rtp[g.r, g.t, g.p], g.c, g.s].where[
            (g.RpcsVar[g.r, g.p, g.c, g.s].where[g.RpcStg[g.r, g.p, g.c]])
        ] = True
        # * Prepare demand sifting storages
        project(source=g.stg_sift, target=g.Trackpc)
        g.Trackpc[g.Rp, g.c].where[
            (
                ~(
                    (
                        g.Top[g.Rp, g.c, "OUT"].where[g.RpcStg[g.Rp, g.c]]
                        + g.Actcg[g.c]
                    ).where[g.RpStg[g.Rp]]
                )
            )
        ] = False
        g.Trackpc[g.Rp, g.c].where[g.PrcNstts[g.Rp, "ANNUAL"]] = False
        with Loop(g.Trackpc[g.r, g.p, g.c]):
            g.Trackp[g.r, g.p] = True
            g.RpcPkc[g.r, g.p, g.c] = False
            g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]] = True
        g.RpcSpg[g.RpcStg[g.Trackp, g.c]] = True
        set_options({"VALIDATION": 0})
        g.RpcStgn[g.Top[g.RpcStg[g.RpcSpg[g.Rp, g.c]], g.io]].where[
            g.Top[g.Rp, g.c, "IN"]
        ] = (g.Trackpc[g.Rp, g.c] & g.ips[g.io]) | (
            ~g.Trackpc[g.Rp, g.c] & ~g.ips[g.io]
        )
        set_options({"VALIDATION": 1})

        with Loop(g.PrcTsl[g.Trackp[g.Rp[g.r, g.p]], g.tslvl]):
            g.RpSts[g.Rp] = False
            g.RpStg[g.Rp] = False
            g.z[...] = 1.0 - Sum(g.RpcsVar[g.Rp, g.c, g.Annual], 2.0)
            with Loop(g.Top[g.RpcStg[g.Rp, g.c], "IN"]):
                with If(g.z > 0.0):
                    g.RpcLs[g.Rp, g.c] = True
                g.z[...] = g.z - 1.0
            g.RpcLs[g.Rp, g.c[g.Actcg]].where[g.z] = True
            # * Levelize STG_SIFT(ACT)
            with Loop(g.Trackpc[g.Rp, g.c[g.Actcg]]):
                g.f[...] = Sum(g.Rlup[g.r, g.tslvl, g.tsl], Ord(g.tsl) - 1.0)
                with If(g.f == 0.0):
                    g.f[...] = g.z
                with Loop(g.Rjlvl[g.j, g.r, g.tsl].where[(g.f >= Ord(g.tsl))]):  # noqa: SIM117
                    with Loop(g.TsGroup[g.r, g.tsl, g.ts]):
                        g.stg_sift[g.r, g.t, g.p, g.c, g.s].where[
                            ~g.stg_sift[g.r, g.t, g.p, g.c, g.s]
                        ] = sparse(
                            g.stg_sift[g.r, g.t, g.p, g.c, g.ts].where[
                                (g.stoal[g.r, g.s] == g.f) & g.RsBelow[g.r, g.ts, g.s]
                            ]
                        )
                g.stg_sift[g.r, g.t, g.p, g.c, g.s].where[
                    (g.stoal[g.r, g.s] != g.f)
                ] = 0.0
            g.act_time[g.Rtp[g.r, g.t, g.p], "LO"].where[
                (g.act_time[g.Rtp, "UP"] == 0.0)
            ] = 0.0
            g.act_time[g.Rtp[g.r, g.t, g.p], g.bd].where[g.act_time[g.Rtp, "FX"]] = (
                g.act_time[g.Rtp, "FX"].where[g.Bdupx[g.bd]]
            )
        g.RpcLs[g.Rpc[g.Rp, g.c]].where[g.RpcLs[g.Rp, pgprim]] = False
        # * Controls for flexible general storage
        g.RpsStg[g.PrcTs[g.RpStg, g.ts]] = True
        g.RpsStg[g.r, g.p, g.Annual].where[g.PrcMap[g.r, "STK", g.p]] = False
        g.RpSts[g.r, g.p].where[g.PrcTsl[g.r, g.p, "ANNUAL"]] = False
        with Loop(g.RpSts[g.r, g.p]):
            g.PrcTs[g.RpsPrcts[g.r, g.p, g.s]].where[g.stoa[g.s]] = True
            g.PrcTs[g.r, g.p, g.Annual].where[g.PrcMap[g.r, "STK", g.p]] = True
            g.PrcStgtss[g.PrcStgips[g.r, g.p, g.c]] = True
            g.stg_loss[g.r, g.v, g.p, g.s].where[g.stg_loss[g.r, g.v, g.p, g.s]] = -abs(
                g.stg_loss[g.r, g.v, g.p, g.s]
            )
        g.RpStl[g.RpSts[g.Rp], g.tsl + 1, "N"].where[
            (g.prc_sgl[g.Rp] >= Ord(g.tsl))
        ] = True
        g.ncap_af[g.Rtp[g.r, g.v, g.p], g.s, g.bd].where[
            ((~(g.RpsStg[g.r, g.p, g.s])).where[g.RpSts[g.r, g.p]])
        ] = g.ncap_afs[g.Rtp, g.s, g.bd]
        # * Levelization of STG_LOSS and STG_SIFT
        g.Trackp[g.RpStg].where[(~(g.RpSts[g.RpStg]))] = True

    def phase_twentyone(self: PpmainMod) -> None:
        g = self.tc
        # * Levelized UC_RHSRTS
        with Loop(g.t):
            g.UcTsl[g.r, g.ucn, g.side, g.tsl].where[g.UcTSucc[g.r, g.ucn, g.t]] = False
        project(source=g.UcTsl, target=g.UcDs)
        project(source=g.UcDs, target=g.RUc)
        project(source=g.RUc, target=g.Mreg)
        g.UcTsl[g.RUc, "LHS", g.tsl] = sparse(g.UcDs[g.RUc, g.tsl])
        with Loop(  # noqa: SIM117
            Domain(g.Rjlvl[g.j, g.r[g.Mreg], g.tslvl], g.tsl).where[
                (Ord(g.tsl) > Ord(g.tslvl))
            ]
        ):
            with Loop(g.TsGroup[g.r, g.tslvl, g.ts]):
                g.uc_rhsrts[g.RUc[g.r, g.ucn], g.t, g.s, g.lA].where[
                    (~(g.uc_rhsrts[g.RUc, g.t, g.s, g.lA])).where[g.UcDs[g.RUc, g.tsl]]
                ] = sparse(
                    g.uc_rhsrts[g.RUc, g.t, g.ts, g.lA].where[
                        g.RsBelow[g.r, g.ts, g.s] & g.TsGroup[g.r, g.tsl, g.s]
                    ]
                )
        with Loop(
            g.UcDs[g.RUc[g.r, g.ucn], g.tsl].where[Sum(g.UcTsEach[g.RUc, g.s], 1.0)]
        ):
            g.uc_rhsrts[g.RUc, g.t, g.s, g.lA].where[
                ((~(g.UcTsEach[g.RUc, g.s])).where[g.TsGroup[g.r, g.tsl, g.s]])
            ] = 0.0
        g.UcTsEach[g.RUc, g.s] = False
        g.UcAttr[g.RUc, g.side, g.ucgrptype, g.ucname[g.tsl]] = False
        # * Support for the obsolete
        g.uc_rhs[g.ucn, g.lA].where[~(g.uc_rhs[g.ucn, g.lA])] = sparse(
            g.uc_rhss[g.ucn, "ANNUAL", g.lA]
        )
        g.uc_rhsr[g.r, g.ucn, g.lA].where[~(g.uc_rhsr[g.r, g.ucn, g.lA])] = sparse(
            g.uc_rhsrs[g.r, g.ucn, "ANNUAL", g.lA]
        )
        # * --- Set UC_R_EACH / UC_R_SUM defaults
        g.uncd1.setRecords(None)
        g.uncd1[g.ucn].where[(~(Sum(g.UcREach[g.allr, g.ucn], 1.0)))] = True
        g.UcOn[g.r, g.ucn].where[Sum(g.lA.where[g.uc_rhsr[g.r, g.ucn, g.lA]], 1.0)] = (
            True
        )
        g.UcOn[g.r, g.ucn].where[
            Sum(Domain(g.t, g.lA).where[g.uc_rhsrt[g.r, g.ucn, g.t, g.lA]], 1.0)
        ] = True
        g.UcOn[g.r, g.ucn].where[
            Sum(
                Domain(g.t, g.s, g.lA).where[g.uc_rhsrts[g.r, g.ucn, g.t, g.s, g.lA]],
                1.0,
            )
        ] = True
        g.UcREach[g.r, g.ucn].where[(~(g.UcOn[g.r, g.ucn]))] = False
        g.UcREach[g.UcOn[g.r, g.ucn]] = sparse(g.uncd1[g.ucn])
        g.uncd1.setRecords(None)
        g.uncd1[g.ucn].where[(~(Sum(g.UcRSum[g.allr, g.ucn], 1.0)))] = True
        g.UcDt[g.r, g.ucn].where[Sum(g.lA.where[g.uc_rhs[g.ucn, g.lA]], 1.0)] = True
        g.UcDt[g.r, g.ucn].where[
            Sum(Domain(g.t, g.lA).where[g.uc_rhst[g.ucn, g.t, g.lA]], 1.0)
        ] = True
        g.UcDt[g.r, g.ucn].where[
            Sum(Domain(g.t, g.s, g.lA).where[g.uc_rhsts[g.ucn, g.t, g.s, g.lA]], 1.0)
        ] = True
        g.UcRSum[g.r, g.ucn].where[(~(g.UcDt[g.r, g.ucn]))] = False
        g.UcRSum[g.UcDt[g.r, g.ucn]] = sparse(g.uncd1[g.ucn])
        g.UcDt.setRecords(None)
        project(source=g.UcREach, target=g.UcOn)
        g.UcOn[g.UcRSum] = True
        # * --- Set UC_TS_EACH / UC_TS_SUM defaults
        g.UcDt[g.UcRSum[g.r, g.ucn]].where[
            (
                (~(Sum(g.UcTsSum[g.r, g.ucn, g.s], 1.0))).where[
                    (~(Sum(g.UcTsEach[g.r, g.ucn, g.s], 1.0)))
                ]
            )
        ] = True
        g.UcTsEach[g.UcDt[g.r, g.ucn], g.Annual].where[
            Sum(g.lA.where[g.uc_rhs[g.ucn, g.lA]], 1.0)
        ] = True
        g.UcTsEach[g.UcDt[g.r, g.ucn], g.s].where[
            Sum(Domain(g.t, g.lA).where[g.uc_rhsts[g.ucn, g.t, g.s, g.lA]], 1.0)
        ] = True
        g.UcTsSum[g.UcDt[g.r, g.ucn], g.Annual].where[
            Sum(Domain(g.t, g.lA).where[g.uc_rhst[g.ucn, g.t, g.lA]], 1.0)
        ] = True
        g.UcDt[g.UcRSum].where[(~(g.UcREach[g.UcRSum]))] = False
        g.UcDt[g.UcREach[g.r, g.ucn]].where[
            (
                (~(Sum(g.UcTsSum[g.r, g.ucn, g.s], 1.0))).where[
                    (~(Sum(g.UcTsEach[g.r, g.ucn, g.s], 1.0)))
                ]
            )
        ] = True
        g.UcTsSum[g.UcDt, g.Annual].where[
            Sum(Domain(g.t, g.lA).where[g.uc_rhsrt[g.UcDt, g.t, g.lA]], 1.0)
        ] = True
        g.UcTsEach[g.UcDt, g.Annual].where[
            Sum(g.lA.where[g.uc_rhsr[g.UcDt, g.lA]], 1.0)
        ] = True
        g.UcDt[g.RUc] = False
        g.UcTsEach[g.UcDt, g.s].where[
            Sum(Domain(g.t, g.lA).where[g.uc_rhsrts[g.UcDt, g.t, g.s, g.lA]], 1.0)
        ] = True
        # * --- Set UC_T_EACH / UC_T_SUM defaults
        # * Assume T_EACH and T_SUCC cannot be used at the same time; Let T_SUCC override T_EACH.
        # * First, copy T_SUCC to T_EACH to reduce testing in what follows:
        g.UcTEach[g.UcTSucc] = True
        project(source=g.UcOn, target=g.UcDt)
        g.UcDt[g.UcDt].where[Sum(g.UcTEach[g.UcDt, g.t], 1.0)] = False
        g.UcDt[g.UcDt].where[Sum(g.UcTSum[g.UcDt, g.t], 1.0)] = False
        g.UcTSum[g.UcRSum[g.UcDt[g.r, g.ucn]], g.t].where[
            Sum(g.lA.where[g.uc_rhs[g.ucn, g.lA]], 1.0)
        ] = True
        g.UcTSum[g.UcREach[g.UcDt], g.t].where[
            Sum(g.lA.where[g.uc_rhsr[g.UcDt, g.lA]], 1.0)
        ] = True
        g.UcTEach[g.UcDt, g.t].where[(~(g.UcTSum[g.UcDt, g.t]))] = True
        # * Defaults for cumulative UCs
        g.Mreg.setRecords(None)
        g.UcDt.setRecords(None)
        with Loop(g.t):
            g.UcDt[g.r, g.ucn].where[
                (g.UcTsEach[g.r, g.ucn, "ANNUAL"].where[g.UcTSum[g.r, g.ucn, g.t]])
            ] = True
        g.UcTsSum[g.UcDt, g.Annual] = True
        g.UcTsEach[g.UcTsSum[g.r, g.ucn, g.Annual]] = False
        g.UcDt[g.RUc].where[g.UcDs[g.RUc, "ANNUAL"]] = False
        g.UcAttr[g.UcDt, g.side, g.ucgrptype, "PERIOD"].where[
            (~(same_as(g.ucgrptype, "NCAP")))
        ] = False
        g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, g.UcCost] = sparse(
            Sum(
                g.UcMapcost[g.UcCost, g.ucname],
                g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, g.ucname],
            )
        )
        # * If the GROWTH attribute is specified, substitute T_SUCC for T_EACH:
        with Loop(g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, "GROWTH"]):
            g.UcDyndir[g.r, g.ucn, g.side] = True
        # * Prepare for the CUMSUM UC attribute. Supported only for UCs with RHS dyndir:
        g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, "PERIOD"].where[
            g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, "CUMSUM"]
        ] = ~(g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, "ANNUL"])
        g.UcAttr[g.r, g.ucn, g.side, "NCAP", "CUMSUM"].where[
            g.UcAttr[g.r, g.ucn, g.side, "NCAP", "ANNUL"]
        ] = True
        g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "CUM+"].where[
            (
                g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "SYNC"].where[
                    g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "CUMSUM"]
                ]
            )
        ] = True
        g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "CUMSUM"].where[
            g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "CUM+"]
        ] = False
        # * Set all UCs that have RHS attributes to be dynamic, if not already so defined
        g.Rxx.setRecords(None)
        with Loop(g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, g.ucname]):
            g.Rxx[g.r, g.ucn, "RHS"] = True
        with Loop(g.t):
            g.Rxx[g.r, g.ucn, "RHS"].where[g.UcTSucc[g.r, g.ucn, g.t]] = False
        g.UcDyndir[g.Rxx[g.r, g.ucn, "RHS"]] = True
        with Loop(g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, g.UcDynt]):
            g.UcDyndir[g.r, g.ucn, "RHS"] = True
        g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "N"].where[
            g.UcAttr[g.r, g.ucn, "RHS", g.ucgrptype, "SYNC"]
        ] = True
        # * Remove RHS from DYNDIR if LHS present:
        g.UcDyndir[g.r, g.ucn, "RHS"].where[g.UcDyndir[g.r, g.ucn, "LHS"]] = False
        g.UcTsl[g.UcDyndir[g.RUc, "RHS"], g.tsl].where[g.UcDs[g.RUc, g.tsl]] = True
        g.UcDyndir[g.RUc, g.side] = False
        # * Add implicit T_SUCC and remove T_EACH whenever T_SUCC
        g.UcTSucc[g.UcTEach[g.r, g.ucn, g.t]] = sparse(
            Sum(g.UcDyndir[g.r, g.ucn, g.side], 1.0)
        )
        g.UcTSucc[g.UcTEach[g.r, g.ucn, g.t]].where[g.UcRSum[g.r, g.ucn]] = sparse(
            Sum(g.UcTSucc[g.UcRSum[g.Reg, g.ucn], g.t], 1.0)
        )
        g.UcTEach[g.UcTSucc] = False
        # * Remove last MILESTONYR from UC_T_SUCC unless RHS-based:
        g.UcTSucc[g.UcTSucc[g.r, g.ucn, g.t]].where[(Ord(g.t) == Card(g.t))] = (
            g.UcDyndir[g.r, g.ucn, "RHS"]
        )
        g.RsPrev[g.r, g.s, g.s.lag(g.rs_stg[g.r, g.s], "circular")] = sparse(
            g.rs_tslvl[g.r, g.s]
        )
        g.GUds[g.s, "LHS", g.s] = True
        with Loop(g.r.where[Sum(g.UcTsl[g.r, g.ucn, "RHS", g.tsl], 1.0)]):
            g.GUds[g.s, "RHS", g.ts].where[g.RsPrev[g.r, g.s, g.ts]] = True

    def phase_twentytwo(self: PpmainMod) -> None:
        g = self.tc
        # * FLO / IRE / COM
        project(source=g.uc_flo, target=g.UcMapFlo)
        g.UcQaflo["1", g.UcMapFlo[g.ucn, g.side, g.RpIre[g.r, g.p], g.c]] = True
        g.UcCapflo[g.ucn, g.side, g.r, g.p, g.c].where[
            (~(g.UcMapFlo[g.ucn, g.side, g.r, g.p, g.c]))
        ] = False
        g.UcMapFlo[g.ucn, g.side, g.RpIre, g.c] = False
        project(source=g.uc_ire, target=g.UcMapIre)
        g.UcQaflo["2", g.ucn, "LHS", g.RpFlo, g.c] = sparse(
            Sum(g.UcMapIre[g.ucn, g.RpFlo, g.c, g.ie], 1.0)
        )
        g.UcMapIre[g.ucn, g.r, g.p, g.c, g.ie].where[
            (~(g.RpcIre[g.r, g.p, g.c, g.ie]))
        ] = False
        project(source=g.uc_com, target=g.UcGmapC)
        g.UcAttr[g.r, g.ucn, g.side, g.ucgrptype, g.UcDynt].where[
            g.UcAttr[g.r, g.ucn, g.side, "COMCON", g.UcDynt]
        ] = sparse(
            Sum(
                g.UcGmapC[g.r, g.ucn, g.comvar, g.c, "COMCON"].where[
                    g.CovMap[g.comvar, g.ucgrptype]
                ],
                1.0,
            )
        )
        # * ACT / CAP / NCAP
        g.UcJmap[
            "2", g.ucn, g.side, g.r, g.t.lag(Ord(g.t), "circular"), g.p, "ACT"
        ].where[g.UcOn[g.r, g.ucn]] = sparse(
            Sum(g.s.where[g.uc_act[g.ucn, g.side, g.r, g.t, g.p, g.s]], 1.0)
        )
        g.UcJmap[
            "3", g.ucn, g.side, g.r, g.t.lag(Ord(g.t), "circular"), g.p, "CAP"
        ].where[g.UcOn[g.r, g.ucn]] = sparse(g.uc_cap[g.ucn, g.side, g.r, g.t, g.p])
        g.UcJmap[
            "4", g.ucn, g.side, g.r, g.t.lag(Ord(g.t), "circular"), g.p, "NCAP"
        ].where[g.UcOn[g.r, g.ucn]] = sparse(g.uc_ncap[g.ucn, g.side, g.r, g.t, g.p])
        project(source=g.UcJmap, target=g.UcGmapP)
        # * Mark those processes that have UC_CAP / COMXXX to also have VAR_CAP / VAR_COMXXX
        with Loop(g.UcGmapP[g.r, g.ucn, "CAP", g.p]):
            g.Trackp[g.r, g.p] = True
        g.RtpVarp[g.Rtp[g.r, g.t, g.p]].where[g.Trackp[g.r, g.p]] = True
        g.Trackp.setRecords(None)
        g.Rxx.setRecords(None)
        g.UcJmap.setRecords(None)
        g.UcOn[g.r, g.ucn] = sparse(Sum(g.UcDynbnd[g.ucn, g.lA], 1.0))
        with Loop(g.UcGmapC[g.UcOn[g.r, g.ucn], g.comvar, g.c, g.ucgrptype]):
            g.Rxx[g.r, g.comvar, g.c] = True
        g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[g.Rxx[g.r, "PRD", g.c]] = True
        g.Rxx[g.r, "NET", g.c].where[g.ComLim[g.r, g.c, "FX"]] = False
        g.Rxx[g.r, "PRD", g.c].where[(~(g.ComLim[g.r, g.c, "LO"]))] = False
        with Loop(g.comvar):
            g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[
                g.Rxx[g.r, g.comvar, g.c]
            ] = True

    def phase_twentythree(self: PpmainMod) -> None:
        g = self.tc
        # * for each refined product determine SPEcifications used from TYPE since required
        g.BleSpe[g.r, g.Com, g.spe].where[g.bl_type[g.r, g.Com, g.spe]] = True
        # ******************************************************************************
        # *  do initialization for BLENDing (interpolation in preppm.mod)
        # ******************************************************************************
        g.refunit[g.r].where[(~(g.refunit[g.r]))] = 1.0
        # * initialize defaults START period and UNIT type
        with Loop(g.BleSpe[g.r, g.Ble, g.spe]):
            g.BleTp[g.r, g.t, g.Ble].where[
                (g.yearval[g.t] >= g.bl_start[g.r, g.Ble, g.spe])
            ] = True
        g.bl_unit[g.BleSpe[g.r, g.Ble, g.spe]].where[
            (~(g.bl_unit[g.r, g.Ble, g.spe]))
        ] = 1.0
        # *** ONLY TID FOR NOW ***
        # * set time-dependent blending SPEcificiation from TID if not provided
        # *TBL_SPEC(BLE_SPE(BLE,SPE),TP)$(BL_SPEC(BLE,SPE) AND (NOT TBL_SPEC(BLE,SPE,TP))) =
        # *         BL_SPEC(BLE,SPE);
        # ** set time-dependent 3-tuple
        g.BleSpeopr[g.BleSpe[g.r, g.Ble, g.spe], g.Opr].where[
            g.bl_com[g.r, g.Ble, g.Opr, g.spe]
        ] = True
        # *BLE_SPEOPR(BLE,SPE,OPR)$(BL_COM(BLE,OPR,SPE) OR
        # *                                  SUM(YEAR,TBL_COM(BLE,SPE,OPR,YEAR))) = YES;
        # *TBL_COM(BLE_SPEOPR(BLE,SPE,OPR),TP)$(BL_COM(BLE,OPR,SPE) AND
        # *                 (NOT TBL_COM(BLE,SPE,OPR,TP))) = BL_COM(BLE,OPR,SPE);
        # *
        # ** assumed BLEND INP not SPE dependent, and that values are to be summed for BLE
        # *BLE_INP(BLE,COM)$(BL_INP(BLE,COM) OR SUM((SPE,YEAR),TBL_INP(BLE,SPE,COM,YEAR)))
        # *                = YES;
        g.BleSpeinp[g.r, g.Ble, g.spe, g.Com].where[
            (g.BleSpe[g.r, g.Ble, g.spe] * g.BleInp[g.r, g.Ble, g.Com])
        ] = True
        # **TBL_INP(BLE_SPE(BLE,SPE),COM,TP) = BL_INP(BLE,COM) + TBL_INP(BLE,SPE,COM,TP);
        # *TBL_INPT(BLE_INP(BLE,ELC),TP) = BL_INP(BLE,ELC) +
        # *                                SUM(BLE_SPE(BLE,SPE), TBL_INP(BLE,SPE,ELC,TP));
        # *
        # **  assume that values are to be summed
        # *TBL_VAROMT(BLE,TP) = BL_VAROM(BLE) + SUM(BLE_SPE(BLE,SPE), TBL_VAROM(BLE,SPE,TP));
        # *
        # **  DELIV assume that values are to be summed
        # *TBL_DELIV(BLE_SPE(BLE,SPE),COM,TP) = BL_DELIV(BLE,COM) +
        # *                                     TBL_DELIV(BLE,SPE,COM,TP);
        # *TBL_DELIVT(BLE,COM,TP) =  SUM(SPE$BLE_SPE(BLE,SPE),
        # *                          TBL_INP(BLE,SPE,COM,TP) * TBL_DELIV(BLE,SPE,COM,TP));
        # *
        # ** setup BLE/OPR combination and handle the emissions
        with Loop(g.BleSpeopr[g.r, g.Ble, g.spe, g.Opr]):
            g.BleOpr[g.r, g.Ble, g.Opr] = True
        with Loop(g.BleOpr[g.r, g.Ble, g.Opr]):
            g.BleEnv[g.r, g.c, g.Ble, g.Opr].where[
                (g.Env[g.r, g.c] * Sum(g.t, g.env_bl[g.r, g.c, g.Ble, g.Opr, g.t]))
            ] = True
        # * handle peakda, setting to 1 if uses COM_PEAK but no value provided
        g.peakda_bl[g.r, g.Ble, g.t].where[
            (
                (~(g.peakda_bl[g.r, g.Ble, g.t])).where[
                    Sum(g.ComPeak[g.r, g.c].where[g.BleInp[g.r, g.Ble, g.c]], 1.0)
                ]
            )
        ] = 1.0

    def phase_twentyfour(self: PpmainMod) -> None:
        g = self.tc
        # * balance of energy carriers
        g.ble_bal[g.BleTp[g.r, g.t, g.Ble], g.opr2].where[g.Opr[g.Ble]] = 1.0
        g.ble_bal[g.BleTp[g.r, g.t, g.Ble], g.opr2].where[(~(g.Opr[g.Ble]))] = (
            Number(1.0).where[(g.refunit[g.r] == 1.0)]
            + g.convert[g.opr2, "WCV"].where[(g.refunit[g.r] == 2.0)]
            + g.convert[g.opr2, "VCV"].where[(g.refunit[g.r] == 3.0)]
        )
        # * create the REFUNIT/BL_UNIT and FEQ convert look-up tables
        # * volume
        with Loop(g.r):
            with If(g.refunit[g.r] == 3.0):
                g.ru_cvt[g.BleSpeopr[g.r, g.Ble, g.spe, g.Opr]] = (
                    Number(1.0).where[(g.bl_unit[g.r, g.Ble, g.spe] == 3.0)]
                    + g.convert[g.Opr, "DENS"].where[
                        (g.bl_unit[g.r, g.Ble, g.spe] == 2.0)
                    ]
                    + g.convert[g.Opr, "VCV"].where[
                        (g.bl_unit[g.r, g.Ble, g.spe] == 1.0)
                    ]
                )
                g.ru_feq[g.r, g.Opr, g.t] = g.convert[g.Opr, "VCV"]
            # * weight
            with If(g.refunit[g.r] == 2.0):
                g.ru_cvt[g.BleSpeopr[g.r, g.Ble, g.spe, g.Opr]] = (
                    (1.0 / g.convert[g.Opr, "DENS"]).where[
                        (g.bl_unit[g.r, g.Ble, g.spe] == 3.0)
                    ]
                    + Number(1.0).where[(g.bl_unit[g.r, g.Ble, g.spe] == 2.0)]
                    + g.convert[g.Opr, "WCV"].where[
                        (g.bl_unit[g.r, g.Ble, g.spe] == 1.0)
                    ]
                )
                g.ru_feq[g.r, g.Opr, g.t] = g.convert[g.Opr, "WCV"]
            # * energy
            with If(g.refunit[g.r] == 1.0):
                g.ru_cvt[g.BleSpeopr[g.r, g.Ble, g.spe, g.Opr]] = (
                    (1.0 / g.convert[g.Opr, "VCV"]).where[
                        (g.bl_unit[g.r, g.Ble, g.spe] == 3.0)
                    ]
                    + (1.0 / g.convert[g.Opr, "WCV"]).where[
                        (g.bl_unit[g.r, g.Ble, g.spe] == 2.0)
                    ]
                    + Number(1.0).where[(g.bl_unit[g.r, g.Ble, g.spe] == 1.0)]
                )
                g.ru_feq[g.r, g.Opr, g.t] = 1.0
        g.ru_feq[g.r, g.Opr, g.t].where[(~(g.ru_feq[g.r, g.Opr, g.t]))] = 1.0
        # *----------------------------------------------------------------
        # * Call reduction algorithm and determine vintaging for processes
        # *----------------------------------------------------------------
        project(source=g.RtpCptyr, target=g.Rvp)
        g.RtpVara[g.r, g.t, g.p].where[(~(g.Rvp[g.r, g.t, g.p]))] = False

    def phase_twentyfive(self: PpmainMod) -> None:
        g = self.tc
        g.RtpcsVarf[g.Rtpc[g.RtpVara[g.r, g.t, g.p], g.c], g.s].where[
            (
                (~(g.RtpcsOut[g.r, g.t, g.p, g.c, g.s])).where[
                    g.RpcsVar[g.r, g.p, g.c, g.s]
                ]
            )
        ] = True
        # *  vintaging period control such that v=t if no vintaging, otherwise = CPT periods
        # *  always variables within availability of process (vintaging should imply capacity)
        # *  PRC_VINT(PRC_VINT(RP)) = PRC_CAP(RP);
        g.RtpVintyr[g.RtpCptyr[g.r, g.v, g.t, g.p]].where[g.PrcVint[g.r, g.p]] = True
        g.RtpVintyr[g.r, g.t, g.t, g.p].where[
            (
                (~(g.PrcVint[g.r, g.p]))
                * g.Rtp[g.r, g.t, g.p].where[g.Rvp[g.r, g.t, g.p]]
            )
        ] = True
        g.RUc.setRecords(None)
        g.Rvp.setRecords(None)
        g.RtpcsOut.setRecords(None)

    def phase_twenty_six(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
    PUTCLOSE QLOG;
    IF(PUTOUT, QLOG.AP = 1);
""",
        )
