# equ_ext_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# *  EQETL.ETL technological change equations, with clusters
# *============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtEtl(GamsClass):
    """Translation unit for equ_ext.etl."""

    # Instance attributes
    module_name: str = "equ_ext_etl"
    gams_source: str = "equ_ext.etl"

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
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------------
* Cumulative capacity definition
* [AL] May-2006: Added COEF_RPTI multiplier; It is also added to EQ_IC1 and EQ_IC2.
{self.env.eq}_CUINV({self.env.r_t},TEG {self.env.swt})$(RTP(R,T,TEG)*SEG(R,TEG)) ..
    {self.env.var}_CCAP(R,T,TEG {self.env.sow}) =E= SUM(RTP(R,V(MILESTONYR),TEG)$(ORD(MILESTONYR) LE ORD(T)),
              {self.env.varv}_NCAP(R,V,TEG {self.env.sws}) * COEF_RPTI(R,V,TEG)) + CCAP0(R,TEG);

* Cumulative Capacity Interpolation
{self.env.eq}_CC(RTP({self.env.r_t},TEG) {self.env.swt})$SEG(R,TEG) ..
    {self.env.var}_CCAP(R,T,TEG {self.env.sow}) =E= SUM(KP$((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1)), {self.env.var}_LAMBD(R,T,TEG,KP {self.env.sow}));

* Force sum of binary variables delta to 1
{self.env.eq}_DEL(RTP({self.env.r_t},TEG) {self.env.swt})$SEG(R,TEG) ..
    SUM(KP$((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1)), {self.env.var}_DELTA(R,T,TEG,KP {self.env.sow})) =E= 1;

* Cumulative Cost Interpolation
{self.env.eq}_COS(RTP({self.env.r_t},TEG) {self.env.swt})$SEG(R,TEG) ..
    {self.env.var}_CCOST(R,T,TEG {self.env.sow}) =E= SUM(KP$((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1)), {self.env.var}_LAMBD(R,T,TEG,KP {self.env.sow})*BETA(R,KP,TEG) + {self.env.var}_DELTA(R,T,TEG,KP {self.env.sow})*ALPH(R,KP,TEG));

* Constraints on lambda
{self.env.eq}_LA1(RTP({self.env.r_t},TEG),KP {self.env.swt})$(((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1))$SEG(R,TEG)) ..
    {self.env.var}_LAMBD(R,T,TEG,KP {self.env.sow}) =G= CCAPK(R,KP-1,TEG)*{self.env.var}_DELTA(R,T,TEG,KP {self.env.sow});

{self.env.eq}_LA2(RTP({self.env.r_t},TEG),KP {self.env.swt})$(((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1))$SEG(R,TEG)) ..
    {self.env.var}_LAMBD(R,T,TEG,KP {self.env.sow}) =L= CCAPK(R,KP,TEG)*{self.env.var}_DELTA(R,T,TEG,KP {self.env.sow});

* Additional constraints to improve solution time
* {self.env.eq}_EXPE1(RTP({self.env.r_t},TEG),KP {self.env.swt})$((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1)) ..
*    SUM(KP2$((ORD(KP2) LE ORD(KP))$(ORD(KP2) GE 2)), {self.env.var}_DELTA(R,T,TEG, KP2 {self.env.sow})) =G=
*    SUM(KP2$(ORD(KP2) LE ORD(KP)$(ORD(KP2) GE 2)),   {self.env.var}_DELTA(R,T+1,TEG, KP2 {self.env.sow}));
 {self.env.eq}_EXPE1(RTP(R,V(T-1),TEG),KP {self.env.swt})$(((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1))$SEG(R,TEG)) ..
    SUM(KP2$((ORD(KP2) LE ORD(KP))$(ORD(KP2) GE 2)), {self.env.varv}_DELTA(R,V,TEG,KP2 {self.env.sws}))
        =G= SUM(KP2$(ORD(KP2) LE ORD(KP)$(ORD(KP2) GE 2)), {self.env.var}_DELTA(R,T,TEG, KP2 {self.env.sow}));

