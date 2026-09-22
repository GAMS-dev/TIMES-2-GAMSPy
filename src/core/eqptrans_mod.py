# eqptrans_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQPTRANS is the flow-to-flow transformation constraint
# *=============================================================================*
# * Questions/Comments:
# *  - EQ_PTRANS is dropped if substition for FLO_FUNC activated
# *  - EQ level according to RPS_S1, VAR_FLOs according RPCS_VAR
# *  - COEF_PTRAN created in coef_ptr.mod

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.cal_nored_red import cal_nored_red
from core.cal_red_red import cal_red_red
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqptransMod(GamsClass):
    """Translation unit for eqptrans.mod."""

    # Instance attributes
    module_name: str = "eqptrans_mod"
    gams_source: str = "eqptrans.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("shg", ",P,COM_GRP,CG")
        base_shp1 = f"(1+RTP_FFCX(R,V,T{self.env.shg})$PRC_VINT(R,P))"
        if self.tc.defined("RTP_FFCS"):
            self.env.set_scoped(
                "shp1",
                f"{base_shp1}*(1+RTP_FFCS(R,V{self.env.shg}{self.env.sow}))",
            )
        else:
            self.env.set_scoped("shp1", base_shp1)

        self.comp1(
            cal_red=self.env.cal_red,
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            shp1=self.env.shp1,
            var=self.env.var,
            sow=self.env.sow,
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
        )

    def comp1(
        self: EqptransMod,
        cal_red: str,
        eq: str,
        r_v_t: str,
        swt: str,
        shp1: str,
        var: str,
        sow: str,
        pgprim: str,
        def_rtp_ffcs: bool,
    ) -> None:
        include_cal_red = ""
        # only set in pp_reduce.red
        if cal_red == "cal_red.red":
            include_cal_red = cal_red_red(
                arg1="C",
                arg2="COM",
                arg3="TS",
                arg4="P",
                arg5="T",
                var=var,
                sow=sow,
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
            )
        elif cal_red == "cal_nored.red":
            include_cal_red = cal_nored_red(
                arg1="C",
                arg2="COM",
                arg3="TS",
                arg4="P",
                arg5="T",
                var=var,
                sow=sow,
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
            )
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")
        rts = macro.rts(s="S", g=self.tc, env=self.env)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
    {eq}_PTRANS(RTP_VINTYR({r_v_t},P),COM_GRP,CG,{rts}{swt})$((RPS_S1(R,P,S) * RP_STD(R,P) *
* All valid tuples are in RPCC_FFUNC (REDUCE taken into account); all STG excluded
                SUM((RPC(R,P,C),RS_TREE(R,S,TS))$COEF_PTRAN(R,V,P,COM_GRP,C,CG,TS),1))$RPCC_FFUNC(R,P,COM_GRP,CG))..

* dependent commodities - consider that the commodity may have a COM_TS shape
       SUM((COM_GMAP(R,CG,C),RS_TREE(R,S,TS))$RTPCS_VARF(R,T,P,C,TS),
           RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")}) *
* [UR] model reduction REDUCE is set in *.run
{include_cal_red}
          )

    =E=

* control commodities
       SUM((RTPCS_VARF(R,T,P,C,TS),RS_TREE(R,S,TS))$COEF_PTRAN(R,V,P,COM_GRP,C,CG,TS),
           COEF_PTRAN(R,V,P,COM_GRP,C,CG,TS) *
           RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")}) *
* [UR] model reduction REDUCE is set in *.run
{include_cal_red}
          ) * {shp1} * (1+(ACT_FLO(R,V,P,CG,S)-1$ACT_FLO(R,V,P,CG,S))$PRC_CG(R,P,COM_GRP))
    ;
""",
        )
