# prepxtra_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREPONLY.MOD oversees that all inputs are interpolated when INTEXT_ONLY
# *=============================================================================*

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from core.fillparm_gms import FillparmGms
from core.filparam_gms import FilparamGms
from core.prepparm_gms import PrepparmGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepxtraMod(GamsClass):
    """Translation unit for prepxtra.mod."""

    # Instance attributes
    module_name: str = "prepxtra_mod"
    gams_source: str = "prepxtra.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        if self.arg1.upper() == "XTIE":
            # * COST PARAMETERS: Interpolated over T
            # fmt: off
            batincludes = [
                ("NCAP_COST", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_DCOST", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_DLAGC", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_FOM", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_FSUB", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_FTAX", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_ISUB", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_ITAX", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_VALU", "R", "P,C,CUR", ",'0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("NCAP_ISPCT", "R", "P", ",'0','0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    PrepparmGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                    )
                )

            # * Commodity related attributes (6)
            # fmt: off
            batincludes = [
                ("COM_CSTNET", "R", "C,S,CUR", ",'0','0'", "T", "1", "EPS", "3"),
                ("COM_CSTPRD", "R", "C,S,CUR", ",'0','0'", "T", "1", "EPS", "3"),
                ("COM_SUBNET", "R", "C,S,CUR", ",'0','0'", "T", "1", "EPS", "3"),
                ("COM_SUBPRD", "R", "C,S,CUR", ",'0','0'", "T", "1", "EPS", "3"),
                ("COM_TAXNET", "R", "C,S,CUR", ",'0','0'", "T", "1", "EPS", "3"),
                ("COM_TAXPRD", "R", "C,S,CUR", ",'0','0'", "T", "1", "EPS", "3"),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    PrepparmGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                    )
                )

            # * Flow related attributes & inter-regional exchange flows (6)
            # fmt: off
            batincludes = [
                ("ACT_COST", "R", "P,CUR", ",'0','0','0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("FLO_COST", "R", "P,C,S,CUR", ",'0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("FLO_DELIV", "R", "P,C,S,CUR", ",'0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("FLO_SUB", "R", "P,C,S,CUR", ",'0'", "T", "RTP(R,T,P)", "EPS", "3"),
                ("FLO_TAX", "R", "P,C,S,CUR", ",'0'", "T", "RTP(R,T,P)", "EPS", "3"),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    PrepparmGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                    )
                )

            # fmt: off
            batincludes = [
                ("IRE_PRICE", "R", "P,C,S,ALL_R,IE,CUR", "", "T", "RTP(R,T,P)", "GE 0", ""),
                # * Components of merged UC attribs
                ("UC_COMCON", "UC_N,SIDE,ALL_R", "C,S", ",'0','0'", "T", "1", "GE 0", ""),
                ("UC_COMNET", "UC_N,SIDE,ALL_R", "C,S", ",'0','0'", "T", "1", "GE 0", ""),
                ("UC_COMPRD", "UC_N,SIDE,ALL_R", "C,S", ",'0','0'", "T", "1", "GE 0", ""),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    FillparmGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                    )
                )

            # * General attribs
            # fmt: off
            batincludes = [
                ("MULTI", "J,", "", ",'','','','',''", "LL", "MILESTONYR", "NO$", ""),
                ("G_DRATE", "R,", "CUR", ",'','','','',''", "YEAR", "T", "", ""),
      ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    FilparamGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                        arg8=arg[7],
                    )
                )

        if self.arg1.upper() in ["XTIE", "POST"]:
            self.tc.enqueue(
                self.exec1,
                condition=self.tc.defined("PRC_RESID"),
            )

        if self.arg1.upper() in ["XTIE", "POST", "UCINT"]:
            # * UC Default values
            self.tc.enqueue(self.exec2, dflbl=self.env.dflbl)

        if self.arg1.upper() == "SAVE":
            # * Rename and move saved data GDX file
            # Compute and pad timestamps in Python (Replaces JSTART math and PAD loop)
            now = datetime.datetime.now()
            py_gdate = now.strftime("%Y%m%d")  # E.g., '20260324'
            py_gtime = now.strftime("%H%M%S")  # E.g., '093000'

            self.tc.enqueue(
                self.exec3,
                gdxpath=self.env.gdxpath,
                run_name=self.env.run_name,
            )

            # removed x1 and PAD, is not necessary anymore since python can handle the padding
            self.env.set_scoped(
                "gdate", "10000*MOD(GYEAR(JSTART),100)+100*GMONTH(JSTART)+GDAY(JSTART)"
            )
            self.env.set_scoped("x1", "")
            self.env.set_scoped(
                "gtime", "10000*GHOUR(JSTART)+100*GMINUTE(JSTART)+GSECOND(JSTART)"
            )
            self.env.set_scoped("x2", "5")

            if rf"{self.env.g2x6}{self.arg1}" == "YESSAVE":
                self.env.set_scoped("x2", "")

            if self.tc.test_run:
                self.tc.save_test_state(env=self.env, checkpoint="prepxtra_mod_save")

            if rf"{self.env.g2x6}{self.arg1}{self.env.x2}".upper() == "YESSAVE5":
                self.tc.enqueue(
                    self.exec4,
                    gdxpath=self.env.gdxpath,
                    run_name=self.env.run_name,
                    gtime=py_gtime,
                    gdate=py_gdate,
                )
            else:
                self.tc.enqueue(
                    self.comp1,
                    gdxpath=self.env.gdxpath,
                    run_name=self.env.run_name,
                    gtime=py_gtime,
                    gdate=py_gdate,
                )

    def exec1(self: PrepxtraMod, condition: bool):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
