# solve_stp.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SOLVE.stp is the code for handling stepped solution of TIMES
# *   arg1 - mod
# *=============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.bnd_cum_mod import bnd_cum_mod
from core.bnd_ucw_mod import bnd_ucw_mod
from core.bndmain_mod import bndmain_mod
from core.clearsol_stc import ClearsolStc
from core.clearsol_stp import clearsol_stp
from core.coef_alt_lin import coef_alt_lin_stp
from core.eqobsalv_mod import eqobsalv_prepro
from core.pextlevs_stc import pextlevs_stc
from core.solve_mod import solve_mod_GP

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolveStp(GamsClass):
    """Translation unit for solve.stp"""

    # Instance attributes
    module_name: str = "solve_stp"
    gams_source: str = "solve.stp"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        model_name: str,
        equations: list[str],
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.model_name = model_name
        self.equations = equations
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("stepped", "YES")
        if (self.env.spines.upper() != "YES") and (self.env.stages.upper() == "YES"):
            self.env.set_scoped("stepped", "NO")

        if self.env.stepped == "NO" and self.env.is_set("timestep"):
            raise Exception("Stepped TIMES Not available with STAGES/SENSIS!")

        if not self.env.var_uc == "YES":
            raise Exception("Invalid VAR_UC setting for stepped mode.")

        if self.env.rpoint != "NO":
            self.env.set_scoped("solve_now", "NO")

        if not self.env.is_set("timestep"):
            self.env.set_scoped("timestep", "999")
            self.env.set_scoped("stepped", "NO")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SCALAR PRESOL / 1 /;
  SET UC_RN(UC_N,ALL_R) //;
  SET RTP_IRE(R,T,P,IE) 'IRE equations with fixed regions';
  SET IRE_RPR(R,P,R,IE) 'All regions REG linked to IRE process by equations in R';
  SET IRE_FXT(R,T,P) 'IRE with some linked regions fixed at T';
  PARAMETER STP_UCT(J,ALL_R,UCN,LL);
  PARAMETER STP_DIV(J,R,T,P) //;
  PARAMETER UC_BND(J,ALL_R,UCN,LL,S,L);
  PARAMETER PAR_CUMFLOM(R,P,C,LL,LL), PAR_UCR(UC_N,ALL_R);
