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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.equcrtp_vda import EqucrtpPhases

from core.bnd_ire_vda import BndIreVda
from core.eqactups_vda import EqactupsVda
from core.eqashar_vda import EqasharVda
from core.eqcaflac_vda import EqcaflacVda
from core.eqlducs_vda import EqlducsVda
from core.equcrtp_vda import EqucrtpVda
from core.powerflo_vda import PowerfloVda
from core.pp_actef_vda import PpActefVda
from core.resloadc_vda import ResloadcVda
from core.ucbet_vda import UcbetVda

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        if self.arg1.upper() != "DECLR":  # L11: GOTO VDA
            pass
        else:
            self.equations(eq=self.env.eq, swtd=self.env.swtd, swd=self.env.swd)
            if self.tc.defined("PREMILE"):
                self.include(BndIreVda(self.tc, self.env))
            return
        self.env.set_scoped("vas", self.env.var)
        if self.env.stages == "YES":
            # TODO: Expected to FAIL: invalid add_gams_code
            self.tc.add_gams_code(
                module=self, phase="init", code=rf"""${self.env.sw_stvars}"""
            )
        self.env.set_scoped(
            "upscap0", f"({self.env.upscaps}$PRC_TS(R,P,S))$RP_UPL(R,P,'FX')"
        )
        self.tc.add_gams_code(
            module=self, phase="init", code="PARAMETER DP_UNS(R,LL,T,P,TSL,IPS,L) //;"
        )
        self.tc.enqueue(self.define_param_dp_uns)
        #         *-----------------------------------------------------------------------------
        # * Call for Implementations
        # *-----------------------------------------------------------------------------
        # * Activity Efficiency Transformation
        self.include(PpActefVda(self.tc, self.env))
        # * Capacity-activity equations:
        eqcaflac_bat_includes = [
            ("E", "'FX'", "$", self.env.mx),
            ("L", "'UP'", "*", self.env.mx),
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
        self.include(EqactupsVda(self.tc, self.env, arg1=self.env.mx))
        self.include(EqlducsVda(self.tc, self.env, arg1="EQU"))

        # * ASHAR equations:
        # fmt: off
        eqashar_batinclude: list[tuple[str, str]] = [
            ("E", "FX"),
            ("L", "LO"),
            ("G", "UP")
        ]
        # fmt: on
        for arg1, arg2 in eqashar_batinclude:
            self.include(
                EqasharVda(
                    self.tc,
                    self.env,
                    arg1=arg1,
                    arg2=arg2,
                )
            )

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
        equcrtp_batinclude: list[tuple[EqucrtpPhases, str, str, str]] = [
            ("EQU_EXT", "N", "L", "BDNEQ"),
            ("EQU_EXT", "E", "E", "'FX'"),
        ]
        for arg1, arg2, arg3, arg4 in equcrtp_batinclude:
            self.include(
                EqucrtpVda(
                    self.tc,
                    self.env,
                    arg1=arg1,
                    arg2=arg2,
                    arg3=arg3,
                    arg4=arg4,
                )
            )

    def equations(self: EquExtVda, eq: str, swtd: str, swd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------------
EQUATIONS
*-----------------------------------------------------------------------------

* Activity efficiency equation
  {eq}E_ACTEFF(R,ALLYEAR,ALLYEAR,P,CG,IO,S {swtd}) 'Process Activity Efficiency (=)'

* CAFLAC equations:
  {eq}E_CAFLAC(R,ALLYEAR,ALLYEAR,P,S {swtd}) 'Commodity based availability (=E=)'
  {eq}L_CAFLAC(R,ALLYEAR,ALLYEAR,P,S {swtd}) 'Commodity based availability (=L=)'
  {eq}L_CAPFLO(R,ALLYEAR,ALLYEAR,P,CG,S{swtd}) 'Flow-specific availability (=L=)'

* Advanced shares
  {eq}E_ASHAR(R,ALLYEAR,ALLYEAR,P,CG,COM_GRP,S{swtd}) 'Advanced share constraint (=E=)'
  {eq}L_ASHAR(R,ALLYEAR,ALLYEAR,P,CG,COM_GRP,S{swtd}) 'Advanced share constraint (=L=)'
  {eq}G_ASHAR(R,ALLYEAR,ALLYEAR,P,CG,COM_GRP,S{swtd}) 'Advanced share constraint (=G=)'

* Dynamic bounds
  {eq}N_UCRTP(UC_N,R,T,P,UC_GRPTYPE,BD{swtd}) 'Dynamic process bound (=L=)'
  {eq}E_UCRTP(UC_N,R,T,P,UC_GRPTYPE,BD{swtd}) 'Dynamic process bound (=E=)'
  {eq}N_UCRTC(UC_N,COM_VAR,R,T,C,TS,BD{swtd}) 'Dynamic commodity bound (=NE=)'
  EQN_UCRTP(UC_N,R,T,P,UC_GRPTYPE,BD) 'Dynamic process bound (=NE=)'

* Activity constraints
  {eq}_CAPLOAD(R,ALLYEAR,ALLYEAR,P,S,L {swtd})    'Augmented capacity-activity'
  {eq}_ACTRAMP(R,ALLYEAR,ALLYEAR,P,S,L {swtd})    'Activity ramping equations'
  {eq}E_ACTUPS(R,ALLYEAR,ALLYEAR,P,TSL,L,S{swtd}) 'Activity startup equations'
  {eq}L_ACTUPS(R,ALLYEAR,ALLYEAR,P,TSL,L,S{swtd}) 'Activity offline balance'
  {eq}L_ACTUPC(R,ALLYEAR,ALLYEAR,P,TSL,L,S{swtd}) 'Activity cycling constraints'
  {eq}_ACTPL(R,ALLYEAR,ALLYEAR,P,S {swtd})        'Activity partial loads'
  {eq}_ACTRMPC(R,ALLYEAR,ALLYEAR,P,S{swtd})       'Activity ramping costs'
  EQL_STGCCL(R,ALLYEAR,ALLYEAR,P,ALLSOW)          'Storage cycling constraints'
  {eq}_SLSIFT(R,ALLYEAR,P,C,S,L,L{swtd})          'Time-slice load sifting'

* Unit commitment
  eq_sdlogic(r,ll,t,p,tsl,s,l,allsow)   'Logical relationship between decision variables'
  eq_sudupt(r,ll,t,p,tsl,s,upt,allsow)  'Selection of start up type a according to non-operational time'
  eq_sdslant(r,ll,t,p,tsl,s,allsow)     'Slanting equation for start-up and shut-down phase'
  eq_sdminon(r,ll,t,p,s,allsow)         'Minimum on-line capacity constraints'
  eq_sudload(r,ll,t,p,s,allsow)         'Load during start-up/shut down phase of the unit (linear growth)'
  eq_sudtime(r,ll,t,p,tsl,s,bd,allsow)  'Minimum on-line / off-line time constraint'
  eq_sudpll(r,ll,t,p,tsl,s,allsow)      'Efficiency losses due to start-up/shut-down of the unit'

* Risk analysis constraints
  {eq}G_UCMAX(UC_N,ALL_R,ITEM,C,*{swd}) 'Maximum group-wise flow (G)'
  {eq}G_UCSUMAX(UC_N{swd})              'Maximum group-wise flow over regions (G)'

* Residual loads
  {eq}_RL_LOAD(R,T,S{swtd})             'Total dispatchable residual loads'
  {eq}_RL_NDIS(R,T,S,ITEM{swtd})        'Non-dispatchable loads by group'
  {eq}_RL_STCAP(R,T,S{swtd})            'Minimum available storage capacity'
  {eq}_RL_PKCAP(R,T,S{swtd})            'Minimum dispatchable reserve during peak'
  {eq}_RL_THMIN(R,T,S,BD{swtd})         'Aggregate thermal minimum constraint'
""",
        )

    def define_param_dp_uns(self: EquExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""

  RP_PL(RP,BD)$SUM(RPG_PACE(RP,CG),1)=NO;
""",
        )
