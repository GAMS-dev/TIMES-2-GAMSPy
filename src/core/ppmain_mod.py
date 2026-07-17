# ppmain_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PPMAIN.MOD oversees all the preprocessor activities
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *   - determination of B/E/D(t)
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Number, Parameter, Set

from core.base_class import GamsClass
from core.eqflomrk_mod import EqflomrkMod
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.filshape_gms import FilshapeGms
from core.main_ext_mod import include_extension
from core.pp_chp_ier import PpChpIer
from core.pp_chp_mod import PpChpMod
from core.pp_lvlbd_mod import PpLvlbdMod
from core.pp_lvlbr_mod import PpLvlbrMod
from core.pp_lvlfc_mod import PpLvlfcMod
from core.pp_lvlff_mod import PpLvlffMod
from core.pp_lvlfs_mod import PpLvlfsMod
from core.pp_lvlif_mod import PpLvlifMod
from core.pp_lvlpk_mod import PpLvlpkMod
from core.pp_lvlus_mod import PpLvlusConfig, PpLvlusMod
from core.pp_micro_mod import PpMicroMod
from core.pp_off_mod import pp_off
from core.pp_prelv_vda import PpPrelvVda
from core.pp_qafs_mod import PpQafsMod
from core.pp_qaput_mod import pp_qaput
from core.pp_reduce_red import PpReduceRed
from core.ppmain_tm import PpmainTm
from core.preppm_mod import PreppmMod
from core.prepxtra_mod import PrepxtraMod
from core.timslice_mod import TimsliceMod
from core.utils import callable_rts

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class PpmainMod(GamsClass):
    """Translation unit for ppmain.mod."""

    # Instance attributes
    module_name: str = "ppmain_mod"
    gams_source: str = "ppmain.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase: GamsPhase = "init"
        g = self.tc
        m = g.container

        r, t, p, s, c = g.r, g.t, g.p, g.s, g.c

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
* establish the QC error message log file
  FILE QLOG / QA_CHECK.LOG /; QLOG.LW=0;