""",
        )

        if (self.env.is_set("fixboh")) or (self.env.stages == "YES"):
            self.tc.enqueue(
                self.set_previous_marginals, eq=self.env.eq, swt=self.env.swt
            )

        sw1 = ""
        sw2 = ""

        if self.env.stages.upper() == "YES":
            sw2 = ",'1',SOW"
            sw1 = "S_"

        if self.env.spines.upper() == "YES":
            self.include(ClearsolStc(self.tc, self.env, arg1="DEF"))

        var = self.env.var
        self.tc.enqueue(
            self.exec_solve_stp_before_solve,
            timestep=self.env.timestep,
            fixboh=self.env.fixboh if self.env.is_set("fixboh") else "",
            fixboh_is_set=self.env.is_set("fixboh"),
            rtpx=self.env.rtpx,
            cli=self.env.cli,
            sysprefix=self.env.sysprefix,
            sw1=sw1,
            sw2=sw2,
            var=var,
            sow=self.env.sow,
            stages=self.env.stages,
            uc_cli_defined=self.tc.defined("UC_CLI"),
            macro=self.env.macro,
            eq=self.env.eq,
            swt=self.env.swt,
            abs_=self.env.abs,
        )

        self.tc.enqueue(
            self.exec_solve_stp_stepped_solve_and_tail,
            arg1=self.arg1,
            stepped=self.env.stepped,
            cli=self.env.cli,
            sensis=self.env.sensis,
            ctst=self.env.ctst,
            obj=self.env.obj,
            oblong=self.env.oblong,
            capjd=self.env.capjd,
            declif=self.env.declif,
            vnret_defined=self.tc.defined("VNRET"),
            rtpx=self.env.rtpx,
            spines=self.env.spines,
            solve_now=self.env.solve_now,
            damage=self.env.damage,
            micro=self.env.micro,
            macro=self.env.macro,
            etl=self.env.etl,
            solmip=self.env.solmip,
            mixlp=self.env.mixlp if self.env.is_set("mixlp") else "",
            nonlp=self.env.nonlp if self.env.is_set("nonlp") else "",
            memclean=self.env.memclean,
            eq=self.env.eq,
            var=self.env.var,
            timesed=self.env.timesed,
            var_dam_defined=self.tc.defined(f"{var}_DAM"),
            var_scap_defined=self.tc.defined(f"{self.env.var}_SCAP"),
            sow=self.env.sow,
            swt=self.env.swt,
            reduce=self.env.reduce,
            dflbl=self.env.dflbl,
            mx=self.env.mx,
            pgprim=self.env.pgprim,
            r_t=self.env.r_t,
            var_uc=self.env.var_uc,
            rts=self.env.rts,
            stochastic_symbols_declared={
                "S_NCAP_BND": self.tc.defined("S_NCAP_BND"),
                "S_CAP_BND": self.tc.defined("S_CAP_BND"),
                "S_COM_BNDNET": self.tc.defined("S_COM_BNDNET"),
                "S_COM_BNDPRD": self.tc.defined("S_COM_BNDPRD"),
            },
            stages=self.env.stages,
            swd=self.env.swd,
            eotime=self.env.eotime,
            cufscal=self.env.cufscal,
            cucscal=self.env.cucscal,
            bnd_ucw_defined={
                f"{var}_UC": self.tc.defined(f"{var}_UC"),
                f"{var}_UCR": self.tc.defined(f"{var}_UCR"),
                f"{var}_UCT": self.tc.defined(f"{var}_UCT"),
                f"{var}_UCRT": self.tc.defined(f"{var}_UCRT"),
                f"{var}_UCTS": self.tc.defined(f"{var}_UCTS"),
                f"{var}_UCRTS": self.tc.defined(f"{var}_UCRTS"),
            },
            tm_hsx_defined=self.tc.defined("TM_HSX"),
            sw1=sw1,
            sw2=sw2,
        )

        if self.env.stepped != "YES":
            self.tc.enqueue(self.exec_solve_stp_nonstepped_after_solve)

        self.tc.enqueue(
            self.exec_solve_stp_cleanup,
            var=self.env.var,
            sow=self.env.sow,
            swt=self.env.swt,
            eq=self.env.eq,
        )

    def set_previous_marginals(self: SolveStp, eq: str, swt: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  {eq}G_COMBAL.M(RTC,S{swt}) $= EQG_COMBAL.M(RTC,S);
  {eq}E_COMBAL.M(RTC,S{swt}) $= EQE_COMBAL.M(RTC,S);
  {eq}_PEAK.M(RTC,S{swt})    $= EQ_PEAK.M(RTC,S);
""",
        )

    def exec_solve_stp_before_solve(
        self,
        timestep: str,
        fixboh: str,
        fixboh_is_set: bool,
        rtpx: str,
        cli: str,
        sysprefix: str,
        sw1: str,
        sw2: str,
        var: str,
        sow: str,
        stages: str,
        uc_cli_defined: bool,
        macro: str,
        eq: str,
        swt: str,
        abs_: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Establish partitioning of T into fixed, current, and pending
* BACKWARD(T) = fixed T
* SUBT(T) = current T
* FORWARD(T) = pending T
  YR_V1 = 0; YR_VL = {timestep}; MY_FYEAR = 0; REG_FIXT(R)$NO = 0;
  IF(G_OVERLAP, G_OVERLAP = MAX(EPS,G_OVERLAP); ELSE G_OVERLAP = FLOOR(YR_VL/2));
{
                "  YR_V1 = ABS(" + fixboh + "); REG_FIXT(R)$(NOT REG_FIXT(R)) = YR_V1;"
                if fixboh_is_set
                else ""
            }
{"  MY_FYEAR = 1;" if rtpx == "X" else ""}
  F = SUM(MIYR_1(T),M(T));
  REG_FIXT(R)$(REG_FIXT(R) < F) = 0;
  YR_V1 = SMIN((R,T)$(M(T) > REG_FIXT(R)),M(T));
  Z = YR_V1 + YR_VL;
  SUBT(T)$(M(T) < YR_V1) = NO;
  SUBT(T)$(M(T) GE Z)    = NO;
  OPTION CLEAR=BACKWARD, CLEAR=FORWARD, RTC_NET<RHS_COMBAL, RTC_PRD<RHS_COMPRD;
  BACKWARD(T)$(M(T) < YR_V1) = YES;
  FORWARD(T) = TT(T)-BACKWARD(T)-SUBT(T);
  RT_PP(R,T) = (M(T) > REG_FIXT(R));
  NO_RT(R,T) = NOT RT_PP(R,T);
*-----------------------------------------------------------------------------
* Clear previous solution for projection years & ensure VAR_ACT loadpoint
{
                clearsol_stp(
                    arg1="",
                    var=var,
                    sow=sow,
                    eq=eq,
                    swt=swt,
                    cli=cli,
                    abs_=abs_,
                    macro=macro,
                    stages=stages,
                )
            }
  VAR_ACT.M(RVT,P,S)=0;
  IF(VAR_UC.L('{
                sysprefix
            }SOLVE_STATUS')=0, OPTION TRACKP<VAR_ACT, RP_PRC<VAR_FLO; RP_PRC(TRACKP)=NO;
   VAR_ACT.L(RTP_VINTYR(R,V,T,P),S)$RP_PRC(R,P) $= SUM(RPC_PG(RP_STD(R,P),C),VAR_FLO.L(R,V,T,P,C,S)*(1/PRC_ACTFLO(R,V,P,C)));
   VAR_ACT.L(RTP_VINTYR(R,V,T,P),S)$(NOT TRACKP(R,P)) $= SUM(RPC_IRE(RPC_PG(R,P,C),IE)$RP_AIRE(R,P,IE),VAR_IRE.L(R,V,T,P,C,S,IE)*(1/PRC_ACTFLO(R,V,P,C)))
   OPTION CLEAR=TRACKP,CLEAR=RP_PRC);
  VAR_COMNET.L(RHS_COMBAL(RTC,S))$(NOT COM_PROJ(RTC)) $= EQG_COMBAL.L(RTC,S);
*-----------------------------------------------------------------------------
* Copy FX UC RHS, COM_CUM and CAP_BND to UP/LO to support relaxation, removing FX bounds at the same time
   {sw1}CAP_BND(R,T,P,BD{sw2})${sw1}CAP_BND(R,T,P,'FX'{sw2}) = {sw1}CAP_BND(R,T,P,'FX'{
                sw2
            })$BDNEQ(BD);
   UC_RHS(UC_N,BD)$UC_RHS(UC_N,'FX') = UC_RHS(UC_N,'FX')$BDNEQ(BD);
   UC_RHSR(R,UC_N,BD)$UC_RHSR(R,UC_N,'FX') = UC_RHSR(R,UC_N,'FX')$BDNEQ(BD);
   UC_RHST(UC_N,T,BD)$UC_RHST(UC_N,T,'FX') = UC_RHST(UC_N,T,'FX')$BDNEQ(BD);
   UC_RHSTS(UC_N,T,S,BD)$UC_RHSTS(UC_N,T,S,'FX') = UC_RHSTS(UC_N,T,S,'FX')$BDNEQ(BD);
   UC_RHSRT(R,UC_N,T,BD)$UC_RHSRT(R,UC_N,T,'FX') = UC_RHSRT(R,UC_N,T,'FX')$BDNEQ(BD);
   UC_RHSRTS(R,UC_N,T,S,BD)$UC_RHSRTS(R,UC_N,T,S,'FX') = UC_RHSRTS(R,UC_N,T,S,'FX')$BDNEQ(BD);
   PRC_DYNUC(UC_N,SIDE,R,LL,P,UC_GRPTYPE,BD)$PRC_DYNUC(UC_N,'RHS',R,LL,P,UC_GRPTYPE,'FX') = PRC_DYNUC(UC_N,SIDE,R,LL,P,UC_GRPTYPE,'FX')$BDNEQ(BD);
* Find UC equations with negative coefficients
  LOOP((UC_N,SIDE,R,T,P)$((NOT UC_RN(UC_N,R))$UC_CAP(UC_N,SIDE,R,T,P)),
    IF(UC_CAP(UC_N,SIDE,R,T,P)*UC_SIGN(SIDE) < 0, UC_RN(UC_N,R) = YES));
  LOOP((UC_N,SIDE,R,T,P)$((NOT UC_RN(UC_N,R))$UC_NCAP(UC_N,SIDE,R,T,P)),
    IF(UC_NCAP(UC_N,SIDE,R,T,P)*UC_SIGN(SIDE) < 0, UC_RN(UC_N,R) = YES));
  LOOP((UC_N,SIDE,R,T,P,S)$((NOT UC_RN(UC_N,R))$UC_ACT(UC_N,SIDE,R,T,P,S)),
    IF(UC_ACT(UC_N,SIDE,R,T,P,S)*UC_SIGN(SIDE) < 0, UC_RN(UC_N,R) = YES));
  LOOP((UC_N,SIDE,R,T,P,C,S)$((NOT UC_RN(UC_N,R))$UC_FLO(UC_N,SIDE,R,T,P,C,S)),
    IF(UC_FLO(UC_N,SIDE,R,T,P,C,S)*UC_SIGN(SIDE) < 0, UC_RN(UC_N,R) = YES));
  LOOP((UC_N,SIDE,R,T,P,C,S,IE)$((NOT UC_RN(UC_N,R))$UC_IRE(UC_N,SIDE,R,T,P,C,S,IE)),
    IF(UC_IRE(UC_N,SIDE,R,T,P,C,S,IE)*UC_SIGN(SIDE) < 0, UC_RN(UC_N,R) = YES));
  LOOP((UC_N,COM_VAR,SIDE,R,T,C,S,UC_GRPTYPE)$((NOT UC_RN(UC_N,R))$UC_COM(UC_N,COM_VAR,SIDE,R,T,C,S,UC_GRPTYPE)),
    IF(UC_COM(UC_N,COM_VAR,SIDE,R,T,C,S,UC_GRPTYPE)*UC_SIGN(SIDE) < 0, UC_RN(UC_N,R) = YES));
  LOOP(UC_MAP_IRE(UC_N,R,P,C,'IMP')$COM_UNIT(R,C,'UCU'),UC_RN(UC_N,R)=YES);
{
                "  LOOP((UC_N,SIDE,R,T,CM_VAR)$UC_CLI(UC_N,SIDE,R,T,CM_VAR),IF(UC_CLI(UC_N,SIDE,R,T,CM_VAR)*UC_SIGN(SIDE)<0,UC_RN(UC_N,R)=YES));"
                if uc_cli_defined
                else ""
            }
  UC_RN(UC_N,'IMPEXP') $= SUM(UC_RN(UC_N,R),1);
* Collect all capacity-related UCs
  LOOP((UC_N,SIDE,R,T,P)$UC_CAP(UC_N,SIDE,R,T,P),R_UC(R,UC_N) = YES);
* Flag to use variables for all CAP_BND
  RTP_VARP(RTP(R,T,P))$(CAP_BND(RTP,'UP')+CAP_BND(RTP,'LO')) = YES;
  OPTION CLEAR=RTP_CAPYR; RTP_CAPYR(RTP_CPTYR(R,V,T,P))$(VAR_NCAP.L(R,V,P)+NCAP_PASTI(R,V,P)) = YES;
  VAR_CAP.L(RTP_VARP(RT_PP(R,T),P)) = SUM(RTP_CAPYR(R,V,T,P),COEF_CPT(R,V,T,P)*(VAR_NCAP.L(R,V,P)$TT(V)+NCAP_PASTI(R,V,P)));
*-----------------------------------------------------------------------------
* Save some original data
  STP_UCT('1',UC_T_SUM) = YES;
  STP_UCT('2',UC_T_SUCC) = YES;
  STP_UCT('3',UC_T_EACH) = YES;
  IF(ALTOBJ > 1,
    STP_DIV('1',R,T,P)  $= OBJ_DIVI(R,T,P);
    STP_DIV('2',R,T,P)  $= OBJ_DIVIV(R,T,P);
    STP_DIV('3',R,T,P)  $= OBJ_DIVIII(R,T,P));
""",
        )

    def exec_solve_stp_stepped_solve_and_tail(
        self,
        arg1: str,
        swd: str,
        cufscal: str,
        cucscal: str,
        stepped: str,
        rtpx: str,
        spines: str,
        solve_now: str,
        damage: str,
        micro: str,
        macro: str,
        etl: str,
        solmip: str,
        mixlp: str,
        nonlp: str,
        memclean: str,
        eq: str,
        var: str,
        timesed: str,
        var_dam_defined: bool,
        var_scap_defined: bool,
        sow: str,
        swt: str,
        reduce: str,
        mx: str,
        pgprim: str,
        r_t: str,
        var_uc: str,
        rts: str,
        stochastic_symbols_declared: dict[str, bool],
        stages: str,
        eotime: str,
        dflbl: str,
        bnd_ucw_defined: dict[str, bool],
        ctst: str,
        capjd: str,
        declif: str,
        vnret_defined: bool,
        obj: str,
        oblong: str,
        sensis: str,
        tm_hsx_defined: bool,
        sw1: str,
        sw2: str,
        cli: str,
    ) -> None:
        g = self.tc
        tolr = "1E-7" if tm_hsx_defined else "3E-6"
        tola = "1E-6" if tm_hsx_defined else "1E-4"
        tolx = "1E-5"

        # {"WHILE(CARD(SUBT)," if stepped == "YES" else ""} breaks for stepped != 'YES'
        # thus, removed the condition

        while len(g.Subt):
            print(len(g.Subt))
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
BACKWARD(T) = (M(T) < YR_V1);
FORWARD(SUBT) = NO;
NO_RT(R,T(BACKWARD)) = 1;
RT_PP(R,T) = SUBT(T)$(NOT NO_RT(R,T));
V(FORWARD) = NO;
* Re-define End-of-Horizon
IF(CARD(SUBT), MIYR_VL = SMAX(SUBT(T),E(T)));
OPTION CLEAR=Y_EOH, CLEAR=MIYR_L;
Y_EOH(EOHYEARS)$((YEARVAL(EOHYEARS) <= MIYR_VL)$(YEARVAL(EOHYEARS) >= MINYR)) = YES;
LOOP(MIYR_1(YEAR), Z=MIYR_VL-YEARVAL(YEAR); MIYR_L(YEAR+Z) = YES);
*-----------------------------------------------------------------------------
* Complete adjusted model
* Adjust divisor data when appropriate
    {
                    coef_alt_lin_stp(
                        obj=obj,
                        ctst=ctst,
                        oblong=oblong,
                    )
                    if ctst != ""
                    else ""
                }
* We must recompute OBJ_LIFE and salvage values
OBJ_LIFE(K(LL),R,JOT,LIFE,CUR)$OBJ_LIFE(K,R,JOT,LIFE,CUR) = SUM((OPYEAR(LIFE,AGE),Y_EOH(LL+(ORD(AGE)-1))),OBJ_DISC(R,Y_EOH,CUR))+EPS;
    {
                    eqobsalv_prepro(
                        arg1=arg1,
                        timestep_is_set=True,
                        stepped=stepped,
                        ctst=ctst,
                        capjd=capjd,
                        etl=etl,
                        declif=declif,
                        vnret_defined=vnret_defined,
                    )
                    if stepped == "YES"
                    else ""
                }
RVPRL(R,K,P)$RVPRL(R,K,P)=MAX(1,SMAX(RTP_CPTYR(R,VNT(K,V(T)),P),YEARVAL(V))-YEARVAL(K));
*-----------------------------------------------------------------------------
* Handle Dynamic constraints and Multi-regional UC relaxation
* Remove UC_T_SUM if it does not overlap with SUBT
OPTION CLEAR=RXX,CLEAR=UNCD1;
RXX(UC_R_EACH(R,UC_N),R)$SUM(UC_T_SUM(R,UC_N,T)$RT_PP(R,T),YES) = YES;
UNCD1(UC_N)$SUM(UC_T_SUM(UC_R_SUM(R,UC_N),T)$RT_PP(R,T),YES) = YES;
UC_T_SUM(R,UC_N,T)$FORWARD(T) = NO;
UC_T_SUM(R,UC_N,T)$((NOT UNCD1(UC_N))$(NOT RXX(R,UC_N,R))) = NO;
IF(PRESOL, VAR_UC.L(UC_N(UNCD1)) = 0; VAR_UCR.L(UC_N,R)$RXX(R,UC_N,R) = 0);
* Remove UC_T_EACH for all but SUBT
* Remove UC_T_SUCC until not completely fixed or if even partly pending
OPTION CLEAR=UC_T;
    LOOP(UC_T_EACH(UC_R_SUM(R,UC_N),T)$RT_PP(R,T), UC_T(UC_N,T) = YES);
    LOOP(UC_T_SUCC(UC_R_SUM(R,UC_N),T)$RT_PP(R,T), UC_T(UC_N,T) = YES);
    UC_T_EACH(UC_R_SUM(R,UC_N),T)$(NOT UC_T(UC_N,T)) = NO;
    UC_T_SUCC(UC_R_SUM(R,UC_N),T)$(UC_DYNDIR(R,UC_N,'RHS')$(NOT UC_T(UC_N,T))) = NO;
    UC_T_EACH(UC_R_EACH(R,UC_N),T)$(NOT RT_PP(R,T)) = NO;
    UC_T_SUCC(UC_R_EACH(R,UC_N),T)$(UC_DYNDIR(R,UC_N,'RHS')$(NOT RT_PP(R,T))) = NO;
    UC_T_SUCC(UC_T_SUCC(R,UC_N,T-1)) = UC_DYNDIR(R,UC_N,'RHS')+RT_PP(R,T);
    UC_T(UC_N,T)$(NOT SUM(R$NO_RT(R,T),1)) = NO;
    {
                    "    LOOP(T$(NOT SUM(R,NOT NO_RT(R,T))),CM_MAXC(LL,CG)$SUPERYR(T,LL) = 0);"
                    if cli.upper() == "YES"
                    else ""
                }

LOOP(BD,UC_T_SUCC(R,UC_N,T)$UC_DYNBND(UC_N,BD) = RT_PP(R,T));
* RHS and Bounds Relaxation
IF(CARD(BACKWARD) OR MY_FYEAR, OPTION CLEAR=UC_BND,CLEAR=R_UCT;
R_UCT(R_UC(R,UC_N),T)$(UC_T_EACH(R,UC_N,T)+UC_T_SUCC(R,UC_N,T)) = YES;
LOOP(UC_R_SUM(R_UC(R,UC_N)),UC_T(UC_N,T)$R_UCT(R,UC_N,T) = YES);
R_UCT(R,UC_N,T)$(NOT REG_FIXT(R)) = NO;
* Set into UC_BND the RHS corrected by actual slack level, if RHS already violated
UC_BND('1','IMPEXP',UC_N,'0','ANNUAL','UP')$UC_RHS(UC_N,'UP')  = MAX(UC_RHS(UC_N,'UP'),VAR_UC.L(UC_N)-INF$(NOT VAR_UC.L(UC_N)));
UC_BND('2',R,UC_N,'0','ANNUAL','UP')$UC_RHSR(R,UC_N,'UP')      = MAX(UC_RHSR(R,UC_N,'UP'),VAR_UCR.L(UC_N,R)-INF$(NOT VAR_UCR.L(UC_N,R)));
UC_BND('3','IMPEXP',UC_N,T,'ANNUAL','UP')$UC_RHST(UC_N,T,'UP') = MAX(UC_RHST(UC_N,T,'UP'),VAR_UCT.L(UC_N,T)-INF$(NOT VAR_UCT.L(UC_N,T)));
UC_BND('4','IMPEXP',UC_N,T,S,'UP')$UC_RHSTS(UC_N,T,S,'UP')     = MAX(UC_RHSTS(UC_N,T,S,'UP'),VAR_UCTS.L(UC_N,T,S)-INF$(NOT VAR_UCTS.L(UC_N,T,S)));
UC_BND('5',R,UC_N,T,'ANNUAL','UP')$UC_RHSRT(R,UC_N,T,'UP')     = MAX(UC_RHSRT(R,UC_N,T,'UP'),VAR_UCRT.L(UC_N,R,T)-INF$(NOT VAR_UCRT.L(UC_N,R,T)));
UC_BND('6',R,UC_N,T,S,'UP')$UC_RHSRTS(R,UC_N,T,S,'UP')         = MAX(UC_RHSRTS(R,UC_N,T,S,'UP'),VAR_UCRTS.L(UC_N,R,T,S)-INF$(NOT VAR_UCRTS.L(UC_N,R,T,S)));
UC_BND('1','IMPEXP',UC_N,'0','ANNUAL','LO')$UC_RHS(UC_N,'LO')  = MIN(UC_RHS(UC_N,'LO'),VAR_UC.L(UC_N)+INF$(NOT VAR_UC.L(UC_N)));
UC_BND('2',R,UC_N,'0','ANNUAL','LO')$UC_RHSR(R,UC_N,'LO')      = MIN(UC_RHSR(R,UC_N,'LO'),VAR_UCR.L(UC_N,R)+INF$(NOT VAR_UCR.L(UC_N,R)));
UC_BND('3','IMPEXP',UC_N,T,'ANNUAL','LO')$UC_RHST(UC_N,T,'LO') = MIN(UC_RHST(UC_N,T,'LO'),VAR_UCT.L(UC_N,T)+INF$(NOT VAR_UCT.L(UC_N,T)));
UC_BND('4','IMPEXP',UC_N,T,S,'LO')$UC_RHSTS(UC_N,T,S,'LO')     = MIN(UC_RHSTS(UC_N,T,S,'LO'),VAR_UCTS.L(UC_N,T,S)+INF$(NOT VAR_UCTS.L(UC_N,T,S)));
UC_BND('5',R,UC_N,T,'ANNUAL','LO')$UC_RHSRT(R,UC_N,T,'LO')     = MIN(UC_RHSRT(R,UC_N,T,'LO'),VAR_UCRT.L(UC_N,R,T)+INF$(NOT VAR_UCRT.L(UC_N,R,T)));
UC_BND('6',R,UC_N,T,S,'LO')$UC_RHSRTS(R,UC_N,T,S,'LO')         = MIN(UC_RHSRTS(R,UC_N,T,S,'LO'),VAR_UCRTS.L(UC_N,R,T,S)+INF$(NOT VAR_UCRTS.L(UC_N,R,T,S)));
* Add relaxation tolerances; absolute only if both positive+negative coefficients
UC_BND(J,ALL_R,UC_N,LL,S,'UP')$UC_BND(J,ALL_R,UC_N,LL,S,'UP')  = UC_BND(J,ALL_R,UC_N,LL,S,'UP')+ABS(UC_BND(J,ALL_R,UC_N,LL,S,'UP'))*{
                    tolr
                }+{tola}$UC_RN(UC_N,ALL_R);
UC_BND(J,ALL_R,UC_N,LL,S,'LO')$UC_BND(J,ALL_R,UC_N,LL,S,'LO')  = UC_BND(J,ALL_R,UC_N,LL,S,'LO')-ABS(UC_BND(J,ALL_R,UC_N,LL,S,'LO'))*{
                    tolr
                }-{tola}$UC_RN(UC_N,ALL_R);
* Copy back to RHS (VAR bounds would be cleared in sensitivity analysis)
UC_RHS(UC_N,BDNEQ(BD))                   $= UC_BND('1','IMPEXP',UC_N,'0','ANNUAL',BD);
UC_RHSR(R,UC_N,BDNEQ(BD))$REG_FIXT(R)    $= UC_BND('2',R,UC_N,'0','ANNUAL',BD);
UC_RHST(UC_T(UC_N,T),BDNEQ(BD))          $= UC_BND('3','IMPEXP',UC_N,T,'ANNUAL',BD);
UC_RHSTS(UC_T(UC_N,T),S,BDNEQ(BD))       $= UC_BND('4','IMPEXP',UC_N,T,S,BD);
UC_RHSRT(R_UCT(R,UC_N,T),BDNEQ(BD))      $= UC_BND('5',R,UC_N,T,'ANNUAL',BD);
UC_RHSRTS(R_UCT(R,UC_N,T),S,BDNEQ(BD))   $= UC_BND('6',R,UC_N,T,S,BD);
* Handle other important dynamic constraints
LOOP((R,T,SAMEAS(T+1,TT))$NO_RT(R,T),
    PRC_DYNUC(UC_N,'LHS',RTP(R,TT,P),UC_GRPTYPE,'UP')$PRC_DYNUC(UC_N,'RHS',R,'0',P,UC_GRPTYPE,'UP') = PRC_DYNUC(UC_N,'LHS',R,TT,P,UC_GRPTYPE,'UP')*(1+{
                    tolr
                });
    PRC_DYNUC(UC_N,'LHS',RTP(R,TT,P),UC_GRPTYPE,'LO')$PRC_DYNUC(UC_N,'RHS',R,'0',P,UC_GRPTYPE,'LO') = PRC_DYNUC(UC_N,'LHS',R,TT,P,UC_GRPTYPE,'LO')*(1-{
                    tolx
                }));
{sw1}COM_CUM(R,COM_VAR,YEAR,LL,C,'UP'{sw2})$(REG_FIXT(R)${
                    sw1
                }COM_CUM(R,COM_VAR,YEAR,LL,C,'UP'{sw2})) = MAX({
                    sw1
                }COM_CUM(R,COM_VAR,YEAR,LL,C,'UP'{sw2}),MIN({
                    sw1
                }COM_CUM(R,COM_VAR,YEAR,LL,C,'UP'{
                    sw2
                }),VAR_CUMCOM.L(R,C,COM_VAR,YEAR,LL)*{cucscal})*(1+{tolr}));
{sw1}COM_CUM(R,COM_VAR,YEAR,LL,C,'LO'{sw2})$REG_FIXT(R) $= {
                    sw1
                }COM_CUM(R,COM_VAR,YEAR,LL,C,'LO'{sw2})*(1-{tolr});
{sw1}FLO_CUM(R,P,C,YEAR,LL,'UP'{sw2})$(REG_FIXT(R)${sw1}FLO_CUM(R,P,C,YEAR,LL,'UP'{
                    sw2
                })) = MAX({sw1}FLO_CUM(R,P,C,YEAR,LL,'UP'{sw2}),MIN({
                    sw1
                }FLO_CUM(R,P,C,YEAR,LL,'UP'{sw2}),VAR_CUMFLO.L(R,P,C,YEAR,LL)*{
                    cufscal
                })*(1+{tolr}));
{sw1}FLO_CUM(R,P,C,YEAR,LL,'LO'{sw2})$REG_FIXT(R)       $= {
                    sw1
                }FLO_CUM(R,P,C,YEAR,LL,'LO'{sw2})*(1-{tolr});
{sw1}CAP_BND(R,T,P,'UP'{sw2})${sw1}CAP_BND(R,T,P,'UP'{sw2}) = MAX({
                    sw1
                }CAP_BND(R,T,P,'UP'{sw2}),VAR_CAP.L(R,T,P)*(1+{tolr}));
{sw1}CAP_BND(R,T,P,'LO'{sw2})                           $= {sw1}CAP_BND(R,T,P,'LO'{
                    sw2
                })*(1-{tolr});
);

    {
                    bnd_ucw_mod(
                        arg1="",
                        arg2="",
                        var=var,
                        stages=stages,
                        swd=swd,
                        sow=sow,
                        defined_symbols=bnd_ucw_defined,
                    )
                }
* Redefine UC_T according to current flags
OPTION UC_RTSUC < UC_T_SUCC;
IF(CARD(REG_CUMCST),LOOP((R,T)$NO_RT(R,T),REG_CUMCST(R,YEAR,LL,COSTCAT,CUR,'UP')$SUPERYR(T,LL) = 0));
*-----------------------------------------------------------------------------
* Activities and flows
{
                    '''
LOOP(R, BACKWARD(T) = NO_RT(R,T); SUBT(T) = RT_PP(R,T);
'''
                    if rtpx == "X"
                    else ""
                }
{var}_ACT.FX(RTP_VINTYR(R,V,BACKWARD(T),P),S{
                    sow
                })$(PRC_TS(R,P,S)) =                            VAR_ACT.L(R,V,T,P,S);
{var}_FLO.FX(RTP_VINTYR(R,V,BACKWARD(T),P),C,S{
                    sow
                })$(RPCS_VAR(R,P,C,S)*RP_FLO(R,P)) =          VAR_FLO.L(R,V,T,P,C,S);
{var}_IRE.FX(RTP_VINTYR(R,V,BACKWARD(T),P),C,S,IE{
                    sow
                })$(RPCS_VAR(R,P,C,S)*RPC_IRE(R,P,C,IE)) = VAR_IRE.L(R,V,T,P,C,S,IE);
{var}_SIN.FX(RTP_VINTYR(R,V,BACKWARD(T),P),C,S{
                    sow
                })$(RPCS_VAR(R,P,C,S)*RPC_STG(R,P,C)) =       VAR_SIN.L(R,V,T,P,C,S);
{var}_SOUT.FX(RTP_VINTYR(R,V,BACKWARD(T),P),C,S{
                    sow
                })$(RPCS_VAR(R,P,C,S)*RPC_STG(R,P,C)) =      VAR_SOUT.L(R,V,T,P,C,S);
{var}_UPS.FX(RTP_VINTYR(R,V,BACKWARD(T),P),S,BD(L){
                    sow
                })$RPS_UPS(R,P,S) =                       VAR_UPS.L(R,V,T,P,S,L);
{var}_UPT.FX(RTP_VINTYR(R,V,BACKWARD(T),P),S,UPT{
                    sow
                })$(RPS_UPS(R,P,S)$RP_DP(R,P)) =            VAR_UPT.L(R,V,T,P,S,UPT);
{var}_UDP.FX(RTP_VINTYR(R,V,BACKWARD(T),P),S,BD(L){
                    sow
                })$(PRC_TS(R,P,S)$RP_UPR(R,P,BD)) =       VAR_UDP.L(R,V,T,P,S,L);
* Commodities
{var}_COMNET.FX(RTC_NET(R,BACKWARD(T),C),S{sow})$COM_TS(R,C,S) = VAR_COMNET.L(R,T,C,S);
{var}_COMPRD.FX(RTC_PRD(R,BACKWARD(T),C),S{sow})$COM_TS(R,C,S) = VAR_COMPRD.L(R,T,C,S);
{var}_ELAST.FX(RTC(R,BACKWARD(T),C),S,J,BD{
                    sow
                })$(COM_TS(R,C,S)$RCJ(R,C,J,BD)) = VAR_ELAST.L(RTC,S,J,BD);
{
                    f"VAR_DAM.L(R,T,C,BD,J)$NO=0; {var}_DAM.FX(R,T(BACKWARD),C,BD,J{sow})$((ORD(J) LE DAM_STEP(R,C,BD))$DAM_STEP(R,C,'FX')) = VAR_DAM.L(R,T,C,BD,J);"
                    if var_dam_defined
                    else ""
                }
* Capacities
{var}_NCAP.FX(R,BACKWARD(T),P{sow})$RP(R,P) = MAX(EPS,VAR_NCAP.L(R,T,P));
{var}_CAP.UP(RTP(R,BACKWARD(T),P){sow}) =  INF;
{var}_CAP.LO(RTP(R,BACKWARD(T),P){sow}) =  0;
OPTION CLEAR=NO_RVP; NO_RVP(RTP_VARP(R,SUBT(T),P))$SUM(RTP_CPTYR(R,BACKWARD(TT),T,P),1) = YES;
{var}_CAP.UP(NO_RVP(R,T,P){sow})$CAP_BND(R,T,P,'UP') = CAP_BND(R,T,P,'UP');
{var}_CAP.LO(NO_RVP(R,T,P){sow})$CAP_BND(R,T,P,'LO') = CAP_BND(R,T,P,'LO');
{var}_SCAP.FX(RTP_CPTYR(R,V,BACKWARD(T),P){sow})$PRC_RCAP(R,P) = VAR_SCAP.L(R,V,T,P);
* Cumulative variables
Z = (SMAX(T,M(T)) > MIYR_VL);
FIL(LL) = Z*(MIYR_VL < YEARVAL(LL));
    {
                    bnd_cum_mod(
                        arg1="COM_VAR",
                        stages=stages,
                        eotime=eotime,
                        var=var,
                        sow=sow,
                        cufscal=cufscal,
                        cucscal=cucscal,
                        macro=macro,
                    )
                    if sensis.upper() != "YES"
                    else ""
                }
* Remove LO bounds if years only partially in current horizon and no adjustment for shorter horizon
{var}_CUMFLO.LO(R,P,C,YEAR,LL {sow})$((NOT FLO_CUM(R,P,C,YEAR,LL,'N'))$FIL(LL)) = 0;
{var}_CUMCOM.LO(R,C,COM_VAR,YEAR,LL {
                    sow
                })$((NOT COM_CUM(R,COM_VAR,YEAR,LL,C,'N'))$FIL(LL)) = 0;
* Blending
VAR_BLND.L(RT_PP,BLE,OPR)=0;
{var}_BLND.FX(R,BACKWARD(T),BLE,OPR{sow})$BLE_OPR(R,BLE,OPR) = VAR_BLND.L(R,T,BLE,OPR);
{
                    '''
); BACKWARD(T) = M(T) < YR_V1; SUBT(T) = TT(T)-BACKWARD(T)-FORWARD(T);
'''
                    if rtpx == "X"
                    else ""
                }
*-----------------------------------------------------------------------------
IF(MY_FYEAR,
* Find all regions REG linked to IRE equations in region R
TRACKPC(RPC(R,P,C))$(RPC_EQIRE(R,P,C,'EXP')+RPC_MARKET(R,P,C,'EXP')) = YES;
LOOP((TRACKPC(R,P,C),TOP_IRE(R,C,REG,COM,P)),IRE_RPR(R,P,REG,'EXP') = YES);
OPTION CLEAR=TRACKPC;
LOOP((TOP_IRE(R,C,REG,COM,P),RPC_EQIRE(REG,P,COM,'IMP')),IRE_RPR(REG,P,R,'IMP') = YES);
OPTION CLEAR=RTPX; RTPX(RTP(R,T,P))$RP_IRE(R,P) = RT_PP(R,T);
LOOP((REG,IE),RTPX(RTP(R,T,P))$(RT_PP(REG,T)$IRE_RPR(R,P,REG,IE)) = YES);
IRE_FXT(RTP(R,T,P))$(NO_RT(R,T)$RP_IRE(R,P)) = YES;
LOOP((REG,IE),IRE_FXT(R,T,P)$(NO_RT(REG,T)$IRE_RPR(R,P,REG,IE)) = YES);
* Remove RTP for IRE fixed in all linked regions, and save marginals
IF(PRESOL,OPTION CLEAR=PAR_IPRIC; EQ_IRE.M(R,T,P,C,IE,S)$NO = 0);
PAR_IPRIC(IRE_FXT,C,S,IE)$(PAR_IPRIC(IRE_FXT,C,S,IE)=0) $= EQ_IRE.M(IRE_FXT,C,IE,S);
* Relax all fixed flows in regions with IRE equations
OPTION CLEAR=RTP_IRE; LOOP(REG,RTP_IRE(RTPX(R,T,P),IE)$(IRE_RPR(R,P,REG,IE)$NO_RT(R,T)) = YES);
{var}_IRE.UP(RTP_VINTYR(R,V,T,P),C,S,IE{
                    sow
                })$(RTP_IRE(R,T,P,IE)*RPCS_VAR(R,P,C,S)*RPC_IREIO(R,P,C,IE,'IN')) = VAR_IRE.L(R,V,T,P,C,S,IE)*(1+{
                    tolx
                }*POWER(8,-1$XPT(IE)));
{var}_IRE.LO(RTP_VINTYR(R,V,T,P),C,S,IE{
                    sow
                })$(RTP_IRE(R,T,P,IE)*RPCS_VAR(R,P,C,S)*RPC_IREIO(R,P,C,IE,'IN')) = VAR_IRE.L(R,V,T,P,C,S,IE)*(1-{
                    tolx
                }*POWER(8,-1$IMP(IE)));
LOOP(IE,
{
                    "   "
                    + var
                    + "_ACT.UP(RTP_VINTYR(R,V,T,P),S"
                    + sow
                    + ")$(RTP_IRE(R,T,P,IE)*PRC_TS(R,P,S)*RP_PGACT(R,P)) = VAR_ACT.L(R,V,T,P,S)*(1+"
                    + tolx
                    + "*POWER(8,-1$XPT(IE)));"
                    if reduce == "YES"
                    else ""
                }
{
                    "   "
                    + var
                    + "_ACT.LO(RTP_VINTYR(R,V,T,P),S"
                    + sow
                    + ")$(RTP_IRE(R,T,P,IE)*PRC_TS(R,P,S)*RP_PGACT(R,P)) = VAR_ACT.L(R,V,T,P,S)*(1-"
                    + tolx
                    + "*POWER(8,-1$IMP(IE)));"
                    if reduce == "YES"
                    else ""
                }
);
* Remove IRE_BND from fixed regions with no related IRE equation, and all IRE_XBND from fixed regions
OPTION CLEAR=RXX;
LOOP((R,T,C,S,ALL_REG,IE,BD)$(NO_RT(R,T)$IRE_BND(R,T,C,S,ALL_REG,IE,BD)),
    IF(NOT SUM(RPC_EQIRE(R,P,C,IE)$RTPX(R,T,P),1),
    IF(NOT SUM(RPC_MARKET(R,P,C,IE)$RTPX(R,T,P),1),RXX(R,C,IE) = YES)));
IRE_BND(R,T,C,S,ALL_REG,IE,BD)$(NO_RT(R,T)$RXX(R,C,IE)) = 0;
IRE_XBND(R,T,C,S,IE,BD)$NO_RT(R,T) = 0;
);
*-----------------------------------------------------------------------------
{
                    '''
FIL(T)=FORWARD(T); LOOP(R, FORWARD(T)=FIL(T)$(NOT NO_RT(R,T));
'''
                    if rtpx == "X"
                    else ""
                }
* Activities and flows
VAR_ACT.FX(RTP_VINTYR(R,V,FORWARD(T),P),S)$(PRC_TS(R,P,S)) =                            0;
VAR_FLO.FX(RTP_VINTYR(R,V,FORWARD(T),P),C,S)$(RPCS_VAR(R,P,C,S)*RP_FLO(R,P)) =          0;
*  VAR_IRE.FX(RTP_VINTYR(R,V,FORWARD(T),P),C,S,IE)$(RPCS_VAR(R,P,C,S)*RPC_IRE(R,P,C,IE)) = 0;
VAR_SIN.FX(RTP_VINTYR(R,V,FORWARD(T),P),C,S)$(RPCS_VAR(R,P,C,S)*RPC_STG(R,P,C)) =       0;
VAR_SOUT.FX(RTP_VINTYR(R,V,FORWARD(T),P),C,S)$(RPCS_VAR(R,P,C,S)*RPC_STG(R,P,C)) =      0;
* Commodities
VAR_COMNET.FX(RTCS_VARC(R,FORWARD(T),C,S)) = 0;
VAR_COMPRD.FX(RTCS_VARC(R,FORWARD(T),C,S)) = 0;
VAR_ELAST.FX(RTCS_VARC(R,FORWARD(T),C,S),J,BD)$RCJ(R,C,J,BD) = 0;
* Capacities
VAR_CAP.LO(RTP(R,FORWARD(T),P)) = 0;
VAR_CAP.UP(RTP(R,FORWARD(T),P)) $= CAP_BND(RTP,'UP');
* Blending
VAR_BLND.FX(R,FORWARD(T),BLE,OPR)$BLE_OPR(R,BLE,OPR) = 0;
{
                    '''
); FORWARD(T)=FIL(T);
'''
                    if rtpx == "X"
                    else ""
                }
*-----------------------------------------------------------------------------
* Reject starting basis if equations were removed:
IF(CARD(NO_RT)+CARD(FORWARD), OPTION BRATIO=1);
OPTION SOLVEOPT=MERGE;
* Save last cum marginal
IF(PRESOL=0, PAR_CUMFLOM(R,P,C,YEAR,LL) $= VAR_CUMFLO.M(R,P,C,YEAR,LL);
    PAR_UCR(UC_N,'IMPEXP') $= VAR_UC.M(UC_N); PAR_UCR(UC_N,R) $= VAR_UCR.M(UC_N,R));
*-----------------------------------------------------------------------------
""",
            )
            ext = "stc" if (stages == "YES" and spines != "YES") else "mod"

            if ext == "mod":
                solve_mod_GP(
                    module=self,
                    equations=self.equations,
                    model_name=self.model_name,
                    solve_now=solve_now,
                    damage=damage,
                    micro=micro,
                    macro=macro,
                    etl=etl,
                    solmip=solmip,
                    mixlp=mixlp,
                    nonlp=nonlp,
                    memclean=memclean,
                )

            elif ext == "stc":
                raise NotImplementedError("Still needs implementation")
            else:
                raise ValueError(f"Unexpected value {ext} for solve_<ext>.")

            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
