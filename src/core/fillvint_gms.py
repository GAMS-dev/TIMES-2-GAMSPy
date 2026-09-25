# fillvint_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILLVINT : Optional weighting of vintaged attributes
# *   arg1 - table name
# *   arg2 - Control set 1
# *   arg3 - Control set 2
# *   arg4 - Name for temporary cache
# *******************************************************************************

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Alias, Loop, Parameter, Set, sparse
from gamspy.math import Max, Min

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class FillvintGmsConfig:
    arg1: Parameter | None = None
    arg2: Set | Alias | None = None
    arg3: tuple[Set | Alias, ...] | None = None
    arg4: str | None = None


class FillvintGms(GamsClass):
    """Translation unit for fillvint.gms."""

    # Instance attributes
    module_name: str = "fillvint_gms"
    gams_source: str = "fillvint.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: FillvintGmsConfig,
        init: bool = False,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.init = init
        self.compile()

    def compile(self) -> None:
        cc = self.config
        g = self.tc
        m = g.container

        if self.init and self.env.vintopt == "2":
            self.tc.register_assignment(g.PrcSimv)

        prc_simv_defined = self.tc.defined("PRC_SIMV")
        if self.init:
            self.tc.enqueue(
                self.initialization,
                vintopteq2=self.env.vintopt == "2",
                prc_simv_defined=prc_simv_defined,
            )
        else:  # fill
            arg1, arg2, arg3, arg4 = cc.arg1, cc.arg2, cc.arg3, cc.arg4
            if arg1 is None or arg2 is None or arg3 is None or arg4 is None:
                raise ValueError("arg1 through arg4 must not be None in fill mode.")

            param = Parameter(m, name=arg4, domain=[arg2, *arg3, g.allyear])
            g.set_parameter(name=arg4, parameter=param)
            g.enqueue(
                self.fill,
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=param,
                prc_simv_defined=prc_simv_defined,
            )

    def initialization(
        self: FillvintGms, vintopteq2: bool, prc_simv_defined: bool
    ) -> None:
        # Initialization
        g = self.tc
        prc_ymin = g.prc_ymin
        PrcMap = g.PrcMap
        pastsum = g.pastsum
        PrcSimv = g.PrcSimv
        PrcVint = g.PrcVint
        r, p, t, ll, v, lead = g.r, g.p, g.t, g.ll, g.v, g.lead
        Rvp, Rtp = g.Rvp, g.Rtp

        prc_ymin.setRecords(None)
        pastsum.setRecords(None)
        if vintopteq2:
            PrcSimv[PrcVint[r, p]] = ~PrcMap[r, "STG", p]

        if prc_simv_defined:
            PrcSimv[r, p].where[PrcMap[r, "STG", p]] = False
            PrcVint[PrcSimv] = True

        # Make sure that all PrcVint have first leading v in Rtp:
        with Loop(t[ll]):
            Rvp[r, v[ll - lead[t]], p].where[
                (~Rvp[r, v, p]).where[Rvp[r, t, p].where[PrcVint[r, p]]]
            ] = True

        if prc_simv_defined:
            Rtp[Rvp[r, v, p]] = sparse(PrcSimv[r, p])

    def fill(
        self: FillvintGms,
        arg1: Parameter,
        arg2: Set | Alias,
        arg3: tuple[Set | Alias, ...],
        arg4: Parameter,
        prc_simv_defined: bool,
    ) -> None:
        g = self.tc
        r, t, p, d, b = g.r, g.t, g.p, g.d, g.b
        pastsum, Rtp = g.pastsum, g.Rtp
        PrcVint, PrcSimv = g.PrcVint, g.PrcSimv
        yearval, lead = g.yearval, g.lead
        ncap_iled, ncap_tlife = g.ncap_iled, g.ncap_tlife
        Trackp = g.Trackp

        if len(pastsum) == 0:
            pastsum[Rtp[r, t, p]].where[PrcVint[r, p]] = Min(
                1,
                (
                    Max(
                        yearval[t] - (lead[t] - 1) / 2,
                        b[t]
                        + Max(
                            ncap_iled[Rtp],
                            (d[t] + ncap_iled[Rtp] - ncap_tlife[Rtp]) / 2,
                        ),
                    )
                    - (yearval[t] - lead[t])
                )
                / lead[t],
            )

        Trackp[PrcVint] = True
        if prc_simv_defined:
            Trackp[PrcSimv] = False

        # Weighted average of vintages t and t-1
        ll, v = g.ll, g.v

        with Loop((t[ll], v[ll - lead[ll]])):  # type: ignore[arg-type]
            arg4[arg2, *arg3, t].where[arg1[arg2, t, *arg3].where[Trackp[r, p]]] = arg1[
                arg2, t, *arg3
            ] * pastsum[r, t, p] + arg1[arg2, v, *arg3] * (1 - pastsum[r, t, p])

        arg1[arg2, t, *arg3] = sparse(arg4[arg2, *arg3, t])

        arg4.setRecords(None)
        Trackp.setRecords(None)