""",
        )

        g.putout = Parameter(m, name="PUTOUT", records=0)
        g.putgrp = Parameter(m, name="PUTGRP", records=0)
        g.errlev = Parameter(m, name="ERRLEV", records=0)
        # * Additional Declarations in PPMAIN
        g.startoff = Parameter(m, name="STARTOFF", records=0)
        g.endoff = Parameter(m, name="ENDOFF", records=0)
        g.Matprc = Set(m, name="MATPRC", domain=[g.prcgrp], records=["PRV", "PRW"])
        g.NoRvp = Set(m, name="NO_RVP", domain=[r, t, p])
        g.IreDist = Set(m, name="IRE_DIST", domain=[r, p])
        g.RpSgs = Set(m, name="RP_SGS", domain=[r, p])
        g.RpSts = Set(m, name="RP_STS", domain=[r, p])
        g.RpStl = Set(m, name="RP_STL", domain=[r, p, g.tsl, g.lA])
        g.RpsStg = Set(m, name="RPS_STG", domain=[r, p, s])
        g.RpcStg = Set(m, name="RPC_STG", domain=[r, p, c])
        g.RpcStgn = Set(m, name="RPC_STGN", domain=[r, p, c, g.io])
        g.UcDt = Set(m, name="UC_DT", domain=[g.allr, g.ucn])
        g.Rcs = Set(m, name="RCS", domain=[g.Reg, g.Com, g.ts])
        g.RcRc = Set(m, name="RC_RC", domain=[g.allreg, g.Com, g.allreg, g.Com])

        self.env.set_scoped("tmp", ".")
        if self.env.datagdx == "YES" and self.env.g2x6 == "YES":
            self.env.set_scoped("tmp", "; Input Data have been filtered via GDX")

        # TODO: $ IF WARNINGS $BATINCLUDE pp_qaput.%1 PUTOUT 0 * 'GAMS Warnings Detected%TMP%'

        self.tc.enqueue(self.phase_one, pgprim=self.env.pgprim)

        # *-----------------------------------------------------------------------------
        # * spread NCAP_PASTI and determine PASTYEAR
        # *-----------------------------------------------------------------------------
        g.Phyr = Set(m, name="PHYR", domain=[g.allyear])
        g.pastsum = Parameter(m, name="PASTSUM", domain=[g.r, g.allyear, g.p])

        self.tc.enqueue(self.phase_two)
        self.add_records_to_universe_item(records=["PASTI"])
        self.tc.enqueue(self.phase_two_two)

        if self.env.obj.upper() == "MOD":
            self.tc.enqueue(self.set_mt_zero)
        self.tc.enqueue(self.phase_three, condition=self.env.oblong.upper() == "YES")

        # Initialize MINYR already here (was in COEF_OBJ.mod)
        self.tc.add_gams_code(module=self, phase=phase, code="SCALAR MINYR;")

        self.tc.enqueue(self.phase_four)

        # Inter/Extrapolate G_OFFTHD if specified
        if self.tc.defined("G_OFFTHD"):
            self.include(
                FilparamGms(
                    tc=self.tc,
                    env=self.env,
                    config=FilparamGmsConfig(
                        src=g.g_offthd,
                        arg2=(),
                        tail1=(),
                        arg4=("", "", "", "", "", ""),
                        arg5=g.year,
                        arg6=g.t,
                        arg9=5,
                    ),
                )
            )

        self.tc.enqueue(self.g_offthd_to_zero)

        # *-----------------------------------------------------------------------------
        # * complete timeslice declarations
        # *-----------------------------------------------------------------------------
        # * Include preprocessing of timeslice attributes
        self.include(TimsliceMod(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_five, botime=self.env.botime)

        self.tc.enqueue(self.check_ncap_pasti, rl=self.env.rl)

        # Set the RTP_OFF for all remaining PRC_NOFF ranges
        self.tc.enqueue(self.set_rtp_off)

        # *-----------------------------------------------
        # * interpolation/extrapolation
        # *-----------------------------------------------
        # * Call interpolation subsystem
        self.include(PreppmMod(tc=self.tc, env=self.env))

        if self.env.intext_only.upper() == "YES":
            return

        # initialize timestep control
        # moved symbol declarion to ppmain_mod.py
        g.Subt.setRecords(records=g.t.toList())

        self.tc.enqueue(
            self.phase_six, rl=self.env.rl, pl=self.env.pl, ctst=self.env.ctst
        )

        if g.PrcRcap is None:
            g.PrcRcap = Set(m, name="PRC_RCAP")
        self.tc.register_assignment(g.PrcRcap)
        if g.prc_refit is None:
            g.prc_refit = Parameter(m, name="PRC_REFIT")
        self.tc.register_assignment(g.prc_refit)

        self.tc.enqueue(self.phase_seven, ctst=self.env.ctst)

        # override the lead delay on capacity if M2T, if viable period
        if self.env.validate == "YES":
            self.tc.enqueue(self.activate_rtp_cptyr)

        self.tc.register_assignment(g.rcap_bnd)
        self.tc.enqueue(
            self.phase_eight,
            pl=self.env.pl,
            rl=self.env.rl,
            cl=self.env.cl,
            pgprim=self.env.pgprim,
            prc_simv_defined=self.tc.defined("PRC_SIMV"),
        )

        # Extensions after establishing RPCS_VAR and PRC_CAPACT but before levelising
        extensions = {"VDA": PpPrelvVda}
        requested_exts = set(self.env.extend.split())
        include_extension(
            module=self,
            extensions=extensions,
            requested_exts=requested_exts,
            source="ppmain",
        )

        # Make various QA checks for FLO_SHAR
        self.include(PpQafsMod(tc=self.tc, env=self.env))

        # *-----------------------------------------------------------------------------
        # * setup and apply (some) SHAPE/MULTI
        # *-----------------------------------------------------------------------------
        self.tc.add_gams_code(module=self, phase=phase, code="SCALAR MAXLIFE;")

        self.tc.enqueue(self.phase_nine)

        # Call the SHAPE inter-/extrapolation routine

        self.include(FilshapeGms(tc=self.tc, env=self.env, arg1=g.startoff))

        self.tc.enqueue(self.adjust_shape)

        # *GG* note that multi will take additional parameter NO/YES to do 2nd assignment or not
        # * Call the inter-/extrapolation routine for MULTI
        self.include(
            FilparamGms(
                tc=self.tc,
                env=self.env,
                config=FilparamGmsConfig(
                    src=g.multi,
                    arg2=(g.j,),
                    tail1=(),
                    arg4=("", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Eohyears,
                    arg7=Number(0),  # "NO$"
                ),
            )
        )

        self.tc.enqueue(self.establish_basic_defaults_for_non_ts_attribute)

        self.tc.add_gams_code(
            module=self, phase=phase, code="SET UC_CAPFLO(UC_N,SIDE,R,P,C);"
        )

        self.tc.enqueue(self.phase_eleven)

        # *-----------------------------------------------------------------------------
        # * do the basic initializations that are TS-based, including aggregate/inherit
        # *-----------------------------------------------------------------------------
        # * commodity related attributes
        # *-----------------------------------------------------------------------------
        # * infastructure efficiency
        # * set seasonal fraction for commodity if necessary, G_YRFR('ANNUAL') already = 1
        # * difference between the average calculated demand and the actual shape of the peak
        # * commodity based costs, subsidies and taxes
        # * elastic demands base price, quantity, elasticity and steps

        self.tc.enqueue(self.activate_rtc_net)
        # fmt: off
        batincludes = [
            ("COM_IE",     "C", "COM_TS", '',               ",'0','0','0','0'",     "ALL_TS", "T",        "RTC(R,T,C)"),
            ("COM_FR",     "C", "COM_TS", '',               ",'0','0','0','0'",     "ALL_TS", "T",        "RTC_NET(R,T,C)", "1"),
            ("COM_PKFLX",  "C", "COM_TS", '',               ",'0','0','0','0'",     "ALL_TS", "T",        "YES"),
            ("OBJ_COMNT",  "C", "COM_TS", ',COSTYPE,CUR',   ",'0','0'",             "ALL_TS", "DATAYEAR", "RC(R,C)"),
            ("OBJ_COMPD",  "C", "COM_TS", ',COSTYPE,CUR',   ",'0','0'",             "ALL_TS", "DATAYEAR", "RC(R,C)"),
            ("COM_ELAST",  "C", "COM_TS", ',BD',            ",'0','0','0'",         "ALL_TS", "DATAYEAR", "RC(R,C)"),
            ("COM_BPRICE", "C", "COM_TS", ',CUR',           ",'0','0','0'",         "ALL_TS", "DATAYEAR", "RC(R,C)"),
            ("COM_BQTY",   "C", "COM_TS", '',               ",'0','0','0','0','0'", "ALL_TS", '',         "RC(R,C)",       "1"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                PpLvlfcMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8] if len(arg) > 8 else "",
                    arg10=arg[9] if len(arg) > 9 else "",
                    arg11=arg[10] if len(arg) > 10 else "",
                    arg12=arg[11] if len(arg) > 11 else "",
                )
            )

        self.tc.enqueue(self.phase_twelve, rl=self.env.rl, cl=self.env.cl)

        # Split of timeslice based upon level and commodity profile
        if "RTCS_FRMX" not in m.listParameters():
            g.rtcs_fr = Parameter(
                self.tc.container, name="RTCS_FR", domain=[g.r, g.t, g.c, g.s, g.s]
            )

        rts = callable_rts(self.env)
        self.tc.enqueue(self.phase_thirteen, mx=self.env.mx, rts=rts)

        # Preprocess TIMES-Micro
        if self.env.timesed == "YES":
            self.include(PpMicroMod(tc=self.tc, env=self.env, arg1="PRE"))

        self.tc.enqueue(self.phase_fourteen)

        self.include(
            PpLvlbrMod(
                tc=self.tc,
                env=self.env,
                arg1="NCAP_AF",
                arg2="",
                arg3="PRC_TS",
                arg4=",'0','0'",
                arg5="0",
                arg6="1",
            )
        )

        self.tc.enqueue(self.phase_fiveteen)

        self.include(PpLvlpkMod(tc=self.tc, env=self.env, arg1=Number(1)))

        # *-----------------------------------------------------------------------------
        # * flow related attributes
        # *-----------------------------------------------------------------------------
        # * costs, subsidy, taxes, & flow rates
        # fmt: off
        batincludes = [
            ("FLO_COST",  'P,C', "RPCS_VAR", ',CUR', ",'0','0'", "ALL_TS", "DATAYEAR", "RPC(R,P,C)", '', '', "N"),
            ("FLO_DELIV", 'P,C', "RPCS_VAR", ',CUR', ",'0','0'", "ALL_TS", "DATAYEAR", "RPC(R,P,C)", '', '', "N"),
            ("FLO_SUB",   'P,C', "RPCS_VAR", ',CUR', ",'0','0'", "ALL_TS", "DATAYEAR", "RPC(R,P,C)", '', '', "N"),
            ("FLO_TAX",   'P,C', "RPCS_VAR", ',CUR', ",'0','0'", "ALL_TS", "DATAYEAR", "RPC(R,P,C)", '', '', "N"),
            ("FLO_PKCOI", 'P,C', "RPCS_VAR", '', ",'0','0','0'", "ALL_TS", "T", "RTP(R,T,P)"),
            ("FLO_BDLVL", 'P',   "PRC_TS",   ',BD', ",'0','0'",  "ALL_TS", "T", "RTP(R,T,P)", "0", ',CG', "1", "$(C(CG)->ACTCG(CG))"),
            ("FLO_BDLVL", 'P,C', "RPCS_VAR", ',BD', ",'0','0'",  "ALL_TS", "T", "RTP(R,T,P)", "0", '',    "1", "$RPC(R,P,C)"),
            ("ACT_FLO",   'P',   "RPS_S1",   '', ",'0','0','0'", "ALL_TS", "V", "RTP(R,V,P)", "0", ',C',  "0", "$STOA(S)"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                PpLvlfcMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8] if len(arg) > 8 else "",
                    arg10=arg[9] if len(arg) > 9 else "",
                    arg11=arg[10] if len(arg) > 10 else "",
                    arg12=arg[11] if len(arg) > 11 else "",
                )
            )

        self.tc.enqueue(self.phase_sixteen)

        # derive the CHP flow control attributes
        if self.arg1.upper() == "IER":
            self.include(PpChpIer(tc=self.tc, env=self.env, arg1=self.arg1))
        elif self.arg1.upper() == "MOD":
            self.include(PpChpMod(tc=self.tc, env=self.env, arg1=self.arg1))
        else:
            raise FileNotFoundError("No matching pp_chp file found.")

        # *-----------------------------------------------------------------------------
        # * the actual flow control attributes
        # *-----------------------------------------------------------------------------
        # * FLO_ attributes

        # * handle FLO_FUNC and FLO_SUM aggregation/inheritance
        self.include(PpLvlffMod(tc=self.tc, env=self.env))
        self.include(PpLvlfsMod(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_seventeen)

        # handle FLO_SHAR aggregation/inheritance
        self.include(
            PpLvlbrMod(
                tc=self.tc,
                env=self.env,
                arg1="FLO_SHAR",
                arg2=",C,CG",
                arg3="RPCS_VAR",
                arg4="",
                arg5="1",
                arg6="0",
                arg7="C,",
            )
        )
        # preprocessing of FLO_MARK/PRC_MARK
        self.include(EqflomrkMod(tc=self.tc, env=self.env))

        self.tc.enqueue(self.deactivate_rpc_noflo)

        # inter-regional exchange related attributes
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                arg1="IRE_PRICE",
                arg2="P,C",
                arg3="RPCS_VAR",
                arg4=",ALL_REG,IE,CUR",
                arg5="",
                arg6="ALL_TS",
                arg7="DATAYEAR",
                arg8="RPC_IRE(R,P,C,IE)",
            )
        )
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                arg1="IRE_FLOSUM",
                arg2="P",
                arg3="PRC_TS",
                arg4=",IE,COM,IO",
                arg5="",
                arg6="ALL_TS",
                arg7="T",
                arg8="RTP(R,T,P)",
                arg9="0",
                arg10=",C",
            )
        )
        # this routine only handles IRE_FLO
        self.include(PpLvlifMod(tc=self.tc, env=self.env, arg1=self.arg1))

        self.tc.enqueue(
            self.phase_eightteen,
            micro=self.env.micro,
            macro=self.env.macro,
            rl=self.env.rl,
            pgprim=self.env.pgprim,
        )

        # process bounds to see if aggregation is necessary
        # fmt: off
        batincludes = [
            ("ACT_BND",    "P", '', '', '',          "PRC_TS", "RPS_PRCTS", "RTPS_BD", "EPS"),
            ("FLO_FR",     "P", "C,", '', ",''",     "RPCS_VAR", "RPCS_VAR", "UNCD7", "0"),
            ("COM_BNDNET", "C", '', '', ",'',''",    "COM_TS", "RCS_COMTS", "UNCD7"),
            ("COM_BNDPRD", "C", '', '', ",'',''",    "COM_TS", "RCS_COMTS", "UNCD7"),
            ("IRE_BND",    "C", '', 'ALL_R,IE,', '', "COM_TS", "RCS_COMTS", "UNCD7", "EPS"),

        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                PpLvlbdMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8] if len(arg) > 8 else "",
                )
            )

        self.tc.enqueue(self.phase_nineteen, pgprim=self.env.pgprim)

        dam_elast_defined = self.tc.defined("DAM_ELAST")
        obj_eq_lin = self.env.obj.upper() == "LIN"
        self.tc.enqueue(
            self.phase_twenty,
            dam_elast_defined=dam_elast_defined,
            obj_eq_lin=obj_eq_lin,
            pgprim=self.env.pgprim,
        )

        # Levelization of STG_LOSS and STG_SIFT
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                arg1="STG_LOSS",
                arg2="P",
                arg3="PRC_TS",
                arg4="",
                arg5=",'0','0','0','0'",
                arg6="S2",
                arg7="V",
                arg8="RTP(R,V,P)$(NOT RPS_STG(R,P,S)$TRACKP(R,P))",
            )
        )
        self.include(
            PpLvlfcMod(
                tc=self.tc,
                env=self.env,
                arg1="STG_SIFT",
                arg2="P,C",
                arg3="RPCS_VAR",
                arg4="",
                arg5=",'0','0','0'",
                arg6="ALL_TS",
                arg7="T",
                arg8="RTP(R,T,P)",
            )
        )

        self.tc.enqueue(self.convert_equilibrium_losses_to_standard_losses)

        # User constraints
        # Default values
        self.include(PrepxtraMod(tc=self.tc, env=self.env, arg1="UCINT"))

        self.tc.enqueue(self.phase_twentyone)

        # Assigning commodities and processes to UC group map sets
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
        SET UC_MAP_FLO(UC_N,SIDE,ALL_REG,PRC,COM) 'Assigning processes to UC_GRP';
        SET UC_MAP_IRE(UC_N,ALL_REG,PRC,COM,IE)   'Assigning processes to UC_GRP';
""",
        )

        self.tc.enqueue(self.phase_twentytwo)

        # ...Handle UC_FLO/IRE/ACT/COM leveling by aggregation/inheritance
        # fmt: off
        pp_lvlus_batincludes: list[PpLvlusConfig] = [
            PpLvlusConfig(uc_parameter=g.uc_act, arg2=(g.p,), arg3=g.PrcTs, arg4=('0', '0'), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl),
            PpLvlusConfig(uc_parameter=g.uc_flo, arg2=(g.p, g.c), arg3=g.RpcsVar, arg4=('0',), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl, arg9=g.prc_sgl[g.r,g.p], arg10=(g.c,)),
            PpLvlusConfig(uc_parameter=g.uc_ire, arg2=(g.p, g.c), arg3=g.PrcTs, arg4=(), arg5=(g.ie,), arg6=(), arg7=g.p, arg8=g.PrcTsl),
            PpLvlusConfig(uc_parameter=g.uc_com, arg2=(g.c,), arg3=g.ComTs, arg4=(), arg5=(g.ucgrptype,), arg6=(g.comvar,), arg7=g.c, arg8=g.ComTsl),
        ]
        # fmt: on
        for config in pp_lvlus_batincludes:
            self.include(PpLvlusMod(tc=self.tc, env=self.env, config=config))

        self.tc.enqueue(
            self.control_set_for_balance_production_equations,
            validate=self.env.validate,
        )

        # *----------------------------------------------------------------------------*
        # *GG* V07_1 BLENDing equation
        # *----------------------------------------------------------------------------*
        # *******************************************************************************
        # *GG* V07_2  Create any Combined & Control Sets Needed for BLENDing Execution
        # *******************************************************************************
        g.BleSpe = Set(m, name="BLE_SPE", domain=[g.r, g.Com, g.spe])
        g.BleTp = Set(m, name="BLE_TP", domain=[g.r, g.allyear, "*"])
        g.BleSpeopr = Set(m, name="BLE_SPEOPR", domain=[g.r, g.Com, g.spe, g.Opr])
        g.BleOpr = Set(m, name="BLE_OPR", domain=[g.r, g.Com, g.Com])
        g.BleInp = Set(m, name="BLE_INP", domain=[g.r, g.Com, g.Com])
        g.BleSpeinp = Set(m, name="BLE_SPEINP", domain=[g.r, g.Com, g.spe, g.Com])
        g.BleEnv = Set(m, name="BLE_ENV", domain=[g.r, g.Com, g.Com, g.Opr])
        g.ble_bal = Parameter(m, name="BLE_BAL", domain=[g.r, g.year, g.c, g.c])

        self.tc.enqueue(self.phase_twentythree)

        # Coefficients for BLENDing
        g.opr2 = Alias(m, name="OPR2", alias_with=g.Opr)

        self.tc.enqueue(self.phase_twentyfour)

        self.include(PpReduceRed(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_twentyfive)

        # *----------------------------------------------------------------
        # * MACRO
        # *----------------------------------------------------------------
        if self.env.macro == "YES":
            self.include(PpmainTm(tc=self.tc, env=self.env))

        self.tc.enqueue(self.phase_twenty_six)

    def control_set_for_balance_production_equations(
        self: PpmainMod, validate: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Control set for balance/production equations based on TS-resolution and RHS
*-----------------------------------------------------------------------------
  RCS_COMBAL(RTCS_VARC(R,T,C,S),LIM)$(COM_LIM(R,C,LIM) * (NOT RHS_COMBAL(R,T,C,S))) = YES;
  RCS_COMBAL(RHS_COMBAL,'FX') = YES;
{"RHS_COMPRD(RTCS_VARC) = YES;" if validate == "YES" else ""}
  RCS_COMPRD(RHS_COMPRD,'FX') = YES;
""",
        )

    def convert_equilibrium_losses_to_standard_losses(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Convert equilibrium losses into standard losses for IPS, and adjust all losses by year fractions
  STG_LOSS(RTP(R,V,P),S(TSL))$((ABS(STG_LOSS(RTP,S)*2-1)>=1)$PRC_MAP(R,'STK',P)) = 1-EXP(-ABS(STG_LOSS(RTP,S)));
  STG_LOSS(RTP(R,V,P),S)$(STOA(S)$STG_LOSS(RTP,S)) = LOG(EXP(STG_LOSS(RTP,S)*G_YRFR(R,S)/RS_STGPRD(R,S)));
  OPTION CLEAR=TRACKP,CLEAR=TRACKPC;
""",
        )

    def deactivate_rpc_noflo(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
RPC_NOFLO(RMKC(RPC)) = NO;
*-----------------------------------------------------------------------------
* inter-regional exchange related attributes
*-----------------------------------------------------------------------------
PUTGRP = 0;
""",
        )

    def activate_rtc_net(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="RTC_NET(RTC(R,T,C))$(NOT COM_TSL(R,C,'ANNUAL')) = YES;",
        )

    def adjust_shape(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    SHAPE('1',AGE)$(ORD(AGE) LE STARTOFF) = 1.;
    SHAPE(J,AGE)$((SHAPE(J,AGE) EQ 0)$SHAPE(J,AGE)) = 0;
""",
        )

    def activate_rtp_cptyr(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self, phase="run", code=r"RTP_CPTYR(R,T,T,P)$RTP(R,T,P) = YES;"
        )

    def phase_one(self: PpmainMod, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Establish set of main currencies by region (for which discount rate provided)
  LOOP((R,LL(BOHYEAR),CUR)$G_DRATE(R,LL,CUR), RDCUR(R,CUR) = YES);
*-----------------------------------------------------------------------------
* establish initial primary looping control sets indicating what region/process/commodities
*-----------------------------------------------------------------------------
* process/commodities in each region, including inter-regional exchanges
   PRC_ACTUNT(R,P,'{pgprim}',UNITS_ACT) = NO;
   OPTION RPC_AIRE <  TOP_IRE; RPC_IRE(RPC_AIRE,'IMP') = YES;
   OPTION RPC_AIRE <= TOP_IRE; RPC_IRE(RPC_AIRE,'EXP') = YES;
   OPTION CLEAR=RPC_AIRE, PRC_ACT < PRC_ACTUNT;
   RP_IRE(ALL_R,P)$SUM(RPC_IRE(ALL_R,P,C,IE),1) = YES;
   TOP(RP_IRE(R,P),C,'IN')$RPC_IRE(R,P,C,'EXP') = NO;
   TOP(RP_IRE(R,P),C,'OUT')$RPC_IRE(R,P,C,'IMP') = NO;
   TOP(RPG_RED(PRC_ACT(R,P),C,IO))$(COM_TMAP(R,'ENV',C)+RP_IRE(R,P)) = YES;
* process/commodities in each region
   RPC(R,P,C)$(SUM(TOP(R,P,C,IO),1) + SUM(RPC_IRE(R,P,C,IE),1)) = YES;
   RC(R,C)$SUM(RPC(R,P,C),1) = YES;
   RP(R,P)$SUM(RPC(R,P,C),1) = YES;
   RP_FLO(RP)$(NOT RP_IRE(RP)) = YES;

* establish PCG, checking for missing ones
   OPTION RP_PG < PRC_ACTUNT, CLEAR=RPG_RED, CLEAR=PRC_ACT;
   PRC_ACT(RP)$(NOT SUM(RP_PG(RP,CG),1))=YES;
   IF(CARD(PRC_ACT),
      TRACKPC(PRC_ACT(R,P),C)$((NOT COM_TMAP(R,'ENV',C)+COM_TMAP(R,'FIN',C))$TOP(R,P,C,'OUT'))=YES;
      PRC_ACT(RP)$(SUM(TRACKPC(RP,C),1) NE 1)=NO; RP_PG(TRACKPC(PRC_ACT,C))=YES;
      OPTION CLEAR=PRC_ACT,CLEAR=TRACKPC);
* add groupings by type
   COM_GMAP(COM_TMAP) = YES;

*-----------------------------------------------------------------------------
* Establish missing sets for storage processes
*  - assumption: stored commodities should be members of the PG
*-----------------------------------------------------------------------------
* Prohibit special storage commodities
 TRACKC(R,C)$COM_LIM(R,C,'N') = YES;
 TRACKC(R,'{pgprim}') = YES;

* Defaults for stored commodity
 RP_STS(R,P)$PRC_MAP(R,'STS',P)=YES;
 TRACKP(R,P)$(PRC_MAP(R,'STG',P)+PRC_MAP(R,'STK',P)+RP_STS(R,P)) = YES;
 TRACKP(R,P)$SUM(PRC_STGTSS(R,P,C),1) = NO;
 TRACKP(R,P)$SUM(PRC_NSTTS(R,P,S),1) = NO;
 TRACKPC(TRACKP(R,P),C)$SUM((TOP(R,P,C,IO),RP_PG(R,P,CG))$COM_GMAP(R,CG,C),1) = YES;
 TRACKPC(TRACKP(R,P),C)$SUM(RP_PG(R,P,C)$(NOT TRACKC(R,C)),1) = YES;
* Auto-generate missing charge/discharge flow
 RPC_STGN(TOP(TRACKP(R,P),C,IO))$SUM((COM_GMAP(R,COM_TYPE(CG),C),TRACKPC(R,P,COM))$COM_GMAP(R,CG,COM),1)=YES;
 OPTION CG_GRP < FLO_FUNC; RPC_STGN(RP,C,IO)$SUM(RPC_STGN(TRACKPC(RP,COM),IO),1)=NO;
 LOOP(CG_GRP(TRACKP(RP),C,COM),IF(TRACKPC(RP,C),RPC_STGN(RP,COM,IO)=NO ELSEIF TRACKPC(RP,COM),RPC_STGN(RP,C,IO)=NO));
 TRACKPC(RPC) $= SUM(RPC_STGN(RPC,IO),1);

* day-night storage
 LOOP(PRC_NSTTS(R,P,S),
    PRC_MAP(R,'STG',P) = YES;
    PRC_MAP(R,'NST',P) = YES;
    PRC_MAP(R,'STK',P) = NO;
 );
* inter-period storage
 PRC_STGIPS(TRACKPC(R,P,C))$PRC_MAP(R,'STK',P) = YES;
 LOOP(PRC_STGIPS(R,P,C),
    PRC_MAP(R,'STG',P) = YES;
    PRC_MAP(R,'STK',P) = YES;
    PRC_MAP(R,'NST',P) = NO;
    IF(NOT SUM(TOP(R,P,C,IO),1),TOP(R,P,C,IO)=YES);
    IF(NOT RP_STS(R,P),PRC_TSL(R,P,TSLVL) = SAMEAS(TSLVL,'ANNUAL'));
 );
* time-slice storage
 PRC_STGTSS(TRACKPC(R,P,C))$(NOT PRC_MAP(R,'STK',P)) = YES;
 LOOP(PRC_STGTSS(R,P,C),
    PRC_MAP(R,'STG',P) = YES;
    PRC_MAP(R,'STS',P) = YES;
    PRC_MAP(R,'NST',P) = NO;
    PRC_MAP(R,'STK',P) = NO;
    IF(NOT SUM(TOP(R,P,C,IO),1),TOP(R,P,C,IO)=YES);
 );

 OPTION CLEAR=TRACKC,CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=CG_GRP,CLEAR=RPC_STGN;
* If storage is input- or output-based, define it such
 RPC_STGN(PRC_STGTSS(R,P,C),IO)$(NOT SUM(TOP(R,P,COM,IO)$PRC_STGTSS(R,P,COM),1)) = YES;
 RPC_STGN(PRC_STGIPS(R,P,C),IO)$(NOT SUM(TOP(R,P,COM,IO)$PRC_STGIPS(R,P,COM),1)) = YES;
 TOP(RPC_STGN) = YES;
""",
        )

    def phase_two(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    OPTION PRC_CAP < NCAP_PASTY;
    LOOP((PRC_CAP(RP(R,P)),PASTYEAR(LL))$(NCAP_PASTY(R,PASTYEAR,P) > 1),
         F = NCAP_PASTY(R,LL,P); MY_F = NCAP_PASTI(R,LL,P) / F;
* for each year within spread build running sum of distributed PASTIs
         FOR(Z = F-1 DOWNTO 0, PASTSUM(R,ALLYEAR(LL-Z),P) = PASTSUM(R,ALLYEAR,P) + MY_F);
* since spread this guy, clear original value
         NCAP_PASTI(R,LL,P) = 0);
* add any spread past investments to any provided originally (and not spread)
    NCAP_PASTI(R,LL,P)$PASTSUM(R,LL,P) = NCAP_PASTI(R,LL,P) + PASTSUM(R,LL,P);
* extend the list of past years
    OPTION PASTYEAR < NCAP_PASTI;
""",
        )

    def phase_two_two(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    INT_DEFAULT('PASTI')$PYR('0')=1; PYR('0')=NO;
    OPTION CLEAR=PRC_CAP, CLEAR=PASTSUM;
*-----------------------------------------------------------------------------
* determination of YEAR subsets and period B/E/D
*-----------------------------------------------------------------------------

* 98/02/23 middle year of period M(T) from *.dd to ppmain.mod
* [UR]: duration of period moved from *.dd to ppmain.mod
    D(MILESTONYR)=E(MILESTONYR)-B(MILESTONYR)+1;
    M(MILESTONYR)=FLOOR(B(MILESTONYR)+(D(MILESTONYR)-1)/2);
""",
        )

    def set_mt_zero(self: PpmainMod) -> None:
        self.tc.add_gams_code(module=self, phase="run", code="M(T) = 0;")

    def g_offthd_to_zero(self: PpmainMod) -> None:
        self.tc.add_gams_code(module=self, phase="run", code="G_OFFTHD('0') = 0;")

    def phase_three(self: PpmainMod, condition: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
    IF(ALTOBJ=1,ALTOBJ=1$SUM(T,M(T) NE YEARVAL(T)));

* establish 1st/last run year
    MIYR_1(T)$(ORD(T) = 1) = YES;
    IF(ALTOBJ,
* If alternate objective, set B and E, D and M:
       E(T(TT-1)) = FLOOR((YEARVAL(T)+YEARVAL(TT))/2); B(T(TT+1)) = E(TT)+1;
       B(MIYR_1(T))$(ABS(B(T)-(YEARVAL(T)-5)) GT 5) = YEARVAL(T);
       E(T)$((ABS(E(T)-(YEARVAL(T)+15)) GT 15)$(ORD(T)=CARD(T))) = 2*YEARVAL(T)-B(T)+1-1$MOD(YEARVAL(T)-B(T)+1,5);
       D(T)=E(T)-B(T)+1; M(T) = YEARVAL(T));
*V0.5c 980904 - set 1st value to B not milestone itself
    MIYR_V1 = SMIN(MIYR_1, B(MIYR_1));
    MIYR_VL = SMAX(T$(ORD(T) = CARD(T)), E(T));
    {"IF(MIYR_V1+SUM(T,E(T)+1-B(T))-MIYR_VL NE 1,ABORT 'Inconsistent periods - cannot use OBLONG.');" if condition else ""}
    LOOP(MIYR_1(LL),PASTYEAR(LL-(YEARVAL(LL)-MIYR_V1+1)) = YES);
* Set LEADs and LAGs for periods
    LEAD(TT(T++1)) = MAX(M(TT)-M(T),M(TT)-B(TT)+1);
    LAGT(TT(T--1)) = MAX(M(T)-M(TT),E(TT)-M(TT)+1);
    IF(ALTOBJ,IPD(T) = LEAD(T)+MIN(E(T)-M(T),LEAD(T)-1)$MIYR_1(T);
    ELSE IPD(T) = D(T)); FPD(T) = D(T);
""",
        )

    def phase_four(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    MINYR = MIN(MIYR_V1-1,SMIN(T,M(T)-IPD(T))+1);
    PYR_V1 = MIN(SMIN(PASTYEAR,YEARVAL(PASTYEAR)),MINYR);
* Define MIYR_L
  LOOP(MIYR_1(ALLYEAR), Z=MIYR_VL-YEARVAL(ALLYEAR); MIYR_L(ALLYEAR+Z) = YES);

* establish the beginning/end/delta for each MILESTONYR
* introduce PASTMILE (PASTYEAR that are not MILESTONYR)
* set the past years to self
    PASTMILE(PASTYEAR)$((YEARVAL(PASTYEAR) LE MIYR_VL)$(NOT T(PASTYEAR))) = YES;
    M(PASTMILE) = YEARVAL(PASTMILE);
    B(PASTMILE) = M(PASTMILE);
    E(PASTMILE) = M(PASTMILE);
    D(PASTMILE) = 1;

*-----------------------------------------------------------------------------
* set EOHYEARS contains all years until MIYR_VL
    EOHYEARS(ALLYEAR)$((YEARVAL(ALLYEAR) >= MINYR) * (YEARVAL(ALLYEAR) <= MIYR_VL)) = YES;
* create list of all years in each period
    PERIODYR(T,EOHYEARS)$((YEARVAL(EOHYEARS) >= B(T)) * (YEARVAL(EOHYEARS) <= E(T))) = YES;
""",
        )

    def phase_five(self: PpmainMod, botime: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Migrate PASTIs defined on Milestonyr if requested
  IF(INT_DEFAULT('PASTI'), LOOP(PYR(T(LL))$(M(T)>B(T)), VNT(LL-1,T)=YES);
    LOOP(VNT(LL,T), B(LL)=M(T)-1; E(LL)=M(T); M(LL)=B(LL); D(LL)=2; PASTYEAR(T)=NO;
      PASTSUM(R,T,P)$NCAP_PASTI(R,T,P) = NCAP_PASTI(R,LL,P)+NCAP_PASTI(R,T,P)+1-1;
      COEF_RTP(R,LL,P)$PASTSUM(R,T,P)  = NCAP_PASTI(R,T,P) / PASTSUM(R,T,P);
      NCAP_PASTI(R,LL,P)$=PASTSUM(R,T,P); NCAP_PASTI(R,T,P)=0; OPTION CLEAR=PASTSUM;
    );
    VNT(PASTMILE,T)$PERIODYR(T,PASTMILE)=YES;
    OPTION PHYR<=VNT; PYR(PHYR)=YES; PASTMILE(PHYR)=YES);

*-----------------------------------------------------------------------------
* initialize start/end year for new investments
*V0.5c 980904 - use OFF instead of START/END
*-----------------------------------------------------------------------------
  PUTGRP = 0;
* Convert START to NOFF
  LOOP(LASTLL(LL)$CARD(NCAP_START), Z=CARD(LL)+{botime};
    PRC_NOFF(RP,'BOH',EOHYEAR)$NCAP_START(RP) = NO;
    PRC_NOFF(RP,'BOH',LL+MIN(-1,NCAP_START(RP)-Z))$NCAP_START(RP) = YES);
* Construct year sets for the active model horizon
  OPTION CLEAR=PRC_YMAX, CLEAR=UNCD1;
  UNCD1('BOH') = YES; UNCD1(YEAR)$(YEARVAL(YEAR) LE MIYR_V1) = YES;
  PRC_YMAX(RP(R,P)) = MAX(0,SMAX(PRC_NOFF(R,P,BOHYEAR(UNCD1),EOHYEAR),ORD(EOHYEAR)+{botime}-2));
* Set RTP_OFF for delayed processes
  TRACKP(RP) $= PRC_YMAX(RP);
  RTP_OFF(R,T,P)$((YEARVAL(T) LE PRC_YMAX(R,P))$TRACKP(R,P)) = ((PRC_YMAX(R,P)-B(T)+1)/D(T) GE G_OFFTHD(T));
  PRC_YMAX(TRACKP(R,P)) = SMAX(RTP_OFF(R,T,P),E(T));
""",
        )

    def check_ncap_pasti(self: PpmainMod, rl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
        LOOP(TRACKP(R,P)$SUM(PYR$NCAP_PASTI(R,PYR,P),1),
            IF(PRC_YMAX(R,P) GT 0,
        {pp_qaput("PUTOUT", "PUTGRP", "01", "Delayed Process but PASTInvestment")}
                PUT QLOG ' WARNING       - Delay is ignored:   R=',{rl},' P=',P.TL ;
            PRC_YMAX(R,P) = 0));
        OPTION CLEAR=TRACKP;
        """,
        )

    def set_rtp_off(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Set the RTP_OFF for all remaining PRC_NOFF ranges
    UNCD1(BOHYEAR) = NOT UNCD1(BOHYEAR);
    LOOP(PRC_NOFF(RP(R,P),BOHYEAR(UNCD1),EOHYEAR),TRACKP(R,P) = YES);
    LOOP(TRACKP(R,P),
    {pp_off("PRC_NOFF", "P", "", "RTP_OFF(R,T,P)$(", "YES")}
    );
    RTP(R,T,P)$RP(R,P) = YES$(YEARVAL(T) GT PRC_YMAX(R,P));
    RTP(R,PYR,P)$(RP(R,P)$(NCAP_PASTI(R,PYR,P)>0)$NCAP_PASTI(R,PYR,P)) = YES;
    RVP(RTP(R,T,P)) = YES;
    OPTION CLEAR=TRACKP;
        """,
        )

    def phase_six(self: PpmainMod, rl: str, pl: str, ctst: str) -> None:
        code = rf"""
RT_PP(R,T) = YES;

* maximum NCAP_ILED+NCAP_TLIFE+NCAP_DLAG+NCAP_DLIFE+NCAP_DELIF
    DUR_MAX=MAX(G_TLIFE,SMAX(RVP(R,T,P),NCAP_ILED(RVP)+NCAP_TLIFE(RVP)+NCAP_DLAG(RVP)+NCAP_DLIFE(RVP)+NCAP_DELIF(RVP)));

* add PASTYEAR to EOHYEARS before 1st period
    EOHYEARS(PYR)$(YEARVAL(PYR)<MINYR) = YES;
* establish EACHYEAR: goes until (MIYR_VL+DUR_MAX)
    EACHYEAR(PASTYEAR) = YES;
    EACHYEAR(ALLYEAR)$((YEARVAL(ALLYEAR) >= MINYR) * (YEARVAL(ALLYEAR) <= (MIYR_VL+DUR_MAX))) = YES;

* LATECOSTS
    PERIODYR(T,EACHYEAR)$((E(T)=MIYR_VL)*(YEARVAL(EACHYEAR) >= MIYR_VL)) = YES;

*-----------------------------------------------------------------------------
* establish rest of primary looping control sets indicating what region/process/commodities
*-----------------------------------------------------------------------------
* expand individual commodities in own CG
    MI_DMAS(COM_GMAP(RC,C)) = YES; MI_DMAS(R,C,C) = NO;



    IF(CARD(MI_DMAS),OPTION DEM<TOP; PUTGRP=0;
    LOOP(MI_DMAS(DEM(R,C),COM),
    {pp_qaput("PUTOUT", "PUTGRP", "09", "Commodity group found in topology violating its integrity")}
        PUT QLOG ' SEVERE ERROR  - Group removed from topology:   R=',{rl},' CG=',C.TL);
    OPTION DEM<=MI_DMAS; RC(DEM)=NO; RPC(R,P,C)$DEM(R,C)=NO; OPTION CLEAR=MI_DMAS,CLEAR=DEM);


    COM_GMAP(RC(R,C),C) = YES;
    NRG_GMAP(R,NRG_GRID(NRG_TYPE),C) $= NRG_TMAP(R,NRG_TYPE,C);

* UR 02/22/99 PRC_CG is now internally generated
    PRC_CG(RPC)   = YES;
    PRC_CG(RP_PG) = YES;

* Add aggregate commodities into RC
    OPTION MI_DMAS<=COM_AGG,FIN<COM_TMAP;
    LOOP(MI_DMAS(R,COM,C)$(FIN(R,COM)$FIN(R,C)),RC(R,C)=YES);
    OPTION CLEAR=FIN,CLEAR=MI_DMAS;

* determination of capacity related flows - initialization
    RPC_CAPFLO(RTP,C)$(NCAP_ICOM(RTP,C)+NCAP_OCOM(RTP,C)) = YES;
    RPC_CAPFLO(RTP,C) $= SUM(IO$NCAP_COM(RTP,C,IO),1);
    OPTION RPC_NOFLO < RPC_CAPFLO;
    LOOP(RPC_NOFLO(R,P,C)$(NOT RC(R,C)),RC(R,C)=YES);

*-----------------------------------------------------------------------------
* process/commodity relationships
*-----------------------------------------------------------------------------
* primary group & commodities in primary group
    RPC_PG(RPC(R,P,C))$SUM(RP_PG(R,P,CG)$COM_GMAP(R,CG,C),1) = YES;
    RPC_PG(RP_IRE(R,P),C)$(NOT RPC_IRE(R,P,C,'IMP')+RPC_IRE(R,P,C,'EXP')) = NO;
* endorse STG level
    RPC_PG(PRC_STGTSS(RP,C))$SUM(PRC_TSL(RP,TSL)$(ORD(TSL)>1),1)=YES;
    RP_PGTYPE(RP(R,P),COM_TYPE)$SUM(RPC_PG(R,P,C)$COM_TMAP(R,COM_TYPE,C),1) = YES;
    RP_AIRE(RP_IRE(RP),IE)$SUM(RPC_IRE(RPC_PG(RP,C),IE),1) = YES;
* input/output normalized process
    RP_INOUT(RP,IO)$SUM(TOP(RPC_PG(RP,C),IO),1) = YES;
* determine shadow primary if not provided - for regular processes only (RP_FLO)
    TRACKP(RP_FLO(RP))$(NOT SUM(PRC_SPG(RP,COM_GRP),1)) = YES;
    LOOP((RP_PGTYPE(RP_FLO(R,P),CG),IO)$(NOT RP_INOUT(R,P,IO)),
      IF(TRACKP(R,P),
* set the SPG to the same type as the PG if commodities on the other side with that COM_TYPE
        IF(SUM(TOP(R,P,C,IO)$COM_GMAP(R,CG,C),1),PRC_SPG(R,P,CG) = YES;
        ELSE
* did not find any commodities with the same type as the PG, so assume energy
* assume material if PRC is material conversion and PGTYPE is DEM
          IF((SUM(RPC(R,P,C)$COM_TMAP(R,'MAT',C),1)$SUM(PRC_MAP(R,MATPRC,P),1))$RP_PGTYPE(R,P,'DEM'),
             PRC_SPG(R,P,'MAT') = YES;
          ELSE Z=1; LOOP(PG_SMAP(CG,J,COM_TYPE)$Z,
             IF(SUM(TOP(R,P,C,IO)$COM_TMAP(R,COM_TYPE,C),1), Z=0; PRC_SPG(R,P,COM_TYPE) = YES)));
        );
      );
    );
* Add commodities in SPG into RPC_SPG
    LOOP((PRC_SPG(R,P,CG),IO)$(NOT RP_INOUT(R,P,IO)),RPC_SPG(R,P,C)$(TOP(R,P,C,IO)$COM_GMAP(R,CG,C)) = YES);
    PRC_CG(PRC_SPG) = YES;
    OPTION CLEAR=TRACKP;
"""
        self.tc.add_gams_code(module=self, phase="run", code=code)

        # *-----------------------------------------------------------------------------
        # * set level and timeslices for each commodity
        # *   - if individual TS provided and no TSL then use TSs to set TSL
        # *     else set the TS from TSL if none provided
        # *-----------------------------------------------------------------------------
        code = rf"""
* remove invalid levels
    OPTION CLEAR=RXX; RXX(R,TSL,R)$(NOT SUM(RJLVL(J,R,TSL),1))=YES; F=CARD(COM_TSL); Z=CARD(PRC_TSL);
    COM_TSL(R,C,TSL-1)$RXX(R,TSL,R)$=COM_TSL(R,C,TSL); F=CARD(COM_TSL)-F; COM_TSL(R,C,TSL)$(RXX(R,TSL,R)$F)=NO;
    PRC_TSL(R,P,TSL-1)$RXX(R,TSL,R)$=PRC_TSL(R,P,TSL); Z=CARD(PRC_TSL)-Z; PRC_TSL(R,P,TSL)$(RXX(R,TSL,R)$Z)=NO;

    IF(F+Z, PUTGRP=0;
        {pp_qaput("PUTOUT", "PUTGRP", "01", "Commodities/processes defined at non-existing TSLVL")}
        PUT QLOG ' WARNING       - Number of COM/PRC resetted to coarser level: ',F:0:0 '/' Z:0:0/);

* check for individual TS provided
    TRACKC(RC) $= SUM(COM_TS(RC,S),1);
    LOOP(COM_TS(RC(R,C),S)$(NOT SUM(COM_TSL(RC,TSL),1)),COM_TSL(RC,TSL)$TS_GROUP(R,TSL,S) = YES);
* check for excess or missing COM_TS
    LOOP(COM_TSL(TRACKC(R,C),TSLVL)$(SUM(TS_GROUP(R,TSLVL,S),1) NE SUM(COM_TS(R,C,S),1)),
      COM_TS(R,C,S)$(NOT TS_GROUP(R,TSLVL,S)) = NO;
      RCS(R,C,S)$((NOT SUM(COM_TS(R,C,TS)$RS_TREE(R,S,TS),1))$G_YRFR(R,S))=YES);
    COM_TSL(RC,'ANNUAL')$(NOT SUM(COM_TSL(RC,TSL),1)) = YES;
*GG/UR make sure to init all S
    LOOP(COM_TSL(RC(R,C),TSL)$(NOT TRACKC(RC)),COM_TS(RC,S)$TS_GROUP(R,TSL,S) = YES);
* identify all TS at/above the COM_TSL
    RCS_COMTS(RC(R,C),S)$SUM(TS_MAP(R,S,TS)$COM_TS(RC,TS),1) = YES;

* determine the spread of periods/slices for the commodities
    OPTION CLEAR=TRACKC;
    LOOP(COM_OFF(RC,BOHYEAR,EOHYEAR),TRACKC(RC) = YES);
    RTC(R,T,C)$RC(R,C) = YES;

LOOP(TRACKC(R,C),
* set the OFF range
{pp_off("COM_OFF", "C", "", "RTC(R,T,C)$(", "NO")}
* create a variable for VAR_COM for desired timeslices unless period turned off
    COM_BNDPRD(R,T,C,S,'FX')$(COM_TS(R,C,S)$(NOT RTC(R,T,C))) = EPS;
    );

RTCS_VARC(RTC(R,T,C),S)$COM_TS(R,C,S) = YES;
OPTION CLEAR=TRACKC;
"""

        self.tc.add_gams_code(module=self, phase="run", code=code)

        """
        * Peaking
        * a) Time-slices specified on COM_PKTS must be on COM_TSLevel
        * b) if no COM_PKTS is specified but COM_PEAK given, for all COM_TS
        *    COM_PKTS will be set and hence peaking equations generated
        *GG*PK 1st check if COM_PKTS has been specified at different level, then set if not provided at all
        *UR*PK 1) com_peak is set if at least one com_pkts exists
        *      2) if com_peak and com_pkts above com_ts => com_pkts is inherited
        *         if at least one com_pkts below com_ts => com_pkts is aggregated
        *      3) if com_peak but no com_pkts           => com_pkts for all com_ts
        """

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* set com_peak when com_pkts
    COM_PEAK(R,CG)$SUM(COM_PKTS(R,CG,S),1) = 1;
    TRACKC(COM_PEAK(R,C))$(NOT SUM(COM_TSL(R,C,TSL),1)) = YES;
    LOOP(ANNUAL(TS(TSL)),COM_TSL(TRACKC(R,C),TSL+SMAX(COM_PKTS(R,C,S),STOAL(R,S)))=YES);
    OPTION CLEAR=TRACKC;
* inherit to the COM_TS level if necessary
    COM_PKTS(COM_PEAK(R,C),S)$SUM(COM_PKTS(R,C,TS)$RS_TREE(R,S,TS),1) = SUM(COM_TSL(R,C,TSL),ORD(TSL)=STOAL(R,S)+1);
* if nothing then set for all
    LOOP(COM_PEAK(R,CG)$(NOT SUM(COM_PKTS(R,CG,S),1)),
        Z = SMAX(COM_TSL(R,C,TSL)$COM_GMAP(R,CG,C),TSLVLNUM(TSL));
        LOOP(TSL$(TSLVLNUM(TSL)=Z),COM_PKTS(R,CG,S)$TS_GROUP(R,TSL,S) = YES)
    );
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* set level and timeslices for each process
*   - if individual TS provided and no TSL then use TSs to set TSL
*     else set the TS from TSL if none provided
*-----------------------------------------------------------------------------
    LOOP(PRC_TS(RP(R,P),S)$(NOT SUM(PRC_TSL(RP,TSL),1)),PRC_TSL(RP,TSL)$TS_GROUP(R,TSL,S) = YES);
    PRC_TSL(RP,'ANNUAL')$(NOT SUM(PRC_TSL(RP,TSL),1)) = YES;
*GG/UR make sure to init all S
    TRACKP(RP)$(NOT SUM(PRC_TS(RP,S),1)) = YES;
    LOOP(TSL,PRC_TS(TRACKP(R,P),S)$(TS_GROUP(R,TSL,S)$PRC_TSL(R,P,TSL)) = YES);
    OPTION CLEAR=TRACKP;
""",
        )

        # * determine seasons for which a process handling seasonal commodities may need to
        # * be tracked, and identify all the TS above this level
        # *   - RPS_PRCTS corresponds to all levels at/above PRC_TS
        # *   - RPS_S2 corresponds to non-PG flo variables
        # *   - RPS_S1 corresponds to level of EQ_PTRANS

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Convert ANNUAL level timeslice storage
  RP_SGS(RP_FLO(R,P))$(PRC_TSL(R,P,'ANNUAL')$(PRC_MAP(R,'STS',P)+PRC_MAP(R,'NST',P))) = YES;
  RP_SGS(RP_FLO(R,P))$=PRC_MAP(R,'SGS',P);
  PRC_MAP(R,'STG',P)$((NOT SUM(TOP(RPC_PG(R,P,C),'IN'),1))$RP_SGS(R,P)) = NO;
* All NST operating below ANNUAL level but producing ANNUAL level commodity will be STG:
  PRC_MAP(R,'STG',P)$((NOT PRC_TSL(R,P,'ANNUAL'))$PRC_MAP(R,'NST',P)) = YES;
  RP_STG(RP(R,P)) $= PRC_MAP(R,'STG',P);

* identify shadow group timeslice level
* For LOAD processes, take the maximum TSLVL
  OPTION DEM < COM_FR;
  LOOP(COM_TSL(DEM(R,C),'ANNUAL'),TRACKP(RP_FLO(R,P))$RPC_PG(R,P,C) = YES);
  PRC_YMAX(RP(R,P)) = SMAX((RPC_SPG(R,P,C),COM_TSL(R,C,TSL)),TSLVLNUM(TSL));
  PRC_YMAX(TRACKP(R,P)) = SMAX((RPC(R,P,C),COM_TSL(R,C,TSL)),TSLVLNUM(TSL));
  PRC_YMAX(RP_STG) = 0;
  PRC_YMAX(RP) = MAX(PRC_YMAX(RP),SMAX(PRC_TSL(RP,TSL),TSLVLNUM(TSL)));
* First, get levels for each TS
  LOOP(R, OPTION CLEAR=TS_ARRAY;
    TS_ARRAY(S) $= RS_TSLVL(R,S);
    Z = MAX(1,SMAX(RLUP(R,TSLVL,TSL),TSLVLNUM(TSL)));
* identify all S at shadow level
    RPS_S2(RP_SGS(R,P),S)$(TS_ARRAY(S) = PRC_YMAX(R,P)) = YES;
    PRC_SGL(RP_FLO(R,P)) = MIN(PRC_YMAX(R,P)-1$RP_STG(R,P),Z)-1;
    PRC_YMAX(RP_SGS(R,P)) = PRC_SGL(R,P)+1;
* save the finer of the PRC_TS and the finest commodity in the shadow primary
    RPS_S1(RP(R,P),S)$(TS_ARRAY(S) = PRC_YMAX(R,P)) = YES;
    RPS_S2(RPS_S1(R,P,S))$(NOT RP_SGS(R,P)) = YES;
  );
* identify all TS at/above the PRC_TSL
  LOOP((TSLVL,TSL)$(ORD(TSL)>ORD(TSLVL)),IF(ORD(TSL)=2,RPS_PRCTS(PRC_TS(RP,S))=1); RPS_PRCTS(RP(R,P),S)$(TS_GROUP(R,TSLVL,S)$PRC_TSL(RP,TSL))=YES);
  RP_PGFLO(TRACKP)$(PRC_YMAX(TRACKP)>1) = YES;
  """,
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Establish the main control set for generation or not of a VAR_FLO/IRE for
*   each commodity involved in a process, and for viable commodity/process timeslices
* Take into consideration whether the commodity is turned off for some timeslice
* Note: RTPCS_VAR further adjusted at the end of PPMAIN (after optional REDUCE)
*-----------------------------------------------------------------------------
* Special handling for storage, esp. night storage
  RPC_STG(RPC(RP_STG(R,P),C))$(PRC_STGTSS(RPC)+PRC_STGIPS(RPC)+(RPC_PG(RPC)+RPC_SPG(RPC))$PRC_MAP(R,'NST',P)) = YES;
  TRACKPC(RPC_STG(R,P,C))$((TOP(R,P,C,'OUT')+PRC_NSTTS(R,P,'ANNUAL'))$COM_TS(R,C,'ANNUAL')$PRC_MAP(R,'NST',P)) = YES;
  RPCS_VAR(RPC(RP_STG(R,P),C),S)$(PRC_TS(R,P,S)$(NOT TRACKPC(RPC))+ANNUAL(S)$TRACKPC(RPC)) = YES;
  PRC_NSTTS(RP_STG(R,P),ANNUAL)$(NOT SUM(TOP(TRACKPC(R,P,C),'IN'),1))=NO; OPTION PRC_ACT<PRC_NSTTS;
  PRC_NSTTS(RPS_S2(R,P,S))$(NOT PRC_ACT(R,P)) $= PRC_MAP(R,'NST',P);
* The commodities in the PCG need to be tracked at the PRC_TS-level
  TRACKP(RP) = NOT RP_STG(RP);
  RPCS_VAR(RPC_PG(TRACKP(R,P),C),S)$PRC_TS(R,P,S) = YES;
* All non-PCG commodities need to be tracked at the S1/S2-level
  RPCS_VAR(RPC_SPG(TRACKP(R,P),C),S)$RPS_S2(R,P,S) = YES;
  RPCS_VAR(RPC(TRACKP(R,P),C),S)$(RPS_S1(R,P,S)$(NOT RPC_PG(R,P,C)+RPC_SPG(R,P,C))) = YES;
* Remove timeslices turned off by COM_TS
  RPCS_VAR(R,P,C,S)$RCS(R,C,S) = NO;
  OPTION CLEAR=PRC_YMAX,CLEAR=RCS,CLEAR=PRC_ACT,CLEAR=TRACKP,CLEAR=TRACKPC;

*-----------------------------------------------------------------------------
* adjustment of life and construction lead if below threshold
*-----------------------------------------------------------------------------

* NCAP_TLIFE duration check
LOOP(SAMEAS(AGE,'1'), OPTION CLEAR=RXX; PUTGRP = 0;
LOOP(RTP(R,T,P)$((NOT LIFE(AGE+(NCAP_TLIFE(RTP)-.999)))$NCAP_TLIFE(RTP)),
    {pp_qaput("PUTOUT", "PUTGRP", "01", "NCAP_TLIFE out of feasible range")}
    IF(NCAP_TLIFE(RTP) < 1, RXX(RTP) = YES;
        PUT QLOG ' WARNING       - Too short, set to 1,   R=',{rl},' P=',{pl},' V=',T.TL;
    ELSE
        PUT QLOG ' WARNING       - No FOM beyond year ',CARD(AGE):<3:0,',  R=',{rl},' P=',{pl},' V=',T.TL;
    ));
NCAP_TLIFE(RXX(R,V,P)) = 1);
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* set the technical lifetime if none set
   NCAP_TLIFE(RTP)$(NOT NCAP_TLIFE(RTP)) = G_TLIFE;
*-----------------------------------------------------------------------------
   G_ILEDNO = (G_ILEDNO+2){ctst}-2;
* Adjust fractional and negative ILED if such exist (only integral ILED can be fully consistent)
   COEF_ILED(RTP)$NCAP_ILED(RTP) = MAX(ABS(NCAP_ILED(RTP)),COEF_ILED(RTP));
   NCAP_ILED(RTP(R,V,P))$NCAP_ILED(RTP) = MAX(EPS,CEIL(NCAP_ILED(RTP)-0.5))$(COEF_ILED(RTP) > MIN(D(V),NCAP_TLIFE(RTP))/G_ILEDNO);
   NCAP_ILED(RTP(R,PHYR,P)) = NCAP_ILED(RTP)+COEF_RTP(RTP)+EPS;
""",
        )

    def phase_seven(self: PpmainMod, ctst: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
   PRC_REFIT(R,P,PRC)$PRC_REFIT(R,P,PRC)=MAX(ABS(ROUND(PRC_REFIT(R,P,PRC))),MIN(6,ABS(MAX(ROUND(PRC_REFIT(R,P,P)),-1)*2)))*MOD(ROUND(PRC_REFIT(R,P,PRC)),2);
   LOOP((RP(R,PRC),P)$PRC_REFIT(RP,P),IF(NOT PRC_RCAP(RP),RTP_OFF(R,T,P)=YES);
     IF(PRC_REFIT(RP,P)<-4,NCAP_ELIFE(RTP(R,T,P))$(NCAP_ELIFE(RTP)<1)=NCAP_TLIFE(RTP);
       NCAP_TLIFE(RTP(R,T,P))=MAX(NCAP_TLIFE(R,T,PRC)+NCAP_ILED(R,T,PRC)-1,NCAP_TLIFE(RTP))));

*-----------------------------------------------------------------------------
* capacity transfer v = year of installation and thus data values where
*   v is >= start and <= end and t is within the TLIFEv adjusted for any ILEDv
*-----------------------------------------------------------------------------
* determine the number of repeated investments
    NCAP_TLIFE(RVP)$((NCAP_PASTI(RVP)=0)$RTP_OFF(RVP)) = 1;
    COEF_RPTI(RTP(R,PASTMILE,P))$NCAP_PASTI(R,PASTMILE,P) = 1;
* If alternate objective, differentiate OBJ1 cases where TLIFE > IPD lead but TLIFE < D
    IF(ALTOBJ,COEF_RPTI(RTP(R,T,P))$NCAP_ILED(R,T,P) =
                MAX(1,CEIL((D(T)-NCAP_ILED(R,T,P))/NCAP_TLIFE(R,T,P)));
              COEF_RPTI(RTP(R,T,P))$(((ROUND(NCAP_TLIFE(R,T,P))-IPD(T){ctst}) > 0)$(NOT NCAP_ILED(R,T,P))) =
                MAX(1,CEIL(MAX(D(T),IPD(T))/NCAP_TLIFE(R,T,P)));
              COEF_RPTI(RTP(R,T,P))$(NOT COEF_RPTI(R,T,P)) = MAX(1,MAX(D(T),IPD(T))/NCAP_TLIFE(R,T,P));
    ELSE COEF_RPTI(RTP(R,T,P)) = MAX(1,CEIL((D(T)-NCAP_ILED(R,T,P))/NCAP_TLIFE(R,T,P))));
* Collect all possible period intervals for capacity transfer
    VNT(V,T)$(M(T) GE M(V)) = YES; YKVAL(VNT(V,T)) = B(T)-B(V);
    IF(ALTOBJ < 2,
      RTP_CPTYR(R,VNT(V,T),P)$((B(V)+NCAP_ILED(R,V,P)<(E(T)+1))$(NCAP_ILED(R,V,P)+COEF_RPTI(R,V,P)*NCAP_TLIFE(R,V,P)>YKVAL(V,T))
                               $RTP(R,V,P)) = YES;
    ELSE
* If linearized objective, use relaxed thresholds
      YKVAL(VNT(TT,T)) = B(T)-B(TT)-(1-MOD(IPD(T),2)+(IPD(T)-1)/9)/2; F=0;
      PASTSUM(RTP(R,V,P)) = (NCAP_ILED(R,V,P)+F)$NCAP_ILED(R,V,P)+COEF_RPTI(R,V,P)*NCAP_TLIFE(R,V,P);
      RTP_CPTYR(R,VNT(V,T),P)$((PASTSUM(R,V,P) > YKVAL(V,T))$(B(V)+NCAP_ILED(R,V,P) < E(T)+1)$RTP(R,V,P)) = YES;
      OPTION CLEAR=PASTSUM;
    );
   OPTION CLEAR=YKVAL,CLEAR=COEF_RTP;
""",
        )

    def phase_eight(
        self: PpmainMod, rl: str, pl: str, cl: str, pgprim: str, prc_simv_defined: bool
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
   RTP_CPTYR(R,MIYR_1(T),T,P)$(RTP(R,T,P)$PRC_MAP(R,'STK',P)) = YES;
*-----------------------------------------------------------------------------
* Preprocess capacity bounds
*-----------------------------------------------------------------------------
* Migrate CAP_BND + QA check
   OPTION CLEAR=RVP; PUTGRP=0;
   CAP_BND(RTP,BDNEQ) $= CAP_BND(RTP,'FX');

    LOOP((RTP(R,T,P),L('UP'))$((CAP_BND(RTP,L)<=PRC_RESID(RTP))$CAP_BND(RTP,L)),
        IF(PRC_RCAP(R,P), Z=0; ELSE Z=PRC_RESID(RTP));
        IF(Z, F=CAP_BND(RTP,L); CAP_BND(RTP,L)$(IFQ<10)=EPS; F$(0**(IFQ+F+1$RP_FLO(R,P)))=Z;
        IF(F<Z, RCAP_BND(RTP,'N')=Z;
        {pp_qaput("PUTOUT", "PUTGRP", "IFQ", "Inconsistent CAP_BND(UP/FX) defined for process capacity")}
        PUT ' WARNING       - Bound converted to NCAP_BND,   R.T.P= ',RTP.TE(RTP); PUT$(IFQ>9)@28 'infeasibility detected,')));
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* clear zero / INF CAP_BNDs
   RVP(RTP)$((CAP_BND(RTP,'UP')=0)$CAP_BND(RTP,'UP')) = YES;
   LOOP(T, NCAP_BND(R,TT,P,'UP')$(RTP_CPTYR(R,TT,T,P)$RVP(R,T,P)) = EPS);
   RVP(RTP_VARP)=NO; CAP_BND(RVP,BD) = 0;
   CAP_BND(RTP,BDLOX)$MAPVAL(CAP_BND(RTP,BDLOX)) = 0;
* Check whether both UP and LO bounds (then it pays to have VAR_CAP)
   RTP_VARP(RTP(R,T,P))$(CAP_BND(RTP,'UP')*CAP_BND(RTP,'LO')) = YES;
   PUTGRP=0;

    LOOP(RTP(RTP_VARP)$((CAP_BND(RTP,'LO')>CAP_BND(RTP,'UP'))$CAP_BND(RTP,'UP')),
    {pp_qaput("PUTOUT", "PUTGRP", "1", "Inconsistent CAP_BND(UP/LO/FX) defined for process capacity")}
    PUT ' WARNING       - Lower bound set equal to upper bound,   R.T.P= ',RTP.TE(RTP));
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* turn off RTP/CPTYR if no new investment & installed capacity no longer available
    LOOP(BDUPX(BD),RTP_OFF(RTP)$((NCAP_BND(RTP,BD)=0)$NCAP_BND(RTP,BD)) = YES);
    NO_RVP(RTP_OFF(R,T,P))$(NOT NCAP_PASTI(R,T,P)) = YES;
    LOOP(T, NO_RVP(R,TT,P)$(RTP_CPTYR(R,T,TT,P)$(NOT RTP_OFF(R,T,P))) = NO);
    LOOP(PYR(V), NO_RVP(R,T,P)$(RTP_CPTYR(R,V,T,P)$NCAP_PASTI(R,V,P)) = NO);
    RTP(NO_RVP) = NO;
    RTP_CPTYR(R,T,TT,P)$((NOT NCAP_PASTI(R,T,P))$RTP_OFF(R,T,P)) = NO;
    OPTION CLEAR=RVP, CLEAR=NO_RVP;

*-----------------------------------------------------------------------------
* initialize start/end year for a process & available years
*-----------------------------------------------------------------------------
*-- Speed up by first tracking RPs with PRC_AOFF
    LOOP(PRC_AOFF(RP(R,P),BOHYEAR,EOHYEAR),TRACKP(R,P) = YES);
    RTP_VARA(RTP(R,T,P))$(NOT TRACKP(R,P)) = YES;

LOOP(TRACKP(R,P), MY_FIL(T) = YES;
* set the OFF range
{pp_off("PRC_AOFF", "P", "", "MY_FIL(T)$(", "NO")}
* set the periods for which VAR_ACT is OK
    RTP_VARA(RTP(R,MY_FIL(T),P)) = YES;
    );
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION CLEAR=TRACKP;

*-----------------------------------------------------------------------------
* initialize start/end year for a process flows
*-----------------------------------------------------------------------------
* Initialize start/end year for process commodities
    RTPC(RTP(R,T,P),C) $= RPC(R,P,C);
    PUTGRP = 0;
*-- track all RPCs with PRC_FOFF:
    LOOP(PRC_FOFF(R,P,C,TS,BOHYEAR,EOHYEAR),TRACKPC(R,P,C) = YES);

LOOP(RPCS_VAR(TRACKPC(R,P,C),S), MY_FIL(T) = NO;
* check for shut-off here or timeslice above
{pp_off("PRC_FOFF", "P,C,TS", "$TS_MAP(R,TS,S)", "MY_FIL(T)$(", "YES")}
* QC check that shut-off not specified below the VAR level
    RTPCS_OUT(RTP_VARA(R,MY_FIL(T),P),C,S) = YES;
    );
    LOOP(PRC_FOFF(RPC(R,P,C),TS,BOHYEAR,EOHYEAR)$SUM(RPCS_VAR(R,P,C,S)$RS_BELOW(R,S,TS),1),
        {pp_qaput("PUTOUT", "PUTGRP", "01", "Flow OFF TS level below VARiable TS level")}
        PUT QLOG ' WARNING       - OFF is ignored:  R=',{rl},' P=',{pl},' C=',{cl},' S=',TS.TL ;
    );
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION CLEAR=TRACKP;

*-----------------------------------------------------------------------------
* Add leading milestones into RTP if/when simulated vintages
{"LOOP(T,NO_RVP(R,TT-1,P)$(RTP_CPTYR(R,TT,T,P)$PRC_SIMV(R,P))=YES); NO_RVP(RTP(R,T,P))=NO; RTP(NO_RVP)=YES;" if prc_simv_defined else ""}
*-----------------------------------------------------------------------------
* Remove commodity from PG if PRC_ACTFLO flagged non-interpolated, as bad
   RPC_PG(R,P,C)$((NOT RP_PG(R,P,C))$(ROUND(PRC_ACTFLO(R,'0',P,C)<0))) = NO;
* Save original non-PG PRC_ACTFLO groups
   RPC_PG(RPC_STG) = YES;
   RP_STD(RP_FLO(RP))$(NOT RP_STG(RP)) = YES;
   OPTION RPC_ACT <= PRC_ACTFLO;
   RPC_ACT(R,P,C)$(RPC_PG(R,P,C)+(NOT RPC(R,P,C)$RP_STD(R,P))) = NO;
   CHP(RP(R,P)) $= PRC_MAP(R,'CHP',P);

*-----------------------------------------------------------------------------
* establishment PRC_CAPACT/ACTFLO from PRC_CAPUNT/ACTUNT/COM_UNIT & determine INOUT(r,p)
*-----------------------------------------------------------------------------
   PRC_CAPACT(RP)$(NOT PRC_CAPACT(RP)) = 1;
* Copy PRC_ACTFLO from PG to individual commodities in PG, allowing reserved word {pgprim}
   PRC_ACTFLO(RTP(R,V,P),C)$((NOT PRC_ACTFLO(RTP,C))$RPC_PG(R,P,C)) $= SUM(RP_PG(R,P,CG),PRC_ACTFLO(R,V,P,CG));
   PRC_ACTFLO(RTP(R,V,P),C)$((NOT PRC_ACTFLO(RTP,C))$RPC_PG(R,P,C)) $= PRC_ACTFLO(RTP,"{pgprim}");
   PRC_ACTFLO(RTP(R,V,P),C)$((NOT PRC_ACTFLO(RTP,C))$RPC_PG(R,P,C)) = 1;
* RP_PGACT signifies that activity can be substituted for the primary flow
   RP_PGACT(RP_FLO(R,P))$(SUM(RPC_PG(R,P,C),1) EQ 1) = YES;
   RP_PGACT(RP_IRE(R,P))$(SUM(RPC_IRE(RPC_PG(R,P,C),IE),1) EQ 1) = YES;
""",
        )

    def phase_nine(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    MAXLIFE = SMAX(RTP,NCAP_TLIFE(RTP));
* Convert indexes to demand elasticity shape curves to tuples
    LOOP(SAMEAS(J,'1'),RTC_SHED(R,T,C,BD,J+MAX(0,COM_ELASTX(R,T,C,BD)-1))$COM_ELASTX(R,T,C,BD) = YES);
    STARTOFF = CEIL(MAX(MAXLIFE,SMAX(RTC_SHED(R,T,C,BD,J),COM_VOC(R,T,C,BD))*100))+1;
""",
        )

    def establish_basic_defaults_for_non_ts_attribute(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    LOOP(J, Z=1; LOOP(LL$(MULTI(J,LL)*Z), Z=0; F=MIN(1,MULTI(J,LL)));
      IF(NOT Z, MULTI(J,EOHYEARS)$(NOT MULTI(J,EOHYEARS)) = F));
    MULTI('1',EACHYEAR) = 1;

*-----------------------------------------------------------------------------
* establish basic defaults for the non-TS attribute
*-----------------------------------------------------------------------------

* economic life = technical life if not provided
    NCAP_ELIFE(RTP)$(NOT NCAP_ELIFE(RTP)) = NCAP_TLIFE(RTP);
* commodity release always in next year if no time provided but release
    NCAP_DLIFE(RTP(R,T,P))$((NOT NCAP_DLIFE(RTP))$SUM(RPC(R,P,C)$NCAP_OCOM(RTP,C),1)) = 1;
    NCAP_DELIF(RTP(R,T,P))$(NOT NCAP_DELIF(RTP))$= NCAP_DLIFE(RTP);
* if investment requires commodity and has a leadtime, set commodity time = lead, if not provided
    NCAP_CLED(RTP(R,T,P),C)$((NOT NCAP_CLED(RTP,C))$NCAP_ICOM(RTP,C)) = COEF_ILED(RTP);
* defaults for CHP plants
    NCAP_BPME(RTP(R,V,P))$((NOT NCAP_BPME(RTP))$NCAP_CDME(RTP)$CHP(R,P)) = 1;
    NCAP_CHPR(RTP(R,V,P),'UP')$((NOT SUM(LIM$NCAP_CHPR(RTP,LIM),1))$CHP(R,P)) = 1;
* set default storage efficiency if not provided
    LOOP(RP_STG(R,P)$(NOT SUM(RTP(R,T,P)$STG_EFF(RTP),1)), STG_EFF(RTP(R,V,P)) = 1);

""",
        )

    def phase_eleven(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* determination of capacity-ONLY related flows
*-----------------------------------------------------------------------------
* Initialize capflo indicators for UC_FLO
  UC_CAPFLO(UC_N,SIDE,RPC_NOFLO(R,P,C))$UC_ATTR(R,UC_N,SIDE,'FLO','CAPFLO') = YES;
  RPC_NOFLO(RPC_PG) = NO;
  RPCS_VAR(RPC_NOFLO(R,P,C),ANNUAL)$(NOT RPC(R,P,C)) = YES;
  TRACKPC(RPC_NOFLO) = YES;
* identify those commodities involved ONLY with capacity by eliminating those with flows
  LOOP(TRACKPC(R,P,C),
    IF(RP_IRE(R,P),
* RPC_IRE implies IRE_FLOc so not only capacity related
      Z = NOT SUM(RPC_IRE(R,P,C,IE),1);
      Z$Z = NOT SUM((RTPC(R,T,P,COM),S,IE,IO)$IRE_FLOSUM(R,T,P,COM,S,IE,C,IO),RPC_IRE(R,P,COM,IE));
    ELSE
      Z = NOT SUM(RTPC(R,T,P,C)$PRC_ACTFLO(R,T,P,C),1);
* check for the commodity within flo_func/sum/shar
      Z$Z = NOT SUM((T,CG1,CG2,S)$FLO_FUNC(R,T,P,CG1,CG2,S),COM_GMAP(R,CG1,C)+COM_GMAP(R,CG2,C));
      Z$Z = NOT SUM((T,CG1,COM,CG2,S)$FLO_SUM(R,T,P,CG1,COM,CG2,S),COM_GMAP(R,COM,C)+COM_GMAP(R,CG2,C));
      Z$Z = NOT SUM((T,CG,S,BD)$FLO_SHAR(R,T,P,C,CG,S,BD),1);
    );
    IF(NOT Z, RPC_NOFLO(R,P,C) = NO);
  );
  OPTION CLEAR=TRACKPC;
""",
        )

    def phase_twelve(self: PpmainMod, rl: str, cl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Defaults for infrastructure efficiency and seasonal fraction
    OPTION RCS < COM_IE, CLEAR=RTC_NET,CLEAR=RP_PGFLO;
    COM_IE(RTCS_VARC(R,T,C,S))$(NOT RCS(R,C,S)) = 1;
*GG* 010406 - sum up COM_FRs below on a seasonal level so RTCS_TSFR set below
* Get the timeslices where COM_FR has been given
    COM_FR(R,LL,C,ANNUAL)=0; OPTION RCS<COM_FR;
    TRACKC(R,C) $= SUM(RCS(R,C,S),1);
    RCS(TRACKC(R,C),S)$G_YRFR(R,S) = (NOT RCS(R,C,S));
* Fill all other COM_TS timeslices and finer with default fractions
    COM_FR(RTC(R,T,C),S)$(RCS(R,C,S)*COM_TS(R,C,S)) = G_YRFR(R,S);
    COM_FR(RTC(R,T,C),TS)$(RCS(R,C,TS)*TS_GROUP(R,'WEEKLY',TS)) $=
      SUM(RS_BELOW1(R,S,TS),COM_FR(R,T,C,S)*(G_YRFR(R,TS)/G_YRFR(R,S)));
    COM_FR(RTC(R,T,C),TS)$(RCS(R,C,TS)*TS_GROUP(R,'DAYNITE',TS)) $=
      SUM(RS_BELOW1(R,S,TS),COM_FR(R,T,C,S)*(G_YRFR(R,TS)/G_YRFR(R,S)));
* Sum up COM_FR for all commodities that have it defined
    COM_FR(R,T,C,TS)$(TRACKC(R,C)$TS_GROUP(R,'WEEKLY',TS)) $= SUM(RS_BELOW1(R,TS,S),COM_FR(R,T,C,S));
    COM_FR(R,T,C,TS)$(TRACKC(R,C)$TS_GROUP(R,'SEASON',TS)) $= SUM(RS_BELOW1(R,TS,S),COM_FR(R,T,C,S));
    COM_FR(R,T,C,S)$NORTS(R,T,S)=0;
    COM_FR(R,T,C,ANNUAL)$TRACKC(R,C) = SUM(RS_BELOW1(R,ANNUAL,S),COM_FR(R,T,C,S));

* Normalize COM_FR:
PUTGRP = 0;
LOOP(TRACKC(R,C), Z=1;
LOOP(RTC(R,T,C)$((COM_FR(R,T,C,'ANNUAL') NE 1)$Z),
IF(ABS(COM_FR(R,T,C,'ANNUAL')-1) GT 1E-5, Z=0;
{pp_qaput("PUTOUT", "PUTGRP", "01", "COM_FR does not sum to unity (T=first year)")}
    PUT QLOG ' WARNING       - Normalized to 1,   R=',{rl},' C=',{cl},' (T=',T.TL:0,')';)));
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    COM_FR(RTC(R,T,C),S)$((COM_FR(RTC,'ANNUAL') NE 1)$TRACKC(R,C)) = COM_FR(RTC,S) / COM_FR(RTC,'ANNUAL');
    RP_PGFLO(RP(R,P))$=SUM(RPC_PG(RP,C)$TRACKC(R,C),1);
    RP_PGFLO(RP)$SUM(RPS_S1(PRC_TS(RP,S)),1)=NO;
    OPTION CLEAR=RCS, CLEAR=TRACKC;
""",
        )

    def phase_thirteen(self: PpmainMod, mx: str, rts: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
    RS_FR(RS_TREE(R,S,TS)) = 1$TS_MAP(R,S,TS) + (G_YRFR(R,S)/G_YRFR(R,TS))$RS_BELOW(R,TS,S);
    RTCS_FR{mx}(RTC(R,T,C),S,TS)$(RS_BELOW(R,TS,S)$COM_FR(RTC,TS)) =
                                 ((COM_FR(RTC,S)/COM_FR(RTC,TS))$(COM_FR(RTC,TS)>0))/RS_FR(R,S,TS)-1;
    COM_FR(RTC(R,T,C),{rts})$((NOT COM_FR(RTC,S))$RCS_COMTS(R,C,S)) = G_YRFR(R,S);

*-----------------------------------------------------------------------------
* Elastic demands
*-----------------------------------------------------------------------------
   OPTION DEM < COM_PROJ;
""",
        )

    def phase_fourteen(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* check sign of COM_ELAST and set RCJ after assigning default COM_STEPs
   COM_ELAST(R,T,C,S,BDNEQ(BD))$COM_ELAST(R,T,C,S,BD) =
      -ABS(COM_ELAST(R,T,C,S,BD)-1+1)$SUM(RDCUR(R,CUR),COM_BPRICE(R,T,C,S,CUR)*COM_VOC(R,T,C,BD)>0);
   OPTION RC_AGP < COM_ELAST; COM_STEP(RC_AGP(RC,BDNEQ))$(NOT COM_STEP(RC,BDNEQ)) = MAX(1,COM_STEP(RC,'FX'));
   RCJ(RC,J,BD)$((ORD(J) <= COM_STEP(RC,BD))$RC_AGP(RC,BD)) = 1; OPTION CLEAR=RC_AGP;

*-----------------------------------------------------------------------------
* process availability factor
*   - apply MULTI (moved to coef_cpt)
*   - move up to the appropriate level, if applicable
*   - move down to the appropriate level, if applicable
*   - set default, if necessary
*-----------------------------------------------------------------------------

* leveling of availability; set at the PRC_TS level by inheriting from above, if not yet set
  PUTGRP = 0;
  RTPS_BD(RTP(R,V,P),S,BD)$PRC_TS(R,P,S) $= NCAP_AFS(RTP,S,BD)$(NOT NCAP_AF(RTP,S,BD));
""",
        )

    def phase_fiveteen(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  NCAP_AF(RTPS_BD)$NCAP_AF(RTPS_BD) $= NCAP_AFS(RTPS_BD);

* Mark those timeslices that have NCAP_AFs:
  OPTION CLEAR=RXX,CLEAR=RTPS_BD;
  RTPS_BD(R,LL--(ORD(LL)*(NCAP_AF(R,LL,P,S,BD) GT 0)),P,S,BDUPX(BD))$(V(LL)$NCAP_AF(R,LL,P,S,BD))=YES;
  OPTION TRACKP < RTPS_BD; RXX(PRC_TS(TRACKP(R,P),S))$=SUM(RTPS_BD(R,LASTLL,P,S,BDUPX),1);
* Set default if no PRC_TS has NCAP_AFs :
  NCAP_AF(RTP(R,V,P),S,'UP')$(PRC_TS(R,P,S)$(NOT TRACKP(R,P))) = 1.0;
  PRC_TS2(PRC_TS(TRACKP(R,P),S)) = (NOT RXX(R,P,S));
  NCAP_AF(RTP(R,V,P),S,'UP')$(PRC_TS2(R,P,S)$RP_STG(R,P)) = EPS;
  PRC_TS2(RP_STG,S) = NO;

* Make sure to get rid of any remaining PRC_TS for which no NCAP_AF
  PRC_TS2(RP(R,P),S) $= SUM(RS_BELOW(R,TS,S)$PRC_TS2(RP,TS),1);
  PRC_TS(PRC_TS2) = NO;
  RPCS_VAR(RPCS_VAR(R,P,C,S))$PRC_TS2(R,P,S) = NO;
  RTPCS_OUT(RTPC(R,T,P,C),S)$PRC_TS2(R,P,S) = YES;
  OPTION CLEAR=PRC_TS2,CLEAR=TRACKP,CLEAR=RTPS_BD;
""",
        )

    def phase_sixteen(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*GG*PKCOI defaults to 1
    LOOP((RPC(R,P,C),COM_GMAP(COM_PEAK(R,CG),C))$(TOP(RPC,'IN')+RPC_IRE(RPC,'EXP')),
        IF(NOT SUM((RTP(R,T,P),RPCS_VAR(RPC,TS))$FLO_PKCOI(RTP,C,TS),1),TRACKPC(RPC)=YES));
    TRACKPC(PRC_PKNO(R,P),C)=NO;
    FLO_PKCOI(RTP(R,T,P),C,S)$(RPCS_VAR(R,P,C,S)$TRACKPC(R,P,C))  = 1.0
    OPTION CLEAR=TRACKPC;
""",
        )

    def phase_seventeen(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Add FLO_SUM translated from PRC_ACTFLO
  IRE_FLOSUM(RTP(R,V,P),C,S,IE,COM,IO)$(RPC_PG(R,P,C)*RPC_IRE(R,P,C,IE)*RPCS_VAR(R,P,C,S)*TOP(R,P,COM,IO)) $=
     SUM(RPC_ACT(RP_IRE(R,P),COM),PRC_ACTFLO(R,V,P,COM)*(1/PRC_ACTFLO(R,V,P,C)));
  FLO_SUM(RTP(R,V,P),CG,C,COM,S)$(RP_PG(R,P,CG)*RPC_PG(R,P,C)*PRC_TS(R,P,S)) $=
     SUM(RPC_ACT(RP_FLO(R,P),COM),PRC_ACTFLO(R,V,P,COM)*(1/PRC_ACTFLO(R,V,P,C)));
  OPTION CLEAR=RPC_ACT;
""",
        )

    def phase_eightteen(
        self: PpmainMod, macro: str, micro: str, rl: str, pgprim: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Preprocess market-based trade
*-----------------------------------------------------------------------------
* Set endogenous trade indicators
  OPTION CLEAR=RXX;
  LOOP(TOP_IRE(R,C,REG,COM,P),RXX(R,C,P) = YES; RPC_IREIO(REG,P,COM,'IMP','IN') = YES);
  RPC_IREIO(R,P,C,'EXP','IN')$RXX(R,C,P) = YES;
  RPC_IREIO(RPC_IRE(R,P,C,IE),'OUT')$(NOT RPC_IREIO(R,P,C,IE,'IN')) = YES;
  PRC_MAP(R,'DISTR',P)$PRC_MAP(R,'CORR',P) = YES;
  IRE_DIST(RP_IRE(R,P))$PRC_MAP(R,'DISTR',P) = YES;

* Define a marketplace whenever imports to several regions, or an intermediate region between two other regions
  LOOP(RXX(R,C,P)$(SUM(TOP_IRE(R,C,REG,COM,P),1) GT 1),RPC_MARKET(R,P,C,'EXP') = YES);
  RXX(R,C,P)$IRE_DIST(R,P) = NO;
  LOOP(TOP_IRE(REG,COM,RXX(R,C,P))$(NOT SUM(COM1$TOP_IRE(R,C,REG,COM1,P),1)),RPC_MARKET(R,P,C,'EXP') = YES);

* Ensure that over distribution all directly linked regions after first market are also markets
  TRACKPC(IRE_DIST(R,P),C)$RPC_MARKET(R,P,C,'EXP') = YES;
  WHILE(CARD(TRACKPC), OPTION CLEAR=RXX;
    LOOP((TRACKPC(R,P,C),TOP_IRE(R,C,REG,COM,P),RPC_IRE(REG,P,COM1,'EXP')),
      IF(NOT SUM(COM2$TOP_IRE(REG,COM1,R,COM2,P),1),RXX(REG,P,COM1)=YES));
    OPTION CLEAR=TRACKPC; TRACKPC(RXX(R,P,C))$(NOT RPC_MARKET(R,P,C,'EXP')) = YES;
    RPC_MARKET(TRACKPC,'EXP') = YES);

PUTGRP=0;
* Set the import commodities for marketplaces
LOOP(RPC_MARKET(R,P,C,IE)$(NOT SUM(TOP_IRE(R,C,R,COM,P),1)),
* If only one import and market commodity is involved for (R,P), choose the import:
    Z=SUM(RPC_IRE(R,P,COM,'IMP'),1)+EPS;
    IF(IRE_DIST(R,P),IF(Z GT 1,
    {pp_qaput("PUTOUT", "PUTGRP", "01", "Unsupported diverging trade topology")}
    PUT QLOG ' WARNING       - Too complex topology:  R=',{rl},' P=',P.TL;)
    ELSEIF Z=1, Z=SUM(COM$RPC_MARKET(R,P,COM,'EXP'),1));
    IF(Z EQ 1, LOOP(RPC_IRE(R,P,COM,'IMP'), Z=0; CG_GRP(R,P,C,COM) = YES));
    IF(Z,CG_GRP(R,P,C,C) = YES));
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(CG_GRP(R,P,C,COM),RC_RC(R,C,R,COM) = YES);
  TOP_IRE(RC_RC(R,C,R,COM),P)$CG_GRP(R,P,C,COM) = YES;
  OPTION CLEAR=CG_GRP;

* Complete the preparation of marketplace
  LOOP(TOP_IRE(R,C,R,COM,P),
* If no IRE_FLO set for marketplace, set default values
    IF(IRE_DIST(R,P),
      IRE_FLO(RTP(R,V,P),C,R,COM,S)$((IRE_FLO(R,V,P,C,R,COM,S) EQ 0)$RPCS_VAR(R,P,COM,S)) = 1;
    ELSE F = SUM((RTP(R,T,P),S)$IRE_FLO(R,T,P,C,R,COM,S),1);
      LOOP((REG,COM1)$(TOP_IRE(R,C,REG,COM1,P)$(NOT F)),
        F = SUM((RTP(R,T,P),S)$IRE_FLO(R,T,P,C,REG,COM1,S),1);
        IF(F, IRE_FLO(RTP(R,V,P),C,R,COM,S)$RPCS_VAR(R,P,COM,S) = IRE_FLO(R,V,P,C,REG,COM1,S)))));

* Set standard EQIRE control for all imports other than from marketplace region
  LOOP(TOP_IRE(R,C,REG,COM,P)$RPC_MARKET(R,P,C,'EXP'),IF(NOT SAMEAS(R,REG),TRACKPC(REG,P,COM) = YES));
  RPC_EQIRE(RPC_IRE(R,P,C,'IMP'))$((NOT TRACKPC(R,P,C))$RPC_IREIO(R,P,C,'IMP','IN')) = YES;
  OPTION CLEAR=TRACKPC;

* Set all non-standard EQIRE and MARKET controls
  LOOP(TOP_IRE(R,C,R,COM,P),
    IF(NOT RPC_EQIRE(R,P,COM,'IMP'), RPC_EQIRE(R,P,C,'EXP') = YES;
    ELSEIF RPC_MARKET(R,P,C,'EXP'),
      IF(IRE_DIST(R,P), RPC_EQIRE(R,P,C,'EXP') = YES; ELSE RPC_MARKET(R,P,COM,'IMP') = YES)));
  TOP_IRE(R,C,R,COM,P)$RPC_EQIRE(R,P,C,'EXP') = NO;

* Copy shutdown periods of marketplace to import regions
  LOOP(RPC_MARKET(R,P,C,'EXP'),RTPC(REG,T,P,COM)$(TOP_IRE(R,C,REG,COM,P)$(NOT RTP_VARA(R,T,P))) = NO);
* Copy shutdown periods of import process to export regions
  LOOP(TOP_IRE(REG,C,R,COM,P)$RPC_EQIRE(R,P,COM,'IMP'),RTPC(REG,T,P,C)$(NOT RTP_VARA(R,T,P)) = NO);

* Reset RP_AIRE for distr IRE processes
  RP_AIRE(RP_IRE(R,P),'EXP')$(RP_AIRE(R,P,'IMP')$IRE_DIST(R,P)) = NO;

* Set IRE_FLOSUM for C if activity has IE flow
  IRE_FLOSUM(RTP(R,T,P),C,S,IE,COM,IO)$(RPC_PG(R,P,C)$RP_AIRE(R,P,IE)$IRE_FLOSUM(RTP,'{pgprim}',S,IE,COM,IO)) =
     IRE_FLOSUM(RTP,'{pgprim}',S,IE,COM,IO)*(1/PRC_ACTFLO(RTP,C));
  IRE_FLOSUM(R,T,P,'{pgprim}',S,IE,COM,IO) = 0;
*-----------------------------------------------------------------------------

* OK inter-regional trade if in topology
* Default values for IRE_FLO by LOOP over TOP_IRE
  LOOP(TOP_IRE(R,C,REG,COM,P),
    IF(NOT SUM((RTP(R,T,P),S)$IRE_FLO(R,T,P,C,REG,COM,S),1),
       IRE_FLO(RTP(R,V,P),C,REG,COM,S)$PRC_TS(REG,P,S) = 1));

*-----------------------------------------------------------------------------
* initialize the commodity balance equation type
*   - equality (MAT,ENV,FIN)
*   - prodution >= consumption (NRG,DEM)
*GG* questions about conservation and renewables being =N= balances?
*   - ignored for now (with no equations created)
*-----------------------------------------------------------------------------
* set the sub-sets of commodities
    NRG(RC(R,C))$COM_TMAP(R,'NRG',C) = YES;
    MAT(RC(R,C))$COM_TMAP(R,'MAT',C) = YES;
    DEM(RC(R,C))$COM_TMAP(R,'DEM',C) = YES;
    ENV(RC(R,C))$COM_TMAP(R,'ENV',C) = YES;
    FIN(RC(R,C))$COM_TMAP(R,'FIN',C) = YES;

* free up if conservation or free energy type, unless provided by the user
    TRACKC(RC) = YES;
    LOOP(LIM,TRACKC(R,C)$COM_LIM(R,C,LIM) = NO);
    COM_LIM(TRACKC(NRG(R,C)),'UP')$(NRG_TMAP(R,'CONSRV',C) + NRG_TMAP(R,'FRERENEW',C)) = YES;
* set defaults if not provided by user
   TRACKC(R,C)$COM_LIM(R,C,'UP') = NO;
   COM_LIM(MAT(TRACKC),'FX') = YES;
   COM_LIM(FIN(TRACKC),'FX') = YES;
   TRACKC(R,C)$COM_LIM(R,C,'FX') = NO;
   COM_LIM(TRACKC,'LO') = YES;
   OPTION CLEAR=TRACKC;
   """,
        )

        # handle TIMES-MACRO
        if macro.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""COM_LIM(RC(DEM),BD)$(NOT COM_LIM(RC,'N')) = NOT BDNEQ(BD);""",
            )
        if micro.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""COM_LIM(RC(DEM),BD)$(NOT COM_LIM(RC,'N')) = NOT BDNEQ(BD);""",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* establish inter-regional convert attributes
*-----------------------------------------------------------------------------
* identify regions trading
    OPTION RREG <= TOP_IRE; OPTION CLEAR=RXX;
    LOOP(RREG(ALL_R,ALL_REG), Z=1;
* if all regions working with same time-slices, set to 1
*  assumption is if have one direction then have the other too
       LOOP(TSLVL$Z,
         Z$Z = PROD(TS_GROUP(ALL_R,TSLVL,S),TS_GROUP(ALL_REG,TSLVL,S));
         Z$Z = PROD(TS_GROUP(ALL_REG,TSLVL,S),TS_GROUP(ALL_R,TSLVL,S));
         IF(Z, RXX(ALL_R,S,ALL_REG)$TS_GROUP(ALL_R,TSLVL,S) = YES)));
    RXX(ALL_R,S,ALL_REG)$RXX(ALL_REG,S,ALL_R) = YES;
    IRE_TSCVT(RXX(ALL_R,S,ALL_REG),S)$(NOT IRE_TSCVT(ALL_R,S,ALL_REG,S)) = 1;
* for the conversion of traded commodities, set default to 1
*  assumption is if have one direction then have the other too
    OPTION RC_RC < IRE_CCVT;
    IRE_CCVT(RC_RC(RC,R,C))$(NOT IRE_CCVT(RC_RC)) = 1/IRE_CCVT(R,C,RC);
    OPTION RC_RC <= TOP_IRE; IRE_CCVT(RC_RC)$(NOT IRE_CCVT(RC_RC)) = 1;
    OPTION RC_RC <  TOP_IRE; IRE_CCVT(RC_RC)$(NOT IRE_CCVT(RC_RC)) = 1;

*-----------------------------------------------------------------------------
* process bounds to see if aggregation is necessary
*-----------------------------------------------------------------------------
   PUTGRP = 0;
   OPTION CLEAR=UNCD7;
""",
        )

    def phase_nineteen(self: PpmainMod, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Add bounds based on rate levels
  FLO_BDLVL(RTP,CG,S,BD)$FLO_BND(RTP,CG,S,BD) = 0;
  FLO_BND(RTPC(R,T,P,C),S,BD)$(RPCS_VAR(R,P,C,S)$FLO_BDLVL(RTPC,S,BD)) = FLO_BDLVL(RTPC,S,BD)*G_YRFR(R,S)*8760;
  FLO_BND(RTP(R,T,P),CG(COM_TYPE),S,BD)$(PRC_TS(R,P,S)$RP_IRE(R,P)$FLO_BDLVL(RTP,CG,S,BD)) = FLO_BDLVL(RTP,CG,S,BD)*G_YRFR(R,S)*8760;
  ACT_BND(RTP(R,T,P),S,BD)$((RP_STG(R,P)->0)$PRC_TS(R,P,S)$FLO_BDLVL(RTP,'{pgprim}',S,BD)) = FLO_BDLVL(RTP,'{pgprim}',S,BD)*G_YRFR(R,S)*8760;

*-----------------------------------------------------------------------------
* process cumulative bounds
*-----------------------------------------------------------------------------
* process flows: UC_CUMFLO
  UC_CUMFLO(UC_N,R,P,C,BOHYEAR+BEOH(BOHYEAR),EOHYEAR+BEOH(EOHYEAR)) $= UC_CUMFLO(UC_N,R,P,C,BOHYEAR,EOHYEAR);
  UC_CUMFLO(UC_N,R,P,C,BOHYEAR,EOHYEAR)$(NOT LL(BOHYEAR)*LL(EOHYEAR)) = 0;
  UC_CUMFLO(UC_N,R,P,'{pgprim}',BOHYEAR+BEOH(BOHYEAR),EOHYEAR+BEOH(EOHYEAR)) $= UC_CUMACT(UC_N,R,P,BOHYEAR,EOHYEAR);
  LOOP((UC_N,RP,C,YEAR,LL)$UC_CUMFLO(UC_N,RP,C,YEAR,LL),RPC_CUMFLO(RP,C,YEAR,LL)=YES);
* process flows: FLO_CUM
  FLO_CUM(R,P,C,BOHYEAR+BEOH(BOHYEAR),EOHYEAR+BEOH(EOHYEAR),L) $= FLO_CUM(R,P,C,BOHYEAR,EOHYEAR,L);
  FLO_CUM(R,P,C,BOHYEAR,EOHYEAR,L)$(NOT LL(BOHYEAR)*LL(EOHYEAR)) = 0;
  FLO_CUM(R,P,'{pgprim}',BOHYEAR+BEOH(BOHYEAR),EOHYEAR+BEOH(EOHYEAR),L) $= ACT_CUM(R,P,BOHYEAR,EOHYEAR,L);
  RPC_CUMFLO(RP,C,YEAR,LL) $= SUM(L$FLO_CUM(RP,C,YEAR,LL,L),YES);
  OPTION CLEAR=UC_CUMACT,CLEAR=ACT_CUM;
* commodities: UC_CUMCOM
  UC_CUMCOM(UC_N,R,COM_VAR,C,BOHYEAR+BEOH(BOHYEAR),EOHYEAR+BEOH(EOHYEAR)) $= UC_CUMCOM(UC_N,R,COM_VAR,C,BOHYEAR,EOHYEAR);
  UC_CUMCOM(UC_N,R,COM_VAR,C,BOHYEAR,EOHYEAR)$(NOT LL(BOHYEAR)*LL(EOHYEAR)*RC(R,C)) = 0;
  LOOP((UC_N,R,COM_VAR,C,YEAR,LL)$UC_CUMCOM(UC_N,R,COM_VAR,C,YEAR,LL),RC_CUMCOM(R,COM_VAR,YEAR,LL,C)=YES);
* commodities: COM_CUMNET/COM_CUMPRD
  COM_CUM(R,'NET',YEAR(BOHYEAR+BEOH(BOHYEAR)),LL(EOHYEAR+BEOH(EOHYEAR)),C,L) $= COM_CUMNET(R,BOHYEAR,EOHYEAR,C,L);
  COM_CUM(R,'PRD',YEAR(BOHYEAR+BEOH(BOHYEAR)),LL(EOHYEAR+BEOH(EOHYEAR)),C,L) $= COM_CUMPRD(R,BOHYEAR,EOHYEAR,C,L);
  OPTION CLEAR=COM_CUMNET,CLEAR=COM_CUMPRD;
  RC_CUMCOM(R,COM_VAR,YEAR,LL(EOHYEAR),C) $= SUM(L$COM_CUM(R,COM_VAR,YEAR,LL,C,L),YES);

*-----------------------------------------------------------------------------
* determine if VAR_COMxxx needed on RHS of EQ_COM equations
*-----------------------------------------------------------------------------
* commodities aggregated by COM_AGG
    LOOP((R,T,C,COM)$COM_AGG(R,T,C,COM),RC_AGP(COM_LIM(R,C,LIM)) = YES);
    RC_AGP(R,C,BD)$(COM_TMAP(R,'DEM',C)$RC_AGP(R,C,'LO')) = NOT BDNEQ(BD);
    RC_AGP(RC,'FX')$RC_AGP(RC,'N') = YES;
    RHS_COMBAL(RTCS_VARC(R,T,C,S))$RC_AGP(R,C,'LO') = YES;
    RHS_COMPRD(RTCS_VARC(R,T,C,S))$RC_AGP(R,C,'FX') = YES;
""",
        )

    def phase_twenty(
        self: PpmainMod, dam_elast_defined: bool, obj_eq_lin: bool, pgprim: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{"RHS_COMPRD(RTCS_VARC(R,T,C,S))$DAM_ELAST(R,C,'N') = YES;" if dam_elast_defined else ""}
* commodities involved in CUM constraints
    LOOP(RC_CUMCOM(R,'NET',ALLYEAR,LL,C),
      RTC_NET(R,T,C)$((E(T) >= YEARVAL(ALLYEAR)) * (B(T) <= YEARVAL(LL))) = YES;
{"RTC_NET(R,T,C)$((M(T)+LAGT(T) > YEARVAL(ALLYEAR)) * (M(T)-LEAD(T) < YEARVAL(LL))) = YES;" if obj_eq_lin else ""}
    );
    LOOP(RC_CUMCOM(R,'PRD',ALLYEAR,LL,C),
      RTC_PRD(R,T,C)$((E(T) >= YEARVAL(ALLYEAR)) * (B(T) <= YEARVAL(LL))) = YES;
{"RTC_PRD(R,T,C)$((M(T)+LAGT(T) > YEARVAL(ALLYEAR)) * (M(T)-LEAD(T) < YEARVAL(LL))) = YES;" if obj_eq_lin else ""}
    );
* check all TS at/above COM_TSL for bounds
    RHS_COMBAL(RTCS_VARC(RTC_NET,S)) = YES;
    COM_CSTNET(R,LL--ORD(LL),C,S--ORD(S),CUR)$(COM_CSTNET(R,LL,C,S,CUR)+COM_SUBNET(R,LL,C,S,CUR)+COM_TAXNET(R,LL,C,S,CUR)) = EPS;
    LOOP((R,C,S,RDCUR(R,CUR))$COM_CSTNET(R,'0',C,S,CUR),RHS_COMBAL(RTCS_VARC(R,T,C,TS)) = YES);
    RHS_COMBAL(RTCS_VARC(R,T,C,S))$SUM((TS_MAP(R,TS,S),BD)$COM_BNDNET(R,T,C,TS,BD),ABS(COM_BNDNET(R,T,C,TS,BD)) NE INF$BDUPX(BD)) = YES;
    RHS_COMPRD(RTCS_VARC(RTC_PRD,S)) = YES;
    COM_CSTPRD(R,LL--ORD(LL),C,S--ORD(S),CUR)$(COM_CSTPRD(R,LL,C,S,CUR)+COM_SUBPRD(R,LL,C,S,CUR)+COM_TAXPRD(R,LL,C,S,CUR)) = EPS;
    LOOP((R,C,S,RDCUR(R,CUR))$COM_CSTPRD(R,'0',C,S,CUR),RHS_COMPRD(RTCS_VARC(R,T,C,TS)) = YES);
    RHS_COMPRD(RTCS_VARC(R,T,C,S))$SUM((TS_MAP(R,TS,S),BD)$COM_BNDPRD(R,T,C,TS,BD),
      (ABS(COM_BNDPRD(R,T,C,TS,BD)) NE INF) AND (COM_BNDPRD(R,T,C,TS,BD) NE NA$BDUPX(BD))) = YES;

*-----------------------------------------------------------------------------
* Storage
*-----------------------------------------------------------------------------
* Remove standard flow variables from genuine storage charge/discharge flows
  RTPCS_OUT(RTP(R,T,P),C,S)$(RPCS_VAR(R,P,C,S)$RPC_STG(R,P,C)) = YES;

* Prepare demand sifting storages
  OPTION TRACKPC < STG_SIFT; TRACKPC(RP,C)$(NOT (TOP(RP,C,'OUT')$RPC_STG(RP,C)+ACTCG(C))$RP_STG(RP))=NO;
  TRACKPC(RP,C)$PRC_NSTTS(RP,'ANNUAL')=NO;
  LOOP(TRACKPC(R,P,C),TRACKP(R,P)=YES; RPC_PKC(R,P,C)=NO; RHS_COMPRD(RTCS_VARC(R,T,C,S))=YES);
  RPC_SPG(RPC_STG(TRACKP,C))=YES; RPC_STGN(TOP(RPC_STG(RPC_SPG(RP,C)),IO))$TOP(RP,C,'IN') = (TRACKPC(RP,C) EQV IPS(IO));
  LOOP(PRC_TSL(TRACKP(RP(R,P)),TSLVL), RP_STS(RP)=NO; RP_STG(RP)=NO;
    Z=1-SUM(RPCS_VAR(RP,C,ANNUAL),2); LOOP(TOP(RPC_STG(RP,C),'IN'),IF(Z>0,RPC_LS(RP,C)=YES);Z=Z-1); RPC_LS(RP,C(ACTCG))$Z=YES;
* Levelize STG_SIFT(ACT)
    LOOP(TRACKPC(RP,C(ACTCG)),F=SUM(RLUP(R,TSLVL,TSL),ORD(TSL)-1); IF(F=0,F=Z);
      LOOP(RJLVL(J,R,TSL)$(F>=ORD(TSL)),
        LOOP(TS_GROUP(R,TSL,TS),STG_SIFT(R,T,P,C,S)$(NOT STG_SIFT(R,T,P,C,S)) $= STG_SIFT(R,T,P,C,TS)$(STOAL(R,S)=F)$RS_BELOW(R,TS,S)));
      STG_SIFT(R,T,P,C,S)$(STOAL(R,S) NE F)=0);
    ACT_TIME(RTP(R,T,P),'LO')$(ACT_TIME(RTP,'UP')=0)=0;
    ACT_TIME(RTP(R,T,P),BD)$ACT_TIME(RTP,'FX')=ACT_TIME(RTP,'FX')$BDUPX(BD));
  RPC_LS(RPC(RP,C))$RPC_LS(RP,'{pgprim}')=NO;

* Controls for flexible general storage
  RPS_STG(PRC_TS(RP_STG,TS)) = YES;
  RPS_STG(R,P,ANNUAL)$PRC_MAP(R,'STK',P) = NO;
  RP_STS(R,P)$PRC_TSL(R,P,'ANNUAL') = NO;
  LOOP(RP_STS(R,P),
    PRC_TS(RPS_PRCTS(R,P,S))$STOA(S) = YES;
    PRC_TS(R,P,ANNUAL)$PRC_MAP(R,'STK',P) = YES;
    PRC_STGTSS(PRC_STGIPS(R,P,C)) = YES;
    STG_LOSS(R,V,P,S)$STG_LOSS(R,V,P,S) = -ABS(STG_LOSS(R,V,P,S)));
  RP_STL(RP_STS(RP),TSL+1,'N')$(PRC_SGL(RP)>=ORD(TSL)) = YES;
  NCAP_AF(RTP(R,V,P),S,BD)$((NOT RPS_STG(R,P,S))$RP_STS(R,P)) = NCAP_AFS(RTP,S,BD);

* Levelization of STG_LOSS and STG_SIFT
  TRACKP(RP_STG)$(NOT RP_STS(RP_STG)) = YES;
  """,
        )

    def phase_twentyone(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Levelized UC_RHSRTS
  LOOP(T,UC_TSL(R,UC_N,SIDE,TSL)$UC_T_SUCC(R,UC_N,T)=NO);
  OPTION UC_DS < UC_TSL, R_UC < UC_DS, MREG < R_UC;
  UC_TSL(R_UC,'LHS',TSL) $= UC_DS(R_UC,TSL);
  LOOP((RJLVL(J,R(MREG),TSLVL),TSL)$(ORD(TSL)>ORD(TSLVL)),
    LOOP(TS_GROUP(R,TSLVL,TS),UC_RHSRTS(R_UC(R,UCN),T,S,L)$((NOT UC_RHSRTS(R_UC,T,S,L))$UC_DS(R_UC,TSL)) $= UC_RHSRTS(R_UC,T,TS,L)$RS_BELOW(R,TS,S)$TS_GROUP(R,TSL,S)));
  LOOP(UC_DS(R_UC(R,UCN),TSL)$SUM(UC_TS_EACH(R_UC,S),1),UC_RHSRTS(R_UC,T,S,L)$((NOT UC_TS_EACH(R_UC,S))$TS_GROUP(R,TSL,S))=0);
  UC_TS_EACH(R_UC,S) = NO; UC_ATTR(R_UC,SIDE,UC_GRPTYPE,UC_NAME(TSL)) = NO;
* Support for the obsolete
  UC_RHS(UC_N,L)$(NOT UC_RHS(UC_N,L)) $= UC_RHSS(UC_N,'ANNUAL',L);
  UC_RHSR(R,UC_N,L)$(NOT UC_RHSR(R,UC_N,L)) $= UC_RHSRS(R,UC_N,'ANNUAL',L);
* --- Set UC_R_EACH / UC_R_SUM defaults
  OPTION CLEAR=UNCD1; UNCD1(UCN)$(NOT SUM(UC_R_EACH(ALL_R,UCN),1)) = YES;
  UC_ON(R,UCN)$SUM(L$UC_RHSR(R,UCN,L),1) = YES;
  UC_ON(R,UCN)$SUM((T,L)$UC_RHSRT(R,UCN,T,L),1) = YES;
  UC_ON(R,UCN)$SUM((T,S,L)$UC_RHSRTS(R,UCN,T,S,L),1) = YES;
  UC_R_EACH(R,UCN)$(NOT UC_ON(R,UCN))=NO; UC_R_EACH(UC_ON(R,UCN))$=UNCD1(UCN);
  OPTION CLEAR=UNCD1; UNCD1(UCN)$(NOT SUM(UC_R_SUM(ALL_R,UCN),1)) = YES;
  UC_DT(R,UCN)$SUM(L$UC_RHS(UCN,L),1) = YES;
  UC_DT(R,UCN)$SUM((T,L)$UC_RHST(UCN,T,L),1) = YES;
  UC_DT(R,UCN)$SUM((T,S,L)$UC_RHSTS(UCN,T,S,L),1) = YES;
  UC_R_SUM(R,UCN)$(NOT UC_DT(R,UCN))=NO; UC_R_SUM(UC_DT(R,UCN))$=UNCD1(UCN);
  OPTION CLEAR=UC_DT,UC_ON<UC_R_EACH; UC_ON(UC_R_SUM)=YES;
* --- Set UC_TS_EACH / UC_TS_SUM defaults
  UC_DT(UC_R_SUM(R,UC_N))$((NOT SUM(UC_TS_SUM(R,UC_N,S),1))$(NOT SUM(UC_TS_EACH(R,UC_N,S),1))) = YES;
  UC_TS_EACH(UC_DT(R,UC_N),ANNUAL)$SUM(L$UC_RHS(UC_N,L),1) = YES;
  UC_TS_EACH(UC_DT(R,UC_N),S)$SUM((T,L)$UC_RHSTS(UC_N,T,S,L),1) = YES;
  UC_TS_SUM(UC_DT(R,UC_N),ANNUAL)$SUM((T,L)$UC_RHST(UC_N,T,L),1) = YES;
  UC_DT(UC_R_SUM)$(NOT UC_R_EACH(UC_R_SUM)) = NO;
  UC_DT(UC_R_EACH(R,UC_N))$((NOT SUM(UC_TS_SUM(R,UC_N,S),1))$(NOT SUM(UC_TS_EACH(R,UC_N,S),1))) = YES;
  UC_TS_SUM(UC_DT,ANNUAL)$SUM((T,L)$UC_RHSRT(UC_DT,T,L),1) = YES;
  UC_TS_EACH(UC_DT,ANNUAL)$SUM(L$UC_RHSR(UC_DT,L),1) = YES; UC_DT(R_UC) = NO;
  UC_TS_EACH(UC_DT,S)$SUM((T,L)$UC_RHSRTS(UC_DT,T,S,L),1) = YES;
* --- Set UC_T_EACH / UC_T_SUM defaults
* Assume T_EACH and T_SUCC cannot be used at the same time; Let T_SUCC override T_EACH.
* First, copy T_SUCC to T_EACH to reduce testing in what follows:
  UC_T_EACH(UC_T_SUCC) = YES; OPTION UC_DT < UC_ON;
  UC_DT(UC_DT)$SUM(UC_T_EACH(UC_DT,T),1) = NO; UC_DT(UC_DT)$SUM(UC_T_SUM(UC_DT,T),1) = NO;
  UC_T_SUM(UC_R_SUM(UC_DT(R,UC_N)),T)$SUM(L$UC_RHS(UC_N,L),1) = YES;
  UC_T_SUM(UC_R_EACH(UC_DT),T)$SUM(L$UC_RHSR(UC_DT,L),1) = YES;
  UC_T_EACH(UC_DT,T)$(NOT UC_T_SUM(UC_DT,T)) = YES;

* Defaults for cumulative UCs
  OPTION CLEAR=MREG,CLEAR=UC_DT;
  LOOP(T,UC_DT(R,UC_N)$(UC_TS_EACH(R,UC_N,'ANNUAL')$UC_T_SUM(R,UC_N,T)) = YES);
  UC_TS_SUM(UC_DT,ANNUAL) = YES; UC_TS_EACH(UC_TS_SUM(R,UC_N,ANNUAL)) = NO;
  UC_DT(R_UC)$UC_DS(R_UC,'ANNUAL') = NO;
  UC_ATTR(UC_DT,SIDE,UC_GRPTYPE,'PERIOD')$(NOT SAMEAS(UC_GRPTYPE,'NCAP')) = NO;

  UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,UC_COST) $= SUM(UC_MAPCOST(UC_COST,UC_NAME),UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,UC_NAME));