PRESOL = 0;
*-----------------------------------------------------------------------------
* Restore last cum marginal
VAR_UC.M(UC_N)$(VAR_UC.M(UC_N)=0) $= PAR_UCR(UC_N,'IMPEXP');
VAR_UCR.M(UC_N,R)$(VAR_UCR.M(UC_N,R)=0) $= PAR_UCR(UC_N,R);
VAR_CUMFLO.M(R,P,C,YEAR,LL)$(VAR_CUMFLO.M(R,P,C,YEAR,LL)=0) $= PAR_CUMFLOM(R,P,C,YEAR,LL);
* Adjust SUBT
SUBT(T) = SUBT(T-1);
Z = SMIN(FORWARD(T),B(T));
YR_V1 = SMIN(SUBT(T)$(M(T) GE Z-G_OVERLAP),M(T));
Z = YR_V1 + YR_VL;
SUBT(T)$(M(T) < Z) = YES;
SUBT(T)$(M(T) < YR_V1) = NO;
*-----------------------------------------------------------------------------
* Restore some original data
V(T) = YES;
UC_T_SUM(R,UC_N,T)    $= STP_UCT('1',R,UC_N,T);
UC_T_SUCC(R,UC_N,T)   $= STP_UCT('2',R,UC_N,T);
UC_T_EACH(R,UC_N,T)   $= STP_UCT('3',R,UC_N,T);
    {"LOOP(R, BACKWARD(T)=NO_RT(R,T);" if rtpx == "X" else ""}
    {
                    pextlevs_stc(
                        arg1="'1'",
                        arg2="(BACKWARD)",
                        eq=eq,
                        var=var,
                        timesed=timesed,
                        var_dam_defined=var_dam_defined,
                        var_scap_defined=var_scap_defined,
                    )
                    if spines.upper() == "YES"
                    else ""
                }
    {");" if rtpx == "X" else ""}
