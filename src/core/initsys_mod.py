# initsys_mod.py
# *==========================================================================================*
# * INITSYS.MOD has all the fixed system declarations for ETSAP TIMES                        *
# *==========================================================================================*
# *  Copyright (C) 2000-2025 IEA Energy Technology Systems Analysis Programme (IEA-ETSAP).
# *  This software (ETSAP TIMES) is open source: you can redistribute it and/or modify it
# *  under the terms of the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *  For further information, visit: <https://www.gnu.org/licenses/gpl-3.0.html>.
# *
# *  This software is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# *  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# *===========================================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Set, UniverseAlias

from core.utils import expand_set

from . import globals_def, maplists_def, units_def
from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitsysMod(GamsClass):
    """Translation unit for initsys.mod."""

    # Instance attributes
    module_name: str = "initsys_mod"
    gams_source: str = "inisys.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase = "init"
        # Easy access gamspy.Container
        m = self.tc.container

        self.env.set_scoped("tmp", "restart")
        # TODO: $ IF %SYSTEM.LICENSELEVEL%==2 $SET TMP Runtime
        # TODO: $ IF SET RunTimes $TITLE %SYSTEM.TITLE% -- %TMP% (v%RunTimes%)

        # $ PHANTOM EMPTY
        Set(m, "PHANTOM", records=["EMPTY"])

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
$ PHANTOM EMPTY
$ ONEMPTY
$ ONMULTI
""",
        )

        self.tc.item = UniverseAlias(m, name="ITEM")

        # $IF NOT SET BOTIME $SETGLOBAL BOTIME 1850
        self.env.set_if_not_exists("botime", "1850", "global")

        # $IF NOT SET EOTIME $SETGLOBAL EOTIME 2200
        self.env.set_if_not_exists("eotime", "2200", "global")

        # $IF NOT %SHELL%==ANSWER
        # $IF SET MAXSOW SET ITEM /BOH, 1*%EOTIME%/;
        if self.env.is_set("shell"):
            if not self.env.shell == "ANSWER":
                if self.env.is_set("maxsow"):
                    # Expand the universe alias item
                    item_records = ["BOH"] + [
                        str(i) for i in range(1, self.env.eotime + 1)
                    ]
                    self.add_records_to_universe_item(records=item_records)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=rf"""
  SET BOHYEAR                        'BOH + years'                  / BOH, {self.env.botime}*{self.env.eotime} /
  SET ALLYEAR                        'All Years'                    / {self.env.botime}*{self.env.eotime} /
  PARAMETER YEARVAL(ALLYEAR)         'Value of each year';
  """,
        )

        # catch botime now and store with queue
        botime = self.env.botime
        self.tc.enqueue(self.assign_yearval, botime=botime)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
  SET EOHYEAR                        "'BOH/EOH' + years"            / SET.BOHYEAR, EOH /
  Parameter BEOH(*)                  'BOH / EOH offset'             / BOH +1, EOH -1 /;
  SET PERIODYR(ALLYEAR,ALLYEAR)      'All years in each period'     //;
""",
        )

        # SET ALL_TS                         'The universe for time-slices' / ANNUAL /
        expand_set(m["ALL_TS"], ["ANNUAL"])

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
  SET ANNUAL(ALL_TS)                 'Annual identifier'            / ANNUAL /
  SET TSLVL                          'Timeslice levels'             / ANNUAL, SEASON, WEEKLY, DAYNITE /;
  PARAMETER TSLVLNUM(TSLVL)          'Timeslice level values'
          / ANNUAL  1
            SEASON  2
            WEEKLY  3
            DAYNITE 4 /;
*  SET SEASON(REG,ALL_TS)             'Seasons'                     //;
*  SET WEEK(REG,ALL_TS)               'Week Sub-divisions '         //;
*  SET DAYNITE(REG,ALL_TS)            'Daily Sub-divisions'         //;
""",
        )
        self.tc.allyear = m["ALLYEAR"]
        self.tc.year = Alias(m, name="YEAR", alias_with=self.tc.allyear)
        self.tc.ll = Alias(m, name="LL", alias_with=self.tc.allyear)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

* topology
  SET IMPEXP       'Imports/Exports'                                / IMP, EXP /
  SET IMP          'Imports'                                        / IMP /
  SET XPT          'Exports'                                        / EXP /
  SET IN_OUT       'Input/Output'                                   / IN, OUT /
""",
        )

        self.tc.impexp = m["IMPEXP"]
        self.tc.in_out = m["IN_OUT"]
        self.tc.ie = Alias(m, name="IE", alias_with=self.tc.impexp)
        self.tc.io = Alias(m, name="IO", alias_with=self.tc.in_out)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

