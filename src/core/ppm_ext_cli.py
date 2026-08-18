# ppm_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PPM_ext.abs oversees preliminary preprocessing activity needed by CLI
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Else, If, Loop, Number, Ord, Set, Sum, set_options, sparse
from gamspy.math import project

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmExtCli(GamsClass):
    """Translation unit for ppm_ext.cli."""

    # Instance attributes
    module_name: str = "ppm_ext_cli"
    gams_source: str = "ppm_ext.cli"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        self.comp1()
        self.tc.enqueue(self.user_defined_emissions)

        # * Interpolation/extrapolation
        self.env.set_scoped("reset", 0)
        self.include(
            FillparmGms(
                self.tc,
                self.env,
                FillparmGmsConfig(
                    arg1=g.cm_couple,
                    arg2=(g.cg1,),
                    arg3=(g.cg, g.cmq),
                    arg4=("0",) * 4,
                    arg5=g.t,
                    arg6=Number(1),
                    arg7=Number(0),
                ),
            )
        )

        self.tc.enqueue(self.statistic_mappings)

    def comp1(self: PpmExtCli) -> None:
        g = self.tc
        m = g.container

        # Additional declarations
        g.CmUsubs = Set(m, name="CM_USUBS", domain=[g.cmitem])
        g.CmCoupmap = Set(m, name="CM_COUPMAP", domain=[g.cmitem, g.cmitem, g.cmq])
        g.CmRebox = Set(
            m,
            name="CM_REBOX",
            domain=[g.cmq, g.cmq],
            records=[("CM-ATM", "ATM"), ("CM-UP", "UP"), ("CM-LO", "LO")],
        )

    def user_defined_emissions(self: PpmExtCli) -> None:
        g = self.tc
        (
            cm_ghgmap,
            r,
            Com,
            c,
            ire_ccvt,
            CmUsubs,
            cmitem,
            Rc,
            cm_ppm,
            uncd1,
            CmHists,
            CmEmis,
            cm_couple,
            cg,
            ll,
            Uncd7,
            lim,
            cmq,
            lA,
            year,
            CmVar,
            CmCoupmap,
            cm_decay,
            t,
            cm_stat0,
        ) = (
            g.cm_ghgmap,
            g.r,
            g.Com,
            g.c,
            g.ire_ccvt,
            g.CmUsubs,
            g.cmitem,
            g.Rc,
            g.cm_ppm,
            g.uncd1,
            g.CmHists,
            g.CmEmis,
            g.cm_couple,
            g.cg,
            g.ll,
            g.Uncd7,
            g.lim,
            g.cmq,
            g.lA,
            g.year,
            g.CmVar,
            g.CmCoupmap,
            g.cm_decay,
            g.t,
            g.cm_stat0,
        )
        # Add user-defined emissions
        cm_ghgmap[r, Com, c].where[~cm_ghgmap[r, Com, c]] = sparse(
            ire_ccvt[r, Com, r, c]
        )
        CmUsubs[cmitem].where[Sum(Rc[r, Com].where[cm_ghgmap[r, Com, cmitem]], 1)] = (
            cm_ppm[cmitem]
        )
        uncd1.setRecords(None)
        uncd1[CmUsubs] = CmHists[CmUsubs]
        CmHists[CmUsubs] = True
        CmEmis[CmUsubs] = True

        # Prepare coupled agents
        cm_couple[cg, ll, cmitem, "ATM"] = 0
        Uncd7[cg, ll.lag(Ord(ll), "circular"), cmitem, lim[cmq], "", "", ""].where[
            cm_couple[cg, ll, cmitem, cmq]
        ] = True

        set_options({"VALIDATION": 0})
        with Loop(Uncd7[cg, ll, cmitem, lA["N"], "", "", ""]):
            with If(CmEmis[cg]):  # type: ignore[arg-type]
                cm_couple[cg, year, cmitem, "ATM"] = sparse(
                    cm_couple[cg, year, cmitem, lA]
                )
            with Else():  # type: ignore[no-untyped-call] # noqa: SIM117
                with Loop(
                    Domain(Rc[r, c[cg]], CmVar).where[
                        cm_ghgmap[r, c, CmVar] & CmEmis[CmVar]
                    ]
                ):
                    cm_couple[CmVar, year, cmitem, "ATM"] = sparse(
                        cm_couple[cg, year, cmitem, lA]
                    )
                    cm_couple[CmVar, year, cmitem, cmq] = sparse(
                        cm_couple[cg, year, cmitem, cmq]
                    )
        set_options({"VALIDATION": 0})

        project(source=cm_couple, target=CmCoupmap, direction="left")
        cm_couple[cg, ll, cmitem, "N"] = 0
        cm_couple[cg, ll, cmitem, cmq].where[~CmCoupmap[cg, cmitem, "ATM"]] = 0
        project(source=CmCoupmap, target=CmUsubs)
        with Loop(CmUsubs[cmitem]):
            cm_ppm[cmitem].where[~cm_ppm[cmitem]] = 1
            cm_stat0[cmitem, "LIFE"].where[~cm_stat0[cmitem, "LIFE"]] = 1
            with If(~(uncd1[cmitem] | cm_decay[cmitem, "ATM"])):
                cm_decay[cmitem, "ATM"] = 1
                cm_couple[CmVar, t, cmitem, "FX"].where[
                    CmCoupmap[CmVar, cmitem, "ATM"]
                ] = 1
            CmEmis[cmitem] = True

    def statistic_mappings(self: PpmExtCli) -> None:
        g = self.tc
        (
            cm_stats,
            CmHists,
            ll,
            CmBox,
            cm_stat0,
            CmVar,
            cm_decay,
            uncd1,
            cm_linfor,
            CmUsubs,
            CmForcmap,
            CmEmis,
            CmOfor,
        ) = (
            g.cm_stats,
            g.CmHists,
            g.ll,
            g.CmBox,
            g.cm_stat0,
            g.CmVar,
            g.cm_decay,
            g.uncd1,
            g.cm_linfor,
            g.CmUsubs,
            g.CmForcmap,
            g.CmEmis,
            g.CmOfor,
        )
        # Statistics mappings
        cm_stats[CmHists, ll, "ATM"] = sparse(cm_stats[CmHists, ll, "N"])
        cm_stats["FORCING", ll, CmBox] = sparse(cm_stats["DELTA", ll, CmBox])
        cm_stat0[CmVar, "LIFE"].where[
            (cm_decay[CmVar, "UP"] > 0) & cm_decay[CmVar, "UP"]
        ] = 1 / cm_decay[CmVar, "UP"]

        # Add missing forcings if functions defined
        uncd1.setRecords(None)
        project(source=cm_linfor, target=CmUsubs)
        uncd1[CmUsubs] = True
        project(source=CmForcmap, target=CmUsubs)
        CmUsubs[CmEmis] = ~CmUsubs[CmEmis]
        CmUsubs[CmUsubs] = uncd1[CmUsubs]
        CmUsubs["CO2-GTC"] = False
        CmForcmap[CmUsubs, CmUsubs] = True
        CmOfor[CmUsubs] = True
