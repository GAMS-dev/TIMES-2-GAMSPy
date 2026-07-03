# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREPPM.MOD oversees all the enhanced interpolation activities
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Set

from core.base_class import GamsClass
from core.curex_gms import CurexGms
from core.fillparm_gms import FillparmGms
from core.fillvint_gms import FillvintGms
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.main_ext_mod import include_extension
from core.prep_ext_abs import PrepExtAbs
from core.prep_ext_dsc import PrepExtDsc
from core.prep_ext_ier import PrepExtIer
from core.prep_ext_mlf import PrepExtMlf
from core.prep_ext_stc import PrepExtStc
from core.prep_ext_tm import PrepExtTm
from core.prep_ext_vda import PrepExtVda
from core.prepparm_gms import PrepparmGms, PrepparmGmsConfig
from core.prepret_dsc import PrepretDsc
from core.prepxtra_mod import PrepxtraMod
from core.preshape_gms import PreshapeGms

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

from gamspy import Number, SpecialValues

logger = logging.getLogger(__name__)


class PreppmMod(GamsClass):
    """Translation unit for preppm.mod."""

    module_name: str = "preppm_mod"
    gams_source: str = "preppm.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        r, v, t, p, c, s = g.r, g.v, g.t, g.p, g.c, g.s
        ts, allreg, ie, costype, item = g.ts, g.allreg, g.ie, g.costype, g.item
        lim, allr, ucn, cur, cg, bd = g.lim, g.allr, g.ucn, g.cur, g.cg, g.bd

        self.env.set_scoped("reset", 0)
        if self.env.intext_only.upper() == "YES":
            self.env.set_scoped("reset", 15)

        if self.env.datagdx.upper() == "YES":
            self.include(PrepxtraMod(self.tc, self.env, arg1="SAVE"))

        if f"{self.env.prep_ans}{self.env.reset}".upper() == "YES15":
            self.include(PrepxtraMod(self.tc, self.env, arg1="POST"))

        if self.env.prep_ans.upper() == "YES":
            return

        self.tc.enqueue(self.exec1, dflbl=self.env.dflbl)

        if self.tc.defined("G_CUREX"):
            self.tc.enqueue(self.exec2)

        if self.tc.defined("R_CUREX"):
            self.include(CurexGms(self.tc, self.env))

        self.tc.enqueue(self.exec3)

        p, c, cur, uccost, reg, prc, com = (
            g.p,
            g.c,
            g.cur,
            g.UcCost,
            g.Reg,
            g.prc,
            g.Com,
        )

        g.ObjVflo = Set(m, name="OBJ_VFLO", domain=[r, p, c, cur, uccost])
        g.RpcCur = Set(m, name="RPC_CUR", domain=[reg, prc, com, cur])

        self.tc.enqueue(self.prepare_flags_for_flow_tax_sub, dflbl=self.env.dflbl)

        # Starting data pre-preprocessing with temporary control sets for parameters
        if not self.env.is_set("def_iebd"):
            self.env.set_scoped("def_iebd", 10)

        self.tc.enqueue(self.exec4)

        if self.env.is_set("retire"):
            self.include(
                PrepretDsc(
                    self.tc,
                    self.env,
                    arg1="PREP",
                    arg2="PRC_RCAP",
                    arg3="RCAP_BND",
                )
            )

        # Use RVP for extrapolating vintaged flow parameters
        self.include(FillvintGms(self.tc, self.env))

        self.tc.enqueue(self.exec5)

        # *-----------------------------------------------------------------------------
        # *       Interpolation Options
        # *       =====================
        # * The placeholder for the option flag is parameter data point of year zero.
        # * Example: NCAP_COST(R,'0',P,CUR) is an option for NCAP_COST(R,T,P,CUR).
        # * Available option codes: See documentation
        # *
        # * Interpolation can be effectively denied for non-cost parameters only.
        # *
        # *=============================================================================
        # * COST PARAMETERS: Interpolated by COEF_OBJ, only special options processed here

        # *-----------------------------------------------------------------------------
        # * General attributes
        # *-----------------------------------------------------------------------------
        # *$BATINCLUDE prepparm G_DRATE R CUR ",'0','0','0','0'" YEAR 1 1
        # ("filparam", "G_RFRIR", "R,", "", ",'0','0','0','0','0'", "YEAR", "V", "", "", "", ""),
        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.g_rfrir,
                    arg2=(r,),
                    tail1=(),
                    arg4=("0", "0", "0", "0", "0"),
                    arg5=g.year,
                    arg6=v,
                ),
            )
        )

        # fmt: off
        batincludes1: list[PrepparmGmsConfig] = [
            # *-----------------------------------------------------------------------------
            # * Capacity related attributes
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(arg1="NCAP_COST", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_DCOST", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_DLAGC", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_FOM", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_FSUB", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_FTAX", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_ISUB", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_ITAX", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_VALU", arg2=(r,), arg3=(p,g.c,cur), arg4=('0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="NCAP_ISPCT", arg2=(r,), arg3=(p,), arg4=('0','0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            # *-----------------------------------------------------------------------------
            # * Commodity related attributes
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(arg1="OBJ_COMNT", arg2=(r,), arg3=(c,ts,costype,cur), arg4=('0','0'), arg5=t, arg6=Number(1), arg7=0),
            PrepparmGmsConfig(arg1="OBJ_COMPD", arg2=(r,), arg3=(c,ts,costype,cur), arg4=('0','0'), arg5=t, arg6=Number(1), arg7=0),
            # *-----------------------------------------------------------------------------
            # * Flow related attributes & inter-regional exchange flows (6)
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(arg1="ACT_COST", arg2=(r,), arg3=(p,cur), arg4=('0','0','0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="FLO_COST", arg2=(r,), arg3=(p,c,ts,cur), arg4=('0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="FLO_DELIV", arg2=(r,), arg3=(p,c,ts,cur), arg4=('0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="FLO_SUB", arg2=(r,), arg3=(p,c,ts,cur), arg4=('0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="FLO_TAX", arg2=(r,), arg3=(p,c,ts,cur), arg4=('0','0'), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
            PrepparmGmsConfig(arg1="IRE_PRICE", arg2=(r,), arg3=(p,c,ts,allreg,ie,cur), arg4=(), arg5=v, arg6=g.Rtp[r,v,p], arg7=0),
        ]
        # fmt: on

        for config in batincludes1:
            self.include(PrepparmGms(self.tc, self.env, config=config))

        if self.tc.defined("DAM_COST"):
            self.include(
                PrepparmGms(
                    self.tc,
                    self.env,
                    config=PrepparmGmsConfig(
                        arg1="DAM_COST",
                        arg2=(r,),
                        arg3=(c, cur),
                        arg4=("0", "0", "0"),
                        arg5=t,
                        arg6=Number(1),
                        arg7=SpecialValues.EPS,
                        arg8=3,
                    ),
                )
            )

        # *=============================================================================
        # ***** REGULAR NON-COST PARAMETERS: Interpolated over DM_YEAR by default ******

        # fmt: off
        batincludes2: list[tuple[str, str, str, str, str, str, str, str, str, str, str]] = [
            # *-----------------------------------------------------------------------------
            # * Capacity related attributes
            # *-----------------------------------------------------------------------------
            ("fillparm", "NCAP_AF", "R", "P,TS,BD", ",'0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RPSB", "", ""),
            ("fillparm", "NCAP_AFA", "R", "P,BD", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RPB", "", ""),
            ("fillparm", "NCAP_AFS", "R", "P,TS,BD", ",'0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RPSB", "", ""),
            ("fillparm", "NCAP_BPME", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_CDME", "R", "P", ",'0','0','0','0','0'", "V", "RVP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_CEH", "R", "P", ",'0','0','0','0','0'", "V", "RVP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_CHPR", "R", "P,BD", ",'0','0','0','0'", "V", "RVP(R,V,P)", "GE 0", "X_RPB", "", ""),
            ("fillparm", "NCAP_CLED", "R", "P,C", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_CLAG", "R", "P,C,IO", ",'0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_COM", "R", "P,C,IO", ",'0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_DELIF", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_DLAG", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_DLIFE", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_DRATE", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_FDR", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_ELIFE", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_ICOM", "R", "P,C", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_ILED", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            ("fillparm", "NCAP_OCOM", "R", "P,C", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_PKCNT", "R", "P,TS", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "NCAP_TLIFE", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RP", "", ""),
            # *-----------------------------------------------------------------------------
            # * Commodity related attributes
            # *-----------------------------------------------------------------------------
            ("fillparm", "COM_AGG", "R", "C,COM", ",'0','0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "COM_ELAST", "R", "C,TS,L", ",'0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "COM_FR", "R", "C,TS", ",'0','0','0','0'", "T", "1", "GE 0", "X_RCS", "", ""),
            ("fillparm", "COM_IE", "R", "C,TS", ",'0','0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "COM_PKFLX", "R", "C,TS", ",'0','0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "COM_PKRSV", "R", "C", ",'0','0','0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "COM_PROJ", "R", "C", ",'0','0','0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "COM_VOC", "R", "C,BD", ",'0','0','0','0'", "T", "1", "GE 0", "", "", ""),
            # *-----------------------------------------------------------------------------
            # * Flow related attributes & inter-regional exchange
            # *-----------------------------------------------------------------------------
            ("fillparm", "ACT_CSTUP", "R", "P,TSL,CUR", ",'0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "ACT_CSTSD", "R", "P,UPT,BD,CUR", ",'0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "ACT_CSTRMP", "R", "P,BD,CUR", ",'0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "ACT_TIME", "R", "P,LIM", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "FLO_FUNC", "R", "P,CG1,CG2,TS", ",'0','0'", "V", "RVP(R,V,P)", "GE 0", "X_RPGGS", "", ""),
            ("fillparm", "FLO_PKCOI", "R", "P,C,TS", ",'0','0','0'", "V", "RVP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "FLO_SUM", "R", "P,CG1,C,CG2,TS", ",'0'", "V", "RVP(R,V,P)", "GE 0", "X_RPGCGS", "", ""),
            ("fillparm", "PRC_ACTFLO", "R", "P,CG", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "X_RPG", "", ""),
        ]
        # fmt: on
        for _, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10 in batincludes2:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=a1,
                    arg2=a2,
                    arg3=a3,
                    arg4=a4,
                    arg5=a5,
                    arg6=a6,
                    arg7=a7,
                    arg8=a8,
                    arg9=a9,
                    arg10=a10,
                )
            )

        batincludes3 = [
            PrepparmGmsConfig(
                arg1="FLO_MARK",
                arg2=(r,),
                arg3=(p, c, bd),
                arg4=("0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
                arg8=3,
                arg9="X_RPCL",
            ),
            PrepparmGmsConfig(
                arg1="PRC_MARK",
                arg2=(r,),
                arg3=(p, item, c, bd),
                arg4=("0",),
                arg5=t,
                arg6=Number(1),
                arg7=1,
                arg8=11,
                arg9="X_MARK",
            ),
        ]

        for config in batincludes3:
            self.include(PrepparmGms(self.tc, self.env, config=config))

        # fmt: off
        batincludes4 = [
            ("fillparm", "IRE_FLO", "R", "P,C,REG,COM,TS", ",'0'", "V", "(RVP(R,V,P) OR RTP(REG,V,P))", "GE 0", "", "", ""),
            ("fillparm", "IRE_FLOSUM", "R", "P,C,TS,IE,COM,IO", "", "V", "RVP(R,V,P)", "GE 0", "", "", ""),
            # *-----------------------------------------------------------------------------
            # * Storage attributes
            # *-----------------------------------------------------------------------------
            ("fillparm", "STG_CHRG", "R", "P,S", ",'0','0','0','0'", "V", "(M(V) GE MIYR_V1-1)", "GE 0", "", "", ""),
            ("fillparm", "STG_EFF", "R", "P", ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "STG_LOSS", "R", "P,S", ",'0','0','0','0'", "V", "RTP(R,V,P)", "GE 0", "", "", ""),
            ("fillparm", "STG_SIFT", "R", "P,C,S", ",'0','0','0'", "T", "RTP(R,T,P)", "GE 0", "", "", ""),
            # *-----------------------------------------------------------------------------
            # * User constraints
            # *-----------------------------------------------------------------------------
            ("fillparm", "UC_ACT", "UC_N,SIDE,R", "P,TS", ",'0','0'", "T", "RTP(R,T,P)", "GE 0", "", "", ""),
            ("fillparm", "UC_CAP", "UC_N,SIDE,R", "P", ",'0','0','0'", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "UC_COM", "UC_N,COM_VAR,SIDE,R", "C,TS,UC_GRPTYPE", "", "T", "1", "GE 0", "", "", ""),
            ("fillparm", "UC_FLO", "UC_N,SIDE,R", "P,C,TS", ",'0'", "T", "1", "GE 0", "X_UZRPCS", "", ""),
            ("fillparm", "UC_IRE", "UC_N,SIDE,R", "P,C,TS,IE", "", "T", "RTP(R,T,P)", "GE 0", "", "", ""),
            ("fillparm", "UC_NCAP", "UC_N,SIDE,R", "P", ",'0','0','0'", "T", "RTP(R,T,P)", "GE 0", "", "", ""),
            ("fillparm", "UC_UCN", "UC_N,SIDE,R", "UCN", ",'0','0','0'", "T", "1", "GE 0", "", "", ""),
        ]
        # fmt: on
        for _, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10 in batincludes4:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=a1,
                    arg2=a2,
                    arg3=a3,
                    arg4=a4,
                    arg5=a5,
                    arg6=a6,
                    arg7=a7,
                    arg8=a8,
                    arg9=a9,
                    arg10=a10,
                )
            )

            self.include(
                FilparamGms(
                    self.tc,
                    self.env,
                    config=FilparamGmsConfig(
                        src=g.uc_time,
                        arg2=(ucn, r),
                        tail1=(),
                        arg4=("0", "0", "0"),
                        arg5=g.Datayear,
                        arg6=t,
                        arg10=(g.year,),
                    ),
                )
            )
        batincludes5: list[PrepparmGmsConfig] = [
            # *=============================================================================
            # ******* NON-REGULAR NON-COST PARAMETERS: NOT interpolated by default *********
            # *-----------------------------------------------------------------------------
            # * Capacity and commodity related attributes
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(
                arg1="CAP_BND",
                arg2=(r,),
                arg3=(p, bd),
                arg4=("0", "0", "0"),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
                arg9="X_RPB",
            ),
            PrepparmGmsConfig(
                arg1="NCAP_BND",
                arg2=(r,),
                arg3=(p, bd),
                arg4=("0", "0", "0"),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
                arg9="X_RPB",
            ),
            PrepparmGmsConfig(
                arg1="COM_BNDNET",
                arg2=(r,),
                arg3=(c, ts, bd),
                arg4=("0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="COM_BNDPRD",
                arg2=(r,),
                arg3=(c, ts, bd),
                arg4=("0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            # *-----------------------------------------------------------------------------
            # * Flow related attributes & inter-regional exchange
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(
                arg1="ACT_BND",
                arg2=(r,),
                arg3=(p, ts, bd),
                arg4=("0", "0"),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
                arg9="X_RPSB",
            ),
            PrepparmGmsConfig(
                arg1="FLO_BND",
                arg2=(r,),
                arg3=(p, cg, ts, bd),
                arg4=("0",),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
                arg9="X_RPGSB",
            ),
            PrepparmGmsConfig(
                arg1="FLO_BDLVL",
                arg2=(r,),
                arg3=(p, cg, s, bd),
                arg4=("0",),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
                arg9="X_RPGSB",
            ),
            PrepparmGmsConfig(
                arg1="FLO_FR",
                arg2=(r,),
                arg3=(p, c, ts, lim),
                arg4=("0",),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
                arg9="X_RPCSL",
            ),
            PrepparmGmsConfig(
                arg1="FLO_SHAR",
                arg2=(r,),
                arg3=(p, c, cg, ts, bd),
                arg4=(),
                arg5=v,
                arg6=g.Rvp[r, v, p],
                arg7=1,
                arg9="X_RPCGSB",
                arg10="+",
            ),
            PrepparmGmsConfig(
                arg1="IRE_BND",
                arg2=(r,),
                arg3=(c, ts, allreg, ie, bd),
                arg4=(),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="IRE_XBND",
                arg2=(allreg,),
                arg3=(c, ts, ie, bd),
                arg4=("0",),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            # *-----------------------------------------------------------------------------
            # * Storage attributes
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(
                arg1="STGIN_BND",
                arg2=(r,),
                arg3=(p, c, s, bd),
                arg4=("0",),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="STGOUT_BND",
                arg2=(r,),
                arg3=(p, c, s, bd),
                arg4=("0",),
                arg5=t,
                arg6=g.Rtp[r, t, p],
                arg7=1,
            ),
            # *-----------------------------------------------------------------------------
            # * User constraints
            # *-----------------------------------------------------------------------------
            PrepparmGmsConfig(
                arg1="UC_RHSRT",
                arg2=(allr, ucn),
                arg3=(lim,),
                arg4=("0", "0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
                arg9="X_RUL",
            ),
            PrepparmGmsConfig(
                arg1="UC_RHSRTS",
                arg2=(allr, ucn),
                arg3=(ts, g.lA),
                arg4=("0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
                arg9="X_RUSL",
            ),
            PrepparmGmsConfig(
                arg1="UC_RHST",
                arg2=(ucn,),
                arg3=(lim,),
                arg4=("0", "0", "0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="UC_RHSTS",
                arg2=(ucn,),
                arg3=(ts, lim),
                arg4=("0", "0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="REG_BNDCST",
                arg2=(r,),
                arg3=(g.costagg, cur, bd),
                arg4=("0", "0"),
                arg5=t,
                arg6=Number(1),
                arg7=1,
            ),
            # *-----------------------------------------------------------------------------
            # * Parameters that are by default inter/extrapolated over PASTYEARS
            # *----------------------------------------------------------------------------
            PrepparmGmsConfig(
                arg1="FLO_SHAR",
                arg2=(r,),
                arg3=(p, c, cg, ts, bd),
                arg4=(),
                arg5=g.Pastmile,
                arg6=g.Rvp[r, g.Pastmile, p],
                arg7=1,
                arg8=3,
                arg9="X_RPCGSB",
                arg10="-ABS",
            ),
        ]
        # fmt: on

        for config in batincludes5:
            self.include(PrepparmGms(self.tc, self.env, config=config))

        if self.env.stages.upper() == "YES":
            self.include(PrepExtStc(self.tc, self.env))

        # $   IF NOT '%EXTEND%' == '' $BATINCLUDE main_ext.mod prep_ext %EXTEND%
        extensions = {
            "ABS": PrepExtAbs,
            "DSC": PrepExtDsc,
            "IER": PrepExtIer,
            "MLF": PrepExtMlf,
            "TM": PrepExtTm,
            "STC": PrepExtStc,
            "VDA": PrepExtVda,
        }
        requested_exts = set(self.env.extend.split())
        include_extension(
            module=self,
            extensions=extensions,
            requested_exts=requested_exts,
            source="prep_ext",
        )

        if self.env.intext_only.upper() == "YES":
            self.include(PrepxtraMod(self.tc, self.env, arg1="XTIE"))

        # *=============================================================================
        # ***************************** SHAPE/MULTI INDEXES ****************************
        # *-----------------------------------------------------------------------------
        preshapes: list[tuple[str, str, str, str, str, str, str, str]] = [
            ("NCAP_AFX", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_AFSX", "R", "P,BD", ",'0','0','0'", "V", "UNCD7", "RTP(R,V,P)", ""),
            ("NCAP_AFM", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_FOMX", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_FSUBX", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_FTAXX", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("FLO_FUNCX", "R", "P,CG1,CG2", ",'0','0'", "V", "UNCD7", "RTP(R,V,P)", ""),
            ("COM_ELASTX", "R", "C,BD", ",'0','0','0'", "T", "UNCD7", "1", "15"),
            ("NCAP_FOMM", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_FSUBM", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_FTAXM", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
            ("NCAP_CPX", "R", "P", "", "V", "RXX", "RTP(R,V,P)", ""),
        ]

        for a1, a2, a3, a4, a5, a6, a7, a8 in preshapes:
            self.include(
                PreshapeGms(
                    self.tc,
                    self.env,
                    arg1=a1,
                    arg2=a2,
                    arg3=a3,
                    arg4=a4,
                    arg5=a5,
                    arg6=a6,
                    arg7=a7,
                    arg8=a8,
                )
            )

        self.tc.enqueue(self.exec6, dflbl=self.env.dflbl)

        # * Optional weighting of vintaged attributes
        if self.env.vintopt == "1":
            fillvints: list[tuple[str, str, str, str]] = [
                ("FLO_FUNC", "R", "P,CG1,CG2,TS", "X_RPGGS"),
                ("FLO_SUM", "R", "P,CG1,C,CG2,TS", "X_RPGCGS"),
                ("NCAP_CDME", "R", "P", "X_RP"),
                ("NCAP_CHPR", "R", "P,BD", "X_RPB"),
                ("FLO_SHAR", "R", "P,C,CG,TS,BD", "X_RPCGSB"),
            ]

            for a1, a2, a3, a4 in fillvints:
                self.include(
                    FillvintGms(
                        self.tc,
                        self.env,
                        arg1=a1,
                        arg2=a2,
                        arg3=a3,
                        arg4=a4,
                    )
                )

            self.tc.enqueue(self.exec7)

    def exec1(self, dflbl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Ensure that both MODLYEAR and DATAYEAR include PASTYEAR
* Also set the special year among datayears for the processing of control options.
MODLYEAR(LL) = MILESTONYR(LL)+PASTYEAR(LL);
DATAYEAR(PASTYEAR)  = YES;
DATAYEAR('{dflbl}') = YES;

* Build DM_YEAR for interpolation, excluding the special year:
DM_YEAR(MILESTONYR) = YES;
DM_YEAR(DATAYEAR) = (YEARVAL(DATAYEAR)>0);

* Set migrating years MY_FIL, and FIL2 of each MY_FIL to the period year, if within periods:
LOOP(T,FIL2(DM_YEAR)$((YEARVAL(DM_YEAR) >= B(T)) * (YEARVAL(DM_YEAR) <= E(T))) = YEARVAL(T));
MY_FIL(DM_YEAR)$(FIL2(DM_YEAR)*(NOT T(DM_YEAR))) = YES;

*-----------------------------------------------------------------------------
""",
        )

    def exec2(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
R_CUREX(R,CURR,CUR)$NO=0; R_CUREX(R,CURR,CUR)$(NOT R_CUREX(R,CURR,CUR))$=G_CUREX(CURR,CUR);
""",
        )

    def exec3(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Merge special case user attributes to generic case
FLO_MARK(R,LL,P,C,BD)$((NOT RPC(R,P,C))$RC(R,C)$FLO_MARK(R,LL,P,C,BD)) = 0;
PRC_MARK(R,LL,P,P,C,BD)$((RPC(R,P,C)->(FLO_MARK(R,'0',P,C,BD)>1))$RC(R,C)$PRC_MARK(R,LL,P,P,C,BD)) = 0;

* Integration of COM costs
OBJ_COMNT(R,DATAYEAR,C,S,'COST',CUR) $= COM_CSTNET(R,DATAYEAR,C,S,CUR);
OBJ_COMNT(R,DATAYEAR,C,S,'TAX',CUR)  $= COM_TAXNET(R,DATAYEAR,C,S,CUR);
OBJ_COMNT(R,DATAYEAR,C,S,'SUB',CUR)  $= COM_SUBNET(R,DATAYEAR,C,S,CUR)*(-1);
OBJ_COMPD(R,DATAYEAR,C,S,'COST',CUR) $= COM_CSTPRD(R,DATAYEAR,C,S,CUR);
OBJ_COMPD(R,DATAYEAR,C,S,'TAX',CUR)  $= COM_TAXPRD(R,DATAYEAR,C,S,CUR);
OBJ_COMPD(R,DATAYEAR,C,S,'SUB',CUR)  $= COM_SUBPRD(R,DATAYEAR,C,S,CUR)*(-1);

* Integration of UC_COMxxx
UC_COM(UC_N,'PRD',SIDE,R,DATAYEAR,C,S,'COMPRD')$(NOT UC_ATTR(R,UC_N,SIDE,'COMPRD','NET')) $= UC_COMPRD(UC_N,SIDE,R,DATAYEAR,C,S);
UC_COM(UC_N,'PRD',SIDE,R,DATAYEAR,C,S,'COMCON')$(NOT UC_ATTR(R,UC_N,SIDE,'COMCON','NET')) $= UC_COMCON(UC_N,SIDE,R,DATAYEAR,C,S);
UC_COM(UC_N,'NET',SIDE,R,DATAYEAR,C,S,'COMPRD')$UC_ATTR(R,UC_N,SIDE,'COMPRD','NET') $= UC_COMPRD(UC_N,SIDE,R,DATAYEAR,C,S);
UC_COM(UC_N,'NET',SIDE,R,DATAYEAR,C,S,'COMCON')$UC_COMCON(UC_N,SIDE,R,DATAYEAR,C,S)  = UC_COMCON(UC_N,SIDE,R,DATAYEAR,C,S)*(-1);
UC_COM(UC_N,'NET',SIDE,R,DATAYEAR,C,S,'COMNET') $= UC_COMNET(UC_N,SIDE,R,DATAYEAR,C,S);
""",
        )

    def prepare_flags_for_flow_tax_sub(self: PreppmMod, dflbl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 OPTION RPC_CUR <= FLO_TAX; OBJ_VFLO(RPC_CUR,'TAX') = YES;
 OPTION RPC_CUR <= FLO_SUB; OBJ_VFLO(RPC_CUR,'SUB') $= OBJ_VFLO(RPC_CUR,'TAX');
 FLO_TAX(R,LL--ORD(LL),P,C,S,CUR)$((NOT FLO_TAX(R,'{dflbl}',P,C,S,CUR))$FLO_TAX(R,LL,P,C,S,CUR)$OBJ_VFLO(R,P,C,CUR,'SUB')) = 3;
 FLO_SUB(R,LL--ORD(LL),P,C,S,CUR)$((NOT FLO_SUB(R,'{dflbl}',P,C,S,CUR))$FLO_SUB(R,LL,P,C,S,CUR)$OBJ_VFLO(R,P,C,CUR,'SUB')) = 3;
""",
        )

    def exec4(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* Starting data pre-preprocessing with temporary control sets for parameters
IE_DEFAULT(INT_DEFAULT) = 3;
""",
        )

    def exec5(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
RVP(RTP(R,V,P))$PRC_VINT(R,P) = YES;
""",
        )

    def exec6(self, dflbl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* All parameters now processed, but second pass (dense interpolation) still needed for cost parameters
OPTION CLEAR = UNCD7;
PRC_MARK(R,T,P,P,C,BD) $= FLO_MARK(R,T,P,C,BD);
*-----------------------------------------------------------------------------
* Augment datayear with MILESTONYR, as they now contain user data.
* Remove the special year from DATAYEAR, as controls are processed.
DATAYEAR(MILESTONYR) = YES;
DATAYEAR('{dflbl}') = NO;
""",
        )

    def exec7(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=PASTSUM;
""",
        )
