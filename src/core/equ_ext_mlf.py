# equ_ext_mlf.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * equ_ext.mlf - Equation formulations for MLF
# *-----------------------------------------------------------------------------
# * Calibration equations
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.calibase_mlf import CalibaseMlf
from core.presolve_mlf import PresolveMlf

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtMlf(GamsClass):
    """Translation unit for equ_ext.mlf."""

    # Instance attributes
    module_name: str = "equ_ext_mlf"
    gams_source: str = "equ_ext.mlf"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        # Calibration equations
        self.utility_objective_function()
        self.production_function()
        self.akl_aggregate()
        self.labor_resource()
        self.capital_dynamics_equation()
        self.capital_dummy_definition()
        self.terminal_condition_investment()
        self.bound_sum_of_investment_and_energy()
        self.demand_coupling_equation()
        self.energy_system_costs()
        self.trade_balance()

        # Variable bounds
        self.tc.enqueue(self.set_variable_bounds)

        self.include(CalibaseMlf(tc=self.tc, env=self.env))

        self.tc.enqueue(
            self.exec1,
            fixboh_set=self.env.is_set("fixboh"),
            fixboh=self.env.fixboh,
            reg_bdncap_defined=self.tc.defined("REG_BDNCAP"),
        )

        kestrel = self.env.kestrel.split(".")
        if len(kestrel) == 2:
            self.env.set_scoped("x1", kestrel[0])
            self.env.set_scoped("x2", kestrel[1])
        else:
            # Mirrors GAMS's own behavior for an unset %KESTREL%: an undefined
            # dollar variable substitutes to an empty string, so
            # `$SETCOMPS %KESTREL% X1 X2 .` yields blank X1/X2 rather than
            # erroring, and the downstream `%X2%==LP` / `%X1%%X2%==NLP` checks
            # simply don't match.
            self.env.set_scoped("x1", "")
            self.env.set_scoped("x2", "")

        if self.env.nonlp.upper() != "NL":
            self.include(PresolveMlf(tc=self.tc, env=self.env))
            if self.env.x2.upper() == "LP":
                self.tc.enqueue(self.option_lp)

            self.full_model_equations()

        self.nlp_equations()

        self.tc.enqueue(self.full_model_bounds)

        if self.env.nonlp.upper() == "NL":
            if f"{self.env.x1}{self.env.x2}".upper() == "NLP":
                self.tc.enqueue(self.option_nlp)
            self.tc.enqueue(self.exec2)

    def utility_objective_function(self: EquExtMlf) -> None:
        """Utility Objective Function"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_UTIL.. SUM(MR(R), SUM(T, TM_NWT(R) * TM_PWT(T) * TM_DFACT(R,T) * LOG(VAR_C(R,T))))
	=E= VAR_UTIL * MAX(1,LOG(TM_SCALE_UTIL*1000))/1000;

""",
        )

    def production_function(self: EquExtMlf) -> None:
        """Production Function"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_PROD_Y(MR(R),T)..  VAR_C(R,T) + VAR_INV(R,T) + VAR_EC(R,T) + VAR_NTX(R,T)$PP(T) =E=
  (TM_AKL(R) * VAR_D(R,T,'AKL')**TM_RHO(R) + SUM(DM,TM_B(R,DM)*VAR_D(R,T,DM)**TM_RHO(R))) ** (1/TM_RHO(R));
""",
        )

    def akl_aggregate(self: EquExtMlf) -> None:
        """AKL aggregate"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_AKL(MR(R),T)..  VAR_D(R,T,'AKL') =E= (VAR_D(R,T,'KN')**(TM_KPVS(R))) * VAR_D(R,T,'LAB')**(1-TM_KPVS(R));
""",
        )

    def labor_resource(self: EquExtMlf) -> None:
        """Labor resource"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_LABOR(MR(R),T)..  VAR_D(R,T,'LAB') =E= TM_L(R,T);
""",
        )

    def capital_dynamics_equation(self: EquExtMlf) -> None:
        """Capital Dynamics Equation"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_MCAP(MR(R),PP(T+1))..  VAR_K(R,PP) =E= VAR_K(R,T)*TM_TSRV(R,T) + (D(T+1)*VAR_INV(R,T+1)+TM_TSRV(R,T)*D(T)*VAR_INV(R,T))/2;
""",
        )

    def capital_dummy_definition(self: EquExtMlf) -> None:
        """Capital dummy definition"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_KNCAP(MR(R),T)..  VAR_D(R,T,'KN') =E= VAR_K(R,T);
""",
        )

    def terminal_condition_investment(self: EquExtMlf) -> None:
        """Terminal Condition for investment in last period"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_TMC(MR(R),TLAST(T))..  VAR_K(R,T) * (TM_GROWV(R,T) + TM_DEPR(R))/100  =L= VAR_INV(R,T);
""",
        )

    def bound_sum_of_investment_and_energy(self: EquExtMlf) -> None:
        """Bound on Sum of Investment and Energy"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_IVECBND(MR(R),PP(T))..  VAR_INV(R,T) + VAR_EC(R,T)  =L=  TM_Y0(R) * TM_L(R,T) ** TM_IVETOL(R);
""",
        )

    def demand_coupling_equation(self: EquExtMlf) -> None:
        """Demand Coupling Equation"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_DD(MR(R),PP(T),C('ACT'))..
  VAR_DEM(R,T,C) =E= ((1/TM_SCALE_NRG) * (TM_AEEIFAC(R,T,C) * VAR_D(R,T,C) + VAR_SP(R,T,C)));
""",
        )

    def energy_system_costs(self: EquExtMlf) -> None:
        """Energy System Costs"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_ESCOST(MR(R),PP(T))..
  SUM(DM('ACT'), TM_QSFA(R,T) + TM_QSFB(R,T,DM)*VAR_DEM(R,T,DM)**2) + TM_AMP(R,T) =E= VAR_EC(R,T)*TM_HDF(R,T);
""",
        )

    def trade_balance(self: EquExtMlf) -> None:
        """Trade balance"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_TRDBAL(PP)..  SUM(MR(R), VAR_NTX(R,PP)) =E= 0;
""",
        )

    def set_variable_bounds(self: EquExtMlf) -> None:
        """Variable bounds"""

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Variable bounds

  VAR_D.LO(MR(R),T,DM) = TM_DMTOL(R) * TM_D0(R,DM);
  VAR_D.L(MR(R),PP,DM) = TM_D0(R,DM);
  VAR_D.FX(MR(R),T(TB),DM) = TM_D0(R,DM);
  VAR_DEM.FX(MR,T(TB),DM)  = TM_DEM(MR,T,DM);

  LOOP(MR(R), Z=TM_K0(R)*TM_DEPR(R)/100; LOOP(PP(T+1), Z=Z*TM_TSRV(R,T); VAR_INV.LO(R,PP) = Z));
  VAR_INV.L(MR,PP)     = TM_IV0(MR) * TM_L(MR,PP);
  VAR_INV.FX(MR,T(TB)) = TM_IV0(MR);
  VAR_D.LO(MR,T,'AKL') = MIN(1,TM_K0(MR))/2;
  VAR_D.LO(MR,T,'KN')  = TM_K0(MR) * 0.33;
  VAR_D.LO(MR,T,'LAB') = TM_L(MR,T)/2;
  VAR_K.FX(MR,T(TB))   = TM_K0(MR);
  VAR_C.L(MR,TP)       = TM_GDP0(MR) - TM_IV0(MR);
  VAR_C.LO(MR,TP)      = TM_GDP0(MR) * 0.33;
  VAR_SP.FX(MR,TP,DM)  = 0;
  VAR_EC.LO(MR,PP)     = TM_ANNC(MR,PP) * 0.33;
  VAR_EC.LO(MR,T(TB))  = TM_EC0(MR) + TM_AMP(MR,TB);

