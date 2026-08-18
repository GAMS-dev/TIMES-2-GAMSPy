# prep_ext_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.stc oversees all the added inperpolation activities needed by STC  *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Card, Domain, Loop, Number, Parameter, SpecialValues, Sum, sparse
from gamspy.math import project

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.prepparm_gms import PrepparmGms, PrepparmGmsConfig
from core.recurrin_stc import RecurrinStc

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtStc(GamsClass):
    """Translation unit for prep_ext.stc."""

    # Instance attributes
    module_name: str = "prep_ext_stc"
    gams_source: str = "prep_ext.stc"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc

        r, p, bd, j, ww, allr, ucn = g.r, g.p, g.bd, g.j, g.ww, g.allr, g.ucn
        c, cur, lA, ts, Milestonyr = g.c, g.cur, g.lA, g.ts, g.Milestonyr

        exclude_list = ["S_DAM_COST", "S_FLO_FUNC", "S_NCAP_AFS", "S_COM_FR"]
        # fmt: off
        batincludes: list[FillparmGmsConfig] = [
            FillparmGmsConfig(g.s_com_proj,  (g.r,), (g.c,g.j,g.ww),                    ("0",) * 3, g.Milestonyr, Number(1), Number(0)),
            FillparmGmsConfig(g.s_com_tax,   (g.r,), (g.c,g.s,g.comvar,g.cur,g.j,g.ww), (),         g.Milestonyr, Number(1), Number(0)),
            FillparmGmsConfig(g.s_ncap_cost, (g.r,), (g.p,g.j,g.ww),                    ("0",) * 3, g.Milestonyr, Number(1), Number(0)),
        ]
        # fmt: on

        for config in batincludes:
            if config.arg1.name in exclude_list and not self.tc.defined(config.arg1):
                continue
            self.include(FillparmGms(self.tc, self.env, config))

        prepparms: list[PrepparmGmsConfig] = [
            PrepparmGmsConfig(
                arg1="S_CAP_BND",
                arg2=(r,),
                arg3=(p, bd, j, ww),
                arg4=("0",),
                arg5=Milestonyr,
                arg6=g.Rtp[r, Milestonyr, p],
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="S_UC_RHSRT",
                arg2=(allr, ucn),
                arg3=(lA, j, ww),
                arg4=("0",),
                arg5=Milestonyr,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="S_UC_RHSRTS",
                arg2=(allr, ucn),
                arg3=(ts, lA, j, ww),
                arg4=(),
                arg5=Milestonyr,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="S_UC_RHST",
                arg2=(ucn,),
                arg3=(lA, j, ww),
                arg4=("0", "0"),
                arg5=Milestonyr,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="S_UC_RHSTS",
                arg2=(ucn,),
                arg3=(ts, lA, j, ww),
                arg4=("0",),
                arg5=Milestonyr,
                arg6=Number(1),
                arg7=1,
            ),
            PrepparmGmsConfig(
                arg1="S_DAM_COST",
                arg2=(r,),
                arg3=(c, cur, j, ww),
                arg4=("0",),
                arg5=Milestonyr,
                arg6=Number(1),
                arg7=SpecialValues.EPS,
                arg8=3,
            ),
        ]

        for prepparms_config in prepparms:
            if prepparms_config.arg1 in exclude_list and not self.tc.defined(
                prepparms_config.arg1
            ):
                continue
            self.include(PrepparmGms(self.tc, self.env, config=prepparms_config))

        # fmt: off
        batincludes = [
            FillparmGmsConfig(g.s_flo_func,  (g.r,), (g.p, g.cg, g.cg2, g.j, g.ww), ("0",) * 1, g.Milestonyr, Number(1), Number(0)),
            FillparmGmsConfig(g.s_ncap_afs,  (g.r,), (g.p, g.ts, g.j,   g.ww),      ("0",) * 2, g.Milestonyr, Number(1), Number(0)),
            FillparmGmsConfig(g.s_com_fr,    (g.r,), (g.c, g.ts, g.j,   g.ww),      ("0",) * 2, g.Milestonyr, Number(1), Number(0)),
        ]
        # fmt: on
        for config in batincludes:
            if config.arg1.name in exclude_list and not self.tc.defined(config.arg1):
                continue
            self.include(FillparmGms(self.tc, self.env, config))

        self.include(RecurrinStc(self.tc, self.env, arg1="MXPAR"))

        m = g.container
        if self.tc.defined(g.s_dam_cost) and not self.tc.defined(g.dam_cost):
            g.dam_cost = Parameter(m, name="DAM_COST")
        if self.tc.defined(g.dam_cost) and not self.tc.defined(g.s_dam_cost):
            g.s_dam_cost = Parameter(m, name="S_DAM_COST")

        self.tc.enqueue(
            self.prep_ext_stc_exec,
            have_s_flo_func=self.tc.defined("S_FLO_FUNC"),
        )

    def prep_ext_stc_exec(self: PrepExtStc, have_s_flo_func: bool) -> None:
        g = self.tc
        # * commodities involved in CUM constraints
        g.s_com_cum[
            g.r,
            "NET",
            g.allyear[g.bohyear + g.beoh[g.bohyear]],
            g.ll[g.eohyear + g.beoh[g.eohyear]],
            g.c,
            g.bd,
            g.j,
            g.ww,
        ] = sparse(g.s_com_cumnet[g.r, g.bohyear, g.eohyear, g.c, g.bd, g.j, g.ww])
        g.s_com_cum[
            g.r,
            "PRD",
            g.allyear[g.bohyear + g.beoh[g.bohyear]],
            g.ll[g.eohyear + g.beoh[g.eohyear]],
            g.c,
            g.bd,
            g.j,
            g.ww,
        ] = sparse(g.s_com_cumprd[g.r, g.bohyear, g.eohyear, g.c, g.bd, g.j, g.ww])
        g.s_com_cumprd.setRecords(None)
        g.s_com_cumnet.setRecords(None)
        g.s_com_cum[g.r, g.comvar, g.allyear, g.ll, g.c, "LO", g.j, g.ww].where[
            (
                (
                    g.s_com_cum[g.r, g.comvar, g.allyear, g.ll, g.c, "LO", g.j, g.ww]
                    == 0.0
                ).where[
                    g.s_com_cum[g.r, g.comvar, g.allyear, g.ll, g.c, "LO", g.j, g.ww]
                ]
            )
        ] = 0.0
        g.RcCumcom[g.r, g.comvar, g.allyear, g.ll, g.c] = sparse(
            Sum(
                Domain(g.bd, g.j, g.ww).where[
                    g.s_com_cum[g.r, g.comvar, g.allyear, g.ll, g.c, g.bd, g.j, g.ww]
                ],
                True,
            )  # type: ignore
        )
        with Loop(
            Domain(g.r, g.t, g.c, g.s, g.comvar, g.cur, g.j, g.ww).where[
                g.s_com_tax[g.r, g.t, g.c, g.s, g.comvar, g.cur, g.j, g.ww]
            ]
        ):
            g.uc_com["OBJ1", g.comvar, "LHS", g.r, "0", g.c, g.Annual, "UCN"] = 1.0
        # * collect transformation tuples
        if have_s_flo_func:
            project(source=g.s_flo_func, target=g.RpFfsgg, direction="left")
        # * Activate capacity variables if S_CAP_BND is specified
        with Loop(
            Domain(g.r, g.t, g.p, g.bd, g.j, g.ww).where[
                g.s_cap_bnd[g.r, g.t, g.p, g.bd, g.j, g.ww]
            ]
        ):
            g.RtpVarp[g.r, g.t, g.p] = True
        # * Set flags for Phased UC_N
        g.UcRSum[g.r, "OBJZ"] = True
        g.UcREach[g.r, "OBJZ"] = True
        g.UcRSum[g.r, "OBJ1"] = True
        g.UcTSum[g.r, "OBJZ", g.t] = True
        g.UcTSum[g.r, "OBJ1", g.Miyr1] = True
        with Loop(Domain(g.ucn, g.ww).where[g.s_ucobj[g.ucn, g.ww]]):
            g.uc_rhs[g.ucn, "N"].where[(~(g.uc_rhs[g.ucn, "N"]))] = -1.0
        # * Initialize SW_PARM
        g.sw_parm[...] = (
            Card(g.s_com_proj)
            + Card(g.s_cap_bnd)
            + Card(g.s_com_cumprd)
            + Card(g.s_com_cumnet)
        )
        g.sw_parm[...] = g.sw_parm + Card(g.s_cm_const) + Card(g.s_cm_maxc)
        # * Set flag for detemininstic RHS if none set but is set for some SOW
        g.uc_rhs[g.ucn, "UP"].where[
            (
                (~(g.uc_rhs[g.ucn, "UP"])).where[
                    Sum(
                        Domain(g.lim, g.j, g.ww).where[
                            g.s_uc_rhs[g.ucn, g.lim, g.j, g.ww]
                        ],
                        1.0,
                    )
                ]
            )
        ] = SpecialValues.POSINF
        g.uc_rhsr[g.r, g.ucn, "UP"].where[
            (
                (~(g.uc_rhsr[g.r, g.ucn, "UP"])).where[
                    Sum(
                        Domain(g.lim, g.j, g.ww).where[
                            g.s_uc_rhsr[g.r, g.ucn, g.lim, g.j, g.ww]
                        ],
                        1.0,
                    )
                ]
            )
        ] = SpecialValues.POSINF
        g.uc_rhst[g.ucn, g.t, "UP"].where[
            (
                (~(g.uc_rhst[g.ucn, g.t, "UP"])).where[
                    Sum(
                        Domain(g.lim, g.j, g.ww).where[
                            g.s_uc_rhst[g.ucn, g.t, g.lim, g.j, g.ww]
                        ],
                        1.0,
                    )
                ]
            )
        ] = SpecialValues.POSINF
        g.uc_rhsrt[g.r, g.ucn, g.t, "UP"].where[
            (
                (~(g.uc_rhsrt[g.r, g.ucn, g.t, "UP"])).where[
                    Sum(
                        Domain(g.lim, g.j, g.ww).where[
                            g.s_uc_rhsrt[g.r, g.ucn, g.t, g.lim, g.j, g.ww]
                        ],
                        1.0,
                    )
                ]
            )
        ] = SpecialValues.POSINF
        g.uc_rhsts[g.ucn, g.t, g.s, "UP"].where[
            (
                (~(g.uc_rhsts[g.ucn, g.t, g.s, "UP"])).where[
                    Sum(
                        Domain(g.lim, g.j, g.ww).where[
                            g.s_uc_rhsts[g.ucn, g.t, g.s, g.lim, g.j, g.ww]
                        ],
                        1.0,
                    )
                ]
            )
        ] = SpecialValues.POSINF
        g.uc_rhsrts[g.r, g.ucn, g.t, g.s, "UP"].where[
            (
                (~(g.uc_rhsrts[g.r, g.ucn, g.t, g.s, "UP"])).where[
                    Sum(
                        Domain(g.lim, g.j, g.ww).where[
                            g.s_uc_rhsrts[g.r, g.ucn, g.t, g.s, g.lim, g.j, g.ww]
                        ],
                        1.0,
                    )
                ]
            )
        ] = SpecialValues.POSINF
        g.UcDynbnd["OBJ1", "N"] = True
