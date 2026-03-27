# equcrtp_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * EQ_UCRTP.MOD : Annual bounds for process dynamic development                 *
# *==============================================================================*
# * arg1 - jump label
# * arg2 - eq. declaration type
# * arg3 - eq. definition type
# * arg4 - bound type


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from core.prepparm_gms import prepparm

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

Phases = Literal["INIT_EXT", "PREP_EXT", "PPM_EXT", "EQU_EXT"]


class EqucrtpVda(GamsClass):
    """Translation unit for equcrtp.vda."""

    # Instance attributes
    module_name: str = "equcrtp_vda"
    gams_source: str = "equcrtp.vda"

    def __init__(
        self: EqucrtpVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Literal[Phases] = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self._sub_modules = {}
        self.compile()

    def compile(self: EqucrtpVda) -> None:
        if self.arg1 == "INIT_EXT":
            self.tc.enqueue(self.init_ext)
        elif self.arg1 == "PREP_EXT":
            self.label_prep_ext()
        elif self.arg1 == "PPM_EXT":
            self.tc.enqueue(self.ppm_ext)
        elif self.arg1 == "EQU_EXT":
            self.label_equ_ext()

    def init_ext(self: EqucrtpVda):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Move dynamic bounds to dedicated attribute
  IF(CARD(UC_DYNBND), OPTION CLEAR=UNCD1; LOOP(UC_DYNBND(UCN,BD),UNCD1(UCN)=YES);
    PRC_DYNUC(UC_N,SIDE,R,LL,P,'CAP',BD)$UC_DYNBND(UC_N,BD) $= UC_CAP(UC_N,SIDE,R,LL,P);
    PRC_DYNUC(UC_N,SIDE,R,LL,P,'NCAP',BD)$UC_DYNBND(UC_N,BD) $= UC_NCAP(UC_N,SIDE,R,LL,P);
    PRC_DYNUC(UC_N,SIDE,R,LL,P,'ACT',BD)$UC_DYNBND(UC_N,BD) $= UC_ACT(UC_N,SIDE,R,LL,P,'ANNUAL');
    UC_COM(UC_N(UNCD1),'NET',SIDE,R,LL,C,ANNUAL(S),'UCN') $= UC_COMNET(UC_N,SIDE,R,LL,C,S);
    UC_COM(UC_N(UNCD1),'PRD',SIDE,R,LL,C,ANNUAL(S),'UCN') $= UC_COMPRD(UC_N,SIDE,R,LL,C,S);
    UC_CAP(UC_N(UNCD1),SIDE,R,LL,P) = 0;
    UC_NCAP(UC_N(UNCD1),SIDE,R,LL,P) = 0;
    UC_ACT(UC_N(UNCD1),SIDE,R,LL,P,S) = 0;
    UC_COMPRD(UC_N(UNCD1),SIDE,R,LL,C,S) = 0;
    UC_COMNET(UC_N(UNCD1),SIDE,R,LL,C,S) = 0;
* Set LHS default IE to 5 and RHS default to 10
    UC_COM(UCN(UNCD1),COM_VAR,'LHS',R,LL--ORD(LL),C,S,'UCN')$((NOT UC_COM(UCN,COM_VAR,'LHS',R,'0',C,S,'UCN'))$UC_COM(UCN,COM_VAR,'LHS',R,LL,C,S,'UCN'))=5;
    UC_COM(UCN(UNCD1),COM_VAR,'RHS',R,LL--ORD(LL),C,S,'UCN')$((NOT UC_COM(UCN,COM_VAR,'RHS',R,'0',C,S,'UCN'))$UC_COM(UCN,COM_VAR,'RHS',R,LL,C,S,'UCN'))=
      UC_COM(UCN,COM_VAR,'LHS',R,'0',C,S,'UCN')+10$(NOT UC_COM(UCN,COM_VAR,'LHS',R,'0',C,S,'UCN'));
* If no RHS/LHS defined, set it to EPS/1 for all other side years except for the IE option as on other side
    UC_COM(UCN,COM_VAR,'RHS',R,LL,C,S,'UCN')$((NOT UC_COM(UCN,COM_VAR,'RHS',R,'0',C,S,'UCN'))$UC_COM(UCN,COM_VAR,'LHS',R,LL,C,S,'UCN'))=
      EPS$(NOT MIYR_1(LL))+UC_COM(UCN,COM_VAR,'LHS',R,LL,C,S,'UCN')$LASTLL(LL);
    UC_COM(UCN,COM_VAR,'LHS',R,LL,C,S,'UCN')$((NOT UC_COM(UCN,COM_VAR,'LHS',R,'0',C,S,'UCN'))$UC_COM(UCN,COM_VAR,'RHS',R,LL,C,S,'UCN'))=
      (1+(UC_COM(UCN,COM_VAR,'RHS',R,LL,C,S,'UCN')-1)$LASTLL(LL));
  );
""",
        )

    def label_prep_ext(self: EqucrtpVda):
        self.env.set_scoped("reset", 1)
        self.tc.enqueue(
            self.manipulate_lhs_and_rhs,
            dflbl=self.env.dflbl,
            def_iebd=self.env.def_iebd,
            reset=self.env.reset,
        )

    def manipulate_lhs_and_rhs(self: EqucrtpVda, dflbl: str, def_iebd: str, reset: str):
        code = rf"""
IF(CARD(PRC_DYNUC),
*  Set LHS default IE to 5 and RHS default to 10
   PRC_DYNUC(UC_N,'LHS',R,LL--ORD(LL),P,UC_GRPTYPE,BD)$((NOT PRC_DYNUC(UC_N,'LHS',R,'0',P,UC_GRPTYPE,BD))$PRC_DYNUC(UC_N,'LHS',R,LL,P,UC_GRPTYPE,BD))=5;
   PRC_DYNUC(UC_N,'RHS',R,LL--ORD(LL),P,UC_GRPTYPE,BD)$((NOT PRC_DYNUC(UC_N,'RHS',R,'0',P,UC_GRPTYPE,BD))$PRC_DYNUC(UC_N,'RHS',R,LL,P,UC_GRPTYPE,BD))=
     PRC_DYNUC(UC_N,'LHS',R,'0',P,UC_GRPTYPE,BD)+10$(NOT PRC_DYNUC(UC_N,'LHS',R,'0',P,UC_GRPTYPE,BD));
   LOOP(BD, UC_GMAP_P(R,UC_N,UC_GRPTYPE,P)$PRC_DYNUC(UC_N,'RHS',R,'0',P,UC_GRPTYPE,BD) = YES);
*  If no RHS defined, set RHS to EPS for all LHS years except for the IE option according to LHS
   PRC_DYNUC(UC_N,'RHS',R,LL,P,UC_GRPTYPE,BD)$((NOT PRC_DYNUC(UC_N,'RHS',R,'0',P,UC_GRPTYPE,BD))$PRC_DYNUC(UC_N,'LHS',R,LL,P,UC_GRPTYPE,BD))=
     EPS+PRC_DYNUC(UC_N,'LHS',R,LL,P,UC_GRPTYPE,BD)$LASTLL(LL);
*  If no LHS defined, set LHS to 1 for all RHS years except for the IE option according to RHS
   PRC_DYNUC(UC_N,'LHS',R,LL,P,UC_GRPTYPE,BD)$((NOT PRC_DYNUC(UC_N,'LHS',R,'0',P,UC_GRPTYPE,BD))$PRC_DYNUC(UC_N,'RHS',R,LL,P,UC_GRPTYPE,BD))=
     (1+(PRC_DYNUC(UC_N,'RHS',R,LL,P,UC_GRPTYPE,BD)-1)$LASTLL(LL))$(NOT SAMEAS('NCAP',UC_GRPTYPE));

     {
            prepparm(
                arg1="PRC_DYNUC",
                arg2="UC_N,SIDE,R",
                arg3="P,UC_GRPTYPE,BD",
                arg4="",
                arg5="T",
                arg6="1",
                arg7="1",
                arg8="",
                arg9="",
                arg10="",
                dflbl=dflbl,
                def_iebd=def_iebd,
                reset=reset,
            )
        }

*  Disable growth/decay equation in first period of availability if no constant specified
   PRC_DYNUC(UCN,RHS,RTP(R,TT(T+1),P),UC_GRPTYPE,BD)$((RTP(R,T,P)->MIYR_1(TT))$(NOT UC_GMAP_P(R,UCN,UC_GRPTYPE,P))$PRC_DYNUC(UCN,'LHS',R,'0',P,UC_GRPTYPE,BD)) = 0;
*  Set final UC_GMAPs for REDUCE
   LOOP(BD,UC_JMAP('1',UCN,RHS,R,T(MIYR_1),P,UC_GRPTYPE)$PRC_DYNUC(UCN,RHS,R,'0',P,UC_GRPTYPE,BD) = YES);
  );
  LOOP(UC_DYNBND(UCN,BD),UC_T_SUCC(R,UCN,'0') = YES);

"""

        self.tc.add_gams_code(module=self, phase="run", code=code)

    def disable_growth(self: EqucrtpVda):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*  Disable growth/decay equation in first period of availability if no constant specified
   PRC_DYNUC(UCN,RHS,RTP(R,TT(T+1),P),UC_GRPTYPE,BD)$((RTP(R,T,P)->MIYR_1(TT))$(NOT UC_GMAP_P(R,UCN,UC_GRPTYPE,P))$PRC_DYNUC(UCN,'LHS',R,'0',P,UC_GRPTYPE,BD)) = 0;
*  Set final UC_GMAPs for REDUCE
   LOOP(BD,UC_JMAP('1',UCN,RHS,R,T(MIYR_1),P,UC_GRPTYPE)$PRC_DYNUC(UCN,RHS,R,'0',P,UC_GRPTYPE,BD) = YES);
  );
  LOOP(UC_DYNBND(UCN,BD),UC_T_SUCC(R,UCN,'0') = YES);
""",
        )

    def ppm_ext(self: EqucrtpVda):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Make sure that standard UCs are not generated
  LOOP(UC_DYNBND(UCN,BD),
    UC_ON(R,UCN) = NO;
    UC_R_SUM(R,UCN) = NO;
    UC_R_EACH(R,UCN) = NO;
  );