* set the bounds for the step variables for quad approx, clearing first
  VAR_XCAPP.UP(RTP,J)   = INF;
  VAR_XCAPP.UP(RTP,XCP(J))$(ORD(J)<7) $= TM_EXPBND(RTP);
""",
        )

    def exec1(
        self: EquExtMlf, fixboh_set: bool, fixboh: str, reg_bdncap_defined: bool
    ) -> None:
        if fixboh_set:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
LOOP(R, Z=REG_FIXT(R); IF(Z=0,Z=ABS({fixboh})); TM_PP(R,T)$(M(T) LE Z)=NO);
""",
            )
        if reg_bdncap_defined:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
LOOP(BD,TM_PP(R,T)$((M(T)<=REG_BDNCAP(R,BD))$REG_BDNCAP(R,BD))=NO);
""",
            )

    def option_lp(self: EquExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION LP=KESTREL;
""",
        )

    def option_nlp(self: EquExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION NLP=KESTREL;
""",
        )

    def full_model_equations(self: EquExtMlf) -> None:
        self.utility_objective_function2()
        self.consumption()
        self.consumption_disaggregation()
        self.consumption_log_steps()
        self.macro_ces_function_shares()
        self.macro_ces_function_aggregation()
        self.macro_ces_function_constraint()
        self.demand_ces_function_shares()
        self.demand_ces_aggregation()
        self.demand_linear_ces_function_constraint()

    def nlp_equations(self: EquExtMlf) -> None:
        self.demand_non_linear_ces_function()
        self.energy_system_costs_nlp()

    def utility_objective_function2(self: EquExtMlf) -> None:
        """Utility Objective Function"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_UTILP..
  SUM(MR(R), SUM(T, TM_NWT(R)*TM_PWT(T)*TM_DFACT(R,T)*(LOG(TM_MIDCON(R,T))-SUM(LOGJ(J,BD),BDSIG(BD)*VAR_MELA(R,T,'CON',J,BD)/TM_LSC)))) +
  SUM(R$(NOT MR(R)),SUM(T,(3*TM_ANNC(R,T)-VAR_OBJCOST(R,T)*TM_SCALE_CST)*TM_UDF(R,T)))
  =E=  VAR_UTIL * MAX(1,LOG(TM_SCALE_UTIL*1000))/1000;
""",
        )

    def consumption(self: EquExtMlf) -> None:
        """Consumption"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_CONSO(MR(R),T)..  VAR_D(R,T,'YN')  =E=  VAR_C(R,T) + VAR_INV(R,T) + VAR_EC(R,T) + VAR_NTX(R,T)$PP(T);
""",
        )

    def consumption_disaggregation(self: EquExtMlf) -> None:
        """Consumption disaggregation"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
 EQ_CONDA(MR(R),T)..  VAR_C(R,T) =E= TM_MIDCON(R,T)*(1-SUM(LOGJ(J,BD),VAR_MELA(R,T,'CON',J,BD)*TM_LOGVAL(J,BD)/TM_LSC));
""",
        )

    def consumption_log_steps(self: EquExtMlf) -> None:
        """Consumption LOG steps constraint"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_LOGBD(MR(R),T)..  SUM(LOGJ(J,BD),VAR_MELA(R,T,'CON',J,BD)/ORD(J)/TM_LOGJOT) =L= TM_LSC;
""",
        )

    def macro_ces_function_shares(self: EquExtMlf) -> None:
        """Macro CES function shares"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_MACSH(MR(R),T,TM_DMAS(CG,CG1))..
  VAR_D(R,T,CG1) + SUM(TM_RCJ(R,CG1,J,BD)$TM_PP(R,T),BDSIG(BD)*VAR_MELA(R,T,CG1,J,BD))
  =E= TM_SHAR(R,T,CG,CG1)*VAR_D(R,T,CG) / TM_CIE(R,T,CG);
""",
        )

    def macro_ces_function_aggregation(self: EquExtMlf) -> None:
        """Macro CES function aggregation"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_MACAG(TM_PP(MR(R),T),TM_CES(CG))..
  SUM(TM_RCJ(R,CG1,J,BDNEQ(BD))$TM_DMAS(CG,CG1),
      (TM_PREF(R,T,CG1)*(TM_AGC(R,T,CG,CG1,J,BD)-1)+TM_SHAR(R,T,CG1,CG))*BDSIG(BD)*VAR_MELA(R,T,CG1,J,BD))
  =E= 0;
""",
        )

    def macro_ces_function_constraint(self: EquExtMlf) -> None:
        """Macro CES function constraint"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_MACES(TM_PP(MR(R),T),TM_DMAS(CG,CG1))..
  SUM(TM_RCJ(R,CG1,J,BDNEQ(BD)),VAR_MELA(R,T,CG1,J,BD)*TM_STEP(R,CG1,BD)/ORD(J)/(TM_QREF(R,T,CG1)*TM_VOC(R,T,CG1,BD)))
  =L= (VAR_D(R,t,CG)/TM_CIE(R,T,CG)/TM_CESLEV(R,T,CG));
""",
        )

    def demand_ces_function_shares(self: EquExtMlf) -> None:
        """Demand CES function shares"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_DEMSH(MR(R),PP(T),C)$TM_DM(R,C)..
  VAR_DEM(R,T,C) + SUM(TM_RCJ(R,C,J,BD)$TM_PP(R,T),BDSIG(BD)*VAR_MELA(R,T,C,J,BD))
  =E= SUM(MAG('ACT'),TM_SHAR(R,T,MAG,C)*VAR_DEM(R,T,MAG));
""",
        )

    def demand_ces_aggregation(self: EquExtMlf) -> None:
        """Demand CES aggregation"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_DEMAG(TM_PP(MR(R),T))..
  SUM(TM_RCJ(R,C,J,BDNEQ(BD))$TM_DM(R,C),
    SUM(MAG('ACT'), (TM_PREF(R,T,C)*(TM_AGC(R,T,MAG,C,J,BD)-1)+TM_SHAR(R,T,C,MAG))*BDSIG(BD)*VAR_MELA(R,T,C,J,BD)))
  =E= 0;
""",
        )

    def demand_linear_ces_function_constraint(self: EquExtMlf) -> None:
        """Demand linear CES function constraint"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_DEMCES(TM_PP(MR(R),T),C)$TM_DM(R,C)..
  SUM(TM_RCJ(R,C,J,BDNEQ(BD)),VAR_MELA(R,T,C,J,BD)*TM_STEP(R,C,BD)/ORD(J)/(TM_QREF(R,T,C)*TM_VOC(R,T,C,BD)))
  =L= SUM(MAG('ACT'),(VAR_DEM(R,T,MAG)/TM_DEM(R,T,MAG)));
""",
        )

    def demand_non_linear_ces_function(self: EquExtMlf) -> None:
        """Demand non-linear CES function constraint"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_DNLCES(MR(R),PP(T))..
  VAR_DEM(R,T,'ACT') =E= TM_DEM(R,T,'ACT') *
  SUM(TM_DM(R,C),TM_CIE(R,T,C)*(VAR_DEM(R,T,C)/TM_DEM(R,T,C))**(1-1/TM_DESUB(R)))**(TM_DESUB(R)/(TM_DESUB(R)-1));
""",
        )

    def energy_system_costs_nlp(self: EquExtMlf) -> None:
        """Energy System costs"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQ_ENSCST(MR(R),T)..
  TM_SCALE_CST * VAR_OBJCOST(R,T) + TM_AMP(R,T) + VAR_SP(R,T,'DEM')$(NOT TM_PP(R,T)) -
* Credit for lump-sum rebate of tax revenues
  TM_SCALE_CST * TM_TAXREV(R,T) +
* quadratic market penetration curves (pending)
  0  =E= VAR_EC(R,T)*TM_HDF(R,T);
""",
        )

    def full_model_bounds(self: EquExtMlf) -> None:
        """Full model bounds"""
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  VAR_DEM.FX(R,T,C)$((NOT TM_DM(R,C)$MR(R))$DEM(R,C))=COM_PROJ(R,T,C);
  VAR_DEM.FX(MR(R),T(TB),C)$TM_DM(R,C) = TM_DEM(R,T,C);
  VAR_EC.UP(MR,T) = INF;
  VAR_EC.LO(MR(R),T) = ((TM_ANNC(R,T) + TM_AMP(R,T))/TM_HDF(R,T))$(NOT TM_PP(R,T));
  VAR_INV.FX(MR(R),T)$(NOT TM_PP(R,T)) = VAR_INV.L(R,T);
* Treat non-MR regions gracefully
  IF(CARD(MR),Z=SUM(TB(T-1),SMAX(MR,EQ_ESCOST.M(MR,T)/COEF_PVT(MR,T))); ELSE Z=0.5);
  TM_UDF(R,T) = COEF_PVT(R,T)*Z;
""",
        )

    def exec2(self: EquExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  TM_CIE(R,T,C)$TM_DM(R,C) = TM_DEM(R,T,C)*TM_DMC(R,T,C) / (TM_DEM(R,T,'ACT')*TM_DMC(R,T,'ACT'));
  VAR_DEM.UP(MR(R),PP(T),C)$((NOT TM_PP(R,T))$TM_DM(R,C)) = TM_DEM(R,T,C);
  VAR_DEM.LO(R,PP,C)$TM_DM(R,C) = TM_DEM(R,PP,C)*0.5;
""",
        )