MODLYEAR(LL) = T(LL)+PASTYEAR(LL);
*-----------------------------------------------------------------------------
* Clean up some unwanted stuff
{"LOOP(PYR_S(LL),NCAP_PASTI(R,LL,P)$PRC_RESID(R,'0',P)=0; NCAP_TLIFE(R,LL,P)$PRC_RESID(R,'0',P)=0);" if condition else ""}
{"PRC_RESID(R,'0',P)=0;" if condition else ""}
""",
        )

    def exec2(self: PrepxtraMod, dflbl: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Check 'every T' specifications through using DFLBL:
* For T_SUM, fill in between user-specified year range or all
  UC_DT(R,UC_N)$UC_T_SUM(R,UC_N,'{dflbl}') = YES; UC_T_SUM(UC_DT,'{dflbl}') = NO;
  LOOP(UC_DT, Z=SMAX(UC_T_SUM(UC_DT,LL),ORD(LL));
    IF(Z > 0, F=SMIN(UC_T_SUM(UC_DT,LL),ORD(LL)); ELSE F=Z);
    IF(Z NE F,UC_T_SUM(UC_DT,T(LL))$((ORD(LL) GT F)$(ORD(LL) LT Z)) = YES;
    ELSE UC_T_SUM(UC_DT,T) = YES));
  OPTION CLEAR=UC_DT;
  UC_T_SUCC(R,UC_N,T)$UC_T_SUCC(R,UC_N,'{dflbl}') = YES;
  UC_T_EACH(R,UC_N,T)$UC_T_EACH(R,UC_N,'{dflbl}') = YES;
  LOOP(T(YEAR),
    UC_T_EACH(R,UC_N,LL+(ORD(YEAR)-ORD(LL)))$(EOHYEARS(LL)$PERIODYR(T,LL)$UC_T_EACH(R,UC_N,LL)) = YES;
    UC_T_SUCC(R,UC_N,LL+(ORD(YEAR)-ORD(LL)))$(EOHYEARS(LL)$PERIODYR(T,LL)$UC_T_SUCC(R,UC_N,LL)) = YES;
    UC_T_SUM(R,UC_N,LL+(ORD(YEAR)-ORD(LL)))$(EOHYEARS(LL)$PERIODYR(T,LL)$UC_T_SUM(R,UC_N,LL)) = YES;
  );
""",
        )

    def exec3(self: PrepxtraMod, gdxpath: str, run_name: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
Z=CARD("{gdxpath}{run_name}")+16;
""",
        )

    def exec4(
        self: PrepxtraMod,
        gdxpath: str,
        run_name: str,
        gtime: str,
        gdate: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
PUT QLOG; FILE.PW=512; PUT_UTILITY 'SHELL' / 'mv -f _dd_.gdx ' '{gdxpath}{run_name}' @(Z+12) '{gtime}' '.GDX' @(Z+5) '{gdate}' "_" @Z '~Data_';
""",
        )

    def comp1(
        self: PrepxtraMod,
        gdxpath: str,
        run_name: str,
        gtime: str,
        gdate: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
$hiddencall mv -f _dd_.gdx "{gdxpath}{run_name}~Data_{gdate}_{gtime}.gdx"
""",
        )