* limits
  SET LIM           'Limit Types'                                   / LO, FX, UP, N /
  SET BND_TYPE(LIM) 'Bound Types'                                   / LO, FX, UP /
""",
        )

        self.tc.lim = m["LIM"]
        self.tc.bnd_type = m["BND_TYPE"]
        self.tc.l = Alias(m, name="L", alias_with=self.tc.lim)
        self.tc.lim_type = Alias(m, name="LIM_TYPE", alias_with=self.tc.lim)
        self.tc.bd = Alias(m, name="BD", alias_with=self.tc.bnd_type)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

* Start-up types
  SET UPT          'Start-up types'                                 / COLD, WARM, HOT /
""",
        )

        # * Numbered sets
        # SET ALLYEAR                                                       / 0 /;
        expand_set(symbol=self.tc.allyear, elements=[0])

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
  SET AGE          'Age for SHAPEing'                               / 1*200 /
  SET J            'Supply/demand steps 1*COM_STEP and SHAPE/MULTI' / 1*999 /
""",
        )

        self.tc.j = m["J"]
        self.tc.jj = Alias(m, name="JJ", alias_with=self.tc.j)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

* Master Set declarations
  SET ALL_REG(*)   'External + Internal Regions'                    //
  SET REG(ALL_REG) 'Region'                                         //
""",
        )

        self.tc.all_reg = m["ALL_REG"]
        self.tc.reg = m["REG"]
        self.tc.all_r = Alias(m, name="ALL_R", alias_with=self.tc.all_reg)
        self.tc.r = Alias(m, name="R", alias_with=self.tc.reg)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

  SET COM_GRP      'Commodities & Groups'
    / DEM          'Demands',
      NRG          'Energy',
      MAT          'Material',
      ENV          'Environmental Indicators',
      FIN          'Financial' /;
""",
        )

        self.tc.com_grp = m["COM_GRP"]
        self.tc.cg = Alias(m, name="CG", alias_with=self.tc.com_grp)
        self.tc.cg1 = Alias(m, name="CG1", alias_with=self.tc.com_grp)
        self.tc.cg2 = Alias(m, name="CG2", alias_with=self.tc.com_grp)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

  SET COM(COM_GRP) 'Commodities'                                    //
""",
        )

        self.tc.com = m["COM"]
        self.tc.c = Alias(m, name="C", alias_with=self.tc.com)
        self.tc.com1 = Alias(m, name="COM1", alias_with=self.tc.com)
        self.tc.com2 = Alias(m, name="COM2", alias_with=self.tc.com)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

  SET PRC(*)       'Processes'                                      //
""",
        )

        self.tc.prc = m["PRC"]
        self.tc.p = Alias(m, name="P", alias_with=self.tc.prc)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
  SET CUR(*)       'Currencies = c$'                                //
""",
        )

        self.tc.cur = m["CUR"]
        self.tc.curr = Alias(m, name="CURR", alias_with=self.tc.cur)

        # Stochastics
        # $ SETGLOBAL MAXSOW 96
        self.env.set_global("maxsow", "96")
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=rf"""

  SET ALLSOW       'State-of-the-World'                             / 1*{self.env.maxsow} /
  SET SOW(ALLSOW)  'State-of-the-World'                             //
""",
        )

        self.tc.sow = m["SOW"]
        self.tc.w = Alias(m, name="W", alias_with=self.tc.sow)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""

*-------------------------------------------------------------------------------
* UC facility - fixed sets and controls for user-constraints
*-------------------------------------------------------------------------------
  SET SIDE                 'LHS and RHS of an equation'        / LHS, RHS /
  PARAMETER UC_SIGN(SIDE)  'Sign of LHS and RHS expression'    / LHS 1, RHS -1 /;
  SETS COM_VAR / NET, PRD /, COV_MAP / NET.COMNET, PRD.COMPRD /;

