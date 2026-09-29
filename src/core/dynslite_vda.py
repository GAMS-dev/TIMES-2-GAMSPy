# dynslite_vda.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number, Sum

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGmsConfig, fillparm
from core.pp_qaput_mod import pp_qaput

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class DynsliteVda(GamsClass):
    """Translation unit for dynslite.vda."""

    # Instance attributes
    module_name: str = "dynslite_vda"
    gams_source: str = "dynslite.vda"

    def __init__(
        self: DynsliteVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self: DynsliteVda) -> None:
        if self.env.rts() == "S":
            return
        self.env.set_scoped("tmp", "$NORTS(R,T,S)")
        if self.arg1.upper() == "PRELEV":
            self.tc.enqueue(
                self.prelev_exec, ducyes=self.env.duc.upper() == "YES", tmp=self.env.tmp
            )
        if self.arg1.upper() in ["PRELEV", "CLEAR"]:
            rts = "$(NORTS(R,V,S)+NORTS(R,T,S)$PASTMILE(V))"
            self.tc.enqueue(self.clear_exec, tmp=self.env.tmp, rts=rts)
        elif self.arg1.upper() == "REDUCE":
            self.tc.enqueue(self.reduce_exec, tmp=self.env.tmp)
        elif self.arg1.upper() == "POSTLEV":
            self.env.set_scoped("reset", 0)
            self.tc.enqueue(
                self.postlev_exec,
                dflbl=self.env.dflbl,
                item=self.env.item,
                data=self.env.data,
                add=self.env.add,
                reset=self.env.reset,
            )
            rts = "$(NORTS(R,V,S)+NORTS(R,T,S)$PASTMILE(V))"
            self.tc.enqueue(self.clear_exec, tmp=self.env.tmp, rts=rts)

    def prelev_exec(self: DynsliteVda, ducyes: bool, tmp: str) -> None:
        if self.tc.norts.number_records > 0:
            if ducyes:
                raise ValueError("TS_OFF cannot be used with DUC")

            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
* Re-calculate the leads for the SEASON timeslice cycle
  LOOP((R,ANNUAL(S),T), F=0;
   LOOP(RS_BELOW1(R,S,TS)$(NOT NORTS(R,T,TS)), IF(F, RS_STG(R,TS)=ORD(TS)-Z; Z=ORD(TS); ELSE Z=ORD(TS); F=Z));
   RS_STG(R,S+(F-ORD(S)))$F = F-Z);
* Re-calculate average residence time for storage activity for SEASON
  LOOP((TS_GROUP(R,'SEASON',S),TS(S--RS_STG(R,S)))$RS_STGPRD(R,S),RS_STGAV(R,S) = (G_YRFR(R,S)+G_YRFR(R,TS))/2/RS_STGPRD(R,S));
* QA Check
  PUTGRP=0;
  LOOP(RT_PP(R,T), Z=SUM((RS_BELOW1(R,ANNUAL,TS),S(TS--RS_STG(R,TS)))$((NOT NORTS(R,T,TS))$NORTS(R,T,S)),1);
    IF(Z,
{pp_qaput("PUTOUT", "PUTGRP", "99", "Unsupported dynamic timeslice trees with overlap -- Fatal")}
     PUT QLOG ' FATAL ERROR   - Timeslice trees have shared branches (R.T)=',RT_PP.TE(RT_PP)));
*------------------------------
* Remove timeslices turned off
* Bounds+varcosts pre-cleared only
    ACT_BND(R,T,P,S,BD){tmp}=0;
    COM_BNDNET(R,T,C,S,BD){tmp}=0;
    COM_BNDPRD(R,T,C,S,BD){tmp}=0;
    FLO_BND(R,T,P,CG,S,BD){tmp}=0;
    FLO_FR(R,T,P,C,S,L){tmp} = 0;
    IRE_BND(R,T,C,S,ALL_R,IE,BD){tmp}=0;
    IRE_XBND(R,T,C,S,IE,BD){tmp}=0;
    STGIN_BND(R,T,P,C,S,BD){tmp}=0;
    STGOUT_BND(R,T,P,C,S,BD){tmp}=0;
    COM_BPRICE(R,T,C,S,CUR){tmp}=0;
