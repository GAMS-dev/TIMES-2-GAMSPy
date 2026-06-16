# curex_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CUREX.GMS oversees the currency conversions
# *   arg1 - name of cost attribute
# *   arg2 - name of temp attribute (set to arg1 if no temp used)
# *   arg3 - indexes before CUR
# *   arg4 - constant indexes before CUR (optional, for temp attribute)
# *   arg5 - indexes after CUR
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CurexGms(GamsClass):
    """Translation unit for curex.gms."""

    # Instance attributes
    module_name: str = "curex_gms"
    gams_source: str = "curex.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.compile()

    def compile(self) -> None:
        if self.env.intext_only == "YES":
            return  # $EXIT
        else:
            if self.arg1 != "":  # SUBR
                if self.arg6 == "":
                    self.env.set_scoped("mx", "1$YEARVAL(LL)")

                if self.arg2 not in self.tc.container.listSymbols():
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=rf"""
PARAMETER {self.arg2}({self.arg3},CUR);
""",
                    )

                self.tc.enqueue(
                    self.exec1,
                    condition=(self.arg1.upper() == self.arg2.upper()),
                    arg1=self.arg1,
                    arg2=self.arg2,
                    arg3=self.arg3,
                    arg4=self.arg4,
                    arg5=self.arg5,
                    arg6=self.arg6,
                    mx=self.env.mx,
                )

            else:
                self.comp1()
                self.tc.enqueue(self.initialization)
                # fmt: off
                batincludes = [
                    ("NCAP_COST", "RYPM", "R,LL,P", "", "", ""),
                    ("NCAP_ITAX", "RYPM ", "R,LL,P", "", "", ""),
                    ("NCAP_ISUB", "RYPM ", "R,LL,P", "", "", ""),
                    ("NCAP_DCOST", "RYPM ", "R,LL,P", "", "", ""),
                    ("NCAP_DLAGC", "RYPM ", "R,LL,P", "", "", ""),
                    ("NCAP_FOM", "RYPM ", "R,LL,P", "", "", ""),
                    ("NCAP_FSUB", "RYPM ", "R,LL,P", "", "", ""),
                    ("NCAP_FTAX", "RYPM ", "R,LL,P", "", "", ""),
                    ("ACT_COST", "RYPM ", "R,LL,P", "", "", ""),
                    ("FLO_COST", "RYPCSM ", "R,LL,P,C,S", "", "", ""),
                    ("FLO_DELIV", "RYPCSM ", "R,LL,P,C,S", "", "", ""),
                    ("FLO_TAX", "RYPCSM ", "R,LL,P,C,S", "", "", ""),
                    ("FLO_SUB", "RYPCSM ", "R,LL,P,C,S", "", "", ""),
                    ("NCAP_VALU", "RYPCSM ", "R,LL,P,C", ",'ANNUAL'", "", ""),
                    ("IRE_PRICE", "RYPCSRXM ", "R,LL,P,C,S,ALL_R,IE", "", "", ""),
                    ("COM_BPRICE", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("COM_CSTNET", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("COM_TAXNET", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("COM_SUBNET", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("COM_CSTPRD", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("COM_TAXPRD", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("COM_SUBPRD", "RYCSM ", "R,LL,C,S", "", "", ""),
                    ("REG_BNDCST", "REG_BNDCST ", "R,LL,COSTAGG", "", ",BD", ""),
                    ("REG_CUMCST", "REG_CUMCST ", "R,LL,YEAR,COSTAGG", "", ",BD", ""),
                    ("BL_VAROMC", "BL_VAROMC ", "R,COM", "", "", "1"),
                    ("BL_DELIVC", "BL_DELIVC ", "R,C,COM", "", "", "1"),
                    ("ACT_CSTUP", "ACT_CSTUP ", "R,LL,P,TSL", "", "", ""),
                    ("ACT_CSTSD", "ACT_CSTSD ", "R,LL,P,UPT,BD", "", "", ""),
                    ("ACT_CSTRMP", "ACT_CSTRMP ", "R,LL,P,BD", "", "", ""),
                    ("ACT_CSTPL", "RYPM ", "R,LL,P", "", "", ""),
                ]
                # fmt: on
                for arg in batincludes:
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            arg1=arg[0],
                            arg2=arg[1],
                            arg3=arg[2],
                            arg4=arg[3],
                            arg5=arg[4],
                            arg6=arg[5],
                        )
                    )

                if self.tc.defined("TL_CT_COST"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            arg1="TL_CT_COST",
                            arg2="RYPM",
                            arg3="R,LL,P",
                        )
                    )

                if self.tc.defined("DAM_COST"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            arg1="DAM_COST",
                            arg2="RYCSM",
                            arg3="R,LL,C",
                            arg4=",'ANNUAL'",
                        )
                    )

                if self.tc.defined("S_DAM_COST"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            arg1="S_DAM_COST",
                            arg2="S_DAM_COST",
                            arg3="R,LL,C",
                            arg4="",
                            arg5=",J,ALLSOW",
                        )
                    )

                if self.tc.defined("S_COM_TAX"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            arg1="S_COM_TAX",
                            arg2="S_COM_TAX",
                            arg3="R,LL,C,S,COM_VAR",
                            arg4="",
                            arg5=",J,ALLSOW",
                        )
                    )

                self.tc.enqueue(self.exec2, prf=self.env.prf)

    def initialization(self: CurexGms) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=CURMAP,PROFILE=0;
