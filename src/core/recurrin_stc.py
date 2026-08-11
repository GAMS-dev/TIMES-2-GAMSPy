# recurrin_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RECURRIN.stc oversees recurring stochastic definitions
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RecurrinStc(GamsClass):  # FilenameExt
    """Translation unit for recurrin.stc."""

    # Instance attributes
    module_name: str = "recurrin_stc"
    gams_source: str = "recurrin.stc"

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
        self.env.set_scoped("tst", "NO")
        if self.env.obmac.upper() == "YES":
            self.env.set_scoped("tst", "YES")

        if self.arg1.upper() == "MXPAR":
            if self.env.stages == "YES":
                self.env.set_global("varmac", "1==1")
                self.env.set_global("vas", "VAS")
            self.env.set_scoped("need", "NO")

            if (
                self.tc.defined("S_NCAP_AFS")
                or self.tc.defined("S_COM_FR")
                or self.env.spines.upper() == "YES"
            ):
                self.env.set_scoped("need", "YES")

            if self.env.need != "NO":
                if not self.env.tst == "TST":
                    raise Exception("Macro support needed. Upgrade your GAMS system.")
                self.env.set_scoped("sw1", "")
                self.env.set_scoped("sw1_GP", ())
                self.env.set_scoped("sw2", "")
                if self.env.stages != "YES":
                    self.env.set_scoped("sw1", "SUM")
                    self.env.set_scoped(
                        "sw1_GP", ("SUM",)
                    )  # NOTE: UPDATE THIS USAGE, AS REQUIRED
                    self.env.set_scoped("sw2", "SOW,")
                self.env.set_global("mx", "MX")
                self.env.set_global("mx_GP", "MX")
                self.tc.add_gams_code(module=self, phase="init", code=r"$macro MX")
                if not self.tc.defined("S_NCAP_AFS"):
                    self.tc.add_gams_code(
                        module=self, phase="init", code=r"$MACRO COEF_AFMX COEF_AF"
                    )
                if not self.tc.defined("S_COM_FR"):
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""$MACRO RTCS_FRMX RTCS_FR
$MACRO COM_FRMX COM_FR""",
                    )
                if self.env.spines.upper() != "YES":
                    self.tc.add_gams_code(
                        module=self, phase="init", code=r"$MACRO PRC_DYNUCMX PRC_DYNUC"
                    )
                if self.tc.defined("S_NCAP_AFS"):
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=rf"$MACRO COEF_AFMX(R,V,T,P,S,BD) COEF_AF(R,V,T,P,S,BD)*{self.env.sw1}({self.env.sw2}1+RTP_SAFS(R,T,P,S,SOW))",
                    )
                if self.tc.defined("S_COM_FR"):
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=rf"""
PARAMETER  RTCS_FRMX(R,T,C,S,S);
$MACRO RTCS_FR(R,T,C,S,TS) RTCS_FRMX(R,T,C,S,TS)+SUM(SW_T2W(SOW,T,W,T0),RCS_SSFR(R,C,S,TS,W,T0))
$MACRO COM_FRMX(R,T,C,S) COM_FR(R,T,C,S)*{self.env.sw1}({self.env.sw2}1+S_COM_FR(R,T,C,S,'1',SOW))
""",
                    )

        elif self.arg1.upper() == "SPINES":
            if self.env.spines.upper() == "YES":
                if not self.env.tst == "TST":
                    raise Exception("Macro support needed. Upgrade your GAMS system.")
                self.env.set_scoped("vsum", "SUM(SW_TSW(SOW,")
                self.env.set_global(
                    "sw_stvars",
                    rf"SET VAR \"Z\" SET VART '{self.env.vsum}T,W),Z' SET VARM '{self.env.vsum}MODLYEAR,W),Z' SET VARV '{self.env.vsum}V,W),Z'",
                )
                self.env.set_global("witspine", True)
                self.env.set_global("ewispine", True)
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=r"SET OBJSW1(OBV); SET UCRTPSW1(UC_GRPTYPE,WW);",
                )
                self.tc.enqueue(self.spines_exec)
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=r"""
$macro QED
$macro PRC_DYNUCMX(uc,side,r,t,p,grp,bd) PRC_DYNUC(uc,side,r,t,p,grp,bd)$UCRTPSW1(grp,SOW)
*-----------------------------------------------------------------------------
* Equations (only if needed)
$macro Q_OBJELS          ES_OBJELS
$macro Q_OBJFIX(rc,sow)  ES_OBJFIX(rc,SOW('1'))
$macro Q_OBJINV(rc,sow)  ES_OBJINV(rc,SOW('1'))
$macro Q_OBJSALV(rc,sow) ES_OBJSALV(rc,SOW('1'))
$macro Q_OBJVAR          ES_OBJVAR
$macro Q_ROBJ            ES_ROBJ
$macro Q_SOBJ            ES_SOBJ