""",
            )

    def clear_exec(self: DynsliteVda, tmp: str, rts: str) -> None:
        if self.tc.norts.number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
* Vintage-based cleared selectively
    RVP(RTP(R,T,P))$(NOT PRC_VINT(R,P))=YES;
    ACT_FLO(RVP(R,T,P),CG,S){tmp}=0;
    FLO_FUNC(RVP(R,T,P),CG,CG2,S){tmp}=0;
    FLO_SUM(RVP(R,T,P),CG,C,CG2,S){tmp}=0;
    NCAP_AF(RVP(R,T,P),S,BD){tmp}=0;
    FLO_SHAR(RVP(R,T,P),C,CG,S,BD){tmp}=0;
    FLO_ASHAR(RVP(R,T,P),C,CG,S,BD){tmp}=0;
    STG_LOSS(RVP(R,T,P),S){tmp}=0;
    IRE_FLO(RVP(R,T,P),C,ALL_R,COM,S){tmp}=0;
    ACT_EFF(RVP(R,T,P),CG,S){tmp}=0;
    OPTION CLEAR=RVP;
* Vintaged ANNUAL
    RVP(RTP(R,V,P))$PRC_VINT(R,P)$=PRC_TSL(R,P,'ANNUAL');
    LOOP(MIYR_1(T),
    ACT_FLO(RVP(R,V,P),CG,S)$(RPS_S1(R,P,'ANNUAL'){rts})=0;
    FLO_FUNC(RVP(R,V,P),CG,CG2,S){rts}=0;
    FLO_SUM(RVP(R,V,P),CG,C,CG2,S)$(RPCS_VAR(R,P,C,'ANNUAL'){rts})=0;
    NCAP_AF(RVP(R,V,P),S,BD){rts}=0;
    FLO_SHAR(RVP(R,V,P),C,CG,S,BD)$(RPCS_VAR(R,P,C,'ANNUAL'){rts})=0;
    FLO_ASHAR(RVP(R,V,P),C,CG,S,BD)$(RPS_S2(R,P,'ANNUAL'){rts})=0;
    STG_LOSS(RVP(R,V,P),S){rts}=0;
    IRE_FLO(RVP(R,V,P),C,ALL_R,COM,S){rts}=0);
    OPTION CLEAR=RVP;
* Milestonyr-based all cleared
    COM_IE(R,T,C,S){tmp}=0;
    COM_PKFLX(R,T,C,S){tmp}=0;
    COM_ELAST(R,T,C,S,L){tmp}=0;
    FLO_PKCOI(R,T,P,C,S){tmp}=0;
    STG_SIFT(R,T,P,C,S){tmp}=0;
    IRE_FLOSUM(R,T,P,C,S,IE,COM,IO){tmp}=0;
    UC_ACT(UCN,SIDE,R,T,P,S){tmp}=0;
    UC_FLO(UCN,SIDE,R,T,P,C,S){tmp}=0;
    UC_IRE(UCN,SIDE,R,T,P,C,S,IE){tmp}=0;
    UC_COM(UCN,COM_VAR,SIDE,R,T,C,S,UC_GRPTYPE){tmp}=0;
    UC_RHSRTS(R,UCN,T,S,L){tmp} = 0;
""",
            )

    def reduce_exec(self: DynsliteVda, tmp: str) -> None:
        if self.tc.norts.number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
* Remove from sets timeslices turned off
    RTPS_OFF(RTP(R,T,P),S)$PRC_TS(R,P,S) $= NORTS(R,T,S);
    RTPCS_OUT(RTP(R,T,P),C,S)$RPCS_VAR(R,P,C,S) $= NORTS(R,T,S);
    RTCS_VARC(R,T,C,S){tmp} = NO;
    RCS_COMBAL(R,T,C,S,BD){tmp} = NO;
    RCS_COMPRD(R,T,C,S,BD){tmp} = NO;
    RHS_COMBAL(R,T,C,S){tmp} = NO;
    RHS_COMPRD(R,T,C,S){tmp} = NO;
    RTX_MARK(R,T,ITEM,C,BD,S){tmp} = NO;