""",
        )

    def label_equ_ext(self: EqucrtpVda):
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{self.env.eq}{self.arg2}_UCRTP(UC_N,RTP({self.env.r_t},P),UC_GRPTYPE,BD({self.arg4}) {self.env.swt})$(PRC_DYNUC{self.env.mx}(UC_N,'RHS',R,T,P,UC_GRPTYPE,BD))..

*-------
* Difference in capacity between previous and current period
  (SUM(SAMEAS(T-1,V(TT))$RTP(R,V,P), POWER(PRC_DYNUC(UC_N,'LHS',R,T,P,UC_GRPTYPE,BD),LEAD(T)) *
     {self.env.varv}_CAP(R,V,P {self.env.swt}))*(1-2$BDUPX(BD))
   -  {self.env.var}_CAP(R,T,P {self.env.sow}) *(1-2$BDUPX(BD)))$SAMEAS('CAP',UC_GRPTYPE)
*-------
  +
* Difference in NCAP between previous and current period
  (SUM(SAMEAS(T-1,V(TT))$RTP(R,V,P), POWER(PRC_DYNUC(UC_N,'LHS',R,T,P,UC_GRPTYPE,BD),LEAD(T)) *
     {self.env.varv}_NCAP(R,V,P {self.env.swt}))*(1-2$BDUPX(BD))
   -  {self.env.var}_NCAP(R,T,P {self.env.sow}) *(1-2$BDUPX(BD)))$SAMEAS('NCAP',UC_GRPTYPE)
*-------
  +
* Difference in ACT between previous and current period
  (SUM(SAMEAS(T-1,V(TT))$RTP_VARA(R,V,P), POWER(PRC_DYNUC(UC_N,'LHS',R,T,P,UC_GRPTYPE,BD),LEAD(T)) *
       SUM((RTP_VINTYR(R,MODLYEAR,V,P),PRC_TS(R,P,S)),{self.env.vartt}_ACT(R,MODLYEAR,V,P,S {self.env.swt})))*(1-2$BDUPX(BD))
   -   SUM((RTP_VINTYR(R,MODLYEAR,T,P),PRC_TS(R,P,S)),  {self.env.var}_ACT(R,MODLYEAR,T,P,S {self.env.sow})) *(1-2$BDUPX(BD)))$SAMEAS('ACT',UC_GRPTYPE)

  ={self.arg3}=

* RHS constant term
  PRC_DYNUC(UC_N,'RHS',R,T,P,UC_GRPTYPE,BD)*LEAD(T)*(-1+2$BDUPX(BD))
  ;
""",
        )
        if self.arg2.upper() == "E":
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{self.env.eq}{self.arg2}_UCRTC(UC_N,COM_VAR,RTC({self.env.r_t},C),ANNUAL(S),BD({self.arg4}) {self.env.swt})$(UC_COM(UC_N,COM_VAR,'RHS',RTC,S,'UCN')$UC_DYNBND(UC_N,BD))..

