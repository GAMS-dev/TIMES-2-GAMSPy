# eqmacro_tm.py
# # *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# *  Utility Production Function, the Objective Function                        *
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqmacroTm(GamsClass):
    """Translation unit for eqmacro.tm."""

    module_name: str = "eqmacro_tm"
    gams_source: str = "eqmacro.tm"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.add_eq_util()
        self.add_eq_conso()
        self.add_eq_dd()
        self.add_eq_mcap()
        self.add_eq_tmc()
        self.add_eq_ivecbnd()
        self.add_eq_escost()
        self.add_eq_mpen()
        self.add_eq_xcapdb()

    def add_eq_util(self) -> None:
        """Utility Production Function, the Objective Function"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_UTIL ..

    SUM((R,T), TM_DFACT(R,T) * TM_PWT(T) * LOG(VAR_C(R,T)))

    =E=

    VAR_UTIL * MAX(1,LOG(TM_SCALE_UTIL*1000))/1000;
""",
        )

    def add_eq_conso(self) -> None:
        """Production constraint."""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_CONSO(R,T) ..

     VAR_C(R,T) =L=

     (TM_AKL(R) * (VAR_K(R,T) ** (TM_KPVS(R)*TM_RHO(R))) * TM_L(R,T) ** ((1-TM_KPVS(R)) * TM_RHO(R)) +

      SUM(DEM(R,C), TM_B(R,C) * VAR_D(R,T,C) ** TM_RHO(R))) ** (1 / TM_RHO(R)) - VAR_INV(R,T) - VAR_EC(R,T);
""",
        )

    def add_eq_dd(self) -> None:
        """Demand coupling equation
        A demand relation is generated for each demand sector DM and ensures that
        the end-use energy output from the demand devices which have output to DM
        is greater than or equal to the end-use demand specified by the user."""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_DD(R,T,C)$DEM(R,C) ..

    VAR_DEM(R,T,C)

    =E=

    ((1/TM_SCALE_NRG) * (TM_AEEIFAC(R,T,C) * VAR_D(R,T,C) + TM_ADDER(R,T,C) + VAR_SP(R,T,C)))$(COM_PROJ(R,T,C) GT 0)
    ;
""",
        )

    def add_eq_mcap(self) -> None:
        """Capital dynamics equation."""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_MCAP(R,T+1) ..

    VAR_K(R,T+1)

    =E=

    VAR_K(R,T) * TM_TSRV(R,T) + (D(T+1)*VAR_INV(R,T+1) + TM_TSRV(R,T)*D(T)*VAR_INV(R,T))/2
    ;
""",
        )

    def add_eq_tmc(self) -> None:
        """Terminal condition for investment in last period."""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_TMC(R,T)$(ORD(T) = CARD(T)) ..

  VAR_K(R,T) * (TM_GROWV(R,T) + TM_DEPR(R))/100

  =L=

  VAR_INV(R,T)
  ;
""",
        )

    def add_eq_ivecbnd(self) -> None:
        """Bound on sum of investment and energy."""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_IVECBND(R,T)$(ORD(T) GT 1) ..

  VAR_INV(R,T) + VAR_EC(R,T)

  =L=

  TM_Y0(R) * TM_L(R,T) ** TM_IVETOL(R);
""",
        )

    def add_eq_escost(self) -> None:
        """Energy system costs equation."""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* Calculate annualized undiscounted investment costs
  TM_CSTINV(R,V,P)$RTP(R,V,P)
  =
  SUM(OBJ_ICUR(R,V,P,CUR), COEF_OBINV(R,V,P,CUR));

EQ_ESCOST(R,T) ..

  TM_SCALE_CST * (

  VAR_OBJCOST(R,T)
  +

* quadratic market penetration curve
  (SUM(RTP(R,T,P)$TM_CAPTB(R,P),
    0.5 * TM_QFAC(R) *
    TM_CSTINV(R,T,P) * (TM_CAPTB(R,P) / TM_EXPF(R,T) * SUM(XCP(J),VAR_XCAPP(R,T,P,J)*ORD(J))))
  )$(TM_QFAC(R) NE 0))

* add initial amortization (from CSA only)
  + TM_AMP(R,T)

  =E=

  VAR_EC(R,T);
""",
        )

    def add_eq_mpen(self) -> None:
        """Variable definition for market penetration cost penalty function"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_MPEN(RTP(R,TT(T+1),P))$((TM_QFAC(R) NE 0)$TM_CSTINV(R,TT,P)$TM_CAPTB(R,P)) ..

  VAR_CAP(R,TT,P)
  =L=
  TM_EXPF(R,T) * VAR_CAP(R,T,P) + VAR_XCAP(R,TT,P);
""",
        )

    def add_eq_xcapdb(self) -> None:
        """Market Penetration Cost Penalty Function, Quadratic Approximation"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
EQ_XCAPDB(RTP(R,TT(T+1),P))$((TM_QFAC(R) NE 0)$TM_CSTINV(R,TT,P)$TM_CAPTB(R,P)) ..

  VAR_XCAP(R,TT,P)

  =E=

  SUM(XCP(J),VAR_XCAPP(R,TT,P,J))
  ;
""",
        )
