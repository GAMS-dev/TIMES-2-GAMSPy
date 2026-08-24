# eqobsalv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJSALV the objective functions for salvaging
# *   - Investment Costs
# *   - Taxes and subsidies on investments
# *   - Decommissioning
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, If, Loop, Number, Ord, Parameter, Set, Smax, Sum
from gamspy.math import Min, Round, exp, project

from core import prepret_dsc
from core.base_class import GamsClass
from core.utils import resolve_ctst
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitParameter

    from core.utils import SET_OR_ALIAS
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobsalvMod(GamsClass):
    """Translation unit for eqobsalv.mod."""

    # Instance attributes
    module_name: str = "eqobsalv_mod"
    gams_source: str = "eqobsalv.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str = ""
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if self.tc.defined("OBJSCC"):
            self._label_prepro()
            return

        self.declarations()
        self._label_prepro()

    def declarations(self) -> None:
        g = self.tc
        m = g.container

        g.salv_dec = Parameter(
            m, name="SALV_DEC", domain=[g.Reg, g.allyear, g.prc, g.cur]
        )
        g.objscc = Parameter(m, name="OBJSCC", domain=[g.Reg, g.allyear, g.prc, g.cur])
        g.objsic = Parameter(m, name="OBJSIC", domain=[g.Reg, g.allyear, g.prc])
        g.obj_dceoh = Parameter(m, name="OBJ_DCEOH", domain=[g.Reg, g.cur])
        g.ObjSali = Set(
            m,
            name="OBJ_SALI",
            domain=[
                g.r,
                g.allyear,
                g.p,
                g.age,
                g.year,
                g.age,
                g.allyear,
                g.year,
            ],
        )

    def _label_prepro(self) -> None:
        self.tc.enqueue(
            self.exec_eqobsalv_prepro,
            arg1=self.arg1,
            timestep_is_set=self.env.is_set("TIMESTEP"),
            stepped=self.env.stepped,
            ctst=self.env.ctst,
            capjd=self.env.capjd_GP,
            etl=self.env.etl,
            declif=self.env.declif,
            vnret_defined=self.tc.defined("VNRET"),
        )

        self._label_equa(
            arg2=self.arg2,
            eq=self.env.eq,
            sow=self.env.sow,
            vart=self.env.vart,
            validate=self.env.validate,
            etl=self.env.etl,
            sws=self.env.sws,
            varv=self.env.varv,
            var=self.env.var,
        )

    def exec_eqobsalv_prepro(
        self: EqobsalvMod,
        arg1: str,
        timestep_is_set: bool,
        stepped: str,
        ctst: Literal["", "**EPS", "**0", "1"],
        capjd: ImplicitParameter | Number,
        etl: str,
        declif: str,
        vnret_defined: bool,
    ) -> None:
        eqobsalv_prepro_GP(
            tc=self.tc,
            arg1=arg1,
            timestep_is_set=timestep_is_set,
            stepped=stepped,
            ctst=ctst,
            capjd=capjd,
            etl=etl,
            declif=declif,
            vnret_defined=vnret_defined,
        )

    def _label_equa(
        self,
        arg2: str,
        eq: str,
        sow: str,
        vart: str,
        validate: str,
        etl: str,
        sws: str,
        varv: str,
        var: str,
    ) -> None:
        if arg2.upper() == "EXIT":
            return

        self.generate_salvage_equation(eq, sow, vart, validate, etl, sws, varv, var)

    def generate_salvage_equation(
        self,
        eq: str,
        sow: str,
        vart: str,
        validate: str,
        etl: str,
        sws: str,
        varv: str,
        var: str,
    ) -> None:
        lhs = rf"    {eq}_OBJSALV(RDCUR(R,CUR) {sow}) .."
        rhs = rf"""
*------------------------------------------------------------------------------
* Cases I - Investment Cost and II - Taxes/Subsidies
*------------------------------------------------------------------------------
* [AL] Note that discounting to EOH+1 is imbedded in OBJSCC and OBJSIC

      SUM(OBJ_SUMS(R,T,P), OBJSCC(R,T,P,CUR) * {vart}_NCAP(R,T,P {sws})) * OBJ_DCEOH(R,CUR) +
"""
        if validate != "YES":
            rhs += "      SUM(OBJ_SUMS(R,PYR(V),P), OBJSCC(R,V,P,CUR) * NCAP_PASTI(R,V,P)) * OBJ_DCEOH(R,CUR) +"

        if etl == "YES":
            rhs += rf"""      SUM((OBJ_SUMS(R,T,TEG(P)),G_RCUR(R,CUR)), OBJSIC(R,T,P) * {vart}_IC(R,T,P {sws})) * OBJ_DCEOH(R,CUR) +
"""

        if self.tc.defined("VNRET"):
            rhs += prepret_dsc.objsalv(var=var, varv=varv, sws=sws, sow=sow)

        rhs += rf"""
*------------------------------------------------------------------------------
* Cases III - Decommissioning
*------------------------------------------------------------------------------
* [AL] Note that discounting to EOH+1 is imbedded in SALV_DEC

      SUM(OBJ_SUMS3(R,T,P), {vart}_NCAP(R,T,P {sws}) * SALV_DEC(R,T,P,CUR)) * OBJ_DCEOH(R,CUR)
      +
* Past investments
      SUM(OBJ_SUMS3(R,PYR,P), NCAP_PASTI(R,PYR,P) * SALV_DEC(R,PYR,P,CUR)) * OBJ_DCEOH(R,CUR)
      +

*------------------------------------------------------------------------------
* Cases IV - Decommissioning Surveillance
*------------------------------------------------------------------------------
* The same proportion SALV_INV is salvaged from investments and surveillance costs
      SUM(OBJ_SUMIVS(R,V,P,K,Y)$SALV_INV(R,V,P,K),
            OBJ_DISC(R,Y,CUR) * {macro.obj_dlagc("R", "K", "P", "CUR")} * SALV_INV(R,V,P,K) *
            ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)))
      +
*------------------------------------------------------------------------------
* LATE REVENUES
*------------------------------------------------------------------------------
* [AL] LATEREVENUES identical to decommissioning, with DCOST replaced by OCOM*VALU
* Revenues are obtained in the proportion 1-SALV_INV of the total revenues

    SUM((OBJ_SUMIII(R,V,P,LL,K,Y),COM)$((NOT Y_EOH(Y))$NCAP_OCOM(R,V,P,COM)),
        (1-SALV_INV(R,V,P,LL)) * NCAP_VALU(R,K,P,COM,CUR) * OBJ_DISC(R,Y,CUR) *
        ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)) *
        NCAP_OCOM(R,V,P,COM) / OBJ_DIVIII(R,V,P))


    =E=

      {var}_OBJ(R,'OBJSAL',CUR {sow});
"""
        equation = lhs + rhs
        self.tc.add_gams_code(module=self, phase="init", code=equation)


