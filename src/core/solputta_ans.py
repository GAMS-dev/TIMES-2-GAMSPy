# solputta_ans.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *---------------------------------------------------------------------
# * SOLPUTTA.ANS
# *
# * Output routine for ANSWER
# *    - creating table for TIMES Analyst within ANSWER
# *    - seperate calls for primal/dual values
# *---------------------------------------------------------------------
# * placeholder for stochastic scenario
# * SET SOW / EMPTY /;

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.solsubta_ans import SolsubtaAns

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolputtaAns(GamsClass):
    """Translation unit for solputta.ans."""

    # Instance attributes
    module_name: str = "solputta_ans"
    gams_source: str = "solputta.ans"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        if self.env.scum == "1":
            self.tc.enqueue(self.exec1)

        if self.env.solveda != "1" and self.env.stages.upper() != "YES":
            # with only three args $SHIFT SHIFT SHIFT removes all
            self.arg1 = ""
            self.arg2 = ""
            self.arg3 = ""

        self.env.set_local("item2", ",ITEM")
        if self.arg1 == "S":
            self.env.set_local("item2", "")

        self.tc.enqueue(self.exec2, run_name=self.env.run_name)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
SET PUTIT({self.arg2}R,T,P);
SET PUTI1({self.arg2}R,ALLYEAR,T,P);
SET PUTI2({self.arg2}R,ALLYEAR,T,P,TS);
SET PUTI3({self.arg2}R,ALLYEAR,T,P,C,S);
SET PUTI4({self.arg2}R,T,C,TS);
SET PUTI5({self.arg2}R,T,P,TS);
SET PUTI6({self.arg2}R,T,P,C,S);
SET PUTI7({self.arg2}R,T,P,C);
SET UCITEM3({self.arg2}UC_N,ITEM,ITEM,ITEM);
SET CUMITEM4({self.arg2}R,ITEM,ITEM,ITEM,ITEM);
* --- Retirement results ---
PARAMETER {self.arg1}PAR_RET({self.arg2}R,ALLYEAR,T,P) //;
* --- CumCom results ---
PARAMETER {self.arg1}PAR_CUMCOML({self.arg2}R,C,COM_VAR,ALLYEAR,ALLYEAR) //;
PARAMETER {self.arg1}PAR_CUMCOMM({self.arg2}R,C,COM_VAR,ALLYEAR,ALLYEAR) //;
""",
        )

        # *---------------------------------------------------------------------
        # * Output of VAR_NCAP, units of capacity
        # *---------------------------------------------------------------------

        # fmt: off
        batincludes: list[tuple[str,str, str, str, str, str, str, str, str, str, str, str, str]] = [
            #*                        ATTR       R        P     COM     V        TS     P/D
            ("PUTIT", "RTP(R,T,P)", "VAR_NCAP", "R.TL", "P.TL", "' '", "'  '", "'  '", '.L', f"{self.arg1}PAR_NCAPL({self.arg3}R,T,P)", f"({self.arg3}R,TT,P)", f"({self.arg3}R,TT(T--ORD(T)),P)", ""),
            ("PUTIT", "RTP(R,T,P)", "VAR_NCAP", "R.TL", "P.TL", "' '", "'  '", "'  '", '.M', f"{self.arg1}PAR_NCAPM({self.arg3}R,T,P)", f"({self.arg3}R,TT,P)", f"({self.arg3}R,TT(T--ORD(T)),P)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )

        # *---------------------------------------------------------------------
        # * Output of VAR_ACT, units of activity
        # *--------------------------------------------------------------------

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* split out non/vintage processes
  PARAMETER APARRTP({self.arg2}R,T,P);
  PARAMETERS NV_ACTL({self.arg2}R,T,P,S);
  PARAMETERS NV_ACTM({self.arg2}R,T,P,S);
""",
        )

        self.tc.enqueue(self.exec3, arg1=self.arg1, arg3=self.arg3)

        # fmt: off
        batincludes = [
            #* ALL-vintage
            ("PUTI5", "(RTP_VARA(R,T,P)*PRC_TS(R,P,S))", "VAR_ACT", "R.TL", "P.TL", "' '", "' '", "S.TL", '.L', f"NV_ACTL({self.arg3}R,T,P,S)", f"({self.arg3}R,TT,P,S)", f"({self.arg3}R,TT(T--ORD(T)),P,S)", ""),
            ("PUTI5", "(RTP_VARA(R,T,P)*PRC_TS(R,P,S))", "VAR_ACT", "R.TL", "P.TL", "' '", "' '", "S.TL", '.M', f"NV_ACTM({self.arg3}R,T,P,S)", f"({self.arg3}R,TT,P,S)", f"({self.arg3}R,TT(T--ORD(T)),P,S)", ""),
            #* by vintage for PRC_VINT
            ("PUTI2", "((RTP_VINTYR(R,V,T,P)*PRC_TS(R,P,S))$PRC_VINT(R,P))", "VAR_ACTV", "R.TL", "P.TL", "' '", "V.TL", "S.TL", '.L', f"{self.arg1}PAR_ACTL({self.arg3}R,V,T,P,S)", f"({self.arg3}R,V,TT,P,S)", f"({self.arg3}R,V,TT(T--ORD(T)),P,S)", ""),
            ("PUTI2", "((RTP_VINTYR(R,V,T,P)*PRC_TS(R,P,S))$PRC_VINT(R,P))", "VAR_ACTV", "R.TL", "P.TL", "' '", "V.TL", "S.TL", '.M', f"{self.arg1}PAR_ACTM({self.arg3}R,V,T,P,S)", f"({self.arg3}R,V,TT,P,S)", f"({self.arg3}R,V,TT(T--ORD(T)),P,S)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )

        # * For retirements
        if self.tc.defined("VNRET"):
            self.tc.enqueue(
                self.exec4,
                arg1=self.arg1,
                arg3=self.arg3,
                vart=self.env.vart,
                sws=self.env.sws,
            )
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="PUTI1",
                    arg2="(RTP_CPTYR(R,V,T,P)$PRC_RCAP(R,P))",
                    arg3="VAR_RCAPGV",
                    arg4="R.TL",
                    arg5="P.TL",
                    arg6="' '",
                    arg7="V.TL",
                    arg8="' '",
                    arg9=".L",
                    arg10=f"{self.arg1}PAR_RET({self.arg3}R,V,T,P)",
                    arg11=f"({self.arg3}R,V,TT,P)",
                    arg12=f"({self.arg3}R,V,TT(T--ORD(T)),P)",
                    arg13="",
                )
            )
            self.tc.enqueue(
                self.exec5,
                arg1=self.arg1,
                arg3=self.arg3,
                vart=self.env.vart,
                sws=self.env.sws,
            )
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="PUTI1",
                    arg2="(RTP_CPTYR(R,V,T,P)$VNRET(V,T)$PRC_RCAP(R,P))",
                    arg3="VAR_RCAPV",
                    arg4="R.TL",
                    arg5="P.TL",
                    arg6="' '",
                    arg7="V.TL",
                    arg8="' '",
                    arg9=".L",
                    arg10=f"{self.arg1}PAR_RET({self.arg3}R,V,T,P)",
                    arg11=f"({self.arg3}R,V,TT,P)",
                    arg12=f"({self.arg3}R,V,TT(T--ORD(T)),P)",
                    arg13="",
                )
            )
            self.tc.enqueue(
                self.exec6,
                arg1=self.arg1,
                arg3=self.arg3,
                vart=self.env.vart,
                sws=self.env.sws,
            )
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="PUTI1",
                    arg2="(RTP_CPTYR(R,V,T,P)$VNRET(V,T)$PRC_RCAP(R,P))",
                    arg3="VAR_RCAPV",
                    arg4="R.TL",
                    arg5="P.TL",
                    arg6="' '",
                    arg7="V.TL",
                    arg8="' '",
                    arg9=".M",
                    arg10=f"{self.arg1}PAR_RET({self.arg3}R,V,T,P)",
                    arg11=f"({self.arg3}R,V,TT,P)",
                    arg12=f"({self.arg3}R,V,TT(T--ORD(T)),P)",
                    arg13="",
                )
            )

        # *---------------------------------------------------------------------
        # * Output of VAR_FLO, units of activity
        # *---------------------------------------------------------------------
        self.env.set_scoped("flots", "RPCS_VAR(R,P,C,S)")
        if self.env.rpt_flots.upper() == "ANNUAL":
            self.env.set_scoped("flots", "ANNUAL(S)")
        if self.env.rpt_flots.upper() == "COM":
            self.env.set_scoped("flots", "COM_TS(R,C,S)")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* split in/out
  PARAMETER NV_FLOL({self.arg2}R,T,P,C,S);
