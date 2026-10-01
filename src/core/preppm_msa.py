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

from gamspy import (
    Alias,
    Domain,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    Smax,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, aggregate, diag, power

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
        g = self.tc
        t, ll = g.t, g.ll
        g.Pp[t].where[Ord(t) > 1.0] = True
        g.Tb[t].where[Ord(t) == 1.0] = True
        g.Tlast[t.lag(Ord(t), "circular")] = True
        g.nyper[t] = g.lagt[t]
        g.nyper[g.Tlast[t + 1]] = g.lagt[t]
        g.cm_led[t + 1] = g.lagt[t]
        g.Xtp[ll] = sparse(g.cm_led[ll])
        g.Xtp[t] = True

    def label_msa_exec2(self: PreppmMsa) -> None:
        g = self.tc
        r, t = g.r, g.t
        g.tm_gdpgoal[r, g.Tb] = g.tm_gdp0[r]
        with Loop(g.Pp[t + 1]):
            g.tm_gdpgoal[r, g.Pp] = g.tm_gdpgoal[r, t] * (
                (1.0 + g.tm_gr[r, t] / 100.0) ** g.nyper[t]
            )

    def label_msa_exec3(self: PreppmMsa) -> None:
        g = self.tc
        r, t, c, cur, Reg = g.r, g.t, g.c, g.cur, g.Reg
        # * Preprocess CBA parameters
        g.z[...] = Max(1.0, abs(g.tm_defval["REFTEMP"]))
        g.f[...] = Max(0.0, Round(g.tm_defval["REFLOSS"], 4))
        g.TmDam[r, "IN"] = sparse(g.tm_mdtl[r].where[g.tm_gdp0[r]])
        g.TmDam[r, "IN"] = sparse(g.tm_mdtq[r].where[g.tm_gdp0[r]])
        aggregate(source=g.tm_hsx, target=g.tm_catt)
        g.tm_catt[r].where[g.tm_catt[r]] = ((g.z**2.0 / g.f) ** 0.5).where[g.f]
        g.TmDam[r, "N"] = sparse(g.tm_catt[r].where[g.tm_gdp0[r]])
        g.Mr[r] = Sum(Domain(g.TmDam[r, g.mdm], g.GRcur[r, cur]), 1.0)
        g.cnt[...] = Smax(g.Mr, g.tm_gdp0[g.Mr])
        with Loop(g.Mr[r].where[g.cnt]), If(g.tm_gdp0[r] == g.cnt):
            g.cnt[...] = 0.0
            g.TmDam[r, "0"] = True
        # * Define initial guess for marginal damage for LP
        with Loop(Domain(g.GRcur[r, cur], c[g.cg[g.CmEmis]]).where[g.TmDam[r, "0"]]):
            g.dam_bqty[r, c] = SpecialValues.EPS
            g.dam_cost[r, g.Pp[t], c, cur] = (
                1.0
                / g.tm_scale_cst
                / (10.0 ** (3.4 - Number(2.0).where[diag("CO2-GTC", c)]))
                * Sum(
                    g.Mr[Reg],
                    Max(
                        0.01,
                        (2.0 * g.z / power(g.tm_catt[r], 2.0)).where[g.tm_catt[r]]
                        + g.tm_mdtl[r] / g.z
                        + 2.0 * g.tm_mdtq[r] / g.z,
                    )
                    * g.tm_gdpgoal[Reg, t],
                )
            )
        g.cmlpk[g.CmKind] = True
        g.cmlpt[g.CmTkind] = True
        g.Mr[r] = False

    def _label_tonlp(
        self: PreppmMsa,
        is_tm_catt_defined: bool,
        is_dam_cost_defined: bool,
    ) -> None:
        preppm_msa_label_tonlp_GP(
            self,
            is_tm_catt_defined=is_tm_catt_defined,
            is_dam_cost_defined=is_dam_cost_defined,
        )

    def _label_tolp(self) -> None:
        preppm_msa_label_tolp_GP(self.tc)


def preppm_msa_label_tonlp_GP(
    module: GamsClass,
    *,
    is_tm_catt_defined: bool,
    is_dam_cost_defined: bool,
) -> None:
    """GAMSPy twin of :func:`preppm_msa_label_tonlp`."""
    g, env = module.tc, module.env
    r, c, cur = g.r, g.c, g.cur
    # Update forcing functions, reset damage and climate module
    if is_tm_catt_defined:
        with Loop(g.GRcur[r, cur].where[g.TmDam[r, "0"]]):
            g.dam_cost[r, g.Pp, c[g.cg[g.CmEmis]], cur] = SpecialValues.EPS

    if is_dam_cost_defined:
        rpt_dam_mod_GP(g, env, solveda=env.solveda)

    if env.cli.upper() != "YES":
        return

    # TODO this needs to be translated before it can be included from inside a loop!
    g.add_gams_code(module=module, phase="run", code=forcupd_cli())

    if not is_tm_catt_defined:
        return

    with Loop(g.GRcur[r, cur].where[g.TmDam[r, "0"]]):
        g.f[...] = g.reg_wobj[r, "DAM-EXT+", cur]
        g.my_f[...] = g.reg_wobj[r, "DAS", cur]
        g.z[...] = Max(0.0, Min(g.my_f, -g.f))
        g.reg_wobj[r, "DAS", cur] = g.my_f - g.z
        g.reg_wobj[r, "DAM-EXT+", cur] = g.f + g.z
    g.cm_maxc_m[g.CmEmis, g.Xtp] = g.VAR_CLITOT.lo[g.CmEmis, g.Xtp]
    if g.TmDam.number_records:
        g.CmTkind[g.CmEmis] = False
        g.VAR_CLITOT.fx[g.CmEmis, g.Xtp] = g.VAR_CLITOT.l[g.CmEmis, g.Xtp]
    else:
        g.CmKind.setRecords(None)
        g.CmTkind.setRecords(None)


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


def preppm_msa_label_tolp_GP(g: TimesModelClass) -> None:
    """GAMSPy twin of :func:`preppm_msa_label_tolp`."""
    r, t, c, cur = g.r, g.t, g.c, g.cur
    # * Redefine marginal damages
    with Loop(
        Domain(c[g.cg[g.CmEmis]], g.GRcur[r, cur]).where[g.cnt.where[g.TmDam[r, "0"]]]
    ):
        g.dam_cost[r, g.Pp[t], c, cur] = Sum(
            g.Superyr[t, g.Xtp],
            abs(g.VAR_CLITOT.m[g.CmEmis, g.Xtp] / g.eq_trdbal.m[t, "NMR"])
            * g.cm_evar[g.CmEmis, g.Xtp]
            * g.obj_disc[r, g.Xtp, cur]
            / g.obj_disc[r, t, cur]
            / g.tm_scale_cst,
        )
    g.CmTkind[g.CmVar[g.cmlpt]] = True
    g.CmKind[g.CmVar[g.cmlpk]] = True
    g.VAR_CLITOT.lo[g.CmEmis, g.Xtp] = g.cm_maxc_m[g.CmEmis, g.Xtp]
    g.VAR_CLITOT.up[g.CmEmis, g.Xtp] = SpecialValues.POSINF
