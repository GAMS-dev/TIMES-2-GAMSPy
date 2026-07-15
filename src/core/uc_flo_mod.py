# uc_flo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_FLO the code associated with the flow variable in the EQ_USERCON
# *     - arg1 region summation index
# *     - arg2 period summation index
# *     - arg3 time-slice summation index
# *     - arg4 'T' or 'T+1' index
# *     - arg5 'LHS' or 'RHS'
# *     - arg6 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*
# *UR Questions/Comments:
# *  -

from __future__ import annotations

import logging

from core.cal_caps_mod import cal_caps_mod
from core.cal_nored_red import cal_nored_red
from core.cal_red_red import cal_red_red
from utils.macros import macro_config as macro

logger = logging.getLogger(__name__)


def uc_flo_mod(
    cal_red: str,
    var: str,
    swt: str,
    def_rtp_ffcs: bool,
    sow: str,
    cufscal: str,
    pgprim: str,
    sws: str,
    varm: str,
    varv: str,
    is_vnret_defined: bool,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    arg10: str = "",
    arg11: str = "",
    arg12: str = "",
) -> str:
    """Translation unit for uc_flo.mod."""
    if arg6 == "1":
        var = arg9
        sow = arg10

    include_cal_red = ""
    # only set in pp_reduce.red
    if cal_red == "cal_red.red":
        include_cal_red = cal_red_red(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5=arg4,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
            sow=sow,
            var=var,
        )
    elif cal_red == "cal_nored.red":
        include_cal_red = cal_nored_red(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5=arg4,
            def_rtp_ffcs=def_rtp_ffcs,
            sow=sow,
            var=var,
            pgprim=pgprim,
        )
    else:
        raise ValueError(f"Unexpected value for cal_red: {cal_red}")

    include_cal_caps_ = cal_caps_mod(
        is_vnret_defined=is_vnret_defined,
        arg1=arg4,
        arg2=f"UC_FLO(UC_N,{arg5},R,{arg7},P,C,TS)",
        arg3="TS",
        varv=varv,
        sws=sws,
        varm=varm,
    )

    return rf"""
*"SUM(UC_R_SUM(R,UC_N)," or bracket "("
 {arg1}
*     "SUM(UC_T_SUM(R,UC_N,T)," or bracket "("
      {arg2}
{"(1+(FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','FLO','PERDISC')-1)$UC_DT(R,UC_N)) *" if arg6 == "2" else ""}
{"(1/G_YRFR(R,S)) *" if arg6 == "S" else ""}
*          "SUM(UC_TS_SUM(R,UC_N,S)," or bracket "("
           {arg3}
                 SUM((RTP_VINTYR(R,V,{arg4},P),RTPCS_VARF(R,{arg4},P,C,TS))$(UC_MAP_FLO(UC_N,{arg5},R,P,C)$RS_FR(R,S,TS)),
                          {arg11}({arg12}
*V0.9a S reference should be TS
* [UR] model reduction REDUCE is set in *.run
{include_cal_red}
                              * UC_FLO(UC_N,{arg5},R,{arg7},P,C,TS) *
*GG* use the derived multipier
* [AL] PROD operator is useful here, but must be activated due to a GAMS bug:
                               PROD(ANNUAL,1)*PROD(RS_BELOW(R,TS,S),RS_FR(R,S,TS)*(1+RTCS_FR(R,{arg4},C,S,TS))) *

{f"                            PROD(UC_ATTR(R,UC_N,{arg5},'FLO','GROWTH')," if arg6 == "1" else ""}
{f"                                     POWER(ABS(UC_FLO(UC_N,{arg5},R,{arg7},P,C,TS)),{arg8}*UC_SIGN({arg5})-1)) *" if arg6 == "1" else ""}
                               PROD(UC_ATTR(R,UC_N,{arg5},'FLO',UC_PERDS),FPD({arg4}) *
                                    PROD(UC_NEWFLO(UC_PERDS),1$(SAMEAS(V,{arg4})+RVPT(R,V,P,{arg4}))/FPD({arg4}))) *

                               PROD(REG(R)$SUM(UC_ATTR(R,UC_N,{arg5},'FLO',UC_COST),1),
                                SUM((RDCUR(R,CUR),TS_ANN(TS,SL)),
                                  {macro.obj_fcost("R", arg4, "P", "C", "SL", "CUR")}$UC_ATTR(R,UC_N,{arg5},'FLO','COST')
                                 +{macro.obj_fdelv("R", arg4, "P", "C", "SL", "CUR")}$UC_ATTR(R,UC_N,{arg5},'FLO','DELIV')
                                 +MIN(0,{macro.obj_ftax("R", arg4, "P", "C", "SL", "CUR")})$UC_ATTR(R,UC_N,{arg5},'FLO','SUB')
                                 +MAX(0,{macro.obj_ftax("R", arg4, "P", "C", "SL", "CUR")})$UC_ATTR(R,UC_N,{arg5},'FLO','TAX')))
                             )
                    ) +

                 SUM(UC_CAPFLO(UC_N,{arg5},R,P,C),
{include_cal_caps_}
                      *
{f"                      PROD(UC_ATTR(R,UC_N,{arg5},'FLO','GROWTH')," if arg6 == "1" else ""}
{f"                        SUM(RPCS_VAR(R,P,C,TS),RS_FR(R,TS,S)*POWER(ABS(UC_FLO(UC_N,{arg5},R,{arg7},P,C,TS)),{arg8}*UC_SIGN({arg5})-1))) *" if arg6 == "1" else ""}
                     PROD(UC_ATTR(R,UC_N,{arg5},'FLO',UC_PERDS),FPD({arg4})$(NOT UC_NEWFLO(UC_PERDS))) *

                     PROD(REG(R)$SUM(UC_ATTR(R,UC_N,{arg5},'FLO',UC_COST),1),
                      SUM(RPCS_VAR(R,P,C,TS),RS_FR(R,TS,S) *
                       SUM((RDCUR(R,CUR),TS_ANN(TS,SL)),
                         {macro.obj_fcost("R", arg4, "P", "C", "SL", "CUR")}$UC_ATTR(R,UC_N,{arg5},'FLO','COST')
                        +{macro.obj_fdelv("R", arg4, "P", "C", "SL", "CUR")}$UC_ATTR(R,UC_N,{arg5},'FLO','DELIV')
                        +MIN(0,{macro.obj_ftax("R", arg4, "P", "C", "SL", "CUR")})$UC_ATTR(R,UC_N,{arg5},'FLO','SUB')
                        +MAX(0,{macro.obj_ftax("R", arg4, "P", "C", "SL", "CUR")})$UC_ATTR(R,UC_N,{arg5},'FLO','TAX'))))
                    )


*          closing bracket of arg3 :
           )

*       closing bracket of arg2 :
        )

*   closing bracket of arg1 :
    )

* Add Cumflos
{f"  +SUM(({arg8}RPC_CUMFLO(R,P,C,ALLYEAR,LL))$UC_CUMFLO(UC_N,R,P,C,ALLYEAR,LL),UC_CUMFLO(UC_N,R,P,C,ALLYEAR,LL)*{var}_CUMFLO(R,P,C,ALLYEAR,LL {swt})*{cufscal})" if arg6 == "2" else ""}
"""