* Reset bounds
    {
                    bndmain_mod(
                        arg1=arg1,
                        arg2="1",
                        var=var,
                        swd=swd,
                        sow=sow,
                        swt=swt,
                        r_t=r_t,
                        stages=stages,
                        timesed=timesed,
                        reduce=reduce,
                        dflbl=dflbl,
                        mx=mx,
                        pgprim=pgprim,
                        eotime=eotime,
                        cufscal=cufscal,
                        cucscal=cucscal,
                        macro=macro,
                        var_uc=var_uc,
                        rts=rts,
                        model_name=self.model_name,
                        bnd_ucw_defined=bnd_ucw_defined,
                        stochastic_symbols_declared=stochastic_symbols_declared,
                    )
                }
""",
            )

    def exec_solve_stp_nonstepped_after_solve(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="  PRESOL = 0;",
        )

    def exec_solve_stp_cleanup(
        self: SolveStp, var: str, sow: str, swt: str, eq: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Remove superfluous values
{var}_NCAP.L(R,T,P{sow})$(({var}_NCAP.L(R,T,P{sow}) EQ 0)${var}_NCAP.L(R,T,P{sow})) = 0;
{var}_NCAP.M(R,T,P{sow})$NO_RT(R,T) = 0;
{var}_ACT.M(R,V,T,P,S{sow})$NO_RT(R,T) = 0;
{var}_FLO.M(R,V,T,P,C,S{sow})$NO_RT(R,T) = 0;
{var}_IRE.M(R,V,T,P,C,S,IE{sow})$NO_RT(R,T) = 0;
IF(MY_FYEAR,{eq}_IRE.M(IRE_FXT(R,T,P),C,IE,S{swt}) $= PAR_IPRIC(R,T,P,C,S,IE));
""",
        )