""",
            )

    def run_fillparm(
        self: DynsliteVda,
        config: FillparmGmsConfig,
        dflbl: str,
        item: ImplicitParameter,
        data: ImplicitParameter,
        reset: str,
        add: ImplicitParameter | None,
    ) -> None:
        fillparm(
            module=self,
            config=config,
            dflbl=dflbl,
            item=item,
            data=data,
            add=add,
            reset=reset,
        )

    def postlev_exec(
        self: DynsliteVda,
        dflbl: str,
        item: ImplicitParameter,
        data: ImplicitParameter,
        add: ImplicitParameter | None,
        reset: str,
    ) -> None:
        g = self.tc

        if self.tc.norts.number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
    RVP(RTP(R,V,P))$PRC_VINT(R,P)$=PRC_TSL(R,P,'ANNUAL');
    OPTION FIL<DATAYEAR; DATAYEAR(LL)=LASTLL(LL);
    FLO_FUNC(R,LL--ORD(LL),P,CG,CG2,ANNUAL)$(FLO_FUNC(R,LL,P,CG,CG2,ANNUAL)$RVP(R,LL,P))=3;
""",
            )
            # fmt: off
            batincludes: list[FillparmGmsConfig] = [
                FillparmGmsConfig(arg1=g.flo_func, arg2=(g.r,), arg3=(g.p, g.cg, g.cg2, g.Annual),       arg4=("",) * 2,    arg5=g.v, arg6=g.Rvp[g.r, g.v, g.p], arg7=Number(0), arg8="X_RPGGS",   arg9="X_RPGGS"  ),
                FillparmGmsConfig(arg1=g.act_eff,  arg2=(g.r,), arg3=(g.p, g.cg, g.Annual),              arg4=("",) * 3,    arg5=g.v, arg6=g.Rvp[g.r, g.v, g.p], arg7=Number(0), arg8="X_RPGS",    arg9="X_RPGS"   ),
                FillparmGmsConfig(arg1=g.act_flo,  arg2=(g.r,), arg3=(g.p, g.cg, g.Annual),              arg4=("",) * 3,    arg5=g.v, arg6=g.Rvp[g.r, g.v, g.p], arg7=Number(0), arg8="X_RPGS",    arg9="X_RPGS"   ),
                FillparmGmsConfig(arg1=g.flo_sum,  arg2=(g.r,), arg3=(g.p, g.cg1, g.c, g.cg2, g.Annual), arg4=("",) * 1,    arg5=g.v, arg6=g.Rvp[g.r, g.v, g.p], arg7=Number(0), arg8="X_RPGCGS",  arg9="X_RPGCGS" )
            ]
            # fmt: on
            config = batincludes.pop()
            self.run_fillparm(
                config=config,
                dflbl=dflbl,
                item=item,
                data=data,
                add=add,
                reset=reset,
            )
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
    RVP(R,V,P)$(NOT RPS_S1(R,P,'ANNUAL')) = NO;
    ACT_EFF(R,LL--ORD(LL),P,CG,ANNUAL)$(ACT_EFF(R,LL,P,CG,ANNUAL)$RVP(R,LL,P))=3;
    ACT_FLO(R,LL--ORD(LL),P,CG,ANNUAL)$(ACT_FLO(R,LL,P,CG,ANNUAL)$RVP(R,LL,P))=3;
    FLO_SUM(R,LL--ORD(LL),P,CG,C,CG2,ANNUAL)$(FLO_SUM(R,LL,P,CG,C,CG2,ANNUAL)$RVP(R,LL,P))=3;