* If the GROWTH attribute is specified, substitute T_SUCC for T_EACH:
  LOOP(UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,'GROWTH'),UC_DYNDIR(R,UC_N,SIDE) = YES);
* Prepare for the CUMSUM UC attribute. Supported only for UCs with RHS dyndir:
  UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,'PERIOD')$UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,'CUMSUM') = NOT UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,'ANNUL');
  UC_ATTR(R,UC_N,SIDE,'NCAP','CUMSUM')$UC_ATTR(R,UC_N,SIDE,'NCAP','ANNUL') = YES;
  UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'CUM+')$(UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'SYNC')$UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'CUMSUM')) = YES;
  UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'CUMSUM')$UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'CUM+') = NO;
* Set all UCs that have RHS attributes to be dynamic, if not already so defined
  OPTION CLEAR=RXX; LOOP(UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,UC_NAME),RXX(R,UC_N,'RHS') = YES);
  LOOP(T,RXX(R,UC_N,'RHS')$UC_T_SUCC(R,UC_N,T) = NO); UC_DYNDIR(RXX(R,UC_N,'RHS')) = YES;
  LOOP(UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,UC_DYNT),UC_DYNDIR(R,UC_N,'RHS') = YES);
  UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'N')$UC_ATTR(R,UC_N,'RHS',UC_GRPTYPE,'SYNC') = YES;
