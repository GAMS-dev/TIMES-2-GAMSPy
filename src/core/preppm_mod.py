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

from gamspy import Loop, Ord, Set, sparse
from gamspy.math import project

from core.base_class import GamsClass
from core.curex_gms import CurexGms, CurexGmsConfig
from core.fillparm_gms import FillparmGms
from core.fillvint_gms import FillvintGms, FillvintGmsConfig
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
from core.prepret_dsc import PrepretDsc, PrepretDscConfig
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
            self.tc.register_assignment(g.r_curex)
            self.tc.enqueue(self.exec2)

        if self.tc.defined("R_CUREX"):
            self.include(CurexGms(self.tc, self.env, CurexGmsConfig()))

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
                    config=PrepretDscConfig(
                        arg1="PREP", arg2="PRC_RCAP", arg3="RCAP_BND"
                    ),
                )
            )

        # Use RVP for extrapolating vintaged flow parameters
        # only runs inititialization step
        self.include(
            FillvintGms(self.tc, self.env, config=FillvintGmsConfig(), init=True)
        )

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
            fillvints: list[FillvintGmsConfig] = [
                FillvintGmsConfig(
                    g.flo_func, g.r, (g.p, g.cg1, g.cg2, g.ts), "X_RPGGS"
                ),
                FillvintGmsConfig(
                    g.flo_sum, g.r, (g.p, g.cg1, g.c, g.cg2, g.ts), "X_RPGCGS"
                ),
                FillvintGmsConfig(g.ncap_cdme, g.r, (g.p,), "X_RP"),
                FillvintGmsConfig(g.ncap_chpr, g.r, (g.p, g.bd), "X_RPB"),
                FillvintGmsConfig(
                    g.flo_shar, g.r, (g.p, g.c, g.cg, g.ts, g.bd), "X_RPCGSB"
                ),
            ]

            for f_config in fillvints:
                self.include(FillvintGms(self.tc, self.env, config=f_config))

            self.tc.enqueue(self.exec7)

    def exec1(self, dflbl: str) -> None:
        g = self.tc
        (
            Modlyear,
            ll,
            Milestonyr,
            Pastyear,
            Datayear,
            DmYear,
            yearval,
            t,
            fil2,
            b,
            e,
            MyFil,
        ) = (
            g.Modlyear,
            g.ll,
            g.Milestonyr,
            g.Pastyear,
            g.Datayear,
            g.DmYear,
            g.yearval,
            g.t,
            g.fil2,
            g.b,
            g.e,
            g.MyFil,
        )
        # -----------------------------------------------------------------------------
        # Ensure that both MODLYEAR and DATAYEAR include PASTYEAR
        # Also set the special year among datayears for the processing of control options.
        Modlyear[ll] = Milestonyr[ll] + Pastyear[ll]
        Datayear[Pastyear] = True
        Datayear[dflbl] = True
        # Build DM_YEAR for interpolation, excluding the special year:
        DmYear[Milestonyr] = True
        DmYear[Datayear] = yearval[Datayear] > 0
        # Set migrating years MY_FIL, and FIL2 of each MY_FIL to the period year, if within periods:
        with Loop(t):
            fil2[DmYear].where[
                (yearval[DmYear] >= b[t]) * (yearval[DmYear] <= e[t])
            ] = yearval[t]
        MyFil[DmYear].where[fil2[DmYear] * ~t[DmYear]] = True
        # -----------------------------------------------------------------------------

    def exec2(self) -> None:
        g = self.tc
        r_curex, r, curr, cur, g_curex = g.r_curex, g.r, g.curr, g.cur, g.g_curex
        r_curex[r, curr, cur].where[False] = 0  # type: ignore[index]
        r_curex[r, curr, cur].where[~r_curex[r, curr, cur]] = sparse(g_curex[curr, cur])

    def exec3(self) -> None:
        g = self.tc
        (
            flo_mark,
            r,
            ll,
            p,
            c,
            bd,
            Rpc,
            Rc,
            prc_mark,
            obj_comnt,
            Datayear,
            s,
            cur,
            com_cstnet,
            com_taxnet,
            com_subnet,
            obj_compd,
            com_cstprd,
            com_taxprd,
            com_subprd,
            uc_com,
            ucn,
            side,
            UcAttr,
            uc_comprd,
            uc_comcon,
            uc_comnet,
        ) = (
            g.flo_mark,
            g.r,
            g.ll,
            g.p,
            g.c,
            g.bd,
            g.Rpc,
            g.Rc,
            g.prc_mark,
            g.obj_comnt,
            g.Datayear,
            g.s,
            g.cur,
            g.com_cstnet,
            g.com_taxnet,
            g.com_subnet,
            g.obj_compd,
            g.com_cstprd,
            g.com_taxprd,
            g.com_subprd,
            g.uc_com,
            g.ucn,
            g.side,
            g.UcAttr,
            g.uc_comprd,
            g.uc_comcon,
            g.uc_comnet,
        )
        # Merge special case user attributes to generic case
        flo_mark[r, ll, p, c, bd].where[
            ~Rpc[r, p, c] & Rc[r, c] & flo_mark[r, ll, p, c, bd]
        ] = 0
        prc_mark[r, ll, p, p, c, bd].where[
            ((~Rpc[r, p, c]) | (flo_mark[r, "0", p, c, bd] > 1)).where[
                Rc[r, c].where[prc_mark[r, ll, p, p, c, bd]]
            ]
        ] = 0
        # Integration of COM costs
        obj_comnt[r, Datayear, c, s, "COST", cur] = sparse(
            com_cstnet[r, Datayear, c, s, cur]
        )
        obj_comnt[r, Datayear, c, s, "TAX", cur] = sparse(
            com_taxnet[r, Datayear, c, s, cur]
        )
        obj_comnt[r, Datayear, c, s, "SUB", cur] = sparse(
            com_subnet[r, Datayear, c, s, cur] * -1
        )
        obj_compd[r, Datayear, c, s, "COST", cur] = sparse(
            com_cstprd[r, Datayear, c, s, cur]
        )
        obj_compd[r, Datayear, c, s, "TAX", cur] = sparse(
            com_taxprd[r, Datayear, c, s, cur]
        )
        obj_compd[r, Datayear, c, s, "SUB", cur] = sparse(
            com_subprd[r, Datayear, c, s, cur] * -1
        )
        # Integration of UC_COMxxx
        uc_com[ucn, "PRD", side, r, Datayear, c, s, "COMPRD"].where[
            ~UcAttr[r, ucn, side, "COMPRD", "NET"]
        ] = sparse(uc_comprd[ucn, side, r, Datayear, c, s])
        uc_com[ucn, "PRD", side, r, Datayear, c, s, "COMCON"].where[
            ~UcAttr[r, ucn, side, "COMCON", "NET"]
        ] = sparse(uc_comcon[ucn, side, r, Datayear, c, s])
        uc_com[ucn, "NET", side, r, Datayear, c, s, "COMPRD"].where[
            UcAttr[r, ucn, side, "COMPRD", "NET"]
        ] = sparse(uc_comprd[ucn, side, r, Datayear, c, s])
        uc_com[ucn, "NET", side, r, Datayear, c, s, "COMCON"].where[
            uc_comcon[ucn, side, r, Datayear, c, s]
        ] = uc_comcon[ucn, side, r, Datayear, c, s] * -1
        uc_com[ucn, "NET", side, r, Datayear, c, s, "COMNET"] = sparse(
            uc_comnet[ucn, side, r, Datayear, c, s]
        )

    def prepare_flags_for_flow_tax_sub(self: PreppmMod, dflbl: str) -> None:
        g = self.tc
        flo_tax, RpcCur, ObjVflo, flo_sub, r, ll, p, c, s, cur = (
            g.flo_tax,
            g.RpcCur,
            g.ObjVflo,
            g.flo_sub,
            g.r,
            g.ll,
            g.p,
            g.c,
            g.s,
            g.cur,
        )
        project(source=flo_tax, target=RpcCur, direction="left")
        ObjVflo[RpcCur, "TAX"] = True
        project(source=flo_sub, target=RpcCur, direction="left")
        ObjVflo[RpcCur, "SUB"] = sparse(ObjVflo[RpcCur, "TAX"])
        flo_tax[r, ll.lag(Ord(ll), "circular"), p, c, s, cur].where[
            ~flo_tax[r, dflbl, p, c, s, cur]
            & flo_tax[r, ll, p, c, s, cur]
            & ObjVflo[r, p, c, cur, "SUB"]
        ] = 3
        flo_sub[r, ll.lag(Ord(ll), "circular"), p, c, s, cur].where[
            ~flo_sub[r, dflbl, p, c, s, cur]
            & flo_sub[r, ll, p, c, s, cur]
            & ObjVflo[r, p, c, cur, "SUB"]
        ] = 3

    def exec4(self) -> None:
        g = self.tc
        ie_default, intdefault = g.ie_default, g.intdefault
        # -----------------------------------------------------------------------------
        # Starting data pre-preprocessing with temporary control sets for parameters
        ie_default[intdefault] = 3

    def exec5(self) -> None:
        g = self.tc
        Rvp, Rtp, r, v, p, PrcVint = g.Rvp, g.Rtp, g.r, g.v, g.p, g.PrcVint
        Rvp[Rtp[r, v, p]].where[PrcVint[r, p]] = True

    def exec6(self, dflbl: str) -> None:
        g = self.tc
        Uncd7, prc_mark, r, t, p, c, bd, flo_mark, Datayear, Milestonyr = (
            g.Uncd7,
            g.prc_mark,
            g.r,
            g.t,
            g.p,
            g.c,
            g.bd,
            g.flo_mark,
            g.Datayear,
            g.Milestonyr,
        )
        # -----------------------------------------------------------------------------
        # All parameters now processed, but second pass (dense interpolation) still needed for cost parameters
        Uncd7.setRecords(None)
        prc_mark[r, t, p, p, c, bd] = sparse(flo_mark[r, t, p, c, bd])
        # -----------------------------------------------------------------------------
        # Augment datayear with MILESTONYR, as they now contain user data.
        # Remove the special year from DATAYEAR, as controls are processed.
        Datayear[Milestonyr] = True
        Datayear[dflbl] = False

    def exec7(self) -> None:
        g = self.tc
        pastsum = g.pastsum
        pastsum.setRecords(None)