R_CUREX(R,CUR,CUR) = 0;
*--------------------------------------------------------------------------
* Convert only if unambiguous single target RDCUR
LOOP((R,CURR),
 IF((SUM(RDCUR(R,CUR)$R_CUREX(R,CURR,CUR),1) EQ 1),
      CURMAP(RDCUR(R,CUR),CURR)$R_CUREX(R,CURR,CUR) = YES;
 ELSE CURMAP(RDCUR(R,CURR),CURR) = YES));
LOOP(CURMAP(R,CUR,CURR)$(NOT SAMEAS(CUR,CURR)), RDCUR(R,CURR) = NO);
R_CUREX(RDCUR(R,CUR),CUR) = 1;

* Resolve two-step chained conversion
OPTION CLEAR=RXX;
LOOP((CURMAP(RDCUR(R,CUR),CURR),CRU)$((NOT RDCUR(R,CURR))$CURMAP(R,CURR,CRU)),RXX(R,CURR,CRU)$(NOT R_CUREX(R,CRU,CUR))=YES);
LOOP(RXX(R,CURR,CRU),R_CUREX(R,CRU,CUR)$CURMAP(R,CUR,CURR)=R_CUREX(R,CRU,CURR)*R_CUREX(R,CURR,CUR));
LOOP(RXX(R,CURR,CRU),CURMAP(R,CURR,CRU)=NO; CURMAP(R,CUR,CRU)$CURMAP(R,CUR,CURR)=YES);
""",
        )

    def exec1(
        self: CurexGms,
        condition: bool,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        arg6: str,
        mx: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{f"OPTION CLEAR={arg2}; {arg2}({arg3}{arg4},CUR) $= {arg1}({arg3},CUR); OPTION CLEAR={arg1};" if not condition else ""}
{arg1}({arg3},CUR{arg5}) $= SUM(CURMAP(R,CUR,CURR)${arg2}({arg3}{arg4},CURR{arg5}),{arg2}({arg3}{arg4},CURR{arg5})*POWER(R_CUREX(R,CURR,CUR),{arg6}{mx}));
{f"{arg1}({arg3},CUR{arg5})$(NOT RDCUR(R,CUR)) = 0;" if condition else ""}
""",
        )

    def exec2(self: CurexGms, prf: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION PRO{prf},CLEAR=RYPM,CLEAR=RYPCSM,CLEAR=RYPCSRXM,CLEAR=RYCSM;
""",
        )

    def comp1(self: CurexGms) -> None:
        g = self.tc
        m = g.container
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
SET CURMAP(REG,CUR,CUR);
""",
        )
        Alias(m, "CRU", alias_with=g.cur)