def eqobsalv_prepro_GP(
    *,
    tc: TimesModelClass,
    arg1: str,
    timestep_is_set: bool,
    stepped: str,
    ctst: Literal["", "**EPS", "**0", "1"],
    capjd: ImplicitParameter | Number,
    etl: str,
    declif: str,
    vnret_defined: bool,
) -> None:
    """GAMSPy twin of the ``$LABEL PREPRO`` block of ``eqobsalv.mod``."""
    # $IF %STEPPED%==+ / $IFI %1==mod $GOTO EQUA
    if stepped == "+" and arg1.upper() == "MOD":
        return

    g = tc

    # $SET PFT ''
    # $IF NOT DEFINED VNRET / $IF NOT '%CTST%'=='' $SET PFT (T)
    pft: SET_OR_ALIAS = g.v
    if not vnret_defined and ctst != "":
        pft = g.v[g.t]

    (r, v, t, p, k, ll, age, jot, cur, prc) = (
        g.r,
        g.v,
        g.t,
        g.p,
        g.k,
        g.ll,
        g.age,
        g.jot,
        g.cur,
        g.prc,
    )
    (ObjSali, ObjSumii, ObjSumsi, ObjSums, ObjSums3, ObjSumiii, ObjSumivs) = (
        g.ObjSali,
        g.ObjSumii,
        g.ObjSumsi,
        g.ObjSums,
        g.ObjSums3,
        g.ObjSumiii,
        g.ObjSumivs,
    )
    (KEoh, Invspred, Rp, Rdcur, ObjIcur, Rtp, Y, Pastmile, GRcur) = (
        g.KEoh,
        g.Invspred,
        g.Rp,
        g.Rdcur,
        g.ObjIcur,
        g.Rtp,
        g.Y,
        g.Pastmile,
        g.GRcur,
    )
    (salv_inv, objscc, obj_dceoh, ncap_tlife, yearval, obj_disc) = (
        g.salv_inv,
        g.objscc,
        g.obj_dceoh,
        g.ncap_tlife,
        g.yearval,
        g.obj_disc,
    )

    # * Check stepped mode
    if timestep_is_set:
        ObjSums.setRecords(None)
        ObjSums3.setRecords(None)
        salv_inv.setRecords(None)
        objscc.setRecords(None)

    # * Salvaging of Investments; LL is investment year, K is commissioning year
    # [UR] 19.12.2003 added -1 below, since lifetime starts at the beginning of year K
    ObjSali[ObjSumii[r, pft, p, age, KEoh, jot], k, ll.lag(Ord(ll), "circular")].where[
        (yearval[k] + ncap_tlife[r, v, p] - 1 > g.miyr_vl).where[
            Invspred[KEoh, jot, k, ll]
        ]
    ] = True
    project(source=ObjSali, target=ObjSumsi, direction="left")
    ObjSali.setRecords(None)

    # * No retrofit salvage
    with (
        Loop(Domain(Rp[r, prc], p).where[g.prc_refit[Rp, p]]),
        If(g.prc_refit[Rp, p] < 0),
    ):
        ObjSumsi[r, t, p, k] = False
    project(source=ObjSumsi, target=ObjSums, direction="left")

    # * Salvaging of Decommissioning
    with Loop(ObjSumiii[ObjSums[r, v, p], ll, k, Y]):
        ObjSums3[r, v, p] = True
    # * Salvaging of Decommissioning surveillance
    with Loop(
        ObjSumivs[r, v, p, k, Y].where[yearval[k] + ncap_tlife[r, v, p] - 1 > g.miyr_vl]
    ):
        ObjSums3[r, v, p] = True
        ObjSumsi[r, v, p, k] = True

    with Loop(Rdcur[r, cur]):
        # * Salvage proportion of investments at the commissioning year K:
        rate = (1 + g.g_drate[r, v, cur]) * exp(g.ncap_fdr[r, v, p])
        salv_inv[ObjSumsi[r, v, p, k]].where[ObjIcur[r, v, p, cur]] = Min(
            1,
            (rate ** (ncap_tlife[r, v, p] + yearval[k] - g.miyr_vl - 1) - 1)
            / (rate ** ncap_tlife[r, v, p] - 1),
        )

    # * Discount factors for the year EOH+1:
    with Loop(g.Miyr1[ll]):
        g.f[...] = g.miyr_vl + 1 - yearval[g.Miyr1]
        obj_dceoh[Rdcur[r, cur]] = obj_disc[r, ll + g.f, cur]
    # * Shape-reduced salvage at EOH+1:
    g.z[...] = Smax(t.where[g.b[t] <= g.miyr_vl + 1], Ord(t) - 1)
    with Loop(g.Miyr1[t - g.z]):
        salv_inv[ObjSumsi[Rtp, k]].where[g.ncap_cpx[Rtp]] = salv_inv[Rtp, k] * (
            1 + g.rtp_cpx[Rtp, t]
        )

    ObjSumsi.setRecords(None)

    # * Salvage value of investments at year EOH+1:
    # * Note that in Cases 2a and 2b investment costs are paid before K
    objscc[ObjIcur[ObjSums[r, v, p], cur]] = (
        g.cor_salvi[r, v, p, cur]
        / obj_dceoh[r, cur]
        / g.obj_divi[r, v, p]
        * Sum(
            Domain(ObjSumii[r, v, p, age, KEoh, jot], Invspred[KEoh, jot, ll, k]).where[
                salv_inv[r, v, p, ll]
            ],
            capjd
            * (
                macro.obj_icost_GP(r, k, p, cur)
                + macro.obj_itax_GP(r, k, p, cur)
                - macro.obj_isub_GP(r, k, p, cur)
            )
            * salv_inv[r, v, p, ll]
            * obj_disc[r, k, cur],
        )
    )

    # * Handle ETL in similar fashion
    if etl == "YES":
        with Loop(Domain(ObjSums[r, t[v], p], GRcur[r, cur]).where[g.seg[r, p]]):
            g.objsic[r, t, p] = (
                g.cor_salvi[r, t, p, cur]
                / obj_dceoh[r, cur]
                / g.obj_divi[r, t, p]
                * Sum(
                    Domain(
                        ObjSumii[r, v, p, age, KEoh, jot],
                        Invspred[KEoh, jot, ll, k],
                    ),
                    capjd * salv_inv[r, t, p, ll] * obj_disc[r, k, cur],
                )
            )

    # * Additional constant term
    g.obj_iad[Rdcur[r, cur]] = Sum(
        ObjIcur[ObjSums[r, Pastmile[v], p], cur].where[
            (g.obj_pasti[r, v, p, cur] == 0) + resolve_ctst(Number(0), ctst)
        ],
        objscc[r, v, p, cur] * g.ncap_pasti[r, v, p] * obj_dceoh[r, cur],
    )

    # *GG* only if decommissioning lifetime provided by user
    ncap_drate, obj_rfr, ncap_delif = g.ncap_drate, g.obj_rfr, g.ncap_delif
    g.cor_salvd[Rtp[r, v, p], cur].where[macro.obj_dcost_GP(r, v, p, cur)] = (
        (
            (1 - 1 / (1 + ncap_drate[r, v, p]))
            * (1 - 1 / (1 + obj_rfr[r, v, cur]) ** ncap_delif[r, v, p])
        )
        / (
            (1 - 1 / (1 + obj_rfr[r, v, cur]))
            * (1 - 1 / (1 + ncap_drate[r, v, p]) ** ncap_delif[r, v, p])
        )
    ).where[ncap_drate[r, v, p] > 0] + Number(1).where[ncap_drate[r, v, p] == 0]
    ncap_declif = g.get_parameter(f"NCAP_{declif}")
    g.obj_crfd[Rtp[r, v, p], cur].where[macro.obj_dcost_GP(r, v, p, cur)] = (
        g.cor_salvd[r, v, p, cur]
        * (1 - (1 / (1 + g.g_drate[r, v, cur])))
        / (1 - (1 + g.g_drate[r, v, cur]) ** (-Round(ncap_declif[r, v, p])))
    )

    # * Salvage value of Decommissioning at year EOH+1:
    # * Documentation defines the value for each decommissioning year Y;
    # * here aggregated by vintage
    g.salv_dec[ObjSums3[r, v, p], cur].where[g.cor_salvd[r, v, p, cur]] = (
        g.cor_salvd[r, v, p, cur]
        / g.obj_diviii[r, v, p]
        / obj_dceoh[r, cur]
        * Sum(
            ObjSumiii[r, v, p, ll, k, Y].where[salv_inv[r, v, p, ll]],
            salv_inv[r, v, p, ll]
            * macro.obj_dcost_GP(r, k, p, cur)
            * obj_disc[r, Y, cur],
        )
    )