""",
        )
        # * VAR_FLO: ALL-vintage
        self.tc.enqueue(self.exec7, arg1=self.arg1, arg3=self.arg3)

        # fmt: off
        batincludes = [
            ("PUTI6", f"(TOP(R,P,C,'IN')*{self.env.flots})", "VAR_FIN", "R.TL", "P.TL", "C.TL", "' '", "S.TL", '.L', f"NV_FLOL({self.arg3}R,T,P,C,S)", f"({self.arg3}R,TT,P,C,S)", f"({self.arg3}R,TT(T--ORD(T)),P,C,S)", ""),
            ("PUTI6", f"((NOT TOP(R,P,C,'IN')+RPC_IRE(R,P,C,'EXP'))$NV_FLOL({self.arg3}R,T,P,C,S))", "VAR_FIN", "R.TL", "P.TL", "C.TL", "' '", "S.TL", '.L', f"NV_FLOL({self.arg3}R,T,P,C,S)", f"({self.arg3}R,TT,P,C,S)", f"({self.arg3}R,TT(T--ORD(T)),P,C,S)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )
        self.tc.enqueue(self.exec8, arg1=self.arg1, arg3=self.arg3)
        # fmt: off
        batincludes = [
            ("PUTI6", f"(TOP(R,P,C,'OUT')*{self.env.flots})", "VAR_FOUT", "R.TL", "P.TL", "C.TL", "' '", "S.TL", '.L', f"NV_FLOL({self.arg3}R,T,P,C,S)", f"({self.arg3}R,TT,P,C,S)", f"({self.arg3}R,TT(T--ORD(T)),P,C,S)", ""),
            ("PUTI6", f"((NOT TOP(R,P,C,'OUT')+RPC_IRE(R,P,C,'IMP'))$NV_FLOL({self.arg3}R,T,P,C,S))", "VAR_FOUT", "R.TL", "P.TL", "C.TL", "' '", "S.TL", '.L', f"NV_FLOL({self.arg3}R,T,P,C,S)", f"({self.arg3}R,TT,P,C,S)", f"({self.arg3}R,TT(T--ORD(T)),P,C,S)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )
        # * VAR_FLO marginals: ALL-vintage (only non-substituted and PG flows)

        if self.arg1.upper() != "S":
            self.tc.enqueue(self.exec9, arg1=self.arg1, arg3=self.arg3)
            # fmt: off
            batincludes= [
                ("PUTI6", f"(TOP(R,P,C,'IN')*{self.env.flots})", "VAR_FIN", "R.TL", "P.TL", "C.TL", "' '", "S.TL", '.M', f"NV_FLOL({self.arg3}R,T,P,C,S)", f"({self.arg3}R,TT,P,C,S)", f"({self.arg3}R,TT(T--ORD(T)),P,C,S)", ""),
                ("PUTI6", f"(TOP(R,P,C,'OUT')*{self.env.flots})", "VAR_FOUT", "R.TL", "P.TL", "C.TL", "' '", "S.TL", '.M', f"NV_FLOL({self.arg3}R,T,P,C,S)", f"({self.arg3}R,TT,P,C,S)", f"({self.arg3}R,TT(T--ORD(T)),P,C,S)", ""),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    SolsubtaAns(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                        arg9=arg[8],
                        arg10=arg[9],
                        arg11=arg[10],
                        arg12=arg[11],
                        arg13=arg[12],
                    )
                )

            self.tc.enqueue(self.exec10)

        # * VAR_IRE: ALL-vintage
        self.tc.enqueue(self.exec11, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2=f"(RPC_IRE(R,P,C,'EXP')*{self.env.flots})",
                arg3="VAR_XEXP",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="' '",
                arg8="S.TL",
                arg9=".L",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,S)",
                arg11=f"({self.arg3}R,TT,P,C,S)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,S)",
                arg13="",
            )
        )
        self.tc.enqueue(self.exec12, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2=f"(RPC_IRE(R,P,C,'IMP')*{self.env.flots})",
                arg3="VAR_XIMP",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="' '",
                arg8="S.TL",
                arg9=".L",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,S)",
                arg11=f"({self.arg3}R,TT,P,C,S)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,S)",
                arg13="",
            )
        )

        if self.arg1.upper() != "S":
            # * VAR_IRE marginals: All vintage
            self.tc.enqueue(self.exec13)
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="PUTI6",
                    arg2="(RPC_IRE(R,P,C,'EXP')*RPCS_VAR(R,P,C,S))",
                    arg3="VAR_XEXP",
                    arg4="R.TL",
                    arg5="P.TL",
                    arg6="C.TL",
                    arg7="' '",
                    arg8="S.TL",
                    arg9=".M",
                    arg10="NV_FLOL(R,T,P,C,S)",
                    arg11="(R,TT,P,C,S)",
                    arg12="(R,TT(T--ORD(T)),P,C,S)",
                    arg13="",
                )
            )
            self.tc.enqueue(self.exec14)
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="PUTI6",
                    arg2="(RPC_IRE(R,P,C,'IMP')*RPCS_VAR(R,P,C,S))",
                    arg3="VAR_XIMP",
                    arg4="R.TL",
                    arg5="P.TL",
                    arg6="C.TL",
                    arg7="' '",
                    arg8="S.TL",
                    arg9=".M",
                    arg10="NV_FLOL(R,T,P,C,S)",
                    arg11="(R,TT,P,C,S)",
                    arg12="(R,TT(T--ORD(T)),P,C,S)",
                    arg13="",
                )
            )

        # * EQIRE marginals: ALL-vintage
        self.tc.enqueue(self.exec15, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2="(RPC_IRE(R,P,C,'EXP')*RPCS_VAR(R,P,C,S))",
                arg3="EQIRE_EXP",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="' '",
                arg8="S.TL",
                arg9=".M",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,S)",
                arg11=f"({self.arg3}R,TT,P,C,S)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,S)",
                arg13="",
            )
        )
        self.tc.enqueue(self.exec16, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2="(RPC_IRE(R,P,C,'IMP')*RPCS_VAR(R,P,C,S))",
                arg3="EQIRE_IMP",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="' '",
                arg8="S.TL",
                arg9=".M",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,S)",
                arg11=f"({self.arg3}R,TT,P,C,S)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,S)",
                arg13="",
            )
        )

        # * ELC supply by source
        self.tc.enqueue(self.exec17, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2="KEEP_FLOF(R,P,C)",
                arg3="ELC-",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="''",
                arg8="''",
                arg9="BY-SRC",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P,C,ANNUAL)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,ANNUAL)",
                arg13="",
            )
        )

        # *---------------------------------------------------------------------
        # * Output of VAR_CAP, units of capacity
        # *---------------------------------------------------------------------
        # *                                                                   ATTR      R      P     COM    V    TS   L/M
        self.tc.enqueue(self.exec18, arg1=self.arg1, arg3=self.arg3)
        # fmt: off
        batincludes = [
            ("PUTIT", "(RTP(R,T,P)*PRC_CAP(R,P))", "VAR_CAP", "R.TL", "P.TL", "' '", "' '", "' '", '.L', f"APARRTP({self.arg3}R,T,P)", f"({self.arg3}R,TT,P)", f"({self.arg3}R,TT(T--ORD(T)),P)", ""),
            ("PUTIT", f"(RTP(R,T,P)*{self.arg1}PAR_CAPM({self.arg3}R,T,P))", "VAR_CAP", "R.TL", "P.TL", "' '", "' '", "' '", '.M', f"{self.arg1}PAR_CAPM({self.arg3}R,T,P)", f"({self.arg3}R,TT,P)", f"({self.arg3}R,TT(T--ORD(T)),P)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )

        # *---------------------------------------------------------------------
        # * Output of Commodity and peaking balance, commodity units
        # *---------------------------------------------------------------------
        # *                                                                       ATTR       R    P    COM     V    TS    L/M
        if f"{self.env.stages}{self.env.scum}".upper() != "YES":
            # fmt: off
            batincludes = [
                ("PUTI4", "RCS_COMBAL(R,T,C,S,'LO')", "EQ_COMBAL", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', "EQG_COMBAL.L(R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
                ("PUTI4", "RCS_COMBAL(R,T,C,S,'FX')", "EQ_COMBAL", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', "EQE_COMBAL.L(R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
                ("PUTI4", "(RTCS_VARC(R,T,C,S)$COM_PKTS(R,C,S))", "EQ_PEAK", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', "EQ_PEAK.L(R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    SolsubtaAns(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                        arg9=arg[8],
                        arg10=arg[9],
                        arg11=arg[10],
                        arg12=arg[11],
                        arg13=arg[12],
                    )
                )
        # fmt: off
        batincludes = [
            ("PUTI4", "RTCS_VARC(R,T,C,S)", "EQ_COMBAL", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', f"{self.arg1}PAR_COMBALEM({self.arg3}R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
            ("PUTI4", "(RTCS_VARC(R,T,C,S)$COM_PKTS(R,C,S))", "EQ_PEAK", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', f"{self.arg1}PAR_PEAKM({self.arg3}R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )
        # * Balance variables
        self.tc.enqueue(self.exec19, arg1=self.arg1, arg3=self.arg3)
        # fmt: off
        batincludes = [
            ("PUTI4", "RHS_COMBAL(R,T,C,S)", "VAR_COMNET", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', f"{self.arg1}PAR_COMNETL({self.arg3}R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
            ("PUTI4", "RHS_COMBAL(R,T,C,S)", "VAR_COMNET", "R.TL", "' '", "C.TL", "' '", "S.TL", '.M', f"{self.arg1}PAR_COMNETM({self.arg3}R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
            ("PUTI4", "RHS_COMPRD(R,T,C,S)", "VAR_COMPRD", "R.TL", "' '", "C.TL", "' '", "S.TL", '.L', f"{self.arg1}PAR_COMPRDL({self.arg3}R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
            ("PUTI4", "RHS_COMPRD(R,T,C,S)", "VAR_COMPRD", "R.TL", "' '", "C.TL", "' '", "S.TL", '.M', f"{self.arg1}PAR_COMPRDM({self.arg3}R,T,C,S)", f"({self.arg3}R,TT,C,S)", f"({self.arg3}R,TT(T--ORD(T)),C,S)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )
        # *---------------------------------------------------------------------
        # * Output of user constraints
        # *---------------------------------------------------------------------
        # fmt: off
        batincludes = [
            ("UCITEM3", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,'NONE','NONE','NONE')",                   "UC.L", "''", "UC_N.TL", "' '", "' '", "' '", "' '", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,'NONE','NONE','NONE')", f"({self.arg3}UC_N,ITEM,ITEM,ITEM)", f"({self.arg3}UC_N,'','','')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,R,'NONE','NONE')",                        "UCR.L", "R.TL", "UC_N.TL", "' '", "' '", "' '", "' '", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,R,'NONE','NONE')", f"({self.arg3}UC_N,R,ITEM,ITEM)", f"({self.arg3}UC_N,R,'','')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,'NONE',T,'NONE')",                        "UCT", "''", "UC_N.TL", "' '", "' '", "' '", ".L", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,'NONE',T,'NONE')", f"({self.arg3}UC_N,ITEM,TT,ITEM)", f"({self.arg3}UC_N,'',TT(T--ORD(T)),'')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,R,T,'NONE')",                             "UCRT", "R.TL", "UC_N.TL", "' '", "' '", "' '", ".L", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,R,T,'NONE')", f"({self.arg3}UC_N,R,TT,ITEM)", f"({self.arg3}UC_N,R,TT(T--ORD(T)),'')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,'NONE',T,S)",                             "UCTS", "''", "UC_N.TL", "' '", "' '", "S.TL", ".L", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,'NONE',T,S)", f"({self.arg3}UC_N,ITEM,TT,S)", f"({self.arg3}UC_N,'',TT(T--ORD(T)),S)", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,R,T,S)",                                  "UCRTS", "R.TL", "UC_N.TL", "' '", "' '", "S.TL", ".L", f"{self.arg1}PAR_UCSL({self.arg3}UC_N,R,T,S)", f"({self.arg3}UC_N,R,TT,S)", f"({self.arg3}UC_N,R,TT(T--ORD(T)),S)", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,'NONE','NONE','NONE')",                   "UC.M", "''", "UC_N.TL", "' '", "' '", "' '", "' '", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,'NONE','NONE','NONE')", f"({self.arg3}UC_N,ITEM,ITEM,ITEM)", f"({self.arg3}UC_N,'','','')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,R,'NONE','NONE')",                        "UCR.M", "R.TL", "UC_N.TL", "' '", "' '", "' '", "' '", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,R,'NONE','NONE')", f"({self.arg3}UC_N,R,ITEM,ITEM)", f"({self.arg3}UC_N,R,'','')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,'NONE',T,'NONE')",                        "UCT", "''", "UC_N.TL", "' '", "' '", "' '", ".M", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,'NONE',T,'NONE')", f"({self.arg3}UC_N,ITEM,TT,ITEM)", f"({self.arg3}UC_N,'',TT(T--ORD(T)),'')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,R,T,'NONE')",                             "UCRT", "R.TL", "UC_N.TL", "' '", "' '", "' '", ".M", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,R,T,'NONE')", f"({self.arg3}UC_N,R,TT,ITEM)", f"({self.arg3}UC_N,R,TT(T--ORD(T)),'')", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,'NONE',T,S)",                             "UCTS", "''", "UC_N.TL", "' '", "' '", "S.TL", ".M", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,'NONE',T,S)", f"({self.arg3}UC_N,ITEM,TT,S)", f"({self.arg3}UC_N,'',TT(T--ORD(T)),S)", ""),
            ("UCITEM3", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,R,T,S)",                                  "UCRTS", "R.TL", "UC_N.TL", "' '", "' '", "S.TL", ".M", f"{self.arg1}PAR_UCSM({self.arg3}UC_N,R,T,S)", f"({self.arg3}UC_N,R,TT,S)", f"({self.arg3}UC_N,R,TT(T--ORD(T)),S)", ""),
            ("CUMITEM4", f"{self.arg1}PAR_UCMRK({self.arg3}R,T,ITEM,C,S)",                              "UC_MARK", "R.TL", "ITEM.TL", "C.TL", "' '", "S.TL", ".M", f"{self.arg1}PAR_UCMRK({self.arg3}R,T,ITEM,C,S)", f"({self.arg3}R,TT,ITEM,C,S)", f"({self.arg3}R,TT(T--ORD(T)),ITEM,C,S)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )
        # *---------------------------------------------------------------------
        # * Output of cumulatives
        # *---------------------------------------------------------------------
        self.tc.enqueue(
            self.exec20,
            arg1=self.arg1,
            arg3=self.arg3,
            var=self.env.var,
            sow=self.env.sow,
            cucscal=self.env.cucscal,
        )

        # fmt: off
        batincludes = [
            ("CUMITEM4", "RC_CUMCOM(R,COM_VAR,YEAR,LL,C)", "VAR_CUMNET.L", "R.TL", '" "', "C.TL", 'YEAR.TL,"-",LL.TL', "' '", "' '", f'{self.arg1}PAR_CUMCOML({self.arg3}R,C,"NET",YEAR,LL)', f"({self.arg3}R,C,COM_VAR,YEAR,LL)", f'({self.arg3}R,C,COM_VAR("NET"),YEAR,LL)', ""),
            ("CUMITEM4", "RC_CUMCOM(R,COM_VAR,YEAR,LL,C)", "VAR_CUMNET.M", "R.TL", '" "', "C.TL", 'YEAR.TL,"-",LL.TL', "' '", "' '", f'{self.arg1}PAR_CUMCOMM({self.arg3}R,C,"NET",YEAR,LL)', f"({self.arg3}R,C,COM_VAR,YEAR,LL)", f'({self.arg3}R,C,COM_VAR("NET"),YEAR,LL)', ""),
            ("CUMITEM4", "RC_CUMCOM(R,COM_VAR,YEAR,LL,C)", "VAR_CUMPRD.L", "R.TL", '" "', "C.TL", 'YEAR.TL,"-",LL.TL', "' '", "' '", f'{self.arg1}PAR_CUMCOML({self.arg3}R,C,"PRD",YEAR,LL)', f"({self.arg3}R,C,COM_VAR,YEAR,LL)", f'({self.arg3}R,C,COM_VAR("PRD"),YEAR,LL)', ""),
            ("CUMITEM4", "RC_CUMCOM(R,COM_VAR,YEAR,LL,C)", "VAR_CUMPRD.M", "R.TL", '" "', "C.TL", 'YEAR.TL,"-",LL.TL', "' '", "' '", f'{self.arg1}PAR_CUMCOMM({self.arg3}R,C,"PRD",YEAR,LL)', f"({self.arg3}R,C,COM_VAR,YEAR,LL)", f'({self.arg3}R,C,COM_VAR("PRD"),YEAR,LL)', ""),
            ("CUMITEM4", "RPC_CUMFLO(R,P,C,YEAR,LL)", "VAR_CUMFLO.L", "R.TL", 'P.TL', "C.TL", 'YEAR.TL,"-",LL.TL', "' '", "' '", f'{self.arg1}PAR_CUMFLOL({self.arg3}R,P,C,YEAR,LL)', f"({self.arg3}R,P,C,YEAR,LL)", f'({self.arg3}R,P,C,YEAR,LL)', ""),
            ("CUMITEM4", "RPC_CUMFLO(R,P,C,YEAR,LL)", "VAR_CUMFLO.M", "R.TL", 'P.TL', "C.TL", 'YEAR.TL,"-",LL.TL', "' '", "' '", f'{self.arg1}PAR_CUMFLOM({self.arg3}R,P,C,YEAR,LL)', f"({self.arg3}R,P,C,YEAR,LL)", f'({self.arg3}R,P,C,YEAR,LL)', ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )
        # *---------------------------------------------------------------------
        # * Output of various cost components - only non-zero series
        # *---------------------------------------------------------------------
        self.env.set_scoped("supzero", "YES")
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
PARAMETER REG_OBJ2({self.arg2}REG,ITEM);
""",
        )
        self.tc.enqueue(self.exec21, arg1=self.arg1, arg3=self.arg3)
        if self.env.stages.upper() != "YES":
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="UNCD1",
                    arg2="YES",
                    arg3="OBJZ",
                    arg4="''",
                    arg5="''",
                    arg6="''",
                    arg7="''",
                    arg8="''",
                    arg9="",
                    arg10="OBJZ.L",
                    arg11="(ANNUAL)",
                    arg12="(ANNUAL)",
                    arg13="",
                )
            )

        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="RXX",
                arg2=f"REG_OBJ2({self.arg3}R,ITEM)",
                arg3="REG_OBJ",
                arg4="R.TL",
                arg5="''",
                arg6="ITEM.TL",
                arg7="''",
                arg8="''",
                arg9="",
                arg10=f"REG_OBJ2({self.arg3}R,ITEM)",
                arg11=f"(R,{self.arg3}ITEM{self.env.item2})",
                arg12=f"(R,{self.arg3}ITEM{self.env.item2})",
                arg13="",
            )
        )

        # *                                                            ATTR       R      P     COM    V     TS    L/M
        # * Annualized investment costs
        self.tc.enqueue(self.exec22, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RTP(R,T,P)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="INV",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P)",
                arg13="",
            )
        )
        # * Annualized investment taxes/subsidies
        self.tc.enqueue(self.exec23, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RTP(R,T,P)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="INVX",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P)",
                arg13="",
            )
        )
        # * Total salvage value at EOH+1
        self.tc.enqueue(self.exec24, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RP(R,P)",
                arg3="COST_SALV",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,T,P)",
                arg12=f"({self.arg3}R,T(MIYR_1),P)",
                arg13="",
            )
        )
        # * Annualized decommissioning costs
        self.tc.enqueue(self.exec25, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RTP(R,T,P)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="DEC",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P)",
                arg13="",
            )
        )
        # * Annualized fixed costs
        self.tc.enqueue(self.exec26, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RTP(R,T,P)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="FOM",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P)",
                arg13="",
            )
        )
        # * Annualized fixed taxes/subsidies
        self.tc.enqueue(self.exec27, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RTP(R,T,P)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="FIXX",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P)",
                arg13="",
            )
        )
        # * Annualized activity costs
        self.tc.enqueue(self.exec28, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTIT",
                arg2="RTP(R,T,P)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="ACT",
                arg10=f"NV_ACTL({self.arg3}R,T,P,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P)",
                arg13="",
            )
        )
        # * Annualized flow costs
        self.tc.enqueue(self.exec29, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2="RPC(R,P,C)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="''",
                arg8="''",
                arg9="FLO",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P,C,ANNUAL)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,ANNUAL)",
                arg13="",
            )
        )
        # * Annualized flow taxes/subsidies
        self.tc.enqueue(self.exec30, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2="RPC(R,P,C)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="''",
                arg8="''",
                arg9="FLOX",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P,C,ANNUAL)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,ANNUAL)",
                arg13="",
            )
        )
        # * Annualized implied trade costs
        self.tc.enqueue(self.exec31, arg1=self.arg1, arg3=self.arg3)
        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="PUTI6",
                arg2="RPC(R,P,C)",
                arg3="COST_",
                arg4="R.TL",
                arg5="P.TL",
                arg6="C.TL",
                arg7="''",
                arg8="''",
                arg9="IRE",
                arg10=f"NV_FLOL({self.arg3}R,T,P,C,'ANNUAL')",
                arg11=f"({self.arg3}R,TT,P,C,ANNUAL)",
                arg12=f"({self.arg3}R,TT(T--ORD(T)),P,C,ANNUAL)",
                arg13="",
            )
        )

        # fmt: off
        batincludes = [
            # * Annualized commodity costs
            ("PUTI4", "RTC(R,T,C)", "COST_", "R.TL", 'C.TL', "' '", "' '", "' '", "COM", f"{self.arg1}CST_COMC({self.arg3}R,T,C)", f"({self.arg3}R,TT,C,ANNUAL)", f"({self.arg3}R,TT(T--ORD(T)),C,ANNUAL)", ""),
            # * Annualized commodity taxes/subsidies
            ("PUTI4", "RTC(R,T,C)", "COST_", "R.TL", 'C.TL', "' '", "' '", "' '", "COMX", f"{self.arg1}CST_COMX({self.arg3}R,T,C)", f"({self.arg3}R,TT,C,ANNUAL)", f"({self.arg3}R,TT(T--ORD(T)),C,ANNUAL)", ""),
            # * Annualized demand elasticity costs
            ("PUTI4", "RTC(R,T,C)", "COST_", "R.TL", 'C.TL', "' '", "' '", "' '", "ELS", f"{self.arg1}CST_COME({self.arg3}R,T,C)", f"({self.arg3}R,TT,C,ANNUAL)", f"({self.arg3}R,TT(T--ORD(T)),C,ANNUAL)", ""),
            # * Annualized commodity costs
            ("PUTI4", "RTC(R,T,C)", "COST_", "R.TL", 'C.TL', "' '", "' '", "' '", "DAM", f"{self.arg1}CST_DAM({self.arg3}R,T,C)", f"({self.arg3}R,TT,C,ANNUAL)", f"({self.arg3}R,TT(T--ORD(T)),C,ANNUAL)", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                    arg12=arg[11],
                    arg13=arg[12],
                )
            )

        # * MACRO
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
SET XRT({self.arg2}ITEM,U2,T);
""",
        )

        if self.arg1 == "":
            self.include(
                SolsubtaAns(
                    self.tc,
                    self.env,
                    arg1="XRT",
                    arg2="TM_RESULT(ITEM,R,T)",
                    arg3="",
                    arg4="R.TL",
                    arg5="''",
                    arg6="''",
                    arg7="''",
                    arg8="''",
                    arg9="_",
                    arg10="TM_RESULT(ITEM,R,T)",
                    arg11="(ITEM,R,TT)",
                    arg12="(ITEM,R,TT(T--ORD(T)))",
                    arg13="@1,ITEM.TL",
                )
            )

        self.include(
            SolsubtaAns(
                self.tc,
                self.env,
                arg1="XRT",
                arg2=f"CM_{self.arg1}RESULT({self.arg3}ITEM,U2,T)",
                arg3="CM",
                arg4="''",
                arg5="''",
                arg6="''",
                arg7="''",
                arg8="''",
                arg9="_",
                arg10=f"CM_{self.arg1}RESULT({self.arg3}ITEM,U2,T)",
                arg11=f"({self.arg3}ITEM,U2,TT)",
                arg12=f"({self.arg3}ITEM,U2,TT(T--ORD(T)))",
                arg13="ITEM.TL",
            )
        )
        self.tc.enqueue(self.exec32)

    def exec1(self: SolputtaAns) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
SOW(W)=AUXSOW(W);
""",
        )

    def exec2(self: SolputtaAns, run_name: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* reconstruct variable levels and marginals for those eliminated by the REDUCE option

* Scenario name for run coming from $SET RUN_NAME in *.DD or .RUN file
FILE sola / {run_name}.ANT /;

sola.PW=1000;
sola.ND=4;
sola.NW=15;
sola.LW=0;

PUT sola;
PUT '*** ' SYSTEM.TITLE
PUT / '*** Case  {run_name}' /
""",
        )

    def exec3(self: SolputtaAns, arg1: str, arg3: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  NV_ACTL({arg3}RTP_VARA(R,T,P),S)$PRC_TS(R,P,S) = SUM(YK(T,V)${arg1}PAR_ACTL({arg3}R,V,T,P,S),{arg1}PAR_ACTL({arg3}R,V,T,P,S));
  NV_ACTM({arg3}R,T,P,S)$(NOT PRC_VINT(R,P)) $= ABS({arg1}PAR_ACTM({arg3}R,T,T,P,S));
  NV_ACTM({arg3}RTP_VARA(R,T,P),S)$(PRC_TS(R,P,S)$PRC_VINT(R,P)) = SMIN(RTP_VINTYR(R,V,T,P),ABS({arg1}PAR_ACTM({arg3}R,V,T,P,S)));
""",
        )

    def exec4(self: SolputtaAns, arg1: str, arg3: str, vart: str, sws: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(TT(T--1),Z=ORD(T)-1;{arg1}PAR_RET({arg3}RTP_CPTYR(R,V,T,P))$PRC_RCAP(R,P) = MAX(0,{vart}_SCAP.L(R,V,T,P{sws})-RTFORC(R,V,T,P)-({vart}_SCAP.L(R,V,TT,P{sws})-RTFORC(R,V,TT,P))$Z));
""",
        )

    def exec5(self: SolputtaAns, arg1: str, arg3: str, vart: str, sws: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR={arg1}PAR_RET; LOOP(RTP(R,V,P)$PRC_RCAP(R,P),Z=1;LOOP(RTP_CPTYR(R,VNRET(V,T),P)$Z,Z=0; {arg1}PAR_RET({arg3}R,V,T,P) $= {vart}_SCAP.L(R,V,T,P{sws})));
  {arg1}PAR_RET({arg3}R,V,T,P) $= {vart}_RCAP.L(R,V,T,P{sws});
""",
        )

    def exec6(self: SolputtaAns, arg1: str, arg3: str, vart: str, sws: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR={arg1}PAR_RET; {arg1}PAR_RET({arg3}R,V,T,P) $= {vart}_RCAP.M(R,V,T,P{sws});
""",
        )

    def exec7(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL; OPTION PUTI6 < {arg1}F_IN;
  NV_FLOL(PUTI6({arg3}R,T,P,C,S)) = SUM(YK(T,V)${arg1}F_IN({arg3}R,V,T,P,C,S),{arg1}F_IN({arg3}R,V,T,P,C,S));
""",
        )

    def exec8(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL; OPTION PUTI6 < {arg1}F_OUT;
  NV_FLOL(PUTI6({arg3}R,T,P,C,S)) = SUM(YK(T,V)${arg1}F_OUT({arg3}R,V,T,P,C,S),{arg1}F_OUT({arg3}R,V,T,P,C,S));
""",
        )

    def exec9(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL;
  TRACKPC(RPC(R,P,C))$(NOT RPC_FFUNC(R,P,C)+RPC_EMIS(R,P,C)) = YES;
  NV_FLOL({arg3}R,T,P,C,S)$(TRACKPC(R,P,C)$(NOT PRC_VINT(R,P))) $= ABS({arg1}PAR_FLOM({arg3}R,T,T,P,C,S))*(1/COEF_PVT(R,T));
  NV_FLOL(RTPCS_VARF({arg3}R,T,P,C,S))$(TRACKPC(R,P,C)$PRC_VINT(R,P)) = SMIN(RTP_VINTYR(R,V,T,P),ABS({arg1}PAR_FLOM({arg3}R,V,T,P,C,S)))/COEF_PVT(R,T);
""",
        )

    def exec10(self: SolputtaAns) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION CLEAR=TRACKPC;
