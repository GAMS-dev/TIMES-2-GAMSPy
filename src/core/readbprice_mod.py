# readbprice_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Importing sol_bprice and assigning it to parameter COM_BPRICE
# *=============================================================================*

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Parameter

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ReadbpriceMod(GamsClass):
    """Translation unit for readbprice.mod."""

    module_name: str = "readbprice_mod"
    gams_source: str = "readbprice.mod"

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
        g = self.tc

        if not g.defined("SOL_BPRICE"):
            g.sol_bprice = Parameter(
                g.container, name="SOL_BPRICE", domain=[g.r, g.year, g.c, g.ts, g.cur]
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
$KILL DAM_TVOC
""",
        )

        self.env.set_scoped("tmp", "com_bprice")

        if self.env.timesed.upper() != "YES":
            self.env.set_local("tmp", f"{self.env.gdxpath}{self.env.timesed}")

            current_tmp = self.env.tmp
            if Path(f"{current_tmp}_DP.gdx").exists():
                self.env.set_local("tmp", f"{current_tmp}_DP")

            current_tmp = self.env.tmp
            if not Path(f"{current_tmp}.gdx").exists():
                self.env.drop_local("tmp")

        # Mirrors GAMS's `$IF NOT ERRORFREE $GOTO FINISH` right after `$GDXIN %TMP%`:
        # a missing bprice save file is tolerated (e.g. a cold-start run with no
        # prior elastic-demand solve), so we skip the load instead of letting
        # GAMSPy's addGamsCode raise a hard compile error. In addition to the
        # cwd-relative path GAMS itself would check, we also check the instance's
        # data directory, since fixture copies of com_bprice.gdx are distributed
        # there (Nextcloud) rather than left lying around in the working directory.
        cwd_gdx = Path(f"{self.env.tmp}.gdx")
        data_dir_gdx = Path(self.tc.config.data_dir, f"{self.env.tmp}.gdx")
        if cwd_gdx.exists():
            gdxin_path = self.env.tmp
        elif data_dir_gdx.exists():
            gdxin_path = str(data_dir_gdx)
        else:
            logger.warning(
                "%s.gdx not found (checked %s and %s); skipping SOL_BPRICE load, "
                "same as vanilla GAMS's $IF NOT ERRORFREE $GOTO FINISH fallback.",
                self.env.tmp,
                cwd_gdx,
                data_dir_gdx,
            )
            return

        # TODO: skipped 1x $IF NOT ERRORFREE $GOTO FINISH after $LOAD sol_bprice. corect?
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
$GDXIN {gdxin_path}
$LOAD sol_bprice
""",
        )

        # $IFI %MACRO%==MLF $SET MX SET MACRO 'Yes'
        # mx_GP carries the deferred switch reassignment as flat (name, value) pairs,
        # e.g. ("macro", "Yes", "timesed", "YES"), replayed by maindrv_mod.py.
        mx_gp_pairs: tuple[str, ...] = ()
        if self.env.macro.upper() == "MLF":
            self.env.set_scoped("mx", "SET MACRO 'Yes'")
            mx_gp_pairs = ("macro", "Yes")

        self.env.set_global("mx", f"{self.env.mx} SET TIMESED 'YES'")
        self.env.set_global("mx_GP", (*mx_gp_pairs, "timesed", "YES"))

        if self.tc.defined("DAM_ELAST"):
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
$LOAD DAM_COEF
$LOAD DAM_TVOC
""",
            )

        if self.env.macro.upper() == "MLF":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
$LOAD SOL_ACFR
""",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
$GDXIN
""",
        )

        self.tc.enqueue(self.exec1)

        # $IF NOT DEFINED DAM_ELAST $GOTO FINISH
        if self.tc.defined("DAM_ELAST"):
            self.tc.enqueue(self.exec2)

            # $IF DEFINED DAM_COST ...
            if self.tc.defined("DAM_COST"):
                self.tc.enqueue(self.exec3)

            self.tc.enqueue(self.exec4)

        # TODO: $clearerror, see https://git.gams.com/consulting/times-2-gamspy/-/issues/253#note_303881
        if self.env.macro.upper() != "MLF":
            pass

    def exec1(self: ReadbpriceMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION DEM < COM_PROJ;
DEM(R,C)$COM_TMAP(R,'DEM',C) = YES;

* Fill in missing tail milestoneyrs to reduce abruption
OPTION FORWARD < SOL_BPRICE;
FIL(T) = PROD(FORWARD(TT),ORD(TT)<ORD(T));
LOOP(FIL(TT(T+1)), COM_BPRICE(R,TT,C,S,CUR) $= SOL_BPRICE(R,T,C,S,CUR));
COM_BPRICE(R,T,C,S,CUR)$DEM(R,C) $= SOL_BPRICE(R,T,C,S,CUR);
OPTION CLEAR=DEM;
""",
        )

    def exec2(self: ReadbpriceMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Apply elastic supply curves if requested
LOOP((R,T,C)$DAM_TVOC(R,T,C,'N'),TRACKC(R,C) = YES);
TRACKC(R,C)$DAM_BQTY(R,C) = NO;
TRACKC(R,C)$(NOT DAM_ELAST(R,C,'N')) = NO;
""",
        )

    def exec3(self: ReadbpriceMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
LOOP((R,T,C,CUR)$DAM_COST(R,T,C,CUR), TRACKC(R,C) = NO);
""",
        )

    def exec4(self: ReadbpriceMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
DAM_COST(R,T,C,CUR)$TRACKC(R,C) = 1$(DAM_TVOC(R,T,C,'N')>0)+EPS;
DAM_TQTY(R,T,C)$TRACKC(R,C) $= DAM_TVOC(R,T,C,'N');
OPTION CLEAR=DAM_TVOC,CLEAR=TRACKC;
""",
        )
