# sensis_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * sensis.stc Wrapper for sensitivity analysis parameters
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.bnd_set_mod import bnd_set_mod
from core.bnd_ucw_mod import bnd_ucw_mod
from core.clearsol_stp import clearsol_stp

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SensisStc(GamsClass):
    """Translation unit for sensis.stc."""

    module_name: str = "sensis_stc"
    gams_source: str = "sensis.stc"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        var = self.env.var

        self.tc.enqueue(
            self.exec_sensis_stc,
            var=var,
            cufscal=self.env.cufscal,
            cucscal=self.env.cucscal,
            cli=self.env.cli,
            model_name=self.env.model_name,
            mca=self.env.mca,
            stages=self.env.stages,
            swd=self.env.swd,
            sow=self.env.sow,
            eq=self.env.eq,
            swt=self.env.swt,
            abs_=self.env.abs_,
            macro=self.env.macro,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            s_cap_bnd_declared=self.tc.defined("S_CAP_BND"),
            bnd_ucw_defined={
                f"{var}_UC": self.tc.defined(f"{var}_UC"),
                f"{var}_UCR": self.tc.defined(f"{var}_UCR"),
                f"{var}_UCT": self.tc.defined(f"{var}_UCT"),
                f"{var}_UCRT": self.tc.defined(f"{var}_UCRT"),
                f"{var}_UCTS": self.tc.defined(f"{var}_UCTS"),
                f"{var}_UCRTS": self.tc.defined(f"{var}_UCRTS"),
            },
        )

    def exec_sensis_stc(
        self,
        *,
        var: str,
        cufscal: str,
        cucscal: str,
        cli: str,
        model_name: str,
        mca: str,
        stages: str,
        swd: str,
        sow: str,
        eq: str,
        swt: str,
        abs_: str,
        macro: str,
        rtp_ffcs_defined: bool,
        s_cap_bnd_declared: bool,
        bnd_ucw_defined: dict[str, bool],
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=sensis_stc(
                var=var,
                cufscal=cufscal,
                cucscal=cucscal,
                cli=cli,
                model_name=model_name,
                mca=mca,
                stages=stages,
                swd=swd,
                sow=sow,
                eq=eq,
                swt=swt,
                abs_=abs_,
                macro=macro,
                rtp_ffcs_defined=rtp_ffcs_defined,
                s_cap_bnd_declared=s_cap_bnd_declared,
                bnd_ucw_defined=bnd_ucw_defined,
            ),
        )


