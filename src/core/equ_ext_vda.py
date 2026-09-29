# equ_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQMAIN.EXT declarations & call for actual equations
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Equation, Parameter, Set, Sum

from core.base_class import GamsClass
from core.bnd_ire_vda import BndIreVda
from core.eqactups_vda import EqactupsVda
from core.eqashar_vda import EqasharVda, EqasharVdaConfig
from core.eqcaflac_vda import EqcaflacVda
from core.eqlducs_vda import EqlducsVda
from core.equcrtp_vda import EqucrtpVda, EqucrtpVdaConfig
from core.powerflo_vda import PowerfloVda
from core.pp_actef_vda import PpActefVda
from core.resloadc_vda import ResloadcVda
from core.ucbet_vda import UcbetVda
from core.utils import apply_sw_stvars
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._algebra.condition import Condition

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass
logger = logging.getLogger(__name__)


class EquExtVda(GamsClass):
    """Translation unit for equ_ext.vda."""

    # Instance attributes
    module_name: str = "equ_ext_vda"
    gams_source: str = "equ_ext.vda"

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
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc
        if self.arg1.upper() != "DECLR":  # L11: GOTO VDA
            pass
        else:
            self.equations(eq=self.env.eq, swtd=self.env.swtd_GP, swd=self.env.swd_GP)
            if self.tc.defined("PREMILE"):
                self.include(BndIreVda(self.tc, self.env))
            return
        self.env.set_scoped("vas", self.env.var)
        if self.env.stages == "YES":
            apply_sw_stvars(env=self.env, g=self.tc)
        self.env.set_scoped(
            "upscap0", f"({macro.upscaps.render()}$PRC_TS(R,P,S))$RP_UPL(R,P,'FX')"
        )
        self.env.set_scoped(
            "upscap0_GP",
            macro.upscaps.render_GP().where[
                g.PrcTs[g.r, g.p, g.s] & g.RpUpl[g.r, g.p, "FX"]
            ],
        )

        r, ll, t, p, tsl, ips, lA = g.r, g.ll, g.t, g.p, g.tsl, g.ips, g.lA

        m = g.container
        g.dp_uns = Parameter(
            m,
            name="DP_UNS",
            domain=[r, ll, t, p, tsl, ips, lA],
        )

        self.tc.enqueue(self.define_param_dp_uns)
        #         *-----------------------------------------------------------------------------
        # * Call for Implementations
        # *-----------------------------------------------------------------------------
        # * Activity Efficiency Transformation
        self.include(PpActefVda(self.tc, self.env))
        # * Capacity-activity equations:
        eqcaflac_bat_includes: list[
            tuple[
                Literal["E", "N", "L", "G"],
                str,
                str,
                Sum
                | Condition
                | Expression
                | tuple[Set | Alias | str, ...]
                | tuple[()],
            ]
        ] = [
            ("E", "FX", "$", self.env.mx_GP),
            ("L", "UP", "*", self.env.mx_GP),
        ]
        for args in eqcaflac_bat_includes:
            self.include(
                EqcaflacVda(
                    self.tc,
                    self.env,
                    arg1=args[0],
                    arg2=args[1],
                    arg3=args[2],
                    arg4=args[3],
                )
            )
        self.include(EqactupsVda(self.tc, self.env, arg1=self.env.mx_GP))
        self.include(EqlducsVda(self.tc, self.env, arg1="EQU"))

        # * ASHAR equations:
        eqashar_batinclude: list[EqasharVdaConfig] = [
            EqasharVdaConfig(sense="E", arg2="FX"),
            EqasharVdaConfig(sense="L", arg2="LO"),
            EqasharVdaConfig(sense="G", arg2="UP"),
        ]
        for eqashar_config in eqashar_batinclude:
            self.include(EqasharVda(self.tc, self.env, config=eqashar_config))

        # * UCBET equations
        if self.tc.defined("UC_FLOBET"):
            self.include(UcbetVda(self.tc, self.env))
        if self.tc.defined("COM_CSTBAL"):
            self.include(PowerfloVda(self.tc, self.env, arg1="OBJBAL"))
        if self.env.powerflo.upper() == "YES":
            self.include(PowerfloVda(self.tc, self.env, arg1="POWFLO"))
        if self.tc.defined("GR_VARGEN"):
            self.include(ResloadcVda(self.tc, self.env, arg1="EQUA"))

        # * EQUCRTP equations
        equcrtp_batinclude: list[EqucrtpVdaConfig] = [
            EqucrtpVdaConfig(arg1="EQU_EXT", arg2="N", arg3="L", arg4=(g.Bdneq,)),
            EqucrtpVdaConfig(arg1="EQU_EXT", arg2="E", arg3="E", arg4=("FX",)),
        ]
        for config in equcrtp_batinclude:
            self.include(EqucrtpVda(self.tc, self.env, config=config))

    def equations(
        self: EquExtVda,
        eq: str,
        swtd: tuple[Set | Alias, ...] | tuple[()],
        swd: tuple[Set | Alias] | tuple[()],
    ) -> None:
        """
        *-----------------------------------------------------------------------------
        EQUATIONS
        *-----------------------------------------------------------------------------
        """
        g = self.tc
        m = g.container

        (
            r,
            ll,
            t,
            p,
            tsl,
            s,
            la,
            allsow,
            upt,
            bd,
            allyear,
            cg,
            io,
            comgrp,
            ucn,
            ucgrptype,
            comvar,
            c,
            ts,
            allr,
            item,
        ) = (
            g.r,
            g.ll,
            g.t,
            g.p,
            g.tsl,
            g.s,
            g.lA,
            g.allsow,
            g.upt,
            g.bd,
            g.allyear,
            g.cg,
            g.io,
            g.comgrp,
            g.ucn,
            g.ucgrptype,
            g.comvar,
            g.c,
            g.ts,
            g.allr,
            g.item,
        )

        # Activity efficiency equation
        g.set_equation(
            f"{eq}E_ACTEFF",
            Equation(
                m,
                name=f"{eq}E_ACTEFF",
                domain=[r, allyear, allyear, p, cg, io, s, *swtd],
                description="Process Activity Efficiency (=)",
            ),
        )

        # CAFLAC equations:
        g.set_equation(
            f"{eq}E_CAFLAC",
            Equation(
                m,
                name=f"{eq}E_CAFLAC",
                domain=[r, allyear, allyear, p, s, *swtd],
                description="Commodity based availability (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_CAFLAC",
            Equation(
                m,
                name=f"{eq}L_CAFLAC",
                domain=[r, allyear, allyear, p, s, *swtd],
                description="Commodity based availability (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}L_CAPFLO",
            Equation(
                m,
                name=f"{eq}L_CAPFLO",
                domain=[r, allyear, allyear, p, cg, s, *swtd],
                description="Flow-specific availability (=L=)",
            ),
        )

        # Advanced shares
        g.set_equation(
            f"{eq}E_ASHAR",
            Equation(
                m,
                name=f"{eq}E_ASHAR",
                domain=[r, allyear, allyear, p, cg, comgrp, s, *swtd],
                description="Advanced share constraint (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_ASHAR",
            Equation(
                m,
                name=f"{eq}L_ASHAR",
                domain=[r, allyear, allyear, p, cg, comgrp, s, *swtd],
                description="Advanced share constraint (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}G_ASHAR",
            Equation(
                m,
                name=f"{eq}G_ASHAR",
                domain=[r, allyear, allyear, p, cg, comgrp, s, *swtd],
                description="Advanced share constraint (=G=)",
            ),
        )

        # Dynamic bounds
        g.set_equation(
            f"{eq}N_UCRTP",
            Equation(
                m,
                name=f"{eq}N_UCRTP",
                domain=[ucn, r, t, p, ucgrptype, bd, *swtd],
                description="Dynamic process bound (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCRTP",
            Equation(
                m,
                name=f"{eq}E_UCRTP",
                domain=[ucn, r, t, p, ucgrptype, bd, *swtd],
                description="Dynamic process bound (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}N_UCRTC",
            Equation(
                m,
                name=f"{eq}N_UCRTC",
                domain=[ucn, comvar, r, t, c, ts, bd, *swtd],
                description="Dynamic commodity bound (=NE=)",
            ),
        )
        g.eqn_ucrtp = Equation(
            m,
            name="EQN_UCRTP",
            domain=[ucn, r, t, p, ucgrptype, bd],
            description="Dynamic process bound (=NE=)",
        )

        # Activity constraints
        g.set_equation(
            f"{eq}_CAPLOAD",
            Equation(
                m,
                name=f"{eq}_CAPLOAD",
                domain=[r, allyear, allyear, p, s, la, *swtd],
                description="Augmented capacity-activity",
            ),
        )
        g.set_equation(
            f"{eq}_ACTRAMP",
            Equation(
                m,
                name=f"{eq}_ACTRAMP",
                domain=[r, allyear, allyear, p, s, la, *swtd],
                description="Activity ramping equations",
            ),
        )
        g.set_equation(
            f"{eq}E_ACTUPS",
            Equation(
                m,
                name=f"{eq}E_ACTUPS",
                domain=[r, allyear, allyear, p, tsl, la, s, *swtd],
                description="Activity startup equations",
            ),
        )
        g.set_equation(
            f"{eq}L_ACTUPS",
            Equation(
                m,
                name=f"{eq}L_ACTUPS",
                domain=[r, allyear, allyear, p, tsl, la, s, *swtd],
                description="Activity offline balance",
            ),
        )
        g.set_equation(
            f"{eq}L_ACTUPC",
            Equation(
                m,
                name=f"{eq}L_ACTUPC",
                domain=[r, allyear, allyear, p, tsl, la, s, *swtd],
                description="Activity cycling constraints",
            ),
        )
        g.set_equation(
            f"{eq}_ACTPL",
            Equation(
                m,
                name=f"{eq}_ACTPL",
                domain=[r, allyear, allyear, p, s, *swtd],
                description="Activity partial loads",
            ),
        )
        g.set_equation(
            f"{eq}_ACTRMPC",
            Equation(
                m,
                name=f"{eq}_ACTRMPC",
                domain=[r, allyear, allyear, p, s, *swtd],
                description="Activity ramping costs",
            ),
        )
        g.eql_stgccl = Equation(
            m,
            name="EQL_STGCCL",
            domain=[r, allyear, allyear, p, allsow],
            description="Storage cycling constraints",
        )
        g.set_equation(
            f"{eq}_SLSIFT",
            Equation(
                m,
                name=f"{eq}_SLSIFT",
                domain=[r, allyear, p, c, s, la, la, *swtd],
                description="Time-slice load sifting",
            ),
        )

        # Unit commitment
        g.eq_sdlogic = Equation(
            m,
            name="eq_sdlogic",
            domain=[r, ll, t, p, tsl, s, la, allsow],
            description="Logical relationship between decision variables",
        )
        g.eq_sudupt = Equation(
            m,
            name="eq_sudupt",
            domain=[r, ll, t, p, tsl, s, upt, allsow],
            description="Selection of start up type a according to non-operational time",
        )
        g.eq_sdslant = Equation(
            m,
            name="eq_sdslant",
            domain=[r, ll, t, p, tsl, s, allsow],
            description="Slanting equation for start-up and shut-down phase",
        )
        g.eq_sdminon = Equation(
            m,
            name="eq_sdminon",
            domain=[r, ll, t, p, s, allsow],
            description="Minimum on-line capacity constraints",
        )
        g.eq_sudload = Equation(
            m,
            name="eq_sudload",
            domain=[r, ll, t, p, s, allsow],
            description="Load during start-up/shut down phase of the unit (linear growth)",
        )
        g.eq_sudtime = Equation(
            m,
            name="eq_sudtime",
            domain=[r, ll, t, p, tsl, s, bd, allsow],
            description="Minimum on-line / off-line time constraint",
        )
        g.eq_sudpll = Equation(
            m,
            name="eq_sudpll",
            domain=[r, ll, t, p, tsl, s, allsow],
            description="Efficiency losses due to start-up/shut-down of the unit",
        )

        # Risk analysis constraints
        g.set_equation(
            f"{eq}G_UCMAX",
            Equation(
                m,
                name=f"{eq}G_UCMAX",
                domain=[ucn, allr, item, c, "*", *swd],
                description="Maximum group-wise flow (G)",
            ),
        )
        g.set_equation(
            f"{eq}G_UCSUMAX",
            Equation(
                m,
                name=f"{eq}G_UCSUMAX",
                domain=[ucn, *swd],
                description="Maximum group-wise flow over regions (G)",
            ),
        )

        # Residual loads
        g.set_equation(
            f"{eq}_RL_LOAD",
            Equation(
                m,
                name=f"{eq}_RL_LOAD",
                domain=[r, t, s, *swtd],
                description="Total dispatchable residual loads",
            ),
        )
        g.set_equation(
            f"{eq}_RL_NDIS",
            Equation(
                m,
                name=f"{eq}_RL_NDIS",
                domain=[r, t, s, item, *swtd],
                description="Non-dispatchable loads by group",
            ),
        )
        g.set_equation(
            f"{eq}_RL_STCAP",
            Equation(
                m,
                name=f"{eq}_RL_STCAP",
                domain=[r, t, s, *swtd],
                description="Minimum available storage capacity",
            ),
        )
        g.set_equation(
            f"{eq}_RL_PKCAP",
            Equation(
                m,
                name=f"{eq}_RL_PKCAP",
                domain=[r, t, s, *swtd],
                description="Minimum dispatchable reserve during peak",
            ),
        )
        g.set_equation(
            f"{eq}_RL_THMIN",
            Equation(
                m,
                name=f"{eq}_RL_THMIN",
                domain=[r, t, s, bd, *swtd],
                description="Aggregate thermal minimum constraint",
            ),
        )

    def define_param_dp_uns(self: EquExtVda) -> None:
        g = self.tc
        g.RpPl[g.Rp, g.bd].where[Sum(g.RpgPace[g.Rp, g.cg], 1)] = False
