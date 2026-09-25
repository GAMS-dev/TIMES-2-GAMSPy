# preppm_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * PREPPM.MSA Preprocessing for Macro Stand-Alone
# *============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter, Set

from core.base_class import GamsClass
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.forcupd_cli import forcupd_cli

# from core.MSADDF_dd import MSADDF
from core.rpt_dam_mod import rpt_dam_mod, rpt_dam_mod_GP

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PreppmMsa(GamsClass):
    """Translation unit for preppm.msa."""

    # Instance attributes
    module_name: str = "preppm_msa"
    gams_source: str = "preppm.msa"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if self.arg1 == "MSA":
            self._label_msa()
        elif self.arg1 == "TONLP":
            self.tc.enqueue(
                self._label_tonlp,
                is_tm_catt_defined=self.tc.defined("TM_CATT"),
                is_dam_cost_defined=self.tc.defined("DAM_COST"),
            )
        elif self.arg1 == "TOLP":
            self.tc.enqueue(self._label_tolp)

    def _label_msa(self) -> None:
        g = self.tc

        self.env.set_global("msa", "CSA")
        if self.env.macro != "N":
            self.env.set_global("msa", self.env.macro)

        self.tc.add_gams_code(module=self, phase="init", code="$KILL TM_UDF")

        if self.env.msa.upper() == "MSA":
            # TODO: $BATINCLUDE MSADDF.dd
            # self.include(MSADDF(self.tc, self.env))
            raise Exception("TODO: MSADDF.dd not implemented")

        m = g.container
        g.mdm = Alias(m, name="MDM", alias_with=g.ips)
        g.cmlpk = Set(m, name="CM_LPK", domain=["*"])
        g.cmlpt = Set(m, name="CM_LPT", domain=["*"])
        g.Xtp = Set(m, name="XTP", domain=[g.ll], description="MACRO XTP periods")
        # CM_LED is also declared (with domain=ALLYEAR) by initmty_cli.py when
        # the CLI extension is active; guard so combining CLI+MSA doesn't hit
        # a domain-mismatch redeclaration crash (same idiom as TM_RESULT
        # above in initmty_msa.py).
        if not g.declared(g.cm_led):
            g.cm_led = Parameter(m, name="CM_LED", domain=[g.ll])
        g.tm_xwt = Parameter(m, name="TM_XWT", domain=[g.r, g.ll])
        # Periods stuff
        g.t1 = Alias(m, name="T_1", alias_with=g.Tb)

        self.tc.enqueue(self.label_msa_exec1)

        # Interpolate MACRO-specific parameters
        batincludes: list[FilparamGmsConfig] = [
            FilparamGmsConfig(
                src=g.tm_ddf,
                arg2=(g.r,),
                tail1=(g.c,),
                arg4=("", "", "", "", ""),
                arg5=g.year,
                arg6=g.t,
            ),
            FilparamGmsConfig(
                src=g.tm_gr,
                arg2=(g.r,),
                tail1=(),
                arg4=("", "", "", "", ""),
                arg5=g.year,
                arg6=g.t,
            ),
            FilparamGmsConfig(
                src=g.tm_growv,
                arg2=(g.r,),
                tail1=(),
                arg4=("", "", "", "", ""),
                arg5=g.year,
                arg6=g.Xtp,
            ),
            FilparamGmsConfig(
                src=g.tm_hsx,
                arg2=(g.r,),
                tail1=(),
                arg4=("", "", "", "", ""),
                arg5=g.year,
                arg6=g.Xtp,
            ),
        ]

        for config in batincludes:
            self.include(FilparamGms(self.tc, self.env, config=config))

        self.tc.enqueue(self.label_msa_exec2)

        if (self.env.msa + self.env.cli).upper() != "MSAYES":
            return

        self.tc.enqueue(self.label_msa_exec3)

    def label_msa_exec1(self: PreppmMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  PP(T)$(ORD(T)>1) = YES;
  TB(T)$(ORD(T)=1) = YES;
  TLAST(T--ORD(T)) = YES;
  NYPER(T) = LAGT(T);
  NYPER(TLAST(T+1)) = LAGT(T);
  CM_LED(T+1)=LAGT(T);
  XTP(LL)$=CM_LED(LL);
  XTP(T) = YES;
""",
        )

    def label_msa_exec2(self: PreppmMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
TM_GDPGOAL(R,TB) = TM_GDP0(R);
LOOP(PP(T+1),TM_GDPGOAL(R,PP) = TM_GDPGOAL(R,T)*(1+TM_GR(R,T)/100)**NYPER(T));
""",
        )

    def label_msa_exec3(self: PreppmMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Preprocess CBA parameters
  Z = MAX(1,ABS(TM_DEFVAL('REFTEMP')));
  F = MAX(0,ROUND(TM_DEFVAL('REFLOSS'),4));
  TM_DAM(R,'IN')$= TM_MDTL(R)$TM_GDP0(R);
  TM_DAM(R,'IN')$= TM_MDTQ(R)$TM_GDP0(R);
  OPTION TM_CATT < TM_HSX;
  TM_CATT(R)$TM_CATT(R) = ((Z**2/F)**0.5)$F;
  TM_DAM(R,'N')$= TM_CATT(R)$TM_GDP0(R);
  MR(R) = SUM((TM_DAM(R,MDM),G_RCUR(R,CUR)),1);
  CNT=SMAX(MR,TM_GDP0(MR));
  LOOP(MR(R)$CNT,IF(TM_GDP0(R)=CNT,CNT=0;TM_DAM(R,'0')=YES));
* Define initial guess for marginal damage for LP
  LOOP((G_RCUR(R,CUR),C(CG(CM_EMIS)))$TM_DAM(R,'0'),DAM_BQTY(R,C) = EPS;
    DAM_COST(R,PP(T),C,CUR) = 1/TM_SCALE_CST / 10**(3.4-2$DIAG('CO2-GTC',C)) *
      SUM(MR(REG),MAX(.01,(2*Z/POWER(TM_CATT(R),2))$TM_CATT(R)+TM_MDTL(R)/Z+2*TM_MDTQ(R)/Z)*TM_GDPGOAL(REG,T)));
  CM_LPK(CM_KIND)=YES; CM_LPT(CM_TKIND)=YES;
  MR(R)=NO;
""",
        )

    def _label_tonlp(
        self: PreppmMsa,
        is_tm_catt_defined: bool,
        is_dam_cost_defined: bool,
    ) -> None:
        # Update forcing functions, reset damage and climate module
        if is_tm_catt_defined:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="LOOP(G_RCUR(R,CUR)$TM_DAM(R,'0'),DAM_COST(R,PP,C(CG(CM_EMIS)),CUR) = EPS);",
            )

        if is_dam_cost_defined:
            rpt_dam_mod_GP(self.tc, self.env, solveda=self.env.solveda)

        if self.env.cli.upper() != "YES":
            return

        self.tc.add_gams_code(module=self, phase="run", code=forcupd_cli())

        if not is_tm_catt_defined:
            return

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
LOOP(G_RCUR(R,CUR)$TM_DAM(R,'0'),
F=REG_WOBJ(R,'DAM-EXT+',CUR); MY_F=REG_WOBJ(R,'DAS',CUR); Z=MAX(0,MIN(MY_F,-F));
REG_WOBJ(R,'DAS',CUR)=MY_F-Z; REG_WOBJ(R,'DAM-EXT+',CUR)=F+Z);
CM_MAXC_M(CM_EMIS,XTP) = VAR_CLITOT.LO(CM_EMIS,XTP);
IF(CARD(TM_DAM),CM_TKIND(CM_EMIS)=NO; VAR_CLITOT.FX(CM_EMIS,XTP)=VAR_CLITOT.L(CM_EMIS,XTP);
ELSE OPTION CLEAR=CM_KIND,CLEAR=CM_TKIND);
""",
        )

    def _label_tolp(self) -> None:
        self.tc.add_gams_code(module=self, phase="run", code=preppm_msa_label_tolp())