* Remove RHS from DYNDIR if LHS present:
  UC_DYNDIR(R,UC_N,'RHS')$UC_DYNDIR(R,UC_N,'LHS') = NO;
  UC_TSL(UC_DYNDIR(R_UC,'RHS'),TSL)$UC_DS(R_UC,TSL)=YES; UC_DYNDIR(R_UC,SIDE)=NO;
* Add implicit T_SUCC and remove T_EACH whenever T_SUCC
  UC_T_SUCC(UC_T_EACH(R,UCN,T)) $= SUM(UC_DYNDIR(R,UCN,SIDE),1);
  UC_T_SUCC(UC_T_EACH(R,UCN,T))$UC_R_SUM(R,UCN) $= SUM(UC_T_SUCC(UC_R_SUM(REG,UCN),T),1);
  UC_T_EACH(UC_T_SUCC) = NO;
* Remove last MILESTONYR from UC_T_SUCC unless RHS-based:
  UC_T_SUCC(UC_T_SUCC(R,UC_N,T))$(ORD(T) = CARD(T)) = UC_DYNDIR(R,UC_N,'RHS');
  RS_PREV(R,S,S--RS_STG(R,S)) $= RS_TSLVL(R,S); G_UDS(S,'LHS',S) = YES;
  LOOP(R$SUM(UC_TSL(R,UCN,'RHS',TSL),1),G_UDS(S,'RHS',TS)$RS_PREV(R,S,TS)=YES);