""",
        )

    def exec11(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL,CLEAR=PUTI3;
  PUTI3({arg3}R,LL--ORD(LL),T,P,C,S)$RP_IRE(R,P) $= {arg1}F_IN({arg3}R,LL,T,P,C,S); OPTION PUTI6 < PUTI3;
  NV_FLOL(PUTI6({arg3}R,T,P,C,S)) = SUM(YK(T,V)${arg1}F_IN({arg3}R,V,T,P,C,S),{arg1}F_IN({arg3}R,V,T,P,C,S));
""",
        )

    def exec12(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL,CLEAR=PUTI3;
  PUTI3({arg3}R,LL--ORD(LL),T,P,C,S)$RP_IRE(R,P) $= {arg1}F_OUT({arg3}R,LL,T,P,C,S); OPTION PUTI6 < PUTI3;
  NV_FLOL(PUTI6({arg3}R,T,P,C,S)) = SUM(YK(T,V)${arg1}F_OUT({arg3}R,V,T,P,C,S),{arg1}F_OUT({arg3}R,V,T,P,C,S));
""",
        )

    def exec13(
        self: SolputtaAns,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION CLEAR=NV_FLOL;
  NV_FLOL(RTPCS_VARF(R,T,P,C,S))$RPC_IRE(R,P,C,'EXP') = SMIN(RTP_VINTYR(R,V,T,P),ABS(PAR_IREM(R,V,T,P,C,S,'EXP')))/COEF_PVT(R,T);
""",
        )

    def exec14(
        self: SolputtaAns,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION CLEAR=NV_FLOL;
  NV_FLOL(RTPCS_VARF(R,T,P,C,S))$RPC_IRE(R,P,C,'IMP') = SMIN(RTP_VINTYR(R,V,T,P),ABS(PAR_IREM(R,V,T,P,C,S,'IMP')))/COEF_PVT(R,T);
""",
        )

    def exec15(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL;
  NV_FLOL({arg3}R,T,P,C,S)$RP_IRE(R,P) $= {arg1}PAR_IPRIC({arg3}R,T,P,C,S,'EXP');
""",
        )

    def exec16(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL;
  NV_FLOL({arg3}R,T,P,C,S)$RP_IRE(R,P) $= {arg1}PAR_IPRIC({arg3}R,T,P,C,S,'IMP');
""",
        )

    def exec17(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=NV_FLOL; OPTION PUTI7 < {arg1}PAR_EOUT; NV_FLOL({arg3}R,T,P,C,ANNUAL)$PUTI7({arg3}R,T,P,C)=SUM(YK(T,V)${arg1}PAR_EOUT({arg3}R,V,T,P,C),{arg1}PAR_EOUT({arg3}R,V,T,P,C));
""",
        )

    def exec18(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  APARRTP({arg3}RTP(R,T,P)) = {arg1}PAR_CAPL({arg3}R,T,P)+SUM(PASTCV,{arg1}PAR_PASTI({arg3}R,T,P,PASTCV));
""",
        )

    def exec19(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{f"LOOP({arg3}" if arg1.upper() == "S" else ""}
  RHS_COMBAL(R,T,C,S)$={arg1}PAR_COMNETL({arg3}R,T,C,S); RHS_COMPRD(R,T,C,S)$={arg1}PAR_COMPRDL({arg3}R,T,C,S);
{" );" if arg1.upper() == "S" else ""}
""",
        )

    def exec20(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
        var: str,
        sow: str,
        cucscal: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Cumcom results (unscaling)
  {arg1}PAR_CUMCOML({arg3}R,C,COM_VAR,ALLYEAR,LL) $= {var}_CUMCOM.L(R,C,COM_VAR,ALLYEAR,LL{sow})*{cucscal};
  {arg1}PAR_CUMCOMM({arg3}R,C,COM_VAR,ALLYEAR,LL) $= {var}_CUMCOM.M(R,C,COM_VAR,ALLYEAR,LL{sow})*(1/{cucscal});
""",
        )

    def exec21(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
REG_OBJ2({arg3}R,ITEM) $= SUM(RDCUR(R,CUR)${arg1}REG_WOBJ({arg3}R,ITEM,CUR),{arg1}REG_WOBJ({arg3}R,ITEM,CUR));
REG_OBJ2({arg3}R,'IRE') = {arg1}REG_IREC({arg3}R);
""",
        )

    def exec22(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized investment costs
OPTION CLEAR=NV_ACTL; OPTION PUTIT < {arg1}CST_INVC; NV_ACTL({arg3}R,T,P,ANNUAL)$PUTIT({arg3}R,T,P)=SUM((YK(T,V),SYSINV)${arg1}CST_INVC({arg3}R,V,T,P,SYSINV),{arg1}CST_INVC({arg3}R,V,T,P,SYSINV));
""",
        )

    def exec23(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized investment taxes/subsidies
OPTION CLEAR=NV_ACTL; OPTION PUTIT < {arg1}CST_INVX; NV_ACTL({arg3}R,T,P,ANNUAL)$PUTIT({arg3}R,T,P)=SUM((YK(T,V),SYSINV)${arg1}CST_INVX({arg3}R,V,T,P,SYSINV),{arg1}CST_INVX({arg3}R,V,T,P,SYSINV));
""",
        )

    def exec24(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Total salvage value at EOH+1
OPTION CLEAR=NV_ACTL;NV_ACTL({arg3}R,TT(MIYR_1),P,ANNUAL) $= SUM((RTP(R,T,P),RDCUR(R,CUR)),{arg1}PAR_OBJSAL({arg3}R,T,P,CUR)*(1/OBJ_DCEOH(R,CUR)));
""",
        )

    def exec25(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized decommissioning costs
OPTION CLEAR=NV_ACTL;NV_ACTL({arg3}R,T,P,ANNUAL) $= SUM(RTP_CPTYR(R,V,T,P),{arg1}CST_DECC({arg3}R,V,T,P));
""",
        )

    def exec26(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized fixed costs
OPTION CLEAR=NV_ACTL; OPTION PUTIT < {arg1}CST_FIXC; NV_ACTL({arg3}R,T,P,ANNUAL)$PUTIT({arg3}R,T,P)=SUM(YK(T,V)${arg1}CST_FIXC({arg3}R,V,T,P),{arg1}CST_FIXC({arg3}R,V,T,P));
""",
        )

    def exec27(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized fixed taxes/subsidies
OPTION CLEAR=NV_ACTL; OPTION PUTIT < {arg1}CST_FIXX; NV_ACTL({arg3}R,T,P,ANNUAL)$PUTIT({arg3}R,T,P)=SUM(YK(T,V)${arg1}CST_FIXX({arg3}R,V,T,P),{arg1}CST_FIXX({arg3}R,V,T,P));
""",
        )

    def exec28(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized activity costs
OPTION CLEAR=NV_ACTL; OPTION PUTIT < {arg1}CST_ACTC; NV_ACTL({arg3}R,T,P,ANNUAL)$PUTIT({arg3}R,T,P)=SUM((YK(T,V),RPM)${arg1}CST_ACTC({arg3}R,V,T,P,RPM),{arg1}CST_ACTC({arg3}R,V,T,P,RPM));
""",
        )

    def exec29(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized flow costs
OPTION CLEAR=NV_FLOL; OPTION PUTI7 < {arg1}CST_FLOC; NV_FLOL({arg3}R,T,P,C,ANNUAL)$PUTI7({arg3}R,T,P,C)=SUM(YK(T,V)${arg1}CST_FLOC({arg3}R,V,T,P,C),{arg1}CST_FLOC({arg3}R,V,T,P,C));
""",
        )

    def exec30(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized flow taxes/subsidies
OPTION CLEAR=NV_FLOL; OPTION PUTI7 < {arg1}CST_FLOX; NV_FLOL({arg3}R,T,P,C,ANNUAL)$PUTI7({arg3}R,T,P,C)=SUM(YK(T,V)${arg1}CST_FLOX({arg3}R,V,T,P,C),{arg1}CST_FLOX({arg3}R,V,T,P,C));
""",
        )

    def exec31(
        self: SolputtaAns,
        arg1: str,
        arg3: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Annualized implied trade costs
OPTION CLEAR=NV_FLOL; OPTION PUTI7 < {arg1}CST_IREC; NV_FLOL({arg3}R,T,P,C,ANNUAL)$PUTI7({arg3}R,T,P,C)=SUM(YK(T,V)${arg1}CST_IREC({arg3}R,V,T,P,C),{arg1}CST_IREC({arg3}R,V,T,P,C));
""",
        )

    def exec32(self: SolputtaAns) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
PUTCLOSE sola;
""",
        )