*-------
* Difference in COMNET between previous and current period
  (SUM(SAMEAS(T-1,Y(TT))$RTC(R,Y,C), POWER(UC_COM(UC_N,COM_VAR,'LHS',RTC,S,'UCN'),LEAD(T)) *
     SUM(RHS_COMBAL(R,Y,C,S),{self.env.vartt}_COMNET(R,Y,C,S {self.env.sws})))*(1-2$BDUPX(BD))
   - SUM(RHS_COMBAL(R,T,C,S),  {self.env.var}_COMNET(R,T,C,S {self.env.sow})) *(1-2$BDUPX(BD)))$SAMEAS('NET',COM_VAR)
*-------
  +
* Difference in COMPRD between previous and current period
  (SUM(SAMEAS(T-1,Y(TT))$RTC(R,Y,C), POWER(UC_COM(UC_N,COM_VAR,'LHS',RTC,S,'UCN'),LEAD(T)) *
     SUM(RHS_COMPRD(R,Y,C,S),{self.env.vartt}_COMPRD(R,Y,C,S {self.env.sws})))*(1-2$BDUPX(BD))
   - SUM(RHS_COMPRD(R,T,C,S),  {self.env.var}_COMPRD(R,T,C,S {self.env.sow})) *(1-2$BDUPX(BD)))$SAMEAS('PRD',COM_VAR)

  ={self.arg3}=

* RHS constant term
  UC_COM(UC_N,COM_VAR,'RHS',R,T,C,S,'UCN')*LEAD(T)*(-1+2$BDUPX(BD))
  ;
""",
        )