def sensis_stc(
    *,
    var: str,
    cufscal: str,
    cucscal: str,
    cli: str,
    model_name: str,
    mca: str,
    stages: str,
    swd: str,
    sow: str,
    eq: str,
    swt: str,
    abs_: str,
    macro: str,
    rtp_ffcs_defined: bool,
    s_cap_bnd_declared: bool,
    bnd_ucw_defined: dict[str, bool],
) -> str:
    coef_ext_code = ""
    if mca.upper() == "YES":
        # from core.coef_ext_mca import coef_ext_mca
        # coef_ext_code = coef_ext_mca(arg1="MCA", arg2="sensis")
        raise FileNotFoundError("coef_ext.mca does not exist.")

    return rf"""
{coef_ext_code}
*------------------------------------------------------------------------------
* Clear deterministic parameter if to be set from uncertain
{"OPTION CLEAR=CM_MAXC;" if cli == "YES" else ""}
{"OPTION CLEAR=RTP_FFCS;" if rtp_ffcs_defined else ""}
* Cumulative variable bounds
 VAR_CUMFLO.LO(R,P,C,ALLYEAR,LL) = 0;
 VAR_CUMFLO.UP(R,P,C,ALLYEAR,LL) = INF;
 VAR_CUMCOM.LO(R,C,COM_VAR,ALLYEAR,LL) = 0;
 VAR_CUMCOM.UP(R,C,COM_VAR,ALLYEAR,LL) = INF;
*------------------------------------------------------------------------------
  LOOP(SOW,
{
        bnd_ucw_mod(
            arg1="",
            arg2="I",
            var=var,
            stages=stages,
            swd=swd,
            sow=sow,
            defined_symbols=bnd_ucw_defined,
        )
    }
{
        bnd_set_mod(
            arg1=f"{var}_CAP",
            arg2="R,T,P",
            arg3="CAP_BND",
            arg4="RTP(RT_PP(R,T),P)",
            arg5="",
            arg6="I",
            stages=stages,
            swd=swd,
            sow=sow,
            stochastic_symbol_declared=s_cap_bnd_declared,
        )
    }
* Cumulative variable bounds
    VAR_CUMFLO.LO(R,P,C,YEAR,LL)$S_FLO_CUM(R,P,C,YEAR,LL,'LO','1',SOW) = S_FLO_CUM(R,P,C,YEAR,LL,'LO','1',SOW)*(1/{
        cufscal
    })*(FLO_CUM(R,P,C,YEAR,LL,'N')+1);
    VAR_CUMFLO.UP(R,P,C,YEAR,LL)$S_FLO_CUM(R,P,C,YEAR,LL,'UP','1',SOW) = S_FLO_CUM(R,P,C,YEAR,LL,'UP','1',SOW)*(1/{
        cufscal
    })*(FLO_CUM(R,P,C,YEAR,LL,'N')+1);
    S_COM_CUM(RC_CUMCOM(R,COM_VAR,YEAR,LL,C),L('LO'),'1',SOW)$(NOT S_COM_CUM(RC_CUMCOM,L,'1',SOW)) = -INF$SUM((RTC(R,T,C),ANNUAL(S)),MIN(0,COM_BNDPRD(RTC,S,L)$DIAG(COM_VAR,'PRD')+COM_BNDNET(RTC,S,L)$DIAG(COM_VAR,'NET')+1-1));
    VAR_CUMCOM.LO(R,C,COM_VAR,YEAR,LL)$S_COM_CUM(R,COM_VAR,YEAR,LL,C,'LO','1',SOW) = S_COM_CUM(R,COM_VAR,YEAR,LL,C,'LO','1',SOW)*(1/{
        cucscal
    })*(COM_CUM(R,COM_VAR,YEAR,LL,C,'N')+1);
    VAR_CUMCOM.UP(R,C,COM_VAR,YEAR,LL)$S_COM_CUM(R,COM_VAR,YEAR,LL,C,'UP','1',SOW) = S_COM_CUM(R,COM_VAR,YEAR,LL,C,'UP','1',SOW)*(1/{
        cucscal
    })*(COM_CUM(R,COM_VAR,YEAR,LL,C,'N')+1);

{
        '''
  RTP_FFCS(RTP(R,T,P),CG,COM_GRP)$RP_FFSGG(R,P,CG,COM_GRP) =
    SUM((RP_FFSGGM(R,P,CG,COM_GRP,CG1,CG2),SW_TSW(SOW,T,W)),PROD(SW_MAP(T,W,J,WW)$S_FLO_FUNC(RTP,CG1,CG2,J,WW),S_FLO_FUNC(RTP,CG1,CG2,J,WW))-1);
* Remap reduced FUNC flows
  LOOP(RPCG_PTRAN(RP,C,COM,CG,CG2)$RP_FFSGG(RP,CG,CG2),IF(RPC_FFUNC(RP,C),RP_DCGG(RP,C,CG,CG2,'UP')=YES; ELSE RP_DCGG(RP,COM,CG,CG2,'LO')=YES));
  RP_DCGG(RPC_FFUNC(RP,COM),CG,C,'UP')$(RPG_1ACE(RP,CG,COM)$RPC_ACT(RP,C)) $= RP_FFSGG(RP,CG,C);
  RTP_FFCS(RTP(R,T,P),ACTCG,C)$RPC_FFUNC(R,P,C) $= SUM(RP_DCGG(R,P,C,CG,CG2,L),(POWER(RTP_FFCS(RTP,CG,CG2)+1,BDSIG(L))-1)$(RTP_FFCS(RTP,CG,CG2)+1));
  OPTION CLEAR=RP_DCGG;
'''
        if rtp_ffcs_defined
        else ""
    }
{"CM_MAXC(ALLYEAR,ITEM) $= S_CM_MAXC(ALLYEAR,ITEM,'1',SOW);" if cli == "YES" else ""}
  );
*------------------------------------------------------------------------------
IF(SW_PHASE=2,SPAR_UCSL(SOW,UC_N,U2,U3,U4)=0);
IF(CARD(REG_FIXT)=0,EQ_OBJ.M$({model_name}.SOLVEOPT<>1)=0; OPTION SOLVEOPT=REPLACE);
{
        clearsol_stp(
            arg1="$EQ_OBJ.M",
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
"""
