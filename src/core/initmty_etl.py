# initmty_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# ******************************************************************************
# * INITMTY.ETL - declarations for technological change                        *
# ******************************************************************************
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyEtl(GamsClass):
    """Translation unit for initmty.etl."""

    # Instance attributes
    module_name: str = "initmty_etl"
    gams_source: str = "initmty.etl"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # OPTCR from default 0.1 to 0.000001, may want to adjust in *.RUN file
        self.tc.enqueue(self.exec1)

        # Input data
        self.env.set_scoped("etl", "YES")
        g.Teg = Set(m, name="TEG", domain=[g.prc])
        g.tl_sc0 = Parameter(m, name="TL_SC0", domain=[g.r, g.prc])
        g.tl_prat = Parameter(m, name="TL_PRAT", domain=[g.r, g.prc])
        g.tl_seg = Parameter(m, name="TL_SEG", domain=[g.r, g.prc])
        g.tl_ccap0 = Parameter(m, name="TL_CCAP0", domain=[g.r, g.prc])
        g.tl_ccapm = Parameter(m, name="TL_CCAPM", domain=[g.r, g.prc])
        # Cluster technologies: TEG plus PRC coupled to TEG, mapping and coupling factors
        g.tl_cluster = Parameter(m, name="TL_CLUSTER", domain=[g.r, g.p, g.p])
        g.tl_mrclust = Parameter(m, name="TL_MRCLUST", domain=[g.r, g.p, g.r, g.p])
        # Input aliases
        g.sc0 = Parameter(m, name="SC0", domain=[g.r, g.prc])
        g.prat = Parameter(m, name="PRAT", domain=[g.r, g.prc])
        g.seg = Parameter(m, name="SEG", domain=[g.r, g.prc])
        g.ccap0 = Parameter(m, name="CCAP0", domain=[g.r, g.prc])
        g.ccapm = Parameter(m, name="CCAPM", domain=[g.r, g.prc])
        g.cluster = Parameter(m, name="CLUSTER", domain=[g.r, g.p, g.p])

        # Internal parameters
        # KP up to 6 as default, can be re-assigned in *.RUN file if desired
        g.kp = Set(m, name="KP", records=range(1, 7))

        g.kp2 = Alias(container=self.tc.container, name="KP2", alias_with=g.kp)

        g.pat = Parameter(m, name="PAT", domain=[g.r, g.prc])
        g.pbt = Parameter(m, name="PBT", domain=[g.r, g.prc])
        g.ccost0 = Parameter(m, name="CCOST0", domain=[g.r, g.prc])
        g.ccostm = Parameter(m, name="CCOSTM", domain=[g.r, g.prc])
        g.weig = Parameter(m, name="WEIG", domain=[g.r, g.kp, g.prc])
        g.ccostk = Parameter(m, name="CCOSTK", domain=[g.r, g.kp, g.prc])
        g.ccapk = Parameter(m, name="CCAPK", domain=[g.r, g.kp, g.prc])
        g.beta = Parameter(m, name="BETA", domain=[g.r, g.kp, g.prc])
        g.alph = Parameter(m, name="ALPH", domain=[g.r, g.kp, g.prc])
        g.ntchteg = Parameter(
            m,
            name="NTCHTEG",
            domain=[g.r, g.prc],
            description="Number of technologies in cluster",
        )
        # report specific
        g.invc_unit = Parameter(m, name="INVC_UNIT", domain=[g.r, g.t, g.p])
        g.prev = Parameter(m, name="PREV", domain=[g.r, g.prc])
        # Starting periods for learning technologies
        g.tl_start = Set(m, name="TL_START", domain=[g.r, g.t, g.p])
        # sets of cluster2 technologies and key components
        g.tl_rp_ct = Set(m, name="TL_RP_CT", domain=[g.Reg, g.prc])
        g.tl_rp_kc = Set(m, name="TL_RP_KC", domain=[g.Reg, g.prc])
        # SET and parameter Declarations for LIC Reporting Module
        g.tl_ct_cost = Parameter(
            m, name="TL_CT_COST", domain=[g.r, g.allyear, g.prc, g.cur]
        )
        # =====================================================*
        #  ETL Iteration parameters used during TESTing        *
        # =====================================================*
        #  new SET MLITER (1*1 default) to enable iterative SOLVE, can be re-assigned in RUN
        g.mliter = Set(m, name="MLITER", records=[1])
        # default MLITERM in RUN
        g.mliterm = Parameter(m, "MLITERM", records=10.0)
        # CCDIFCRIT is termination criterion for average difference in CCAPM - CCAP(TLAST)
        #  or for CCAPM values in two subsequent iterations, now set to 0.1
        g.ccdifcrit = Parameter(m, "CCDIFCRIT", records=0.1)

    def exec1(self: InitmtyEtl) -> None:
        self.tc.solve_options.relative_optimality_gap = 0.000001