* List of parameters that can be used in user-constraints
  SET UC_NAME   'Allowed parameters in user-constraints'
    / COST, DELIV, TAX, SUB
      EFF, NET, N
      GROWTH, PERIOD, PERDISC, BUILDUP
      CUMSUM, CUM+, SYNC, YES
      CAPACT, CAPFLO, NEWFLO, ONLINE
      ANNUL, INVCOST, INVTAX, INVSUB
      FLO_COST, FLO_DELIV, FLO_SUB, FLO_TAX
      NCAP_COST, NCAP_ITAX, NCAP_ISUB
    /;

  SET UC_COST(UC_NAME) 'UC cost attributes'
    / COST, DELIV, TAX, SUB, ANNUL /;

  SET UC_MAPCOST(UC_COST,UC_NAME) 'Compatibility map for cost attributes'
    / COST.(FLO_COST,NCAP_COST)
      DELIV.FLO_DELIV
      ANNUL.(INVCOST,INVTAX,INVSUB)
      TAX.(FLO_TAX,NCAP_ITAX)
      SUB.(FLO_SUB,NCAP_ISUB) /;

  SET UC_ANNUL(UC_NAME) / INVCOST, INVTAX, INVSUB /;
  SET UC_DYNT(UC_NAME) / N, CUMSUM, CUM+, SYNC /;

  SET UC_NUMBER 'Determines way of handling REG,T and TS'
    / SEVERAL, SUCC, EACH, DYNAMIC /;

  SET UC_PERDS(UC_NAME) / PERIOD, NEWFLO /;
  SET UC_NEWFLO(UC_NAME) / NEWFLO /;

  SET UC_GRPTYPE 'Type of components within UC_GRP'
    / ACT, FLO, IRE, CAP, NCAP, COMNET, COMPRD, COMCON, UCN /;

  SET COSTAGG 'Types of cost aggregations'
    / INV, INVTAX, INVSUB, FOM, FOMTAX, FOMSUB, COMTAX, COMSUB, FLOTAX, FLOSUB,
      INVTAXSUB, INVALL, FOMTAXSUB, FOMALL, FIX, FIXTAX, FIXSUB, FIXTAXSUB, FIXALL,
      COMTAXSUB, FLOTAXSUB, ALLTAX, ALLSUB, ALLTAXSUB /;
""",
        )

        self.tc.costagg = m["COSTAGG"]
        self.tc.uc_cost = m["UC_COST"]
        self.tc.costcat = Alias(m, name="COSTCAT", alias_with=self.tc.costagg)
        self.tc.costype = Alias(m, name="COSTYPE", alias_with=self.tc.uc_cost)

        # *-------------------------------------------------------------------------------
        # * control sets
        # *  - expected in *.RUN file
        # *  - throw switch other way in *.RUN to change
        # *-------------------------------------------------------------------------------
        # * user should provide name in *.RUN
        self.env.set_scoped("model_name", "TIMES")
        self.env.set_scoped("run_name", "TEST")
        # * control of whether all 0 lines are dumped in *.PUT files; user provides 0 to NOT print lines with all 0s (or empty)
        self.tc.add_gams_code(
            module=self, phase=phase, code="SCALAR DUMP0 /1/, OPTFILEID /1/;"
        )

        # * user set to 'YES' to activate
        self.env.set_scoped("debug", "NO")
        self.env.set_scoped("dumpsol", "NO")
        self.env.set_scoped("solans", "NO")

        # * user set to 'NO' to not abort when error condition fails
        self.env.set_scoped("err_abort", "YES")
        # * user sets to 'WWW' to activate
        self.env.set_scoped("gams_cgi", "NO")
        # * user sets to 'NO' if only want to compile
        self.env.set_scoped("solve_now", "YES")

        # get list of default units
        self.include(units_def.Units(tc=self.tc, env=self.env))

        # get list of default mapping group lists
        self.include(maplists_def.Maplists(tc=self.tc, env=self.env))

        # # get default global scalars and parameters
        self.include(globals_def.Globals(tc=self.tc, env=self.env))

    def assign_yearval(self, botime):
        phase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=rf"""YEARVAL(ALLYEAR) = {botime} + ORD(ALLYEAR)-1;""",
        )