def preppm_msa_label_tonlp(
    is_tm_catt_defined: bool,
    is_dam_cost_defined: bool,
    cli: str,
    solveda: str,
    stages: str,
    var: str,
    vart: str,
    sws: str,
    sow: str,
    scum: str,
    sw_notags: str,
) -> str:
    """String-building twin of ``PreppmMsa._label_tonlp``.

    NOTE: kept raw-GAMS-string (not natively translated) solely because its
    callers (solprep_msa.py, reached from rpt_ext_msa.py and solve_msa.py)
    are themselves still raw-GAMS-string generators whose output gets
    spliced into larger untranslated blocks. Uses the legacy string-based
    ``rpt_dam_mod`` rather than ``rpt_dam_mod_GP`` for the same reason
    documented on ``rpt_dam_mod``. ``sw_notags`` is accepted only for
    call-site compatibility with solprep_msa.py; it's unused since
    rpt_dam_mod's own scum=="1" handling already mirrors sw_notags's fixed
    reset internally.
    """
    del sw_notags
    return_str = ""
    # Update forcing functions, reset damage and climate module
    if is_tm_catt_defined:
        return_str += (
            "LOOP(G_RCUR(R,CUR)$TM_DAM(R,'0'),DAM_COST(R,PP,C(CG(CM_EMIS)),CUR) = EPS);"
        )

    if is_dam_cost_defined:
        return_str += rpt_dam_mod(
            solveda=solveda,
            stages=stages,
            var=var,
            cli=cli,
            vart=vart,
            sws=sws,
            sow=sow,
            scum=scum,
        )

    if cli.upper() != "YES":
        return return_str

    return_str += forcupd_cli()

    if not is_tm_catt_defined:
        return return_str

    return_str += """
LOOP(G_RCUR(R,CUR)$TM_DAM(R,'0'),
F=REG_WOBJ(R,'DAM-EXT+',CUR); MY_F=REG_WOBJ(R,'DAS',CUR); Z=MAX(0,MIN(MY_F,-F));
REG_WOBJ(R,'DAS',CUR)=MY_F-Z; REG_WOBJ(R,'DAM-EXT+',CUR)=F+Z);
CM_MAXC_M(CM_EMIS,XTP) = VAR_CLITOT.LO(CM_EMIS,XTP);
IF(CARD(TM_DAM),CM_TKIND(CM_EMIS)=NO; VAR_CLITOT.FX(CM_EMIS,XTP)=VAR_CLITOT.L(CM_EMIS,XTP);
ELSE OPTION CLEAR=CM_KIND,CLEAR=CM_TKIND);
"""
    return return_str


def preppm_msa_label_tolp() -> str:
    return """
* Redefine marginal damages
LOOP((C(CG(CM_EMIS)),G_RCUR(R,CUR))$(CNT$TM_DAM(R,'0')),
DAM_COST(R,PP(T),C,CUR) = SUM(SUPERYR(T,XTP),ABS(VAR_CLITOT.M(CM_EMIS,XTP)/EQ_TRDBAL.M(T,"NMR"))*CM_EVAR(CM_EMIS,XTP)*OBJ_DISC(R,XTP,CUR)/OBJ_DISC(R,T,CUR)/TM_SCALE_CST));
CM_TKIND(CM_VAR(CM_LPT))=YES; CM_KIND(CM_VAR(CM_LPK))=YES;
VAR_CLITOT.LO(CM_EMIS,XTP) = CM_MAXC_M(CM_EMIS,XTP);
VAR_CLITOT.UP(CM_EMIS,XTP) = INF;
"""
