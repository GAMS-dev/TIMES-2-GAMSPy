# equserco_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQ_UC - user constraints
# *   %1  - mod or v# for the source code to be used
# *   %2  - equation declaration type
# *   %3  - equation name suffix and condition of existence of equation
# *   %4  - region summation index or bracket
# *   %5  - period summation index or bracket
# *   %6  - time-slice summation index or bracket
# *   %7  - summand for region
# *   %8  - 0 if UC_DYN=EACH, 1 if UC_DYN=SUCC, 2 if SEVERAL
# *   %9  - UC variable name
# *   %10 - UC RHS parameter
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.uc_act_mod import uc_act_mod
from core.uc_cap_mod import uc_cap_mod
from core.uc_cli_mod import uc_cli_mod
from core.uc_com_mod import uc_com_mod
from core.uc_flo_mod import uc_flo_mod
from core.uc_ire_mod import uc_ire_mod
from core.uc_ncap_mod import uc_ncap_mod
from core.uc_pasti_mod import uc_pasti_mod

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqusercoMod(GamsClass):
    """Translation unit for eq_uc.mod."""

    module_name: str = "eq_uc_mod"
    gams_source: str = "eq_uc.mod"

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
        arg7: str = "",
        arg8: str = "",
        arg9: str = "",
        arg10: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self.arg8 = arg8
        self.arg9 = arg9
        self.arg10 = arg10
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        lhs = ""
        if self.arg8 != "1":
            self.env.set_local("hs", "'LHS'")
            if self.arg8 == "2":
                self.env.set_scoped("sow", self.env.swd)
                self.env.set_scoped("swt", self.env.sow)
            elif self.arg8 == "S":
                self.env.set_local("hs", "SIDE")
            lhs = self._static_lhs(
                hs=self.env.hs,
                swt=self.env.swt,
                is_several=self.arg8 == "2",
            )
        else:
            lhs = self._label_dynamic(
                is_stages=self.env.stages == "YES",
                is_cli=self.env.cli == "YES",
            )

        rhs = (
            self.arg9
            if self.env.var_uc == "YES"
            else f"{self.arg10}$({self.arg10} NE 0)"
        )

        time_term = ""
        if self.arg8 != "1":
            time_term = rf"""
+SUM(({self.arg7}V(T))$UC_TIME(UC_N,R,T), {self.arg5} UC_TIME(UC_N,R,T)*FPD(T)))
"""
        else:
            time_term = rf"""
+SUM(({self.arg7}V(T))$UC_TIME(UC_N,R,T), UC_TIME(UC_N,R,T)*(LEAD(T)$UC_DYNDIR(R,UC_N,'RHS')+LAGT(T)$(NOT UC_DYNDIR(R,UC_N,'RHS'))))
"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
    {self.env.eq}{self.arg2}_UC{self.arg3}..
{lhs}

        ={self.arg2}=

        {rhs}
{time_term}

   ;
""",
        )

    def _static_lhs(
        self: EqusercoMod,
        hs: str,
        swt: str,
        is_several: bool,
    ) -> str:
        include_uc_flo = uc_flo_mod(
            cal_red=self.env.cal_red,
            var=self.env.var,
            swt=self.env.swt,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            shff=self.env.shff,
            sow=self.env.sow,
            cufscal=self.env.cufscal,
            pgprim=self.env.pgprim,
            sws=self.env.sws,
            varm=self.env.varm,
            varv=self.env.varv,
            is_vnret_defined=self.tc.defined("VNRET"),
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
            arg8=self.arg7,
        )
        include_uc_ncap = uc_ncap_mod(
            var=self.env.var,
            sow=self.env.sow,
            varv=self.env.varv,
            sws=self.env.sws,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3="T",
            arg4=hs,
            arg5=self.arg8,
            arg6="T",
        )
        include_uc_cap = uc_cap_mod(
            var=self.env.var,
            sow=self.env.sow,
            upscaps=self.env.upscaps,
            vda=self.env.vda,
            abs=self.env.abs,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3="T",
            arg4=hs,
            arg5=self.arg8,
            arg6="T",
        )
        include_uc_act = uc_act_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
            arg8=self.arg7,
        )
        include_uc_com_prd = uc_com_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
            arg8="PRD",
            arg9="PRD",
            arg10="PD",
        )
        include_uc_com_net = uc_com_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
            arg8="BAL",
            arg9="NET",
            arg10="NT",
        )
        include_uc_ire = uc_ire_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
            arg8=self.arg7,
        )

        cumcom_term = ""
        if is_several:
            cumcom_term = rf"""
+SUM(({self.arg7}COM_VAR,C,YEAR,LL)$UC_CUMCOM(UC_N,R,COM_VAR,C,YEAR,LL),UC_CUMCOM(UC_N,R,COM_VAR,C,YEAR,LL)*{self.env.var}_CUMCOM(R,C,COM_VAR,YEAR,LL{swt})*{self.env.cucscal})
"""

        return rf"""
{include_uc_flo}
+
{include_uc_ncap}
+
{include_uc_cap}
+
{include_uc_act}
+
{include_uc_com_prd}
+
{include_uc_com_net}
+
{include_uc_ire}
{cumcom_term}
"""

    def _label_dynamic(
        self: EqusercoMod,
        is_stages: bool,
        is_cli: bool,
    ) -> str:
        self.env.set_scoped("swflo", self.env.var)
        if is_stages:
            self.env.set_scoped("var", f"SUM({self.arg5}{self.env.var}")
            self.env.set_scoped("sow", ",WW)")
            self.env.set_scoped("swflo", f"{self.env.var},WW SUM {self.arg5}")

        self.env.set_local("tsum", "SUM(UC_TMAP(TT,T,T,SIDE,'N'),UC_SIGN(SIDE)*")
        block_tplus = rf"""
(
{
            uc_flo_mod(
                cal_red=self.env.cal_red,
                var=self.env.var,
                swt=self.env.swt,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                shff=self.env.shff,
                sow=self.env.sow,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws,
                varm=self.env.varm,
                varv=self.env.varv,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="LAGT(T)",
                arg9=self.env.swflo,
                arg10=self.env.sow,
            )
        }
+
{
            uc_ncap_mod(
                var=self.env.var,
                sow=self.env.sow,
                varv=self.env.varv,
                sws=self.env.sws,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="TT",
                arg7="LAGT(T)",
            )
        }
+
{
            uc_cap_mod(
                var=self.env.var,
                sow=self.env.sow,
                upscaps=self.env.upscaps,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="TT",
                arg7="LAGT(T)",
            )
        }
+
{
            uc_act_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="LAGT(T)",
            )
        }
+
{
            uc_com_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="PRD",
                arg9="PRD",
                arg10="PD",
                arg11="LAGT(T)",
            )
        }
+
{
            uc_com_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="BAL",
                arg9="NET",
                arg10="NT",
                arg11="LAGT(T)",
            )
        }
+
{
            uc_ire_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="LAGT(T)",
            )
        }
+SUM(({self.arg7}UC_GMAP_U(R,UC_N,UCN)),{self.env.tsum} UC_UCN(UC_N,SIDE,R,TT,UCN)*{
            self.env.var
        }_UCRT(UCN,R,TT{self.env.sow})$UC_RHSRT(R,UCN,TT,'N')))
)$(NOT SUM(UC_DYNDIR(R,UC_N,'RHS'),1))
"""

        self.env.set_local(
            "tsum",
            "SUM(UC_TMAP(T,LL,TT,SIDE,UC_DYNT)$(LIM(UC_DYNT) xor UC_ATTR(R,UC_N,SIDE,",
        )
        self.env.set_local("tucn", ",UC_DYNT)),UC_SIGN(SIDE)*")

        block_tminus = rf"""
(
{
            uc_flo_mod(
                cal_red=self.env.cal_red,
                var=self.env.var,
                swt=self.env.swt,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                shff=self.env.shff,
                sow=self.env.sow,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws,
                varm=self.env.varm,
                varv=self.env.varv,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'FLO'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
                arg9=self.env.swflo,
            )
        }
+
{
            uc_ncap_mod(
                var=self.env.var,
                sow=self.env.sow,
                varv=self.env.varv,
                sws=self.env.sws,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'NCAP'{self.env.tucn}",
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="LL",
                arg7="-LEAD(T)",
            )
        }
+
{
            uc_cap_mod(
                var=self.env.var,
                sow=self.env.sow,
                upscaps=self.env.upscaps,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'CAP'{self.env.tucn}",
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="LL",
                arg7="-LEAD(T)",
            )
        }
+
{
            uc_act_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'ACT'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
            )
        }
+
{
            uc_com_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'COMPRD'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="PRD",
                arg9="PRD",
                arg10="PD",
                arg11="-LEAD(T)",
            )
        }
+
{
            uc_com_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'COMNET'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="BAL",
                arg9="NET",
                arg10="NT",
                arg11="-LEAD(T)",
            )
        }
+
{
            uc_ire_mod(
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'IRE'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
            )
        }
+SUM(({self.arg7}UC_GMAP_U(R,UC_N,UCN)),{self.env.tsum}'UCN'{
            self.env.tucn
        } UC_UCN(UC_N,SIDE,R,LL,UCN)*{self.env.var}_UCRT(UCN,R,TT{
            self.env.sow
        })$UC_RHSRT(R,UCN,TT,'N')))
{
            uc_cli_mod(
                is_uc_cli_defined=self.tc.defined("UC_CLI"),
                var=self.env.var,
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'CLI'{self.env.tucn}",
                arg3=self.arg6,
                arg4="'TT'",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
            )
            if is_cli
            else ""
        }
-
{
            uc_pasti_mod(
                arg1=f"{self.arg4}{self.arg7}",
                arg2="MIYR_1",
                arg3="T",
                arg4="'RHS'",
            )
        }
)$SUM(UC_DYNDIR(R,UC_N,'RHS'),1)
"""
        return block_tplus + "\n+\n" + block_tminus
