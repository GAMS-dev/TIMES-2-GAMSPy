# powerflo_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Powerflo - define powerflow equations and nodal balance costs
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Equation, Number, Parameter, Set, Sum, Variable

from core.base_class import GamsClass
from core.cal_red_red import cal_red_red
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.gasgrids_vda import GasgridsVda
from core.pp_lvlfc_mod import PpLvlfcMod, PpLvlfcModConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PowerfloVda(GamsClass):
    """Translation unit for powerflo.vda."""

    # Instance attributes
    module_name: str = "powerflo_vda"
    gams_source: str = "powerflo.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.env.set_scoped("mx", f"{self.arg3}")
        if self.arg3 == "":
            self.env.set_scoped("mx_GP", ())
        else:
            raise ValueError("Double check MX variable. Not implemented")
        self.env.set_scoped("pdtol", "1E-5")
        self.env.set_scoped("bigm", "10")

        if self.arg1 == "":
            # this ends with a $EXIT so we flip the if to keep the layout
            self.declaration1()
            self.tc.enqueue(self.exec1)
            # * levelization
            self.include(
                PpLvlfcMod(
                    self.tc,
                    self.env,
                    config=PpLvlfcModConfig(
                        arg1=g.gr_demfr,
                        arg2=(g.c,),
                        arg3=g.ComTs,
                        arg4=(),
                        arg5=("0", "0", "0", "0"),
                        arg6=g.allts,
                        arg7=(g.t,),
                        arg8=g.Rtc[g.r, g.t, g.c],
                    ),
                )
            )
            self.tc.enqueue(self.exec2)
            self.env.set_scoped("tmp", "0")
            if f"{self.env.dsc}{self.env.solmip}".upper() == "YESYES":
                self.env.set_scoped("tmp", "NCAP_DISC(r,v,p,u)")
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
$ MACRO GR_DUNIT(r,v,p,u) {self.env.tmp}
""",
            )
            if self.env.tmp != "0":
                self.env.set_scoped("tmp", "PRC_DSCNCAP(r,p)")

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
$ MACRO GR_DNCAP(r,p) {self.env.tmp}
""",
            )

            if self.env.tmp != "0":
                self.env.set_scoped("tmp", "1")
                self.tc.enqueue(self.exec3, tmp=self.env.tmp)

            self.tc.enqueue(
                self.complete_ptfd_processing,
                pdtol=self.env.pdtol,
                tmp=self.env.tmp,
            )

            self.include(GasgridsVda(self.tc, self.env))

        else:  # $GOTO %1%2%3
            label = f"{self.arg1}{self.arg2}{self.arg3}"
            if label == "PREP":
                # ends with $EXIT
                if not self.tc.defined("PRC_REACT"):
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code=r"""$CLEAR PRC_REACT""",
                    )
                # fmt: off
                batincludes: list[FillparmGmsConfig] = [
                    FillparmGmsConfig(g.prc_react, (g.r, ), (g.p,),                   ("0",) * 5, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_ptdf,   (g.r, ), (g.p, g.c, g.Reg, g.Com), ("0",) * 2, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_demfr,  (g.r, ), (g.c, g.s),               ("0",) * 4, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_endfr,  (g.r, ), (g.c, g.Com),             ("0",) * 4, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_genfr,  (g.r, ), (g.c, g.item),            ("0",) * 4, g.t, Number(1), Number(0)),
                ]
                # fmt: on
                for config in batincludes:
                    self.include(FillparmGms(self.tc, self.env, config))

                self.include(
                    FilparamGms(
                        self.tc,
                        self.env,
                        FilparamGmsConfig(
                            src=g.gr_xbnd,
                            arg2=(g.r,),
                            tail1=(),
                            arg4=("0", "0", "0", "0", "0"),
                            arg5=g.Datayear,
                            arg6=g.t,
                        ),
                    )
                )

                if self.tc.gg_kgf.number_records == 0:
                    return

                # fmt: off
                fillparam_batincludes: list[FillparmGmsConfig] = [
                    FillparmGmsConfig(g.gg_gamma,  (g.r,), (g.p, g.c),            ("0",) * 4, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_kgf,    (g.r,), (g.p, g.c),            ("0",) * 4, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_klp,    (g.r,), (g.p, g.c),            ("0",) * 4, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_pp,     (g.r,), (g.p, g.c, g.bd, g.j), ("0",) * 2, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_prbd,   (g.r,), (g.c, g.lA),           ("0",) * 4, g.t, Number(1),            Number(0)),
                ]
                # fmt: on
                for config in fillparam_batincludes:
                    self.include(FillparmGms(self.tc, self.env, config))

            elif label == "DECL":
                # ends with $EXIT
                self.declaration2(
                    var=self.env.var,
                    swd=self.env.swd,
                    eq=self.env.eq,
                    swtd=self.env.swtd,
                )
                self.env.set_global("ireauxbal", "$BATINCLUDE powerflo.vda IREAUX")
                self.tc.enqueue(
                    self.exec4,
                    var=self.env.var,
                    sow=self.env.sow,
                )
                if self.tc.defined("VAR_GRVIRT"):
                    return

                self.env.set_scoped("tmp", "0")
                if f"{self.env.dsc}{self.env.solmip}".upper() == "YESYES":
                    self.env.set_scoped(
                        "tmp",
                        f"SUM((VNT(TT(V),T),UNIT)$((NCAP_DISC(r,v,p,unit)>0)$RTP(r,v,p)),{self.env.varv}_DNCAP(r,v,p{self.env.sws},unit)*(1-MAX((1-COEF_CPT(r,v,t,p))/{self.env.bigm},(1-COEF_CPT(r,v,t,p))**4)))",
                    )
                self.comp1(
                    tmp=self.env.tmp,
                    var=self.env.var,
                    sow=self.env.sow,
                    pgprim=self.env.pgprim,
                )
                self.tc.enqueue(
                    self.exec5,
                    var=self.env.var,
                    sow=self.env.sow,
                )

                self.include(GasgridsVda(self.tc, self.env, "DECL"))

            elif label == "POWFLO":
                # ends with $EXIT
                self.dc_power_flow_eqs(
                    eq=self.env.eq,
                    r_t=self.env.r_t,
                    swt=self.env.swt,
                    var=self.env.var,
                    sow=self.env.sow,
                    bigm=self.env.bigm,
                    varv=self.env.varv,
                    sws=self.env.sws,
                    pgprim=self.env.pgprim,
                    def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                )
                self.include(GasgridsVda(self.tc, self.env, arg1="MODEL"))

            elif label == "IREAUXOUT":
                pass  # end of file

            elif label == "CSTBAL":
                # ends with $EXIT
                self.comp2()
                if self.tc.defined("RC_GRID"):
                    self.tc.enqueue(self.exec6)
                # * levelization
                self.include(
                    PpLvlfcMod(
                        self.tc,
                        self.env,
                        config=PpLvlfcModConfig(
                            arg1=g.com_cstbal,
                            arg2=(g.c,),
                            arg3=g.ComTs,
                            arg4=(g.item, g.cur),
                            arg5=("0", "0"),
                            arg6=g.allts,
                            arg7=(g.t,),
                            arg8=g.Rtc[g.r, g.t, g.c],
                            arg11="N",
                        ),
                    )
                )
                self.tc.enqueue(self.exec7)

            elif label == "OBJBAL":
                # ends with $EXIT
                self.env.set_scoped(
                    "tpulse", "TT$OBJ_LINT(R,T,TT,CUR),OBJ_LINT(R,T,TT,CUR)"
                )
                # needed because it is set inside the equation definition
                self.env.set_scoped("sowpre", self.env.sow)
                if self.env.stages == "YES":
                    self.env.set_scoped("sow", ",WW")
                    self.env.set_scoped("sow_GP", (g.ww,))
                self.eq_objbal(
                    sowpre=self.env.sowpre,
                    var=self.env.var,
                    swd=self.env.swd,
                    swx=self.env.swx,
                    swsw=self.env.swsw,
                    sow=self.env.sow,
                    tpulse=self.env.tpulse,
                    condition=self.env.stages == "YES",
                    cal_red=self.env.cal_red,
                    pgprim=self.env.pgprim,
                    def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                )

            elif label == "RPTB":
                # ends with $EXIT
                self.tc.enqueue(
                    self.exec_powerflo_vda_rptb,
                    arg4=self.arg4,
                    arg5=self.arg5,
                    arg6=self.arg6,
                    var=self.env.var,
                    vart=self.env.vart,
                    sws=self.env.sws,
                )

            elif label == "IREAUXIN-" or label == "IREAUXOUT":
                pass  # end of file

    def declaration1(self: PowerfloVda) -> None:
        g = self.tc
        m = g.container
        # * Declarations
        g.RpGrid = Set(m, name="RP_GRID", domain=[g.r, g.p])
        g.RcGrid = Set(m, name="RC_GRID", domain=[g.r, g.t, g.c])
        g.GrTop = Set(m, name="GR_TOP", domain=[g.allreg, g.c, g.allreg, g.c, g.p])
        g.GrArc = Set(m, name="GR_ARC", domain=[g.allreg, g.c, g.allreg, g.c])
        g.GrGrid = Set(m, name="GR_GRID", domain=[g.j, g.r, g.Com])
        g.GrAllmap = Set(m, name="GR_ALLMAP", domain=[g.r, g.cg, g.Com])
        g.GrPrcmap = Set(m, name="GR_PRCMAP", domain=[g.r, g.p, g.c, g.item])
        g.GrDemmap = Set(m, name="GR_DEMMAP", domain=[g.r, g.c, g.Com])
        g.GrAlgmap = Set(m, name="GR_ALGMAP", domain=[g.r, g.cg, g.cg])
        g.GrEndc = Set(m, name="GR_ENDC", domain=[g.r, g.cg])
        g.GrGenp = Set(m, name="GR_GENP", domain=[g.r, g.p])
        g.GrCandid = Set(m, name="GR_CANDID", domain=[g.r, g.year, g.p])
        g.GrGnall = Set(m, name="GR_GNALL", domain=[g.r, g.t, g.c])
        g.gr_sus = Parameter(
            m, name="GR_SUS", domain=[g.allreg, g.t, g.c, g.allreg, g.c]
        )
        g.gr_flow = Parameter(m, name="GR_FLOW", domain=[g.r, g.p, g.c])
        g.gr_gid = Parameter(m, name="GR_GID", domain=[g.r, g.c])
        g.gr_admit = Parameter(
            m, name="GR_ADMIT", domain=[g.allreg, g.t, g.c, g.allreg, g.c]
        )
        g.gr_units = Parameter(m, name="GR_UNITS", domain=[g.r, g.t, g.item])
        g.gr_capup = Parameter(m, name="GR_CAPUP", domain=[g.r, g.year, g.p])

    def exec1(self: PowerfloVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Define grid and default line directions
  NRGELC(RC(R,C))$COM_TMAP(R,'NRG',C) $= NRG_TMAP(R,'ELC',C);
  TRACKP(R,P) $= SUM(RPC_IRE(R,P,C,IE)$NRGELC(R,C),1);
  PRC_REACT(R,LL,P)$(NOT TRACKP(R,P)) = 0;
  OPTION TRACKC <= GR_DEMFR, GR_GID <= GR_ENDFR;
  GR_GID(TRACKC)=1; OPTION TRACKC < GG_PRBD; GR_GID(TRACKC)=1;
  LOOP((R,LL,C,ITEM)$GR_GENFR(R,LL,C,ITEM),GR_GID(R,C)=1);
  OPTION CLEAR=TRACKC, TRACKP < PRC_REACT, RP_PRC < GR_PTDF;
  DFUNC=CARD(RP_PRC); TRACKP(RP_PRC)=YES;
  TRACKC(R,C) $= SUM(NRG_GMAP(R,NRG_GRID,C),1);
* Add any IRE between add-on nodes
  LOOP(RPC_IRE(R,P,C,IE)$GR_GID(R,C),TRACKP(R,P)=YES);
  GR_TOP(TOP_IRE(R,C,TRACKC(REG,COM),P))$(TRACKC(R,C)$TRACKP(R,P)) = YES;
  GR_TOP(TOP_IRE(TRACKC(REG,COM),R,C,P))$(TRACKC(R,C)$TRACKP(R,P)) = YES;
  LOOP(GR_TOP(R,C,REG,COM,P),GR_FLOW(R,P,C)=GR_FLOW(R,P,C)*2+1; GR_FLOW(REG,P,COM)=GR_FLOW(REG,P,COM)*2-1);
  OPTION CLEAR=TRACKP, CLEAR=RP_PRC, RP_GRID < GR_FLOW;
  GR_TOP(R,C,REG,COM,P)$(GR_FLOW(R,P,C) < 0) = NO;
  GR_TOP(R,C,R,C,P) = NO;
  LOOP(GR_TOP(R,C,R,COM,P)$SUM(RPC_IRE(RPC_PG(R,P,C),IE),RPC_PG(R,P,COM)),PRC_MAP(R,'DISTR',P)=YES);
* Synchronize and check for zero line reactances
  LOOP(GR_TOP(R,C,REG,COM,P),F=1;
    IF(NOT SAMEAS(R,REG),RP_PRC(REG,P)=YES; F=0;
      RTP_VARA(RTP(R,T,P))$(NOT RTP_VARA(REG,T,P)) = NO;
      PRC_REACT(R,T,P) = MAX(PRC_REACT(R,T,P),PRC_REACT(REG,T,P)));
    IF(NOT SAMEAS(C,COM)$F,
      GR_PTDF(R,T,P,C,ALL_R,COM2)$GR_PTDF(REG,T,P,COM,ALL_R,COM2) =
        MAX(ABS(GR_PTDF(R,T,P,C,ALL_R,COM2)),ABS(GR_PTDF(REG,T,P,COM,ALL_R,COM2)))*SIGN(2*SIGN(GR_PTDF(R,T,P,C,ALL_R,COM2)-SIGN(GR_PTDF(REG,T,P,COM,ALL_R,COM2))));
      GR_PTDF(REG,T,P,COM,ALL_R,COM2) = -GR_PTDF(R,T,P,C,ALL_R,COM2)));
  PRC_REACT(R,T,P)$((PRC_REACT(R,T,P) LE 0)$PRC_REACT(R,T,P)) = 0;
  LOOP(GR_TOP(R,C,REG,COM,P), GR_ARC(R,C,REG,COM) = YES);
  OPTION TRACKC < GR_FLOW;

* Internodal admittance
  OPTION GR_GID <= GR_PTDF; LOOP(RPC_IRE(R,P,C,IE)$GR_GID(R,C),PRC_REACT(R,T,P) = 0);
  GR_ADMIT(R,T,C,REG,COM)$GR_ARC(R,C,REG,COM) = SUM(GR_TOP(R,C,REG,COM,P)$(PRC_REACT(R,T,P)$RTP_VARA(R,T,P)),1/PRC_REACT(R,T,P));
  OPTION RREG <= GR_ARC;

* Construct all disjoint grids
  CNT = EPS; OPTION CLEAR=GR_GID;
  LOOP(GR_ARC(R,C,REG,COM), F = GR_GID(R,C); Z = GR_GID(REG,COM);
   IF(NOT F+Z, GR_GID(R,C)=CNT; GR_GID(REG,COM)=CNT; CNT=CNT+1;
   ELSEIF NOT F, GR_GID(R,C)=Z;
   ELSEIF NOT Z, GR_GID(REG,COM)=F;
   ELSEIF F NE Z, MY_F=MIN(F,Z); DONE=MAX(F,Z); IF(CNT=DONE+1,CNT=DONE);
     GR_GID(TRACKC)$(GR_GID(TRACKC)=DONE) = MY_F));
* Assign each node with unique grid ID
  LOOP(SAMEAS('1',J),GR_GRID(J+GR_GID(R,C),TRACKC(R,C)) = YES);
* GR_GID holds the reactance grid nodes only
  OPTION GR_GID <= GR_PTDF; GR_GID(TRACKC) = NOT GR_GID(TRACKC);

* QA checks - for reactance nodes only
  TRACKPC(RP_GRID(R,P),C)$GR_FLOW(R,P,C) $= GR_GID(R,C);
  LOOP((R,TSL('DAYNITE')), Z=0;
   IF(SUM(TRACKPC(R,P,C)$(NOT PRC_TSL(R,P,TSL)$COM_TSL(R,C,TSL)),1),Z=1);
   LOOP(RREG(R,REG),
     IF(SUM(S$(TS_GROUP(R,TSL,S) XOR TS_GROUP(REG,TSL,S)),1),
        TRACKC(NRGELC(REG,C))$GR_GID(REG,C)=NO; Z = 1));
   IF(Z,TRACKC(NRGELC(R,C))$GR_GID(R,C)=NO));
  RC_GRID(RTC(R,T,C))$TRACKC(R,C) = YES;
* Collect RP_GRID for PTDF grids
  OPTION TRACKPC <= GR_PTDF; TRACKPC(R,P,C)$GR_GID(R,C) = NO;
  OPTION RP_GRID < TRACKPC, CLEAR=TRACKPC, CLEAR=TRACKP;

* Admittance / susceptance matrix
  option gr_sus < gr_admit;
  gr_sus(rc_grid,rc) $= gr_admit(rc_grid,rc)*(-1);
  gr_sus(rc_grid(r,t,c),r,c) = -sum(trackc(rc),gr_sus(rc_grid,rc));
  """,
        )

    def exec2(self: PowerfloVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Preliminaries
  GR_ENDFR(R,T,COM,C)$TRACKC(R,C) = 0;
  OPTION CLEAR=RXX, GR_GENP < GR_GENMAP, GR_ENDC < GR_ENDFR;
  GR_GENLEV(TRACKC) = 0;
  GR_GENLEV(R,C)$GR_GENLEV(R,C) = ROUND(GR_GENLEV(R,C));
  TRACKPC(RPC(GR_GENP(R,P),C))$GR_GENLEV(R,C)=YES;
  GR_PRCMAP(TRACKPC(R,P,C),ITEM)$(TOP(R,P,C,'OUT')$GR_GENMAP(R,P,ITEM))=YES;
  GR_PRCMAP(TRACKPC(RP_IRE(R,P),C),ITEM)$GR_GENMAP(R,P,ITEM)=YES;
  GR_GENFR(R,LL--ORD(LL),C,ITEM)$GR_GENFR(R,LL,C,ITEM)=1;
  LOOP((GR_GRID(J,R,C),ITEM)$GR_GENFR(R,'0',C,ITEM),LOOP(GR_PRCMAP(R,P,COM,ITEM),RXX(R,J,COM)=YES));
  LOOP(RXX(R,J,COM), GR_ALLMAP(TRACKC(R,C),COM)$GR_GRID(J,R,C)=YES);
  LOOP(NRG_GRID,GR_ALLMAP(R,C,COM)$((NOT NRG_GMAP(R,NRG_GRID,C))$NRG_GMAP(R,NRG_GRID,COM)) = NO);
* Grid allocations
  GR_ALGMAP(R,'NRG',C)$((GR_GENLEV(R,C)=1)$GR_GENLEV(R,C))=YES;
  GR_ALGMAP(R,C,C)$((GR_GENLEV(R,C)=2)$GR_GENLEV(R,C))=YES;
  GR_ALGMAP(R,COM_TYPE(CG),CG)$(SUM(TRACKC(R,C),1)>1) $= SUM(GR_ALGMAP(R,CG,C),1);
  GR_DEMMAP(GR_ALLMAP(R,C,COM))$(GR_GENLEV(R,COM) < 3) = YES;
  IF(CARD(GR_DEMFR),GR_DEMFR(RTCS_VARC(RC_GRID(R,T,C),S)) = GR_DEMFR(R,T,C,S)+EPS);
  GR_ENDC(R,'DEM')$SUM(GR_ENDC(R,C),1) = YES;
* Process regions with sectoral demand fractions
  LOOP(R$GR_ENDC(R,'DEM'),
    GR_DEMFR(RTCS_VARC(RC_GRID(R,T,C),S)) = SUM(GR_ENDC(R,COM),MIN(0.33,GR_ENDFR(R,T,C,COM)));
    GR_UNITS(RTC(R,T,COM))$GR_ENDC(R,COM) = SUM(RC_GRID(R,T,C),GR_ENDFR(R,T,C,COM))+1-1;
    GR_ENDFR(RC_GRID(R,T,C),COM)$GR_UNITS(R,T,COM) = GR_ENDFR(R,T,C,COM)/GR_UNITS(R,T,COM);
    OPTION CLEAR=GR_UNITS;
  );
  GR_ENDC(R,C)$((GR_GENLEV(R,C)>2)$GR_GENLEV(R,C)) = YES;
  GR_ENDC(R,'NRG')$(NOT GR_ENDC(R,'DEM')) = YES;
* Genmap normalization
  PRC_YMAX(GR_GENP(R,P)) = SUM(ITEM$GR_GENMAP(R,P,ITEM),GR_GENMAP(R,P,ITEM))+1-1;
  GR_GENMAP(GR_GENP(R,P),ITEM)$(PRC_YMAX(R,P)$GR_GENMAP(R,P,ITEM)) = GR_GENMAP(R,P,ITEM)/PRC_YMAX(R,P);
* GENFR normalization
  LOOP(RC_GRID(R,T,C),GR_UNITS(R,T,ITEM)$GR_GENFR(R,T,C,ITEM)=1);
  GR_UNITS(R,T,ITEM)$GR_UNITS(R,T,ITEM) = SUM(TRACKC(R,C),GR_GENFR(R,T,C,ITEM))+1-1;
  GR_GENFR(RC_GRID(R,T,C),ITEM)$GR_UNITS(R,T,ITEM) = GR_GENFR(R,T,C,ITEM)/GR_UNITS(R,T,ITEM);
  OPTION CLEAR=PRC_YMAX,CLEAR=GR_UNITS;
* DEMFR normalization
  LOOP(RC_GRID(R,T,C),GR_UNITS(R,T,S)$GR_DEMFR(R,T,C,S)=1);
  GR_UNITS(R,T,S)$GR_UNITS(R,T,S) = SUM(TRACKC(R,C),GR_DEMFR(R,T,C,S))+1-1;
  GR_DEMFR(RC_GRID(R,T,C),S)$GR_UNITS(R,T,S) = GR_DEMFR(R,T,C,S)/GR_UNITS(R,T,S)+EPS;
  OPTION CLEAR=GR_UNITS,CLEAR=RXX;
* Find and remove node with max demand fraction from GR_DEMFR
  LOOP(J$SUM(GR_GRID(J,R,C),1),
    GR_UNITS(RC_GRID(R,T,C))$GR_GRID(J,R,C) = SUM(COM_TS(R,C,S),GR_DEMFR(R,T,C,S));
    LOOP((R,T), Z=MAX(EPS,SMAX(GR_GRID(J,R,C),GR_UNITS(R,T,C)));
      LOOP(GR_GRID(J,R,C)$Z,IF(GR_UNITS(R,T,C)=Z,RXX(R,T,C)=YES;Z=0)));
    GR_DEMFR(RXX(R,T,C),S)=0;
    IF(SUM(GR_ALLMAP(R,C,COM)$GR_GRID(J,R,C),1),GR_GNALL(RC_GRID(R,T,C))$GR_GRID(J,R,C) = YES));
  """,
        )

    def exec3(self: PowerfloVda, tmp: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{tmp}$PRC_YMAX(R,P) = NO;
""",
        )

    def complete_ptfd_processing(self: PowerfloVda, pdtol: str, tmp: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Complete PTDF processing
  IF(DFUNC, OPTION GR_ARC <= GR_TOP, CLEAR=GR_CANDID;
    GR_PTDF(R,T,P,C,ALL_R,COM)$RP_PRC(R,P)=0;
    GR_PTDF(R,T,P,C,ALL_R,COM)$((ABS(GR_PTDF(R,T,P,C,ALL_R,COM))<{pdtol})$GR_PTDF(R,T,P,C,ALL_R,COM)) = 0;
    GR_PTDF(R,T,P,C,ALL_R,COM)$((NOT GR_ALGMAP(R,'NRG','NRG'))$GR_PTDF(R,T,P,C,ALL_R,COM)) = ROUND(GR_PTDF(R,T,P,C,ALL_R,COM)/POWER(2,-32))*POWER(2,-32);
    OPTION TRACKP < GR_PTDF, PRC_YMAX < NCAP_PASTI, TRACKC < GR_PTDF;
*...First set all lines with non-zero PTDF as candidates
    GR_CANDID(R,T,P)$(RP_GRID(R,P)$TRACKP(R,P)) = YES;
*...No new capacity allowed for existing lines
    NCAP_BND(GR_CANDID(R,T,P),'UP')$PRC_YMAX(R,P) = MAX(EPS,NCAP_BND(R,T,P,'UP'));
    DFUNC = {tmp}; OPTION CLEAR=PRC_YMAX, CLEAR=TRACKP;
  ELSE OPTION CLEAR=RP_GRID);
* Check nodal commodity balances
*  COM_BNDNET(RTCS_VARC(RC_GRID,S),'LO') = EPS;
  COM_LIM(TRACKC(RC),'FX')$((NOT SUM(COM_LIM(RC,L),1))$GR_GID(RC)) = YES;
  OPTION CLEAR=TRACKC,CLEAR=RP_PRC,CLEAR=TRACKPC;
""",
        )

    def declaration2(self: PowerfloVda, var: str, swd: str, eq: str, swtd: str) -> None:
        g = self.tc
        m = g.container
        r, c, t, p, j, io, cg, ie, bd, s, year, item = (
            g.r,
            g.c,
            g.t,
            g.p,
            g.j,
            g.io,
            g.cg,
            g.ie,
            g.bd,
            g.s,
            g.year,
            g.item,
        )
        # * Declare variables and equations
        g.set_variable(
            f"{var}_GRIDIO",
            Variable(
                m,
                name=f"{var}_GRIDIO",
                domain=[r, year, c, c, s, io, *swd],
                type="POSITIVE",
            ),
        )
        g.set_variable(
            f"{var}_XCAP",
            Variable(
                m, name=f"{var}_XCAP", domain=[r, year, item, *swd], type="POSITIVE"
            ),
        )
        g.set_variable(
            f"{var}_COMAUX",
            Variable(m, name=f"{var}_COMAUX", domain=[r, t, c, s, *swd]),
        )
        g.set_equation(
            f"{eq}_GR_POWFLO",
            Equation(
                m,
                name=f"{eq}_GR_POWFLO",
                domain=[r, t, c, s, r, c, *swtd],
                description="Phase-angle formulation",
            ),
        )
        g.set_equation(
            f"{eq}_GR_PTDFLO",
            Equation(
                m,
                name=f"{eq}_GR_PTDFLO",
                domain=[r, t, p, c, s, *swtd],
                description="Generalized PTDF formulation",
            ),
        )
        g.set_equation(
            f"{eq}_GR_GENALL",
            Equation(
                m,
                name=f"{eq}_GR_GENALL",
                domain=[r, t, c, s, cg, *swtd],
                description="Allocation of supply to Add-on nodes",
            ),
        )
        g.set_equation(
            f"{eq}_GR_DEMALL",
            Equation(
                m,
                name=f"{eq}_GR_DEMALL",
                domain=[r, t, c, s, *swtd],
                description="Allocation of demand to Add-on nodes",
            ),
        )
        g.set_equation(
            f"{eq}_GR_XBND",
            Equation(
                m,
                name=f"{eq}_GR_XBND",
                domain=[r, t, j, ie, s, *swtd],
                description="Simplified N-1 security constraint",
            ),
        )
        g.set_equation(
            f"{eq}_GR_VIRTCAP",
            Equation(
                m,
                name=f"{eq}_GR_VIRTCAP",
                domain=[r, t, p, c, s, bd, *swtd],
                description="Candidate line virtual capacity",
            ),
        )
        g.set_equation(
            f"{eq}_GR_VIRTBND",
            Equation(
                m,
                name=f"{eq}_GR_VIRTBND",
                domain=[r, t, p, *swtd],
                description="Bound on virtual capacity",
            ),
        )

    def exec4(self: PowerfloVda, var: str, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* For each disjoint grid, set phase angle to zero for the node with most connected lines
  LOOP(J$SUM(GR_GRID(J,R,C)$GR_GID(R,C),1), Z = SMAX(GR_GRID(J,R,C),SUM(P$GR_FLOW(R,P,C),1));
    LOOP(GR_GRID(J,R,C)$Z,IF(SUM(P$GR_FLOW(R,P,C),1)=Z, Z=0; {var}_COMAUX.FX(R,T,C,S{sow})=EPS)));
  GR_GRID(J,R,'ACT') $= SUM(GR_GRID(J,NRGELC(R,C)),1);
""",
        )

    def comp1(self: PowerfloVda, tmp: str, var: str, pgprim: str, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
$ MACRO VAR_PTDNCAP(r,t,p) {tmp}
$ MACRO VAR_GRVIRT(r,t,p,n,s) SUM(IE(XPT),{var}_IRE(r,t,t,p,'{pgprim}',s,ie{sow}))
""",
        )

    def exec5(self: PowerfloVda, var: str, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(CARD(GR_CANDID),
*...Remove existing lines from candidate lines for their full lifespan
    GR_CAPUP(GR_CANDID(R,T,P)) = SUM(PYR(V)$COEF_CPT(R,V,T,P),NCAP_PASTI(R,V,P)*ROUND(COEF_CPT(R,V,T,P)));
    GR_CANDID(R,T,P)$SUM(RP_GRID(REG,P)$GR_CAPUP(REG,T,P),1) = NO;
    RVP(GR_CANDID) = YES;
*...Complete virtual CAP bounds for candidate/removed lines
    GR_CAPUP(RVP(R,T,P))$GR_DNCAP(R,P) = MAX(0,SMAX((VNT(V,T),UNIT)$COEF_CPT(R,V,T,P),GR_DUNIT(R,V,P,UNIT)*(COEF_CPT(R,V,T,P)>0)));
    LOOP(T,GR_CAPUP(RVP(R,TT(MIYR_1),P))$(NOT GR_CAPUP(RVP)) = MAX(CAP_BND(R,T,P,'UP'),GR_CAPUP(R,T,P))+1-1);
    LOOP(TT(T+1),GR_CAPUP(RVP(R,TT,P))$(NOT GR_CAPUP(RVP)) = GR_CAPUP(R,T,P)+(CAP_BND(RVP,'UP')-GR_CAPUP(R,T,P))$(CAP_BND(RVP,'UP')>0));
*...Copy CAP bounds from import side if needed
    LOOP(GR_TOP(R,C,REG,COM,P),GR_CAPUP(R,T,P)$GR_CAPUP(REG,T,P)=MIN(GR_CAPUP(REG,T,P),GR_CAPUP(R,T,P)+INF$(NOT GR_CAPUP(R,T,P)));
         IF(NOT SAMEAS(R,REG),GR_CAPUP(REG,T,P) = 0));
    GR_CANDID(RVP)$(NOT GR_CAPUP(RVP)) = NO;
    CAP_BND(GR_CANDID(R,T,P),'UP')$((NOT CAP_BND(R,T,P,'UP'))$(NOT GR_DNCAP(R,P))) = GR_CAPUP(R,T,P);
    RTP_VARP(GR_CANDID(R,T,P))$(NOT GR_DNCAP(R,P)) = YES;
    {var}_IRE.LO(R,T,T,P,C(ACTCG),S,'EXP'{sow})$(PRC_TS(R,P,S)$RVP(R,T,P)) = -INF;
    OPTION CLEAR=RVP);
""",
        )

    def dc_power_flow_eqs(
        self: PowerfloVda,
        eq: str,
        r_t: str,
        swt: str,
        var: str,
        sow: str,
        bigm: str,
        varv: str,
        sws: str,
        pgprim: str,
        def_rtp_ffcs: bool,
    ) -> None:
        # both includes are the same
        include_cal_red = cal_red_red(
            arg1="COM",
            arg2="COM1",
            arg3="TS",
            arg4="P",
            arg5="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
        )
        rts = macro.rts(s="S", g=self.tc, env=self.env)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Standard DC power flow equations - Omega
  {eq}_GR_POWFLO(RTCS_VARC(RC_GRID({r_t},C),{rts}),REG,COM{swt})$GR_ADMIT(R,T,C,REG,COM)..

  SUM((GR_TOP(R,C,REG,COM,P),RTP_VINTYR(REG,V,T,P))$RTPCS_VARF(REG,T,P,COM,S),
    SUM(RPC_IRE(REG,P,COM,IE)$PRC_REACT(R,T,P),{var}_IRE(REG,V,T,P,COM,S,IE{sow})*(1-2*XPT(IE))))

  =E=  ({var}_COMAUX(R,T,C,S{sow})-{var}_COMAUX(REG,T,COM,S{sow})) * GR_ADMIT(R,T,C,REG,COM);

*------------------------------------------------------------------------

* Standard DC power flow equations - PTDF
  {eq}_GR_PTDFLO({r_t},P,C,{rts}{swt})$(RPS_S1(R,P,S)$(GR_FLOW(R,P,C)>0)$RP_GRID(R,P))..
*...Real flow over the line
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS))$RS_FR(R,S,TS),RS_FR(R,S,TS)*SUM(RPC_IRE(R,P,C,IE),{var}_IRE(R,V,T,P,C,S,IE{sow})*(2*XPT(IE)-1))) +
*...Virtual powerflow over the line (if candidate)
    SUM(RC_GRID(R,T,C),VAR_GRVIRT(R,T,P,C,S))$GR_CANDID(R,T,P)
  =E=
*...PTDF for net injections: Normal grid nodes
    SUM(RC_GRID(REG,T,COM)$(COM_TS(REG,COM,S)$GR_PTDF(R,T,P,C,REG,COM)), GR_PTDF(R,T,P,C,REG,COM) * {var}_COMAUX(REG,T,COM,S{sow}))
*...PTDF for virtual injections (redundant in this formulation)
*   +SUM(GR_TOP(REG,COM1,RC,PRC)$GR_CANDID(REG,T,PRC),
*     (GR_PTDF(R,T,P,C,REG,COM1)-GR_PTDF(R,T,P,C,RC)) * SUM(RPS_S1(REG,PRC,TS)$RS_FR(REG,S,TS),RS_FR(REG,S,TS)*VAR_GRVIRT(REG,T,PRC,COM1,TS)));
  ;
*------------------------------------------------------------------------
* Implied capacity of virtual powerflow
  {eq}_GR_VIRTCAP(GR_CANDID({r_t},P),C,{rts},BDNEQ(BD){swt})$((GR_FLOW(R,P,C)>0)$RPS_S1(R,P,S))..
    SUM(GR_TOP(R,C,RC,P),VAR_GRVIRT(R,T,P,C,S))*BDSIG(BD)  =L=  {macro.VAR_XCAP(var, "R", "T", "P", sow)}*PRC_CAPACT(R,P)*G_YRFR(R,S)
  ;
*------------------------------------------------------------------------
* Bounds on virtual capacity
  {eq}_GR_VIRTBND(GR_CANDID({r_t},P){swt})..
*...Upper bound on virtual flow capacity: Zero if line is installed, less than BIGM*F if line not installed
    {macro.VAR_XCAP(var, "R", "T", "P", sow)} =E=  {bigm}*GR_CAPUP(R,T,P) *
*...Virtual capacity indicator
    (1 - (VAR_PTDNCAP(r,t,p)$GR_DNCAP(R,P) + (1-(1-SUM(RTP(R,T,P),{macro.VAR_CAP(var, "R", "T", "P", sow)})/GR_CAPUP(R,T,P))/{bigm})$(NOT GR_DNCAP(R,P))))
  ;
*------------------------------------------------------------------------
* Generation fractions for all grid nodes C
  {eq}_GR_GENALL(RTCS_VARC(GR_GNALL({r_t},C),{rts}),CG {swt})$GR_ALGMAP(R,CG,CG)..

* Normal processes
  SUM((GR_PRCMAP(RP_STD(R,P),COM,ITEM),GR_ALGMAP(R,CG,COM)), GR_GENMAP(R,P,ITEM)*GR_GENFR(R,T,C,ITEM) *
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,COM,TS))$RS_FR(R,S,TS),
{include_cal_red}
         * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "COM", "S", "TS")}))$GR_ALLMAP(R,C,COM)) +
* Imports
  SUM((GR_PRCMAP(RP_IRE(R,P),COM,ITEM),RPC_IRE(R,P,COM,IE('IMP')))$GR_ALGMAP(R,CG,COM), GR_GENMAP(R,P,ITEM)*GR_GENFR(R,T,C,ITEM) *
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,COM,TS))$RS_FR(R,S,TS),
       (1+IRE_FLOSUM(R,T,P,COM,TS,IE,COM,'OUT')) *
       ({var}_IRE(R,V,T,P,COM,TS,IE{sow})$(NOT RPC_AIRE(R,P,COM))+
        ({var}_ACT(R,V,T,P,TS{sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM))*RS_FR(R,S,TS))) +
* Net storage output
  SUM((GR_PRCMAP(RPC_STG(R,P,COM),ITEM),GR_ALGMAP(R,CG,COM)), GR_GENMAP(R,P,ITEM)*GR_GENFR(R,T,C,ITEM) *
    SUM((RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,COM,TS)),({var}_SOUT(R,V,T,P,COM,TS {sow})-{var}_SIN(R,V,T,P,COM,TS {sow})$TOP(R,P,COM,'IN'))*RS_FR(R,S,TS)))

* Net balance
  +SUM(GR_ALLMAP(R,CG,C),{var}_GRIDIO(R,T,C,C,S,'OUT'{sow}) - {var}_GRIDIO(R,T,C,C,S,'IN'{sow}) -
    SUM(GR_DEMMAP(R,C,COM),{var}_GRIDIO(R,T,COM,C,S,'OUT'{sow}) - {var}_GRIDIO(R,T,COM,C,S,'IN'{sow})$GR_ALGMAP(R,'NRG',COM)))

  =E=
  SUM((GR_ALGMAP(R,CG,COM),GR_ALLMAP(R,C,COM))$RTC(R,T,COM),{var}_GRIDIO(R,T,COM,C,S,'OUT'{sow}) + {var}_GRIDIO(R,T,COM,C,S,'IN'{sow})$GR_ALGMAP(R,COM,COM));
*------------------------------------------------------------------------
* Demand fractions for all but the largest fraction
  {eq}_GR_DEMALL(RTCS_VARC(RC_GRID({r_t},C),{rts}) {swt})$GR_DEMFR(R,T,C,S)..

* Net injection
  SUM(GR_ENDC(R,COM),
    SUM(TOP(RP_STD(R,P),COM,'OUT')$(NOT GR_GENP(R,P)*GR_DEMMAP(R,C,COM)),
      SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,COM,TS))$RS_FR(R,S,TS),
{include_cal_red}
         * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "COM", "S", "TS")})) *
      (SUM(GR_PRCMAP(R,P,COM,ITEM),GR_GENMAP(R,P,ITEM)*GR_GENFR(R,T,C,ITEM))-GR_ENDFR(R,T,C,COM)*(1+GR_ENDFR(R,T,COM,COM))-GR_DEMFR(R,T,C,S)$GR_GENP(R,P)$GR_ENDC(R,'NRG')))) +
* Exports
  SUM((GR_PRCMAP(RP_IRE(R,P),COM,ITEM),RPC_IRE(R,P,COM,IE('EXP')))$GR_ALGMAP(R,'NRG',COM), GR_GENMAP(R,P,ITEM) *
    (GR_ENDFR(R,T,C,COM) + GR_DEMFR(R,T,C,S)$GR_ENDC(R,'NRG') - GR_GENFR(R,T,C,ITEM)) *
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,COM,TS))$RS_FR(R,S,TS),
       (1+IRE_FLOSUM(R,T,P,COM,TS,IE,COM,'IN')) *
       ({var}_IRE(R,V,T,P,COM,TS,IE{sow})$(NOT RPC_AIRE(R,P,COM))+
        ({var}_ACT(R,V,T,P,TS{sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM))*RS_FR(R,S,TS))$GR_ALLMAP(R,C,COM)) +
* Net demand shares
  SUM(GR_DEMMAP(R,C,COM)$RTC(R,T,COM), {var}_GRIDIO(R,T,COM,C,S,'IN'{sow}) -
    (GR_ENDFR(R,T,C,COM)+GR_DEMFR(R,T,C,S)$GR_ENDC(R,'NRG')) *
    SUM(RTC(R,T,COM2)$GR_DEMMAP(R,COM2,COM),{var}_GRIDIO(R,T,COM,COM2,S,'IN'{sow})))

  =E= 0;
*------------------------------------------------------------------------
* Bound on net imports/exports from grid J
  {eq}_GR_XBND({r_t},J,IE,{rts}{swt})$(FINEST(R,S)$GR_GRID(J,R,'ACT')$GR_XBND(R,T))..

  SUM((GR_GRID(J,R,C),GR_DEMMAP(R,C,COM))$(RTC(R,T,COM)$RC_GRID(R,T,C)), PROD(XPT(IE),-1) *
    ({var}_GRIDIO(R,T,COM,C,S,'IN'{sow})$GR_ALGMAP(R,'NRG',COM) - {var}_GRIDIO(R,T,COM,C,S,'OUT'{sow})))

  =L=
  SUM((GR_GRID(J,R,C),TOP_IRE(R,C,ALL_R,COM,P))$((NOT SAMEAS(R,ALL_R))$RC_GRID(R,T,C)),
    SUM(V$COEF_VNT(R,T,P,V), COEF_VNT(R,T,P,V) * PRC_CAPACT(R,P) * GR_XBND(R,T) * G_YRFR(R,S) *
      ({macro.VAR_NCAP(varv, "R", "V", "P", sws)}$TT(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V)))$PRC_CAP(R,P) +
    SUM((REG(ALL_R),V)$COEF_VNT(REG,T,P,V), COEF_VNT(REG,T,P,V) * PRC_CAPACT(REG,P) * GR_XBND(R,T) * G_YRFR(R,S) *
      ({macro.VAR_NCAP(varv, "REG", "V", "P", sws)}$TT(V)+NCAP_PASTI(REG,V,P)$PASTYEAR(V))$PRC_CAP(REG,P))$(NOT PRC_CAP(R,P)))$XPT(IE) +
  SUM((TOP_IRE(ALL_R,COM,R,C,P),GR_GRID(J,R,C))$((NOT SAMEAS(R,ALL_R))$RC_GRID(R,T,C)),
    SUM(V$COEF_VNT(R,T,P,V), COEF_VNT(R,T,P,V) * PRC_CAPACT(R,P) * GR_XBND(R,T) * G_YRFR(R,S) *
      ({macro.VAR_NCAP(varv, "R", "V", "P", sws)}$TT(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V)))$PRC_CAP(R,P) +
    SUM((REG(ALL_R),V)$COEF_VNT(REG,T,P,V), COEF_VNT(REG,T,P,V) * PRC_CAPACT(REG,P) * GR_XBND(R,T) * G_YRFR(R,S) *
      ({macro.VAR_NCAP(varv, "REG", "V", "P", sws)}$TT(V)+NCAP_PASTI(REG,V,P)$PASTYEAR(V))$PRC_CAP(REG,P))$(NOT PRC_CAP(R,P)))$IMP(IE)
;
""",
        )

    def comp2(self: PowerfloVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* Preprocess nodal balance costs
  SET OBV / OBJBAL /;
  SET ITEM / CON, NTX, NPG /;
""",
        )

        g = self.tc
        m = g.container
        g.Rcgrid = Set(m, name="RC_GRID", domain=[g.r, g.t, g.c])
        g.GrAllmap = Set(m, name="GR_ALLMAP", domain=[g.r, g.cg, g.Com])
        g.GrPrcmap = Set(m, name="GR_PRCMAP", domain=[g.r, g.p, g.c, g.item])
        g.GrDemmap = Set(m, name="GR_DEMMAP", domain=[g.r, g.c, g.Com])
        g.GrAlgmap = Set(m, name="GR_ALGMAP", domain=[g.r, g.cg, g.cg])
        g.GrEndc = Set(m, name="GR_ENDC", domain=[g.r, g.cg])
        g.obj_combal = Parameter(
            m, name="OBJ_COMBAL", domain=[g.r, g.t, g.c, g.s, g.item, g.cur]
        )

    def exec6(self: PowerfloVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=RC_GRID,CLEAR=GR_ALLMAP,CLEAR=GR_ALGMAP,CLEAR=GR_DEMMAP,CLEAR=GR_PRCMAP,CLEAR=GR_ENDC;
""",
        )

    def exec7(self: PowerfloVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION TRACKC < COM_CSTBAL;
  TRACKC(R,C)$SUM(GR_ALLMAP(R,C,COM),1)=NO;
  OBJ_COMBAL(RTCS_VARC(RTC(R,T,C),TS),'PRD',CUR)$TRACKC(R,C) = SUM(TS_ANN(TS,S),COM_CSTBAL(RTC,S,'PRD',CUR)+COM_CSTBAL(RTC,S,'CON',CUR)+COM_CSTBAL(RTC,S,'OUT',CUR));
  OBJ_COMBAL(RTCS_VARC(RTC(R,T,C),TS),'IMP',CUR)$TRACKC(R,C) = SUM(TS_ANN(TS,S),COM_CSTBAL(RTC,S,'IMP',CUR)+COM_CSTBAL(RTC,S,'NTX',CUR)-COM_CSTBAL(RTC,S,'PRD',CUR));
  OBJ_COMBAL(RTCS_VARC(RTC(R,T,C),TS),'EXP',CUR)$TRACKC(R,C) = SUM(TS_ANN(TS,S),COM_CSTBAL(RTC,S,'EXP',CUR)-COM_CSTBAL(RTC,S,'NTX',CUR)-COM_CSTBAL(RTC,S,'CON',CUR));
  LOOP(RDCUR(R,CUR),RHS_COMPRD(RTCS_VARC(R,T,C,S))$OBJ_COMBAL(R,T,C,S,'PRD',CUR)=YES); RCS_COMPRD(RHS_COMPRD(R,T,C,S),'FX')$TRACKC(R,C) = YES;
  OBJ_COMBAL(RTCS_VARC(RTC(RC_GRID),TS),'GEN',CUR) = SUM(TS_ANN(TS,S),COM_CSTBAL(RTC,S,'PRD',CUR)+COM_CSTBAL(RTC,S,'CON',CUR));
  OBJ_COMBAL(RTCS_VARC(RTC(RC_GRID),TS),'NTX',CUR) = SUM(TS_ANN(TS,S),COM_CSTBAL(RTC,S,'NTX',CUR)+COM_CSTBAL(RTC,S,'CON',CUR));
  OBJ_COMBAL(RTCS_VARC(RTC(RC_GRID),TS),IE,CUR)    = SUM(TS_ANN(TS,S),COM_CSTBAL(RTC,S,IE,CUR));
* Add balancer variables if penalty costs on excess
  OPTION CLEAR=UNCD7; UNCD7(R,T--ORD(T),C,S--ORD(S),CUR,'','')$RC_GRID(R,T,C) $= COM_CSTBAL(R,T,C,S,'NPG',CUR);
  LOOP(UNCD7(R,TT,C,SL,CUR,'',''), GR_ALLMAP(R,'FIN',C) = YES; GR_ALGMAP(R,CG('FIN'),CG) = YES;
    OBJ_COMBAL(RC_GRID(R,T,C),TS,'NPG',CUR) $= SUM(TS_ANN(TS,S),COM_CSTBAL(R,T,C,S,'NPG',CUR)));
  OPTION CLEAR=TRACKC;
""",
        )

    def eq_objbal(
        self: PowerfloVda,
        cal_red: str,
        sowpre: str,
        var: str,
        swd: str,
        swx: str,
        swsw: str,
        sow: str,
        tpulse: str,
        pgprim: str,
        def_rtp_ffcs: bool,
        condition: bool,
    ) -> None:
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red as cal_red_func
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red = cal_red_func(
            arg1="COM",
            arg2="COM1",
            arg3="TS",
            arg4="P",
            arg5="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
        )
        g = self.tc
        m = g.container
        r, c, io, cur, s, year, allsow = g.r, g.c, g.io, g.cur, g.s, g.year, g.allsow
        g.set_variable(
            f"{var}_GRIDIO",
            Variable(
                m,
                name=f"{var}_GRIDIO",
                domain=[r, year, c, c, s, io, *swd],
                type="POSITIVE",
            ),
        )
        g.eq_objbal = Equation(m, name="EQ_OBJBAL", domain=[r, cur, allsow])

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_OBJBAL(RDCUR(R,CUR){swx})..

   {var}_OBJ(R,'OBJBAL',CUR {sowpre}) =E=

{f"SUM({swsw}" if condition else ""}
* Costs on commodity production
   SUM(RHS_COMPRD(R,T,C,S),{var}_COMPRD(R,T,C,S {sow}) * SUM({tpulse} * OBJ_COMBAL(R,TT,C,S,'PRD',CUR))) +
   SUM(RTCS_VARC(RC_GRID(R,T,C),S)$OBJ_COMBAL(R,T,C,S,'GEN',CUR),
     (SUM(GR_ALGMAP(R,CG,COM)$GR_ALLMAP(R,C,COM),{var}_GRIDIO(R,T,COM,C,S,'OUT' {sow}) + {var}_GRIDIO(R,T,COM,C,S,'IN'{sow})$GR_ALGMAP(R,COM,COM))+
      SUM((GR_PRCMAP(RP_STD(R,P),COM,ITEM),GR_ENDC(R,COM)), GR_GENMAP(R,P,ITEM)*GR_GENFR(R,T,C,ITEM) *
        SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,COM,TS))$RS_FR(R,S,TS),
{include_cal_red}
         * RS_FR(R,S,TS)))) * SUM({tpulse} * OBJ_COMBAL(R,TT,C,S,'GEN',CUR))) +

* Costs on net imports to grid node
   SUM(RTCS_VARC(RC_GRID(R,T,C),S)$OBJ_COMBAL(R,T,C,S,'NTX',CUR),
     SUM(GR_DEMMAP(R,C,COM),{var}_GRIDIO(R,T,COM,C,S,'IN'{sow})$GR_ALGMAP(R,'NRG',COM) - {var}_GRIDIO(R,T,COM,C,S,'OUT'{sow})) *
     SUM({tpulse} * OBJ_COMBAL(R,TT,C,S,'NTX',CUR))) +

* Costs on Net Positive Generation (NPG)
   SUM(RTCS_VARC(RC_GRID(R,T,C),S)$OBJ_COMBAL(R,T,C,S,'NPG',CUR),
     {var}_GRIDIO(R,T,C,C,S,'OUT' {sow}) * SUM({tpulse} * MAX(0,OBJ_COMBAL(R,TT,C,S,'NPG',CUR)))) +

* Costs on commodity imports / exports
   SUM((RTPCS_VARF(R,T,P,C,S),RPC_IRE(R,P,C,IE))$OBJ_COMBAL(R,T,C,S,IE,CUR),
     SUM(RTP_VINTYR(R,V,T,P),
       ({var}_IRE(R,V,T,P,C,S,IE {sow})$(NOT RPC_AIRE(R,P,C))+({var}_ACT(R,V,T,P,S {sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))) *
     SUM({tpulse} * OBJ_COMBAL(R,TT,C,S,IE,CUR)))

{" )" if condition else ""}
   ;
""",
        )

    def exec_powerflo_vda_rptb(
        self: PowerfloVda,
        arg4: str,
        arg5: str,
        arg6: str,
        var: str,
        vart: str,
        sws: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=powerflo_vda_rptb(
                arg4=arg4,
                arg5=arg5,
                arg6=arg6,
                var=var,
                vart=vart,
                sws=sws,
            ),
        )