""",
            )
            for config in batincludes:
                self.run_fillparm(
                    config=config,
                    dflbl=dflbl,
                    item=item,
                    data=data,
                    add=add,
                    reset=reset,
                )
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"OPTION DATAYEAR<FIL;",
            )


def dynslite_vda_bounds_GP(
    *,
    g: TimesModelClass,
    module: GamsClass,
    swd_GP: tuple[Set | Alias] | tuple[()],
    stages: str,
    model_name: str,
    var: str,
    var_uc_yes: bool,
) -> None:
    """Native translation of `$BATINCLUDE dynslite.vda BOUNDS`.

    `{model_name}.HOLDFIXED=1;`/`{model_name}.SOLVEOPT=1;` are GAMS solve
    options -- like the SOLVEOPT/BRATIO case in solve_stp.py's
    exec_solve_stp, GAMSPy runs every statement as its own job so an
    OPTION/model-attribute statement here cannot reach the next solve
    natively; kept as the one raw fragment, emitted only for traceability.
    """
    if g.norts.number_records == 0:
        return

    r, v, t, p, c, s, ie, lA, upt, bd = (
        g.r,
        g.v,
        g.t,
        g.p,
        g.c,
        g.s,
        g.ie,
        g.lA,
        g.upt,
        g.bd,
    )

    # swt = f"{swd})$({swt}RT_PP(R,T){tmp}"
    # {swd})$ moves into the use later
    tmp = g.norts[r, t, s]
    swt: Expression | Condition = g.RtPp[r, t].where[tmp]
    if stages == "YES":
        swt = g.SwT[t, *swd_GP] * swt

    g.RtcNet[r, t, c] = Sum(s, g.RhsCombal[r, t, c, s]) > 0
    g.RtcPrd[r, t, c] = Sum(s, g.RhsComprd[r, t, c, s]) > 0

    g.add_gams_code(
        module=module,
        phase="run",
        code=f"{model_name}.HOLDFIXED=1;\n{model_name}.SOLVEOPT=1;",
    )

    VAR_ACT = g.get_variable(f"{var}_ACT")
    VAR_FLO = g.get_variable(f"{var}_FLO")
    VAR_IRE = g.get_variable(f"{var}_IRE")
    VAR_SIN = g.get_variable(f"{var}_SIN")
    VAR_SOUT = g.get_variable(f"{var}_SOUT")
    VAR_UPS = g.get_variable(f"{var}_UPS")
    VAR_UPT = g.get_variable(f"{var}_UPT")
    VAR_UDP = g.get_variable(f"{var}_UDP")
    VAR_COMNET = g.get_variable(f"{var}_COMNET")
    VAR_COMPRD = g.get_variable(f"{var}_COMPRD")

    VAR_ACT.fx[g.RtpVintyr[r, v, t, p], s, *swd_GP].where[
        # nned to multiply here, since swt is a condition
        swt * g.PrcTs[r, p, s]
    ] = 0
    VAR_FLO.fx[g.RtpVintyr[r, v, t, p], c, s, *swd_GP].where[
        swt * g.RpcsVar[r, p, c, s]
    ] = 0
    VAR_IRE.fx[g.RtpVintyr[r, v, t, p], c, s, ie, *swd_GP].where[
        swt * g.RpcsVar[r, p, c, s]
    ] = 0
    VAR_SIN.fx[g.RtpVintyr[r, v, t, p], c, s, *swd_GP].where[
        swt * g.RpcsVar[r, p, c, s]
    ] = 0
    VAR_SOUT.fx[g.RtpVintyr[r, v, t, p], c, s, *swd_GP].where[
        swt * g.RpcsVar[r, p, c, s]
    ] = 0
    VAR_UPS.fx[g.RtpVintyr[r, v, t, p], s, lA, *swd_GP].where[
        swt * g.RpsUps[r, p, s]
    ] = 0
    VAR_UPT.fx[g.RtpVintyr[r, v, t, p], s, upt, *swd_GP].where[
        swt * g.RpsUps[r, p, s] * g.RpDp[r, p]
    ] = 0
    VAR_UDP.fx[g.RtpVintyr[r, v, t, p], s, bd, *swd_GP].where[
        swt * g.PrcTs[r, p, s] * g.RpUpr[r, p, bd]
    ] = 0
    VAR_COMNET.fx[g.RtcNet[r, t, c], s, *swd_GP].where[swt * g.ComTs[r, c, s]] = 0
    VAR_COMPRD.fx[g.RtcPrd[r, t, c], s, *swd_GP].where[swt * g.ComTs[r, c, s]] = 0

    if var_uc_yes:
        g.UcRhsmap[r, t, g.ucn, g.ucnumber, s].where[tmp] = False
