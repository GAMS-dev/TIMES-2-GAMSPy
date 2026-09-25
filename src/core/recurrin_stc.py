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

from gamspy import Equation, Parameter, Set

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RecurrinStc(GamsClass):
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
        g = self.tc
        m = g.container

        self.env.set_scoped("tst", "NO")
        if self.env.obmac.upper() == "YES":
            self.env.set_scoped("tst", "YES")

        # --------------------------------------------------------

        # GOTO %1 == MXPAR
        if self.arg1.upper() == "MXPAR":
            if self.env.stages == "YES":
                self.env.set_global("varmac", "1==1")
                self.env.set_global("vas", "VAS")
            # Do we need MX parameter macroes?
            self.env.set_scoped("need", "NO")

            if (
                g.defined("S_NCAP_AFS")
                or g.defined("S_COM_FR")
                or self.env.spines.upper() == "YES"
            ):
                self.env.set_scoped("need", "YES")

            # ------------------------------------------

            if self.env.need != "NO":  # GOTO NONEED -> EXIT
                if not self.env.tst == "YES":  # GOTO DEFPAR
                    raise ModuleNotFoundError(
                        "Macro support needed. Upgrade your GAMS system."
                    )
                # LABEL DEFPAR
                self.env.set_scoped("sw1", "")
                self.env.set_scoped("sw1_GP", ())
                self.env.set_scoped("sw2", "")
                self.env.set_scoped("sw2_GP", ())
                if self.env.stages != "YES":
                    self.env.set_scoped("sw1", "SUM")
                    self.env.set_scoped("sw2", "SOW,")
                    self.env.set_scoped("sw2_GP", (g.Sow,))

                self.env.set_global("mx", "MX")
                self.env.set_global("mx_GP", ("MX",))
                g.add_gams_code(module=self, phase="init", code=r"$macro MX")

                # Mirrors recurrin.stc's two mutually exclusive $IF/$IF NOT
                # DEFINED pairs (COEF_AFMX: lines 41/46, COM_FRMX: lines
                # 43/49) as explicit if/else branches
                if g.defined("S_NCAP_AFS"):
                    # recurrin.stc line 46: $MACRO COEF_AFMX(...) COEF_AF(...)*%SW1%(%SW2%1+RTP_SAFS(...))
                    macro.coef_af_mx.activate(
                        g=g,
                        sw1=self.env.sw1,
                        sw2=self.env.sw2,
                        sw2_GP=self.env.sw2_GP,
                    )
                if g.defined("S_COM_FR"):
                    # recurrin.stc line 47: PARAMETER RTCS_FRMX(R,T,C,S,S);
                    macro.rtcs_fr.activate(g=g)
                    # recurrin.stc line 48: $MACRO RTCS_FR(R,T,C,S,TS) RTCS_FRMX(...)+SUM(...)
                    g.rtcs_frmx = Parameter(
                        m, name="RTCS_FRMX", domain=[g.r, g.t, g.c, g.s, g.s]
                    )
                    # recurrin.stc line 49: $MACRO COM_FRMX(...) COM_FR(...)*%SW1%(%SW2%1+S_COM_FR(...))
                    macro.com_fr.activate(
                        g=g,
                        sw1=self.env.sw1,
                        sw2=self.env.sw2,
                        sw2_GP=self.env.sw2_GP,
                    )

        # ------------------------------------------------

        elif self.arg1.upper() == "SPINES":
            # Do we need SPINES macroes?
            if self.env.spines.upper() == "YES":
                if not self.env.tst == "YES":
                    raise ModuleNotFoundError(
                        "Macro support needed. Upgrade your GAMS system."
                    )
                self.env.set_scoped("vsum", "SUM(SW_TSW(SOW,")
                self.env.set_global(
                    "sw_stvars",
                    rf"SET VAR 'Z' SET VART '{self.env.vsum}T,W),Z' SET VARM '{self.env.vsum}MODLYEAR,W),Z' SET VARV '{self.env.vsum}V,W),Z'",
                )
                self.env.set_global("witspine", True)
                self.env.set_global("ewispine", True)

                g.Objsw1 = Set(m, name="OBJSW1", domain=g.obv)
                g.UcrtpSw1 = Set(m, name="UCRTPSW1", domain=[g.ucgrptype, g.ww])
                g.enqueue(self.spines_exec)

                g.add_gams_code(module=self, phase="init", code="$macro QED")
                macro.prc_dynuc_mx.activate(g=g)

                # Equations (only if needed)
                g.q_objels = g.es_objels
                macro.q_objfix_active = True
                macro.q_objinv_active = True
                macro.q_objsalv_active = True
                g.q_objvar = g.es_objvar
                g.q_robj = g.es_robj
                g.q_sobj = g.es_sobj

                macro.q_cpt_active = True  # QG_CPT, QE_CPT, QL_CPT
                macro.q_dscret_active = True
                macro.q_cumret_active = True
                macro.ql_refit_active = True
                macro.q_dscncap_active = True
                macro.q_dscone_active = True

                g.qe_uct = g.ese_uct
                g.qe_ucrt = g.ese_ucrt
                g.qe_ucts = g.ese_ucts
                g.qe_ucrs = g.ese_ucrs
                g.qe_ucrts = g.ese_ucrts

                # Cumulative / dynamic
                if self.env.solveda != "1":
                    self.env.set_global(
                        "sw_stvars",
                        f"{self.env.sw_stvars} SET VARTT '{self.env.vsum}TT,W),Z' SET SWSW SW_TSW(SOW,T,WW),",
                    )
                    g.q_cumnet = g.es_cumnet
                    g.q_cumprd = g.es_cumprd
                    g.q_cumflo = g.es_cumflo
                    g.q_bndcst = g.es_bndcst
                    g.qe_uc = g.ese_uc
                    g.qe_ucr = g.ese_ucr
                    g.qe_ucsu = g.ese_ucsu
                    g.qe_ucsus = g.ese_ucsus
                    g.qe_ucrsu = g.ese_ucrsu
                    g.qe_ucrsus = g.ese_ucrsus
                    g.ql_scap = g.esl_scap
                else:  # LABEL DYQAGG
                    self.env.set_global("scum", "1")
                    self.env.set_global(
                        "sw_stvars",
                        f"{self.env.sw_stvars} SET VARTT 'SUM(SW_TSW(W,TT,W),SW_TPROB(TT,W)*Z' SET SWSW SW_TSW(SOW(WW),T,WW),SW_TPROB(T,WW)*",
                    )
                    macro.q_cum_active = True  # Q_CUMNET, Q_CUMPRD
                    macro.q_cumflo_active = True
                    macro.q_bndcst_active = True
                    macro.eq_uc.activate(g=g)  # UC, UCR, UCSU, UCSUS, UCRSU, UCRSUS
                    macro.ql_scap_active = True

                # -----------------------------------------------------------

                # Variables (must have for all standard)
                g.Z_OBJ = g.VAS_OBJ
                g.Z_OBJELS = g.VAS_OBJELS

                g.Z_ACT = g.VAS_ACT
                g.Z_FLO = g.VAS_FLO
                g.Z_IRE = g.VAS_IRE
                g.Z_SIN = g.VAS_SIN
                g.Z_SOUT = g.VAS_SOUT
                g.Z_BLND = g.VAS_BLND
                g.Z_COMNET = g.VAS_COMNET
                g.Z_COMPRD = g.VAS_COMPRD
                g.Z_ELAST = g.VAS_ELAST
                g.Z_DEM = g.VAS_DEM
                g.Z_UPS = g.VAS_UPS
                g.Z_UPT = g.VAS_UPT
                g.Z_UDP = g.VAS_UDP
                g.Z_RLD = g.VAS_RLD
                g.Z_GRIDIO = g.VAS_GRIDIO
                g.Z_COMAUX = g.VAS_COMAUX

                macro.z_cap_active = True
                macro.z_ncap_active = True
                macro.z_rcap_active = True
                macro.z_scap_active = True
                macro.z_drcap_active = True
                macro.z_dncap_active = True
                macro.z_sncap_active = True
                macro.z_xcap_active = True

                g.Z_UC = g.VAS_UC
                g.Z_UCR = g.VAS_UCR
                g.Z_UCT = g.VAS_UCT
                g.Z_UCRT = g.VAS_UCRT
                g.Z_UCTS = g.VAS_UCTS
                g.Z_UCRTS = g.VAS_UCRTS

                g.add_gams_code(
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

$macro Z_UC VAS_UC
$macro Z_UCR VAS_UCR
$macro Z_UCT VAS_UCT
$macro Z_UCRT VAS_UCRT
$macro Z_UCTS VAS_UCTS
$macro Z_UCRTS VAS_UCRTS
""",
                )
                if self.env.solveda != "1":
                    g.Z_CUMCOM = g.VAS_CUMCOM
                    g.Z_CUMFLO = g.VAS_CUMFLO
                    g.Z_CUMCST = g.VAS_CUMCST

                    g.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""
$macro Z_CUMCOM VAS_CUMCOM
$macro Z_CUMFLO VAS_CUMFLO
$macro Z_CUMCST VAS_CUMCST
""",
                    )
                else:  # LABEL DYZAGG
                    macro.z_cumcom_active = True
                    macro.z_cumflo_active = True
                    macro.z_cumcst_active = True

                g.Z_CLITOT = g.VAS_CLITOT
                g.Z_CLIBOX = g.VAS_CLIBOX
                g.add_gams_code(
                    module=self,
                    phase="init",
                    code=r"""
$macro Z_CLITOT VAS_CLITOT
$macro Z_CLIBOX VAS_CLIBOX
""",
                )

                obv, r, cur, allsow = g.obv, g.r, g.cur, g.allsow
                Objsw1, Rdcur, Sow = g.Objsw1, g.Rdcur, g.Sow

                VAR_OBJ = g.get_variable(name=f"{self.env.var}_OBJ")
                # Map objective components
                g.es_obw1 = Equation(
                    m, name=f"{self.env.eq}_OBW1", domain=[obv, r, cur, allsow]
                )
                g.es_obw1[Objsw1[obv], Rdcur[r, cur], Sow] = (
                    VAR_OBJ[r, obv, cur, Sow] == VAR_OBJ[r, obv, cur, "1"]
                )

    def spines_exec(self: RecurrinStc) -> None:
        g = self.tc

        g.Objsw1["OBJINV"] = True
        g.Objsw1["OBJFIX"] = True
        g.Objsw1["OBJSAL"] = True

        g.UcrtpSw1["ACT", g.Sow] = True
        g.UcrtpSw1["CAP", "1"] = True
        g.UcrtpSw1["NCAP", "1"] = True