$macro QG_CPT(rtp,swt)   ESG_CPT(rtp,T,SOW('1'))
$macro QE_CPT(rtp,swt)   ESE_CPT(rtp,T,SOW('1'))
$macro QL_CPT(rtp,swt)   ESL_CPT(rtp,T,SOW('1'))
$macro Q_DSCRET(cpt,sw)  ES_DSCRET(cpt,T,SOW('1'))
$macro Q_CUMRET(r,v,p,w) ES_CUMRET(r,v,p,T,SOW('1'))
$macro QL_REFIT(rttp,l,swt) ESL_REFIT(rttp,l,T,SOW('1'))
$macro Q_DSCNCAP(rtp,sw) ES_DSCNCAP(rtp,T,SOW('1'))
$macro Q_DSCONE(rtp,swt) ES_DSCONE(rtp,T,SOW('1'))

$macro QE_UCT    ESE_UCT
$macro QE_UCRT   ESE_UCRT
$macro QE_UCTS   ESE_UCTS
$macro QE_UCRS   ESE_UCRS
$macro QE_UCRTS  ESE_UCRTS
""",
                )

                if self.env.solveda != "1":
                    self.env.set_global(
                        "sw_stvars",
                        f"{self.env.sw_stvars} SET VARTT '{self.env.vsum}TT,W),Z' SET SWSW SW_TSW(SOW,T,WW),",
                    )
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""
$macro Q_CUMNET  ES_CUMNET
$macro Q_CUMPRD  ES_CUMPRD
$macro Q_CUMFLO  ES_CUMFLO
$macro Q_BNDCST  ES_BNDCST
$macro QE_UC     ESE_UC
$macro QE_UCR    ESE_UCR
$macro QE_UCSU   ESE_UCSU
$macro QE_UCSUS  ESE_UCSUS
$macro QE_UCRSU  ESE_UCRSU
$macro QE_UCRSUS ESE_UCRSUS
$macro QL_SCAP   ESL_SCAP
""",
                    )
                else:
                    self.env.set_global("scum", "1")
                    self.env.set_global(
                        "sw_stvars",
                        f"{self.env.sw_stvars} SET VARTT 'SUM(SW_TSW(W,TT,W),SW_TPROB(TT,W)*Z' SET SWSW SW_TSW(SOW(WW),T,WW),SW_TPROB(T,WW)*",
                    )
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""
$macro Q_CUMNET(rc,y1,y2,sow) ES_CUMNET(rc,y1,y2,'1')
$macro Q_CUMPRD(rc,y1,y2,sow) ES_CUMPRD(rc,y1,y2,'1')
$macro Q_CUMFLO(rpcyy,sw)     ES_CUMFLO(rpcyy,'1')
$macro Q_BNDCST(r,y,y2,c,m,w) ES_BNDCST(r,y,y2,c,m,'1')
$macro QE_UC(uc,sow)          ESE_UC(uc,'1')
$macro QE_UCR(ruc,sow)        ESE_UCR(ruc,'1')
$macro QE_UCSU(uc,t,sw)       ESE_UCSU(uc,t,'1')
$macro QE_UCSUS(uc,t,s,sw)    ESE_UCSUS(uc,t,s,'1')
$macro QE_UCRSU(rtuc,sw)      ESE_UCRSU(rtuc,'1')
$macro QE_UCRSUS(rtuc,s,sw)   ESE_UCRSUS(rtuc,s,'1')
$macro QL_SCAP(rtp,ip,sow)    ESL_SCAP(rtp,ip,'1')
""",
                    )
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=r"""
* Variables (must have for all standard)
$macro Z_OBJ VAS_OBJ
$macro Z_OBJELS VAS_OBJELS

