# eqobjinv_rpt.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  EQOBJINV the objective functions on investments
#    - Investment Costs
#    - Investment Tax/Subsidies
#    - Decommissioning
# =============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Ord, Parameter, Set, Sum
from gamspy.math import Round

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjinvRpt(GamsClass):
    """Translation unit for eqobjinv.rpt."""

    # Instance attributes
    module_name: str = "eqobjinv_rpt"
    gams_source: str = "eqobjinv.rpt"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        r, allyear, p, Reg, prc, cur, age = (
            g.r,
            g.allyear,
            g.p,
            g.Reg,
            g.prc,
            g.cur,
            g.age,
        )
        g.vdisc = Parameter(m, name="vdisc", records=0)
        g.NcapYes = Set(m, name="NCAP_YES", domain=[r, allyear, p])
        g.obj_sumik = Parameter(m, name="obj_sumik", domain=[Reg, allyear, prc, cur])
        g.ykagep = Parameter(m, name="ykagep", domain=[allyear, allyear, age])

        self.tc.enqueue(
            self.exec1, etl_enabled=(self.env.etl == "YES"), declif=self.env.declif
        )

    def exec1(self: EqobjinvRpt, etl_enabled: bool, declif: str) -> None:
        g = self.tc
        (
            ObjIcur,
            r,
            t,
            Teg,
            p,
            cur,
            f,
            obj_crf,
            obj_divi,
            g_drate,
            ObjSumii,
            life,
            KEoh,
            jot,
            Invspred,
            ll,
            k,
            my_f,
            obj_disc,
            age,
            Opyear,
            par_objinv,
            Y,
            vdisc,
            ykagep,
            VAR_IC,
        ) = (
            g.ObjIcur,
            g.r,
            g.t,
            g.Teg,
            g.p,
            g.cur,
            g.f,
            g.obj_crf,
            g.obj_divi,
            g.g_drate,
            g.ObjSumii,
            g.life,
            g.KEoh,
            g.jot,
            g.Invspred,
            g.ll,
            g.k,
            g.my_f,
            g.obj_disc,
            g.age,
            g.Opyear,
            g.par_objinv,
            g.Y,
            g.vdisc,
            g.ykagep,
            g.VAR_IC,
        )

        (
            NcapYes,
            Rtp,
            v,
            VAR_NCAP,
            ncap_pasti,
            pyr,
            obj_sumik,
            NCAP_DECLIF,
        ) = (
            g.NcapYes,
            g.Rtp,
            g.v,
            g.VAR_NCAP,
            g.ncap_pasti,
            g.pyr,
            g.obj_sumik,
            g.get_variable(f"NCAP_{declif}"),
        )
        # ------------------------------------------------------------------------------
        # Identify new capacities
        NcapYes[Rtp[r, v, p]].where[
            VAR_NCAP[r, v, p].l.where[t[v]] + ncap_pasti[r, v, p].where[pyr[v]]
        ] = True
        NcapYes[r, ll.lag(Ord(ll)), p].where[NcapYes[r, ll, p]] = True
        # ------------------------------------------------------------------------------
        # Cases I - Investment Cost and II - Taxes/Subsidies
        # ------------------------------------------------------------------------------
        obj_sumik[r, k, p, cur].where[
            macro.obj_icost_GP(r, k, p, cur)
            + macro.obj_itax_GP(r, k, p, cur)
            + macro.obj_isub_GP(r, k, p, cur)
            & NcapYes[r, "0", p]
        ] = (
            macro.obj_icost_GP(r, k, p, cur)
            + macro.obj_itax_GP(r, k, p, cur)
            - macro.obj_isub_GP(r, k, p, cur)
        )
        # Calculate Annual discounted investment costs PAR_OBJINV
        # vdisc is the constant discount rate used to discount annual payments to the investment year LL
        with Loop(ObjIcur[NcapYes[r, v, p], cur]):
            f[...] = (
                (VAR_NCAP[r, v, p].l.where[t[v]] + ncap_pasti[r, v, p].where[pyr[v]])
                * obj_crf[r, v, p, cur]
                / obj_divi[r, v, p]
            )
            vdisc[...] = 1 + g_drate[r, v, cur]
            ykagep.setRecords(None)
            with Loop(
                Domain(ObjSumii[r, v, p, life, KEoh, jot], Invspred[KEoh, jot, ll, k])
            ):
                my_f[...] = f * obj_disc[r, ll, cur] * obj_sumik[r, k, p, cur]
                ykagep[ll + (Ord(age) - 1), ll, age].where[Opyear[life, age]] = my_f
            par_objinv[r, v, Y, p, cur] = Sum(
                Domain(ll, age).where[ykagep[Y, ll, age]],
                ykagep[Y, ll, age] * vdisc ** (1 - Ord(age)),
            )

        if etl_enabled:
            # Handle ETL
            with Loop(ObjIcur[r, t, Teg[p], cur].where[VAR_IC[r, t, p].l]):
                f[...] = obj_crf[r, t, p, cur] * VAR_IC[r, t, p].l / obj_divi[r, t, p]
                vdisc[...] = 1 + g_drate[r, t, cur]
                ykagep.setRecords(None)
                with Loop(
                    Domain(
                        ObjSumii[r, t, p, life, KEoh, jot], Invspred[KEoh, jot, ll, k]
                    )
                ):
                    my_f[...] = f * obj_disc[r, ll, cur]
                    ykagep[ll + (Ord(age) - 1), ll, age].where[Opyear[life, age]] = my_f
                par_objinv[r, t, Y, p, cur] = par_objinv[r, t, Y, p, cur] + Sum(
                    Domain(ll, age).where[ykagep[Y, ll, age]],
                    ykagep[Y, ll, age] * vdisc ** (1 - Ord(age)),
                )

        (
            obj_c,
            Pastmile,
            v,
            cor_salvi,
            year,
            obj_pasti,
            obj_d,
            Rdcur,
            obv,
            sum_obj,
            VAR_OBJ,
            NcapYes,
            VAR_NCAP,
            ncap_pasti,
            pyr,
            obj_crfd,
            obj_diviii,
            z,
            par_objdec,
            ObjSumiii,
            Yk,
            yearval,
        ) = (
            g.obj_c,
            g.Pastmile,
            g.v,
            g.cor_salvi,
            g.year,
            g.obj_pasti,
            g.obj_d,
            g.Rdcur,
            g.obv,
            g.sum_obj,
            g.VAR_OBJ,
            g.NcapYes,
            g.VAR_NCAP,
            g.ncap_pasti,
            g.pyr,
            g.obj_crfd,
            g.obj_diviii,
            g.z,
            g.par_objdec,
            g.ObjSumiii,
            g.Yk,
            g.yearval,
        )
        # ------------------------------------------------------------------------------
        # Check that total OBJINV value is the same in all calculation methods:
        # PAST Investments cannot be accurately matched in case 2a; therefore check with OBJ_PASTI
        obj_c[...] = Sum(
            Domain(r, t, Y, p, cur).where[par_objinv[r, t, Y, p, cur]],
            par_objinv[r, t, Y, p, cur],
        ) + Sum(
            Domain(ObjSumii[r, Pastmile[v], p, age, KEoh, jot], cur),
            cor_salvi[r, v, p, cur]
            / obj_divi[r, v, p]
            * Sum(
                Invspred[KEoh, jot, year, k],
                obj_disc[r, year, cur]
                * obj_sumik[r, k, p, cur]
                * obj_pasti[r, v, p, cur],
            ),
        )
        obj_d[...] = Sum(
            Rdcur[r, cur], Sum(obv, sum_obj["OBJINV", obv] * VAR_OBJ[r, obv, cur].l)
        )
        print(g.obj_c.records)
        obj_sumik.setRecords(None)
        # ------------------------------------------------------------------------------
        # Cases III - Decommissioning
        # ------------------------------------------------------------------------------
        # Calculate Annual discounted decommissioning costs PAR_OBJDEC
        # vdisc is the constant discount rate used to discount annual payments to the investment year LL
        with Loop(
            Domain(NcapYes[r, v, p], cur).where[macro.obj_dcost_GP(r, v, p, cur)]
        ):
            f[...] = (
                (VAR_NCAP[r, v, p].l.where[t[v]] + ncap_pasti[r, v, p].where[pyr[v]])
                * obj_crfd[r, v, p, cur]
                / obj_diviii[r, v, p]
            )
            vdisc[...] = 1 + g_drate[r, v, cur]
            z[...] = Round(NCAP_DECLIF[r, v, p]) - 1
            par_objdec[r, v, Y, p, cur] = Sum(
                Domain(ObjSumiii[r, v, p, KEoh, k, ll], Yk[ll + z, Y]).where[Yk[Y, ll]],
                f
                * macro.obj_dcost_GP(r, k, p, cur)
                * obj_disc[r, ll, cur]
                * vdisc ** (yearval[ll] - yearval[Y]),
            )
