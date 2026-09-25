# wrtbprice_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================
# * Saving shadow prices of commodity balances to be used as base prices
# * for elastic demands into gdx files com_bprice.gdx & <RUN_NAME>_DP.dgx
# *==============================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Parameter, Set, SpecialValues, Sum

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class WrtbpriceMod(GamsClass):
    """Translation unit for wrtbprice.mod."""

    module_name: str = "wrtbprice_mod"
    gams_source: str = "wrtbprice.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        r, year, cur, Reg, allyear, Com, allts, UcCost, item = (
            g.r,
            g.year,
            g.cur,
            g.Reg,
            g.allyear,
            g.Com,
            g.allts,
            g.UcCost,
            g.item,
        )

        g.dinv = Parameter(m, name="DINV", domain=[r, year, cur])
        if not g.defined("SOL_BPRICE"):
            g.sol_bprice = Parameter(
                m, name="SOL_BPRICE", domain=[Reg, allyear, Com, allts, cur]
            )
        g.sol_acfr = Parameter(m, name="SOL_ACFR", domain=[r, UcCost, year])
        g.Ancat = Set(
            m,
            name="ANCAT",
            domain=[UcCost, item],
            records=[
                ("COST", "INV"),
                ("COST", "FIX"),
                ("COST", "VAR"),
                ("COST", "DAM"),
                ("TAX", "INVX"),
                ("TAX", "FIXX"),
                ("TAX", "VARX"),
            ],
        )

        self.tc.enqueue(
            self.exec_wrtbprice_mod,
            stages=self.env.stages,
            anncost=self.env.anncost,
            gdxpath=self.env.gdxpath,
            run_name=self.env.run_name,
            dam_elast_defined=self.tc.defined("DAM_ELAST"),
            dam_cost_defined=self.tc.defined("DAM_COST"),
        )

    def exec_wrtbprice_mod(
        self: WrtbpriceMod,
        stages: str,
        anncost: str,
        gdxpath: str,
        run_name: str,
        dam_elast_defined: bool,
        dam_cost_defined: bool,
    ) -> None:
        g = self.tc
        m = g.container
        (
            r,
            t,
            cur,
            GRcur,
            coef_pvt,
            c,
            s,
            RcsCombal,
            Dem,
            eqg_combal,
            eqe_combal,
            dinv,
            sol_bprice,
        ) = (
            g.r,
            g.t,
            g.cur,
            g.GRcur,
            g.coef_pvt,
            g.c,
            g.s,
            g.RcsCombal,
            g.Dem,
            g.eqg_combal,
            g.eqe_combal,
            g.dinv,
            g.sol_bprice,
        )

        (
            dam_coef,
            dam_tvoc,
            RtcsVarc,
            Trackc,
            eqe_comprd,
            Rtc,
            VAR_COMPRD,
            rb,
            ComTs,
            Rdcur,
            com_fr,
            com_proj,
        ) = (
            g.dam_coef,
            g.dam_tvoc,
            g.RtcsVarc,
            g.Trackc,
            g.eqe_comprd,
            g.Rtc,
            g.VAR_COMPRD,
            g.rb,
            g.ComTs,
            g.Rdcur,
            g.com_fr,
            g.com_proj,
        )

        # Undiscounting via matrix inversion currently disabled; using direct method
        dinv[r, t, cur].where[GRcur[r, cur]] = 1 / coef_pvt[r, t]
        sol_bprice[r, t, c, s, cur].where[RcsCombal[r, t, c, s, "LO"] & Dem[r, c]] = (
            dinv[r, t, cur] * eqg_combal[r, t, c, s].m
        )
        sol_bprice[r, t, c, s, cur].where[RcsCombal[r, t, c, s, "FX"] & Dem[r, c]] = (
            dinv[r, t, cur] * eqe_combal[r, t, c, s].m
        )

        # Check elastic supply curve requests
        if dam_elast_defined:
            Trackc, Rc, dam_bqty, dam_elast = g.Trackc, g.Rc, g.dam_bqty, g.dam_elast
            Trackc[Rc].where[~dam_bqty[Rc] & dam_elast[Rc, "N"]] = True

        if dam_cost_defined:
            r, t, c, cur, dam_cost, Trackc = g.r, g.t, g.c, g.cur, g.dam_cost, g.Trackc
            with Loop(Domain(r, t, c, cur).where[dam_cost[r, t, c, cur]]):
                Trackc[r, c] = False

        dam_coef.setRecords(None)
        dam_tvoc.setRecords(None)
        dam_coef[RtcsVarc[r, t, c, s]].where[Trackc[r, c]] = (
            eqe_comprd[r, t, c, s].m / coef_pvt[r, t] + SpecialValues.EPS
        )
        dam_tvoc[Rtc[r, t, c], "N"].where[Trackc[r, c]] = Sum(
            RtcsVarc[Rtc, s], dam_coef[Rtc, s] * VAR_COMPRD[Rtc, s].l
        )

        # Save also annual cost to expenditure ratios for TIMES CGE calibration
        rb[r, t] = (
            Sum(
                Domain(ComTs[Dem[r, c], s], Rdcur[r, cur]),
                sol_bprice[r, t, c, s, cur] * com_fr[r, t, c, s] * com_proj[r, t, c],
            )
            + 1
            - 1
        )

        if stages.upper() != "YES" and anncost.upper() == "LEV":
            r, UcCost, t, rb, Sysucmap, sysuc, item, reg_acost, Ancat, sol_acfr = (
                g.r,
                g.UcCost,
                g.t,
                g.rb,
                m["SYSUCMAP"],
                g.sysuc,
                g.item,
                g.reg_acost,
                g.Ancat,
                g.sol_acfr,
            )
            assert isinstance(Sysucmap, Set)
            sol_acfr[r, UcCost, t].where[rb[r, t]] = (
                Sum(
                    Sysucmap[sysuc, item].where[Ancat[UcCost, item]],
                    reg_acost[r, t, sysuc],
                )
                / rb[r, t]
            )

        rb.setRecords(None)
        Trackc.setRecords(None)

        m.write(
            "com_bprice",
            symbol_names=["SOL_BPRICE", "DAM_COEF", "DAM_TVOC", "SOL_ACFR"],
        )
        m.write(
            f"{gdxpath}{run_name}_DP",
            symbol_names=["SOL_BPRICE", "DAM_COEF", "DAM_TVOC", "SOL_ACFR"],
        )