$macro Z_ACT VAS_ACT
$macro Z_FLO VAS_FLO
$macro Z_IRE VAS_IRE
$macro Z_SIN VAS_SIN
$macro Z_SOUT VAS_SOUT
$macro Z_BLND VAS_BLND
$macro Z_COMNET VAS_COMNET
$macro Z_COMPRD VAS_COMPRD
$macro Z_ELAST VAS_ELAST
$macro Z_DEM VAS_DEM
$macro Z_UPS VAS_UPS
$macro Z_UPT VAS_UPT
$macro Z_UDP VAS_UDP
$macro Z_RLD VAS_RLD
$macro Z_GRIDIO VAS_GRIDIO
$macro Z_COMAUX VAS_COMAUX

$macro Z_CAP(r,t,p,sow)     VAS_CAP(r,t,p,'1')
$macro Z_NCAP(r,t,p,sow)    VAS_NCAP(r,t,p,'1')
$macro Z_RCAP(r,v,t,p,sow)  VAS_RCAP(r,v,t,p,'1')
$macro Z_SCAP(r,v,t,p,sow)  VAS_SCAP(r,v,t,p,'1')
$macro Z_DRCAP(r,v,t,p,w,j) VAS_DRCAP(r,v,t,p,'1',j)
$macro Z_DNCAP(r,t,p,sow,j) VAS_DNCAP(r,t,p,'1',j)
$macro Z_SNCAP(r,t,p,sow)   VAS_SNCAP(r,t,p,'1')
$macro Z_XCAP(r,t,p,sow)    VAS_XCAP(r,t,p,'1')

$macro Z_UC VAS_UC
$macro Z_UCR VAS_UCR
$macro Z_UCT VAS_UCT
$macro Z_UCRT VAS_UCRT
$macro Z_UCTS VAS_UCTS
$macro Z_UCRTS VAS_UCRTS
""",
                )
                if self.env.solveda != "1":
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""
$macro Z_CUMCOM VAS_CUMCOM
$macro Z_CUMFLO VAS_CUMFLO
$macro Z_CUMCST VAS_CUMCST
""",
                    )
                else:
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""
$macro Z_CUMCOM(r,c,cv,y1,y2,w) VAS_CUMCOM(r,c,cv,y1,y2,'1')
$macro Z_CUMFLO(r,p,cv,y1,y2,w) VAS_CUMFLO(r,p,cv,y1,y2,'1')
$macro Z_CUMCST(r,y1,y2,cg,m,w) VAS_CUMCST(r,y1,y2,cg,m,'1')
""",
                    )
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=rf"""
$macro Z_CLITOT VAS_CLITOT
$macro Z_CLIBOX VAS_CLIBOX

* Map objective components
 EQUATION {self.env.eq}_OBW1(OBV,R,CUR,ALLSOW);
 {self.env.eq}_OBW1(OBJSW1(OBV),RDCUR(R,CUR),SOW) .. {self.env.var}_OBJ(R,OBV,CUR,SOW) =E= {self.env.var}_OBJ(R,OBV,CUR,'1');
""",
                )

    def spines_exec(self: RecurrinStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OBJSW1('OBJINV')=YES;
  OBJSW1('OBJFIX')=YES;
  OBJSW1('OBJSAL')=YES;
  UCRTPSW1('ACT',SOW) = YES;
  UCRTPSW1('CAP','1') = YES;
  UCRTPSW1('NCAP','1') = YES;
""",
        )