def powerflo_vda_ireaux(
    # TODO: if powerflow_vda() is called with arg2=="IN", this is done in powerflo.vda first: $SET MX COM_IE(R,T,C,S)*
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    var: str = "",
    sow: str = "",
) -> str:
    target_label = f"{arg1}{arg2}{arg3}".strip().upper()

    if target_label not in ["IREAUXIN", "IREAUXOUT-"]:
        return ""

    mx = arg3
    if target_label == "IREAUXIN":
        mx = "COM_IE(R,T,C,S)*"

    return rf"""
* For balance of C (and grid nodes COM)
    SUM(GR_DEMMAP(R,COM,C), {mx}({var}_GRIDIO(R,T,C,COM,S,'OUT'{sow}) - {var}_GRIDIO(R,T,C,COM,S,'IN'{sow})$GR_ALGMAP(R,'NRG',C))) +
* For balance of grid node C
    SUM(GR_DEMMAP(R,C,COM), {mx}({var}_GRIDIO(R,T,COM,C,S,'IN'{sow})$GR_ALGMAP(R,'NRG',COM) - {var}_GRIDIO(R,T,COM,C,S,'OUT'{sow}))) +
"""


def powerflo_vda_ireaux_GP(
    g: TimesModelClass,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    var: str = "",
    sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()] = (),
) -> Expression | ImplicitSet | int:
    """GAMSPy counterpart of powerflo_vda_ireaux(). Returns 0 outside the two labels."""
    target_label = f"{arg1}{arg2}{arg3}".strip().upper()

    if target_label not in ["IREAUXIN", "IREAUXOUT-"]:
        return 0

    r, t, c, s, Com = g.r, g.t, g.c, g.s, g.Com
    VAR_GRIDIO: Variable = g.get_variable(f"{var}_GRIDIO")

    # arg3 is "-" for IREAUXOUT-, i.e. the terms are negated
    def mx(expr: Expression | ImplicitSet) -> Expression | ImplicitSet:
        if target_label == "IREAUXIN":
            return g.com_ie[r, t, c, s] * expr
        return -expr

    # * For balance of C (and grid nodes COM)
    balance_c = Sum(
        g.GrDemmap[r, Com, c],
        mx(
            VAR_GRIDIO[r, t, c, Com, s, "OUT", *sow]
            - VAR_GRIDIO[r, t, c, Com, s, "IN", *sow].where[g.GrAlgmap[r, "NRG", c]]
        ),
    )
    # * For balance of grid node C
    balance_node = Sum(
        g.GrDemmap[r, c, Com],
        mx(
            VAR_GRIDIO[r, t, Com, c, s, "IN", *sow].where[g.GrAlgmap[r, "NRG", Com]]
            - VAR_GRIDIO[r, t, Com, c, s, "OUT", *sow]
        ),
    )
    return balance_c + balance_node