* {self.env.eq}_EXPE2(RTP({self.env.r_t},TEG),KP {self.env.swt})$(((ORD(KP) GE 2) AND (NOT (E(T) EQ MIYR_VL)))$(ORD(KP) LE SEG(R,TEG)+1)) ..
*    SUM(KP2$(ORD(KP2) GE ORD(KP)), {self.env.var}_DELTA(R,T,TEG, KP2)) =L= SUM(KP2$(ORD(KP2) GE ORD(KP)), {self.env.var}_DELTA(R,T+1,TEG, KP2));
 {self.env.eq}_EXPE2(RTP(R,V(T-1),TEG),KP {self.env.swt})$(((ORD(KP) GE 2)$(ORD(KP) LE SEG(R,TEG)+1))$SEG(R,TEG)) ..
    SUM(KP2$(ORD(KP2) GE ORD(KP)), {self.env.varv}_DELTA(R,V,TEG,KP2 {self.env.sws}))
        =L= SUM(KP2$(ORD(KP2) GE ORD(KP)), {self.env.var}_DELTA(R,T,TEG, KP2 {self.env.sow}));


* Investments 1st period
* {self.env.eq}_IC1(RTP(R,T,TEG))$(YEARVAL(T) EQ MIYR_V1) .. {self.env.var}_IC(R,T,TEG {self.env.sow}) =E= {self.env.var}_CCOST(R,T,TEG {self.env.sow}) - CCOST0(R,TEG);
 {self.env.eq}_IC1(TL_START({self.env.r_t},TEG) {self.env.swt})$SEG(R,TEG) ..
    {self.env.var}_IC(R,T,TEG {self.env.sow})*COEF_RPTI(R,T,TEG) =E= {self.env.var}_CCOST(R,T,TEG {self.env.sow}) - CCOST0(R,TEG);

* Investments other periods
*{self.env.eq}_IC2(RTP(R,T,TEG))$(YEARVAL(T) GT MIYR_V1) .. {self.env.var}_IC(R,T,TEG) =E= {self.env.var}_CCOST(R,T,TEG)- {self.env.var}_CCOST(R,T-1,TEG);
{self.env.eq}_IC2(RTP({self.env.r_t},TEG) {self.env.swt})$((NOT TL_START(R,T,TEG))$SEG(R,TEG)) ..
    {self.env.var}_IC(R,T,TEG {self.env.sow})*COEF_RPTI(R,T,TEG) =E= {self.env.var}_CCOST(R,T,TEG {self.env.sow}) - SUM(V(T-1),{self.env.varv}_CCOST(R,V,TEG {self.env.sws}));

* Salvage of learning investments: Handled in TIMES by EQOBSALV.mod

* Coupling equation for key in TEG to cluster TCH's, only if TCH in cluster TEG and TEG NE TCH
{self.env.eq}_CLU(RTP({self.env.r_t},TEG) {self.env.swt})$NTCHTEG(R,TEG) ..
   {self.env.var}_NCAP(R,T,TEG {self.env.sow}) =E=
   SUM(PRC$(RTP(R,T,PRC) * CLUSTER(R,TEG,PRC)), CLUSTER(R,TEG,PRC) * {self.env.var}_NCAP(R,T,PRC {self.env.sow}));

*-----------------------------------------------------------------------------
* new clustering equation
{self.env.eq}_MRCLU(RTP({self.env.r_t},TEG) {self.env.swt})$TL_RP_KC(R,TEG) ..
   {self.env.var}_NCAP(R,T,TEG {self.env.sow}) =E=
   SUM(TL_RP_CT(REG,P)$RTP(REG,T,P), TL_MRCLUST(R,TEG,REG,P) * {self.env.var}_NCAP(REG,T,P {self.env.sow}));

*-----------------------------------------------------------------------------
        """,
        )
