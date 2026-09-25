# cal_nored_red.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================================*
# * CAL_RED the code associated with the substitution of flow variables by activity variables
# *	arg1 - commodity of flow
# *	arg2 - commodity associated with the activity variable
# *	arg3 - timeslice index	of flow variable
# *	arg4 - process index of flow variable
# *	arg5 - period index of flow variable
# *	arg6 - for output routine '.L' suffix. otherwise nothing
# *	arg7 - optional T or V or '' (for non-vintaged / vintaged / general case)
# *=============================================================================================*

from __future__ import annotations

from typing import TYPE_CHECKING

from gamspy import Domain, Number, Sum

from core.cal_red_red import CalRedRedConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Variable
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SET_OR_ALIAS
    from utils.times_model_class import TimesModelClass


# Use same config as in cal_red_red to make it easier to switch
def cal_nored_red_GP(
    g: TimesModelClass, config: CalRedRedConfig
) -> Expression | ImplicitSet | Sum:
    """GAMSPy counterpart of cal_nored_red().

    arg6 selects the '.L' suffix, arg9 the optional SUM domain (arg8 of the string
    version) and arg10 the optional multiplier.
    """
    cc = config

    r, v, allts, cg3, com2 = g.r, g.v, g.allts, g.cg3, g.com2

    shp3: Expression | Number = Number(1)
    vnt: SET_OR_ALIAS = cc.arg5 if cc.arg7 == "T" else v
    shg = (cc.arg4, cg3, cc.arg1)
    tst: ImplicitSet | Number = g.PrcVint[r, cc.arg4]

    if cc.arg7 == "V":
        tst = Number(1)

    if cc.arg7 != "T":
        vnt = v

    if cc.def_rtp_ffcs:
        shp3 = 1 + g.rtp_ffcs[r, vnt, *shg, *cc.sow]

    if vnt is v:
        shp3 = (1 + g.rtp_ffcx[r, v, cc.arg5, *shg].where[tst]) * shp3

    def total(
        expr: Expression | ImplicitSet,
    ) -> Expression | ImplicitSet | Sum:
        """arg8/arg9 of the string version: SUM(arg9, expr) or just expr."""
        # NB: gamspy's Sum() type hint omits Condition, which GAMS accepts
        return expr if cc.index_set is None else Sum(cc.index_set, expr)  # type: ignore[arg-type]

    VAR_FLO: Variable = g.get_variable(f"{cc.var}_FLO")
    flo = VAR_FLO.l if cc.is_output else VAR_FLO

    return total(
        # *  flow variable cannot be replaced
        flo[r, vnt, cc.arg5, cc.arg4, cc.arg1, cc.arg3, *cc.sow].where[
            ~g.RpcEmis[r, cc.arg4, cc.arg1]
        ]
        # *   emission flow = flow variable * emission factor
        + Sum(
            Domain(g.FsEmit[r, cc.arg4, cc.arg1, cg3, com2], allts).where[
                g.rs_fr[r, cc.arg3, allts]
                * g.RtpcsVarf[r, cc.arg5, cc.arg4, com2, allts]
            ],
            (
                flo[r, vnt, cc.arg5, cc.arg4, com2, allts, *cc.sow]
                * g.coef_ptran[r, vnt, cc.arg4, cg3, com2, cc.arg1, allts]
                * shp3
            )
            * g.rs_fr[r, cc.arg3, allts]
            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, cc.arg5, com2, cc.arg3, allts, cc.sow)),
        ).where[g.RpcEmis[r, cc.arg4, cc.arg1]]
    )


def cal_nored_red(
    var: str,
    sow: str,
    pgprim: str,
    def_rtp_ffcs: bool,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    arg10: str = "",
) -> str:
    shp3 = ""
    vnt = arg5
    shg = f",{arg4},CG3,{arg1}"
    tst = f"$PRC_VINT(R,{arg4})"

    if arg7 == "V":
        tst = ""
    if arg7 != "T":
        vnt = "V"
    if def_rtp_ffcs:
        shp3 = f"*(1+RTP_FFCS(R,{vnt}{shg}{sow}))"
    if vnt == "V":
        shp3 = f"*(1+RTP_FFCX(R,V,{arg5}{shg}){tst}){shp3}"

    return rf"""
{arg8}({arg9}
*  flow variable cannot be replaced
   {var}_FLO{arg6}(R,{vnt},{arg5},{arg4},{arg1},{arg3} {sow})$(NOT RPC_EMIS(R,{arg4},{arg1}))
    +
*   emission flow = flow variable * emission factor
   SUM((FS_EMIT(R,{arg4},{arg1},CG3,COM2),ALL_TS)$(RS_FR(R,{arg3},ALL_TS)*RTPCS_VARF(R,{arg5},{arg4},COM2,ALL_TS)),
     {var}_FLO{arg6}(R,{vnt},{arg5},{arg4},COM2,ALL_TS{sow}) * COEF_PTRAN(R,{vnt},{arg4},CG3,COM2,{arg1},ALL_TS){shp3} *
     RS_FR(R,{arg3},ALL_TS)*(1+{macro.rtcs_fr.rtcs_fr("R", arg5, "COM2", arg3, "ALL_TS")})
   )$RPC_EMIS(R,{arg4},{arg1})
)
"""