""",
        )

    def phase_twentytwo(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* FLO / IRE / COM
  OPTION UC_MAP_FLO < UC_FLO;
  UC_QAFLO('1',UC_MAP_FLO(UCN,SIDE,RP_IRE(R,P),C))=YES;
  UC_CAPFLO(UC_N,SIDE,R,P,C)$(NOT UC_MAP_FLO(UC_N,SIDE,R,P,C)) = NO;
  UC_MAP_FLO(UC_N,SIDE,RP_IRE,C) = NO;
  OPTION UC_MAP_IRE < UC_IRE;
  UC_QAFLO('2',UCN,'LHS',RP_FLO,C)$=SUM(UC_MAP_IRE(UCN,RP_FLO,C,IE),1);
  UC_MAP_IRE(UC_N,R,P,C,IE)$(NOT RPC_IRE(R,P,C,IE)) = NO;
  OPTION UC_GMAP_C < UC_COM;
  UC_ATTR(R,UCN,SIDE,UC_GRPTYPE,UC_DYNT)$UC_ATTR(R,UCN,SIDE,'COMCON',UC_DYNT)$=SUM(UC_GMAP_C(R,UCN,COM_VAR,C,'COMCON')$COV_MAP(COM_VAR,UC_GRPTYPE),1);

* ACT / CAP / NCAP
  UC_JMAP('2',UCN,SIDE,R,T--ORD(T),P,'ACT')$UC_ON(R,UCN)  $= SUM(S$UC_ACT(UCN,SIDE,R,T,P,S),1);
  UC_JMAP('3',UCN,SIDE,R,T--ORD(T),P,'CAP')$UC_ON(R,UCN)  $= UC_CAP(UCN,SIDE,R,T,P);
  UC_JMAP('4',UCN,SIDE,R,T--ORD(T),P,'NCAP')$UC_ON(R,UCN) $= UC_NCAP(UCN,SIDE,R,T,P);
  OPTION UC_GMAP_P < UC_JMAP;

* Mark those processes that have UC_CAP / COMXXX to also have VAR_CAP / VAR_COMXXX
  LOOP(UC_GMAP_P(R,UCN,'CAP',P),TRACKP(R,P)=YES);
  RTP_VARP(RTP(R,T,P))$TRACKP(R,P) = YES;
  OPTION CLEAR=TRACKP,CLEAR=RXX,CLEAR=UC_JMAP;
  UC_ON(R,UCN) $= SUM(UC_DYNBND(UCN,L),1);
  LOOP(UC_GMAP_C(UC_ON(R,UC_N),COM_VAR,C,UC_GRPTYPE),RXX(R,COM_VAR,C)=YES);
  RHS_COMPRD(RTCS_VARC(R,T,C,S))$RXX(R,'PRD',C) = YES;
  RXX(R,'NET',C)$COM_LIM(R,C,'FX')=NO;
  RXX(R,'PRD',C)$(NOT COM_LIM(R,C,'LO'))=NO;
  LOOP(COM_VAR,RHS_COMBAL(RTCS_VARC(R,T,C,S))$RXX(R,COM_VAR,C) = YES);
""",
        )

    def phase_twentythree(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* for each refined product determine SPEcifications used from TYPE since required
BLE_SPE(R,COM,SPE)$BL_TYPE(R,COM,SPE) = YES;

******************************************************************************
*  do initialization for BLENDing (interpolation in preppm.mod)
******************************************************************************
REFUNIT(R)$(NOT REFUNIT(R)) = 1;

* initialize defaults START period and UNIT type
LOOP(BLE_SPE(R,BLE,SPE),
  BLE_TP(R,T,BLE)$(YEARVAL(T) >= BL_START(R,BLE,SPE)) = YES
);
BL_UNIT(BLE_SPE(R,BLE,SPE))$(NOT BL_UNIT(R,BLE,SPE)) = 1;

*** ONLY TID FOR NOW ***
* set time-dependent blending SPEcificiation from TID if not provided
*TBL_SPEC(BLE_SPE(BLE,SPE),TP)$(BL_SPEC(BLE,SPE) AND (NOT TBL_SPEC(BLE,SPE,TP))) =
*         BL_SPEC(BLE,SPE);
** set time-dependent 3-tuple
BLE_SPEOPR(BLE_SPE(R,BLE,SPE),OPR)$BL_COM(R,BLE,OPR,SPE) = YES;
*BLE_SPEOPR(BLE,SPE,OPR)$(BL_COM(BLE,OPR,SPE) OR
*                                  SUM(YEAR,TBL_COM(BLE,SPE,OPR,YEAR))) = YES;
*TBL_COM(BLE_SPEOPR(BLE,SPE,OPR),TP)$(BL_COM(BLE,OPR,SPE) AND
*                 (NOT TBL_COM(BLE,SPE,OPR,TP))) = BL_COM(BLE,OPR,SPE);
*
** assumed BLEND INP not SPE dependent, and that values are to be summed for BLE
*BLE_INP(BLE,COM)$(BL_INP(BLE,COM) OR SUM((SPE,YEAR),TBL_INP(BLE,SPE,COM,YEAR)))
*                = YES;
BLE_SPEINP(R,BLE,SPE,COM)$(BLE_SPE(R,BLE,SPE) * BLE_INP(R,BLE,COM)) = YES;
**TBL_INP(BLE_SPE(BLE,SPE),COM,TP) = BL_INP(BLE,COM) + TBL_INP(BLE,SPE,COM,TP);
*TBL_INPT(BLE_INP(BLE,ELC),TP) = BL_INP(BLE,ELC) +
*                                SUM(BLE_SPE(BLE,SPE), TBL_INP(BLE,SPE,ELC,TP));
*
**  assume that values are to be summed
*TBL_VAROMT(BLE,TP) = BL_VAROM(BLE) + SUM(BLE_SPE(BLE,SPE), TBL_VAROM(BLE,SPE,TP));
*
**  DELIV assume that values are to be summed
*TBL_DELIV(BLE_SPE(BLE,SPE),COM,TP) = BL_DELIV(BLE,COM) +
*                                     TBL_DELIV(BLE,SPE,COM,TP);
*TBL_DELIVT(BLE,COM,TP) =  SUM(SPE$BLE_SPE(BLE,SPE),
*                          TBL_INP(BLE,SPE,COM,TP) * TBL_DELIV(BLE,SPE,COM,TP));
*
** setup BLE/OPR combination and handle the emissions
LOOP(BLE_SPEOPR(R,BLE,SPE,OPR),
  BLE_OPR(R,BLE,OPR) = YES;
);
LOOP(BLE_OPR(R,BLE,OPR),
  BLE_ENV(R,C,BLE,OPR)$(ENV(R,C) * SUM(T, ENV_BL(R,C,BLE,OPR,T))) = YES;
);

* handle peakda, setting to 1 if uses COM_PEAK but no value provided
PEAKDA_BL(R,BLE,T)$((NOT PEAKDA_BL(R,BLE,T))$SUM(COM_PEAK(R,C)$BLE_INP(R,BLE,C),1)) = 1;
""",
        )

    def phase_twentyfour(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* balance of energy carriers
  BLE_BAL(BLE_TP(R,T,BLE),OPR2)$OPR(BLE) = 1;
  BLE_BAL(BLE_TP(R,T,BLE),OPR2)$(NOT OPR(BLE)) = 1$(REFUNIT(R)=1) +
                                                 CONVERT(OPR2,'WCV')$(REFUNIT(R)=2) +
                                                 CONVERT(OPR2,'VCV')$(REFUNIT(R)=3);

* create the REFUNIT/BL_UNIT and FEQ convert look-up tables
* volume
LOOP(R,
IF (REFUNIT(R) = 3,
  RU_CVT(BLE_SPEOPR(R,BLE,SPE,OPR)) = 1$(BL_UNIT(R,BLE,SPE) = 3) +
                                        CONVERT(OPR,'DENS')$(BL_UNIT(R,BLE,SPE) = 2) +
                                        CONVERT(OPR,'VCV')$(BL_UNIT(R,BLE,SPE) = 1);
  RU_FEQ(R,OPR,T) = CONVERT(OPR,'VCV');
);
* weight
IF (REFUNIT(R) = 2,
  RU_CVT(BLE_SPEOPR(R,BLE,SPE,OPR)) =
                                (1/CONVERT(OPR,'DENS'))$(BL_UNIT(R,BLE,SPE) = 3) +
                                1$(BL_UNIT(R,BLE,SPE) = 2) +
                                CONVERT(OPR,'WCV')$(BL_UNIT(R,BLE,SPE) = 1);
  RU_FEQ(R,OPR,T) = CONVERT(OPR,'WCV');
);
* energy
IF (REFUNIT(R) = 1,
  RU_CVT(BLE_SPEOPR(R,BLE,SPE,OPR)) =
                                (1/CONVERT(OPR,'VCV'))$(BL_UNIT(R,BLE,SPE) = 3) +
                                (1/CONVERT(OPR,'WCV'))$(BL_UNIT(R,BLE,SPE) = 2) +
                                1$(BL_UNIT(R,BLE,SPE) = 1);
  RU_FEQ(R,OPR,T) = 1;
));
RU_FEQ(R,OPR,T)$(NOT RU_FEQ(R,OPR,T)) = 1;


*----------------------------------------------------------------
* Call reduction algorithm and determine vintaging for processes
*----------------------------------------------------------------
   OPTION RVP < RTP_CPTYR;
   RTP_VARA(R,T,P)$(NOT RVP(R,T,P)) = NO;
""",
        )

    def phase_twentyfive(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
   RTPCS_VARF(RTPC(RTP_VARA(R,T,P),C),S)$((NOT RTPCS_OUT(R,T,P,C,S))$RPCS_VAR(R,P,C,S)) = YES;

*  vintaging period control such that v=t if no vintaging, otherwise = CPT periods
*  always variables within availability of process (vintaging should imply capacity)
*  PRC_VINT(PRC_VINT(RP)) = PRC_CAP(RP);
   RTP_VINTYR(RTP_CPTYR(R,V,T,P))$PRC_VINT(R,P)= YES;
   RTP_VINTYR(R,T,T,P)$((NOT PRC_VINT(R,P))*RTP(R,T,P)$RVP(R,T,P)) = YES;

   OPTION CLEAR=R_UC,CLEAR=RVP,CLEAR=RTPCS_OUT;
""",
        )

    def phase_twenty_six(self: PpmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
    PUTCLOSE QLOG;
    IF(PUTOUT, QLOG.AP = 1);
""",
        )