def powerflo_vda_rptb(
    arg4: str,
    arg5: str,
    arg6: str,
    var: str,
    vart: str,
    sws: str,
) -> str:
    return rf"""
 {arg4}REG_WOBJ({arg5}R,'VAR',CUR) = {arg4}REG_WOBJ({arg5}R,'VAR',CUR) + {var}_OBJ.L(R,'OBJBAL',CUR{arg6});
 OPTION TRACKC < COM_CSTBAL;
 {arg4}CST_COMC({arg5}RTC(R,T,C))$TRACKC(R,C) = {arg4}CST_COMC({arg5}RTC) +
   SUM((RTCS_VARC(RTC,S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'PRD',CUR),OBJ_COMBAL(RTC,S,'PRD',CUR)*VAR_COMPRD.L(RTC,S)) +
   SUM((RPCS_VAR(R,P,C,S),RPC_IRE(R,P,C,IE),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,IE,CUR),
     SUM(RTP_VINTYR(R,V,T,P),OBJ_COMBAL(RTC,S,IE,CUR)*PAR_IRE(R,V,T,P,C,S,IE))) +
* Cost on generation to grid
   SUM((RTCS_VARC(RC_GRID(RTC),S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'GEN',CUR),
     OBJ_COMBAL(RTC,S,'GEN',CUR) *
     (SUM(GR_ALGMAP(R,CG,COM),{vart}_GRIDIO.L(R,T,COM,C,S,'OUT' {sws}) + {vart}_GRIDIO.L(R,T,COM,C,S,'IN'{sws})$GR_ALGMAP(R,COM,COM))+
      SUM((GR_PRCMAP(RP_STD(R,P),COM,ITEM),GR_ENDC(R,COM)), GR_GENMAP(R,P,ITEM)*GR_GENFR(RTC,ITEM) *
        SUM((RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,TS))$RS_FR(R,S,TS),
          PAR_FLO(R,V,T,P,C,TS)*RS_FR(R,S,TS))))) +
* Costs on net imports to grid node
   SUM((RTCS_VARC(RC_GRID(RTC),S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'NTX',CUR),
     SUM(GR_DEMMAP(R,C,COM),{vart}_GRIDIO.L(R,T,COM,C,S,'IN'{sws})$GR_ALGMAP(R,'NRG',COM) - {vart}_GRIDIO.L(R,T,COM,C,S,'OUT'{sws})) *
     OBJ_COMBAL(RTC,S,'NTX',CUR)) +
* Costs on Net Positive Generation (NPG)
   SUM((RTCS_VARC(RC_GRID(RTC),S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'NPG',CUR),
     {vart}_GRIDIO.L(RTC,C,S,'OUT'{sws}) * OBJ_COMBAL(RTC,S,'NPG',CUR));

 OPTION CLEAR=TRACKC;
"""
