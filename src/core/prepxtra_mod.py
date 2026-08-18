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
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Else, If, Loop, Number, Ord, Smax, Smin, SpecialValues

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.prepparm_gms import PrepparmGms, PrepparmGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        g = self.tc

        r, p, c, s, t, cur = g.r, g.p, g.c, g.s, g.t, g.cur

        if self.arg1.upper() == "XTIE":
            prepparms: list[PrepparmGmsConfig] = [
                # * COST PARAMETERS: Interpolated over T
                PrepparmGmsConfig(
                    arg1="NCAP_COST",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_DCOST",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_DLAGC",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_FOM",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_FSUB",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_FTAX",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_ISUB",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_ITAX",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_VALU",
                    arg2=(r,),
                    arg3=(p, c, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="NCAP_ISPCT",
                    arg2=(r,),
                    arg3=(p,),
                    arg4=("0", "0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                # * Commodity related attributes (6)
                PrepparmGmsConfig(
                    arg1="COM_CSTNET",
                    arg2=(r,),
                    arg3=(c, s, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=Number(1),
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="COM_CSTPRD",
                    arg2=(r,),
                    arg3=(c, s, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=Number(1),
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="COM_SUBNET",
                    arg2=(r,),
                    arg3=(c, s, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=Number(1),
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="COM_SUBPRD",
                    arg2=(r,),
                    arg3=(c, s, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=Number(1),
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="COM_TAXNET",
                    arg2=(r,),
                    arg3=(c, s, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=Number(1),
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="COM_TAXPRD",
                    arg2=(r,),
                    arg3=(c, s, cur),
                    arg4=("0", "0"),
                    arg5=t,
                    arg6=Number(1),
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                # * Flow related attributes & inter-regional exchange flows (6)
                PrepparmGmsConfig(
                    arg1="ACT_COST",
                    arg2=(r,),
                    arg3=(p, cur),
                    arg4=("0", "0", "0"),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="FLO_COST",
                    arg2=(r,),
                    arg3=(p, c, s, cur),
                    arg4=("0",),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="FLO_DELIV",
                    arg2=(r,),
                    arg3=(p, c, s, cur),
                    arg4=("0",),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="FLO_SUB",
                    arg2=(r,),
                    arg3=(p, c, s, cur),
                    arg4=("0",),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
                PrepparmGmsConfig(
                    arg1="FLO_TAX",
                    arg2=(r,),
                    arg3=(p, c, s, cur),
                    arg4=("0",),
                    arg5=t,
                    arg6=g.Rtp[r, t, p],
                    arg7=SpecialValues.EPS,
                    arg8=3,
                ),
            ]

            for config in prepparms:
                self.include(PrepparmGms(self.tc, self.env, config=config))

            # fmt: off
            batincludes: list[FillparmGmsConfig] = [
                FillparmGmsConfig(g.ire_price, (g.r,),                 (g.p, g.c, g.s, g.allr, g.ie, g.cur), (),        g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                # * Components of merged UC attribs
                FillparmGmsConfig(g.uc_comcon, (g.ucn, g.side,g.allr), (g.c,g.s),                            ("0",) * 2, g.t, Number(1),            Number(0)),
                FillparmGmsConfig(g.uc_comnet, (g.ucn, g.side,g.allr), (g.c,g.s),                            ("0",) * 2, g.t, Number(1),            Number(0)),
                FillparmGmsConfig(g.uc_comprd, (g.ucn, g.side,g.allr), (g.c,g.s),                            ("0",) * 2, g.t, Number(1),            Number(0)),
            ]
            # fmt: on
            for fillparm_config in batincludes:
                self.include(FillparmGms(self.tc, self.env, fillparm_config))

            # * General attribs
            filparam_batincludes: list[FilparamGmsConfig] = [
                FilparamGmsConfig(
                    src=g.multi,
                    arg2=(g.j,),
                    tail1=(),
                    arg4=("", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Milestonyr,
                    arg7=Number(0),  # "NO$"
                ),
                FilparamGmsConfig(
                    src=g.g_drate,
                    arg2=(g.r,),
                    tail1=(g.cur,),
                    arg4=("", "", "", "", ""),
                    arg5=g.year,
                    arg6=g.t,
                ),
            ]
            for f_config in filparam_batincludes:
                self.include(FilparamGms(self.tc, self.env, config=f_config))

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

    def exec1(self: PrepxtraMod, condition: bool) -> None:
        g = self.tc
        r, p, t, ll = g.r, g.p, g.t, g.ll

        g.Modlyear[ll] = t[ll] + g.Pastyear[ll]
        # -----------------------------------------------------------------------------
        # Clean up some unwanted stuff
        if condition:
            with Loop(g.PyrS[ll]):
                g.ncap_pasti[r, ll, p].where[g.prc_resid[r, "0", p]] = 0
                g.ncap_tlife[r, ll, p].where[g.prc_resid[r, "0", p]] = 0
            g.prc_resid[r, "0", p] = 0

    def exec2(self: PrepxtraMod, dflbl: str) -> None:
        g = self.tc
        r, t, ll, year = g.r, g.t, g.ll, g.year
        ucn, z, f = g.ucn, g.z, g.f
        UcDt, UcTSum, UcTSucc, UcTEach = g.UcDt, g.UcTSum, g.UcTSucc, g.UcTEach

        # Check 'every T' specifications through using DFLBL:
        # For T_SUM, fill in between user-specified year range or all
        UcDt[r, ucn].where[UcTSum[r, ucn, dflbl]] = True
        UcTSum[UcDt, dflbl] = False
        with Loop(UcDt):
            z[...] = Smax(UcTSum[UcDt, ll], Ord(ll))
            with If(z > 0):
                f[...] = Smin(UcTSum[UcDt, ll], Ord(ll))
            with Else():  # type: ignore[no-untyped-call]
                f[...] = z
            with If(z != f):
                UcTSum[UcDt, t[ll]].where[(Ord(ll) > f) & (Ord(ll) < z)] = True
            with Else():  # type: ignore[no-untyped-call]
                UcTSum[UcDt, t] = True
        UcDt.setRecords(None)
        UcTSucc[r, ucn, t].where[UcTSucc[r, ucn, dflbl]] = True
        UcTEach[r, ucn, t].where[UcTEach[r, ucn, dflbl]] = True
        with Loop(t[year]):
            UcTEach[r, ucn, ll + (Ord(year) - Ord(ll))].where[
                g.Eohyears[ll] & g.Periodyr[t, ll] & UcTEach[r, ucn, ll]
            ] = True
            UcTSucc[r, ucn, ll + (Ord(year) - Ord(ll))].where[
                g.Eohyears[ll] & g.Periodyr[t, ll] & UcTSucc[r, ucn, ll]
            ] = True
            UcTSum[r, ucn, ll + (Ord(year) - Ord(ll))].where[
                g.Eohyears[ll] & g.Periodyr[t, ll] & UcTSum[r, ucn, ll]
            ] = True

    def exec3(self: PrepxtraMod, gdxpath: str, run_name: str) -> None:
        # CARD of a string literal is its number of characters, computed in Python
        self.tc.z[...] = len(f"{gdxpath}{run_name}") + 16

    def exec4(
        self: PrepxtraMod, gdxpath: str, run_name: str, gtime: str, gdate: str
    ) -> None:
        # PUT / PUT_UTILITY has no GAMSPy equivalent, so this stays raw GAMS.
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
PUT QLOG; FILE.PW=512; PUT_UTILITY 'SHELL' / 'mv -f _dd_.gdx ' '{gdxpath}{run_name}' @(Z+12) '{gtime}' '.GDX' @(Z+5) '{gdate}' "_" @Z '~Data_';
""",
        )

    def comp1(
        self: PrepxtraMod, gdxpath: str, run_name: str, gtime: str, gdate: str
    ) -> None:
        # $hiddencall mv -f _dd_.gdx "%GDXPATH%%RUN_NAME%~Data_%GDATE%_%GTIME%.gdx"
        source = Path("_dd_.gdx")
        target = Path(f"{gdxpath}{run_name}~Data_{gdate}_{gtime}.gdx")

        if not source.exists():
            # mv reports a missing source, but $hiddencall discards the error
            # level, so a missing data dump must never stop the run.
            logger.debug("No %s to move to %s", source, target)
            return

        try:
            # shutil.move replaces an existing target, just like mv -f
            shutil.move(source, target)
        except OSError:
            # Same reasoning as above: a failing move (e.g. because %GDXPATH%
            # does not exist) is silent in GAMS and must not stop the run.
            logger.warning("Could not move %s to %s", source, target)
