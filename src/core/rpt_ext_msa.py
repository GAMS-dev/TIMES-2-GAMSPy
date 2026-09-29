# rpt_ext_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * RPT_EXT.msa - Extension for MACRO Stand-Alone link: soft-link driver
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Equation

from core.base_class import GamsClass
from core.pp_clean_mod import PpCleanMod
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.solprep_msa import solprep_msa
from core.solvcoef_msa import SolvcoefMsa
from core.solve_msa import SolveMsa
from core.solve_stp import SolveStp

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtMsa(GamsClass):
    """Translation unit for rpt_ext.msa."""

    # Instance attributes
    module_name: str = "rpt_ext_msa"
    gams_source: str = "rpt_ext.msa"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        model_name: str,
        equations: list[Equation],
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.model_name = model_name
        self.equations = equations
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET MACST / VAR, IRE, DAM /;
""",
        )

        rpt_labels = [
            "TM_GDP-REF",
            "TM_GDP-ACT",
            "TM_PRD-Y",
            "TM_CON-C",
            "TM_INV-I",
            "TM_ESCOST",
        ]
        if self.env.msa.upper() == "MSA":
            rpt_labels.append("TM_GDPLOS")
        self.add_records_to_universe_item(records=rpt_labels)

        self.tc.enqueue(self.exec1)

        self.env.set_scoped("solveda", "1")
        self.include(RptliteRpt(self.tc, self.env, config=RptliteRptConfig()))
        self.env.set_scoped("solveda", "0")
        self.tc.enqueue(
            self.exec_solprep_msa,
            arg1="INIT",
            arg2="0",
            msa=self.env.msa,
            v=self.env.v,
            pgprim=self.env.pgprim,
            sow=self.env.sow,
            stages=self.env.stages,
            etl=self.env.etl,
            invlif=self.env.invlif,
            anncost=self.env.anncost,
            sysprefix=self.env.sysprefix,
            tpulse=self.env.tpulse,
            mx=self.env.mx,
            varv=self.env.varv,
            sws=self.env.sws,
            varm=self.env.varm,
            var=self.env.var,
            vart=self.env.vart,
            micro=self.env.micro,
            capjd=self.env.capjd,
            capwd=self.env.capwd,
            timesed=self.env.timesed,
            obj=self.env.obj,
            varcost=self.env.varcost,
            cli=self.env.cli,
            solveda=self.env.solveda,
            scum=self.env.scum,
            sw_notags=self.env.sw_notags,
            objann=self.env.objann,
            dflbl=self.env.dflbl,
            bencost=self.env.bencost,
            discshift=self.env.discshift,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            vnret_defined=self.tc.defined("VNRET"),
            is_vnret_defined=self.tc.defined("VNRET"),
            is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
            is_mi_agc_defined=self.tc.defined("MI_AGC"),
            is_tm_catt_defined=self.tc.defined("TM_CATT"),
            is_dam_cost_defined=self.tc.defined("DAM_COST"),
        )
        if self.env.rpoint != "NO":
            self.tc.enqueue(self.exec_optfile, self.env.model_name)
            self.include(PpCleanMod(self.tc, self.env))
            if self.env.is_set("fixboh"):
                self.include(
                    SolveStp(
                        self.tc,
                        self.env,
                        arg1="mod",
                        model_name=self.model_name,
                        equations=self.equations,
                    )
                )

        self.tc.enqueue(self.exec_process_macro, self.env.msa)
        self.include(SolvcoefMsa(self.tc, self.env))
        self.tc.enqueue(self.exec_complete_beoh_params)
        self.include(SolveMsa(self.tc, self.env))
        self.tc.enqueue(self.exec_reporting, self.env.msa)

    def exec1(self: RptExtMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  LOOP(T,MR(R)$(REG_FIXT(R) LT YEARVAL(T)) = YES);
  MR(R)$(NOT SUM(ALLYEAR$TM_GR(R,ALLYEAR),YES)) = NO;
  MREG(MR) = YES;
""",
        )

    def exec_optfile(self: RptExtMsa, model_name: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  {model_name}.OPTFILE = 1;
""",
        )

    def exec_process_macro(self: RptExtMsa, msa: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Process macro parameters
  TM_DEPR(R)$(NOT TM_DEPR(R)) = TM_DEFVAL('DEPR');
  TM_ESUB(R)$(NOT TM_ESUB(R)) = TM_DEFVAL('ESUB');
  TM_KGDP(R)$(NOT TM_KGDP(R)) = TM_DEFVAL('KGDP');
  TM_KPVS(R)$(NOT TM_KPVS(R)) = TM_DEFVAL('KPVS');
  TM_DMTOL(R)$(NOT TM_DMTOL(R))   = TM_DEFVAL('DMTOL');
  TM_IVETOL(R)$(NOT TM_IVETOL(R)) = TM_DEFVAL('IVETOL');

  IF(CARD(TM_GROWV)=0, TM_GROWV(R,T) $= TM_GR(R,T));
{"TM_AMP(MR,T) = MAX(0,SMAX(PP(TT)$(ORD(TT)>ORD(T)),TM_ANNC(MR,TT)/(TM_GDPGOAL(MR,TT)/TM_GDPGOAL(MR,T))*POWER(TM_DEFVAL('ESC'),YEARVAL(T)-YEARVAL(TT)))-TM_ANNC(MR,T));" if msa.upper() == "CSA" else ""}
  OPTION DEM < TM_DEM;
  OPTION MRTC < TM_DEM;
  IF(CARD(TM_DDF) = 0, TM_DDF(MRTC) = EPS);
  VAR_NTX.FX(MR,TP,TRD) = EPS; TRD(MACST) = NO;
""",
        )

    def exec_complete_beoh_params(self: RptExtMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Complete BEOH parameters for damage
  LOOP(TLAST(T), F=E(T); CNT=TM_PWT(T)/D(T));
  LOOP((XTP(YEAR),SUPERYR(TLAST,LL(YEAR-CM_LED(YEAR)))),Z=CM_LED(XTP)/2; MY_F=YEARVAL(LL);
   IF(MY_F>F,TM_PWT(LL)=CNT*(MY_F-F+Z); F=MY_F+Z); TM_PWT(XTP)=CNT*CEIL(YEARVAL(XTP)-F);
   TM_UDF(R,XTP) = TM_UDF(R,LL) * TM_DFACTCURR(R,LL)**(2*Z));
  Z=SUM(TLAST(T),B(T)+TM_ARBM*D(T)); TM_XWT(R,XTP)$(CM_LED(XTP)>0)=(MIN(YEARVAL(XTP),Z)-MIN(YEARVAL(XTP)-CM_LED(XTP),Z))/CM_LED(XTP)*TM_PWT(XTP)*TM_UDF(R,XTP);
  LOOP(PP(T),TM_XWT(MR(R),XTP)$SUPERYR(T,XTP)=TM_XWT(R,XTP)/SUM(SUPERYR(T,LL)$XTP(LL),TM_XWT(R,LL)));
""",
        )

    def exec_reporting(self: RptExtMsa, msa: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Reporting parameters
  TM_RESULT('TM_GDP-REF',MR,T) = TM_GDPGOAL(MR,T);
  TM_RESULT('TM_GDP-ACT',MR,T) = TM_GDP(MR,T);
  TM_RESULT('TM_PRD-Y',MR,T)   = VAR_Y.L(MR,T);
  TM_RESULT('TM_CON-C',MR,T)   = VAR_C.L(MR,T);
  TM_RESULT('TM_INV-I',MR,T)   = VAR_INV.L(MR,T);
  TM_RESULT('TM_ESCOST',MR,T)  = VAR_EC.L(MR,T);
{"TM_RESULT('TM_GDPLOS',MR,T) = 100*(TM_GDPGOAL(MR,T)-TM_GDP(MR,T))/TM_GDPGOAL(MR,T);" if msa.upper() == "MSA" else ""}
  DISPLAY TM_RESULT;
""",
        )

    def exec_solprep_msa(
        self: RptExtMsa,
        arg1: str,
        arg2: str,
        msa: str,
        v: str,
        pgprim: str,
        sow: str,
        rtp_ffcs_defined: bool,
        stages: str,
        etl: str,
        invlif: str,
        anncost: str,
        sysprefix: str,
        tpulse: str,
        is_vnret_defined: bool,
        varv: str,
        sws: str,
        varm: str,
        is_obj_combal_defined: bool,
        var: str,
        vart: str,
        micro: str,
        is_mi_agc_defined: bool,
        capjd: str,
        capwd: str,
        timesed: str,
        obj: str,
        varcost: str,
        vnret_defined: bool,
        is_tm_catt_defined: bool,
        is_dam_cost_defined: bool,
        cli: str,
        mx: str,
        solveda: str,
        scum: str,
        sw_notags: str,
        objann: str,
        dflbl: str,
        bencost: str,
        discshift: float,
    ) -> None:
        code = solprep_msa(
            arg1=arg1,
            arg2=arg2,
            msa=msa,
            v=v,
            pgprim=pgprim,
            sow=sow,
            stages=stages,
            etl=etl,
            invlif=invlif,
            anncost=anncost,
            sysprefix=sysprefix,
            tpulse=tpulse,
            mx=mx,
            varv=varv,
            sws=sws,
            varm=varm,
            var=var,
            vart=vart,
            micro=micro,
            capjd=capjd,
            capwd=capwd,
            timesed=timesed,
            obj=obj,
            varcost=varcost,
            cli=cli,
            solveda=solveda,
            rtp_ffcs_defined=rtp_ffcs_defined,
            is_vnret_defined=is_vnret_defined,
            is_obj_combal_defined=is_obj_combal_defined,
            is_mi_agc_defined=is_mi_agc_defined,
            vnret_defined=vnret_defined,
            is_tm_catt_defined=is_tm_catt_defined,
            is_dam_cost_defined=is_dam_cost_defined,
            scum=scum,
            sw_notags=sw_notags,
            objann=objann,
            dflbl=dflbl,
            bencost=bencost,
            discshift=discshift,
        )
        self.tc.add_gams_code(module=self, phase="run", code=code)
