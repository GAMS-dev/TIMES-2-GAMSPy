# equ_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * EQU_EXT.cli - Extension for Climate Module
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *=============================================================================


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtCli(GamsClass):
    """Translation unit for equ_ext.cli."""

    # Instance attributes
    module_name: str = "equ_ext_cli"
    gams_source: str = "equ_ext.cli"

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
        self.compile()

    def compile(self) -> None:
        g = self.tc

        # CLIMATE MODULE EQUATIONS
        if self.env.stages.upper() == "YES":
            self.env.set_local("swtd", "SUM(SOW,")
            self.env.set_local("swtd_GP", "SUM(SOW,")  # How to handle sum here?
            self.env.set_local("swo", ",SOW")
            self.env.set_local("send", ")")
            self.env.set_local("swts", ",SW_TSW(SOW,T,W)")
        else:
            self.env.set_local("swo", ",'1'")
            self.env.set_local("send", "")
            self.env.set_local("swts", "")

        if self.env.stages == "YES":
            self.env.set_local("swtd", "SUM(SW_TSW(SOW,T-1,W),")
            self.env.set_local(
                "swtd_GP", "SUM(SW_TSW(SOW,T-1,W),"
            )  # how to handle sum here?
            self.env.set_local("swd", ",W")
            self.env.set_local("swd_GP", (g.w,))
            self.env.set_local("send", "")
            self.env.set_local("swt", "$SW_T(T,SOW)")
            self.env.set_local(
                "swt_GP", (g.SwT[g.t, g.Sow],)
            )  # todo: move $ to main code
        else:
            self.env.set_local("cpar", "CM_MAXC(LL,CG)")

        if self.env.stages == "YES":
            self.env.set_local("cpar", f"S_CM_MAXC(LL,CG,'1'{self.env.sow})")
            # TODO Resolve: %SW_STVARS%
            raise NotImplementedError("# TODO Resolve: $%SW_STVARS%")

        eq = self.env.eq
        var = self.env.var
        vart = self.env.vart
        vartt = self.env.vartt
        sow = self.env.sow
        sws = self.env.sws
        stages = self.env.stages
        obj = self.env.obj
        cpar = self.env.cpar
        swt = self.env.swt
        swd = self.env.swd
        swtd = self.env.swtd
        send = self.env.send
        swts = self.env.swts
        swo = self.env.swo

        self.balance_equation_for_total_emission(
            eq=eq, var=var, sow=sow, cpar=cpar, swt=swt
        )
        self.balance_equation_co2_in_box_t(
            eq=eq, var=var, sow=sow, swd=swd, sws=sws, swt=swt, swtd=swtd, send=send
        )
        self.balance_equation_temperature_clitemp(
            eq=eq, var=var, vart=vart, sow=sow, swo=swo, sws=sws, swtd=swtd, send=send
        )
        self.balance_equation_temperature_clibeoh(
            eq=eq, var=var, vart=vart, sow=sow, sws=sws, swo=swo, swd=swd, swts=swts
        )
        self.constraint_max_ghg(
            stages=stages,
            obj=obj,
            eq=eq,
            var=var,
            vart=vart,
            vartt=vartt,
            sow=sow,
            cpar=cpar,
            sws=sws,
        )

    def balance_equation_for_total_emission(
        self: EquExtCli, eq: str, var: str, sow: str, swt: str, cpar: str
    ) -> None:
        """Balance equation for the total emissions/forcing in each T"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}_CLITOT(CM_TKIND,SUPERYR(T,LL) {sow})$(CM_LED(LL){swt})..

  SUM((RTCS_VARC(R,T,C,S),CG(CM_EMIS(CM_TKIND)))$CM_GHGMAP(R,C,CG),
    {var}_COMNET(R,T,C,S {sow}) * CM_GHGMAP(R,C,CG) * CM_EVAR(CM_TKIND,LL))$CM_PPM(CM_TKIND) +
  CM_BEMI(CM_TKIND,LL) +
  SUM(CM_FORCMAP(CM_TKIND,CM_EMIS)$(NOT CM_EMIS(CM_TKIND)),CM_LINFOR(LL,CM_EMIS,'FX') + CM_LINFOR(LL,CM_EMIS,'N')/CM_PPM(CM_EMIS)*
    SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$CM_PHI(CM_EMIS,CM_BOX,CM_EMIS),{var}_CLIBOX(CM_VAR,CM_BOX,LL {sow}))) +
  SUM(CM_FORCMAP(CM_TKIND,CM_VAR(CG))$(NOT CM_EMIS(CM_VAR)),{cpar}) +
  SUM(SAMEAS('FORCING',CM_TKIND),CM_EXOFORC(LL))

  =E=  {var}_CLITOT(CM_TKIND,LL {sow});
""",
        )

    def balance_equation_co2_in_box_t(
        self: EquExtCli,
        eq: str,
        var: str,
        sow: str,
        swd: str,
        sws: str,
        swt: str,
        swtd: str,
        send: str,
    ) -> None:
        """Balance equation for the mass of CO2 in each box in each T"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}_CLICONC(CM_CONC(CM_EMIS(CM_KIND),CM_BOX),T {sow}){swt}..

 {swtd}
  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BUCK), CM_AA(CM_KIND,T,'1',CM_BOX,CM_BUCK) * {var}_CLIBOX(CM_VAR,CM_BUCK,T-1 {swd})) +
    CM_CC(CM_KIND,T,'1',CM_BOX)  * {var}_CLITOT(CM_KIND,T-1 {swd}) +
    CM_BB(CM_KIND,T,'1',CM_BOX)  * {var}_CLITOT(CM_KIND,T {sow}) +
  SUM(CM_COUPMAP(CM_EMIS,CM_VAR,CM_BOX), CM_COUPLE(CM_VAR,T,CM_EMIS,'N')*CM_COUPLE(CM_VAR,T,CM_EMIS,'ATM') *
   (CM_BB(CM_KIND,T,'1','ATM')   * {var}_CLIBOX(CM_VAR,'ATM',T {sow}) +
    CM_CC(CM_KIND,T,'1','ATM')   * {var}_CLIBOX(CM_VAR,'ATM',T-1 {sws}))) +

  SUM(CM_BOXMAP(CM_KIND,CM_HISTS,CM_BUCK)$CM_AA(CM_KIND,T,'1',CM_BOX,CM_BUCK),
    CM_AA(CM_KIND,T,'1',CM_BOX,CM_BUCK) * CM_STAT0(CM_KIND,CM_BUCK))$(ORD(T)=1)
 {send}
  =E=  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BOX),{var}_CLIBOX(CM_VAR,CM_BOX,T {sow}));
""",
        )

    def balance_equation_temperature_clitemp(
        self: EquExtCli,
        eq: str,
        var: str,
        vart: str,
        sow: str,
        swo: str,
        sws: str,
        swtd: str,
        send: str,
    ) -> None:
        """Balance equation for the temperature"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}_CLITEMP(CM_CONC(CM_KIND('FORCING'),CM_BOX),T {sow})..

 {swtd}
  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BUCK), CM_AA(CM_KIND,T{swo},CM_BOX,CM_BUCK) * {var}_CLIBOX(CM_VAR,CM_BUCK,T-1 {sow})) +
  CM_CC(CM_KIND,T{swo},CM_BOX)     * {var}_CLITOT(CM_KIND,T-1 {sws}) +
  CM_BB(CM_KIND,T{swo},CM_BOX)     * {vart}_CLITOT(CM_KIND,T {sws}) +

  SUM(CM_BOXMAP(CM_KIND,CM_HISTS,CM_BUCK)$CM_AA(CM_KIND,T{swo},CM_BOX,CM_BUCK),
    CM_AA(CM_KIND,T{swo},CM_BOX,CM_BUCK) * CM_STAT0(CM_KIND,CM_BUCK))$(ORD(T)=1)
 {send}
  =E=  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BOX),{var}_CLIBOX(CM_VAR,CM_BOX,T {sow}));
""",
        )

    def balance_equation_temperature_clibeoh(
        self: EquExtCli,
        eq: str,
        var: str,
        vart: str,
        sow: str,
        sws: str,
        swo: str,
        swd: str,
        swts: str,
    ) -> None:
        """Balance equation for the temperature"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}_CLIBEOH(CM_CONC(CM_KIND,CM_BOX),SUPERYR(T,LL) {sow})$((NOT MILESTONYR(LL))$CM_LED(LL))..

 SUM(YEAR(LL-CM_LED(LL)),
  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BUCK), CM_AA(CM_KIND,LL,'1',CM_BOX,CM_BUCK) * {vart}_CLIBOX(CM_VAR,CM_BUCK,YEAR {sws})) +
  CM_CC(CM_KIND,LL,'1',CM_BOX) * {vart}_CLITOT(CM_KIND,YEAR {sws}) +
  CM_BB(CM_KIND,LL,'1',CM_BOX) * {vart}_CLITOT(CM_KIND,LL {sws})
 )$CM_EMIS(CM_KIND) +
 SUM((YEAR(LL-CM_LED(LL)){swts}),
  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BUCK), CM_AA(CM_KIND,LL{swo},CM_BOX,CM_BUCK) * {var}_CLIBOX(CM_VAR,CM_BUCK,YEAR {sow})) +
  CM_CC(CM_KIND,LL{swo},CM_BOX) * {var}_CLITOT(CM_KIND,YEAR {swd}) +
  CM_BB(CM_KIND,LL{swo},CM_BOX) * {var}_CLITOT(CM_KIND,LL {swd})
 )$(NOT CM_EMIS(CM_KIND))

  =E=  SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BOX),
         {vart}_CLIBOX(CM_VAR,CM_BOX,LL {sws})$CM_EMIS(CM_KIND) +
         {var}_CLIBOX(CM_VAR,CM_BOX,LL {sow})$(NOT CM_EMIS(CM_KIND)));
""",
        )

    def constraint_max_ghg(
        self: EquExtCli,
        stages: str,
        obj: str,
        eq: str,
        var: str,
        vart: str,
        vartt: str,
        sow: str,
        sws: str,
        cpar: str,
    ) -> None:
        """Constraint for the maximum atmospheric concentration of GHGs"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 {eq}_CLIMAX(LL,CM_HISTS(CG) {sow})${cpar}..
  SUM((SUPERYR(YK(T,LL)),PRET(T,TT)),
* Bound on atmospheric quantity (concentration/delta-T)
   SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$(CM_ATMAP(CM_EMIS,CM_HISTS)*CM_PHI(CM_EMIS,CM_BOX,CM_EMIS)),
    ({var}_CLIBOX(CM_VAR,CM_BOX,T {sow}) + ({vartt}_CLIBOX(CM_VAR,CM_BOX,TT {sws}) - {var}_CLIBOX(CM_VAR,CM_BOX,T {sow})) *
                           (YEARVAL(T)-YEARVAL(LL)) / LEAD(T)) / CM_PPM(CM_EMIS))$(NOT CM_TKIND(CM_HISTS)) +
* Bound on temperature
   SUM(CM_BOXMAP('FORCING',CM_VAR,'ATM')$CM_ATMAP('FORCING',CM_HISTS),
{"VAR_CLIBOX(CM_VAR,'ATM',T)+(VAR_CLIBOX(CM_VAR,'ATM',TT)-VAR_CLIBOX(CM_VAR,'ATM',T)) * (YEARVAL(T)-YEARVAL(LL))" if stages != "YES" else ""}
{f"(SUM(SW_TSW(W,T,SOW),SW_PROB(W)*{var}_CLIBOX(CM_VAR,'ATM',T,W))/SW_TPROB(T,SOW) * (LEAD(T)+YEARVAL(LL)-YEARVAL(T)) +" if stages == "YES" else ""}
{"SUM(SW_TSW(WW,TT,W)$SW_TSW(SOW,TT,W),SW_PROB(WW)*{var}_CLIBOX(CM_VAR,'ATM',TT,WW)/SW_TPROB(TT,W)) * (YEARVAL(T)-YEARVAL(LL)))" if stages == "YES" else ""}
       / LEAD(T)) +
* Bound on radiative forcing
   SUM(CM_TKIND(CM_HISTS)$(SUM(CM_FORCMAP(CM_TKIND,CM_EMIS),1)$(NOT CM_EMIS(CM_HISTS))),
    {var}_CLITOT(CM_HISTS,T {sow}) + ({vartt}_CLITOT(CM_HISTS,TT {sws}) - {var}_CLITOT(CM_HISTS,T {sow})) *
                           (YEARVAL(T)-YEARVAL(LL)) / LEAD(T))) +
* Bound on global emissions

{f"SUM((CM_EMIS(CM_HISTS),TPULSEYR(T,LL)),TPULSE(T,LL)*{vart}_CLITOT(CM_EMIS,T {sws}))" if obj == "LIN" else f"SUM((CM_EMIS(CM_HISTS),PERIODYR(T,EOHYEARS(LL))), {vart}_CLITOT(CM_HISTS,T {sws}))"}

* Bound beyond last Milestone
+ SUM(SUPERYR(T,LL)$(NOT YK(T,LL)),
    SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX)$(CM_ATMAP(CM_EMIS,CM_HISTS)*CM_PHI(CM_EMIS,CM_BOX,CM_EMIS)),
      {var}_CLIBOX(CM_VAR,CM_BOX,LL {sow}) / CM_PPM(CM_EMIS))$(NOT CM_TKIND(CM_HISTS)) +
    SUM(CM_BOXMAP('FORCING',CM_VAR,'ATM')$CM_ATMAP('FORCING',CM_HISTS),{var}_CLIBOX(CM_VAR,'ATM',LL {sow})) +
    SUM(CM_TKIND(CM_HISTS)$(SUM(CM_FORCMAP(CM_TKIND,CM_EMIS),1)$(NOT CM_EMIS(CM_HISTS))),{var}_CLITOT(CM_HISTS,LL {sow})))

  =L=

  {cpar}$(SUM(CM_ATMAP(CM_KIND,CM_HISTS),YES)+CM_TKIND(CM_HISTS));
""",
        )
