# mod_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * MOD_EXT.EXT Extension equations
# * Called from MAINDRV.MOD
# *============================================================================*

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def mod_ext_vda(
    equations: list[str],
    eq: str,
    obmac: str,
    duc: str,
    solmip: str,
    powerflo: str,
    ecb: str,
    def_uc_flobet: bool,
    def_com_cstbal: bool,
    def_gr_vargen: bool,
    def_rtc_ms: bool,
    def_gg_mm: bool,
) -> None:
    """Translation unit for mod_ext.vda."""

    equations.extend(
        [
            f"{eq}E_ACTEFF",
            f"{eq}L_CAFLAC",
            f"{eq}E_CAFLAC",
            f"{eq}L_CAPFLO",
            f"{eq}_CAPLOAD",
            f"{eq}_ACTRAMP",
            f"{eq}E_ACTUPS",
            f"{eq}L_ACTUPS",
            f"{eq}L_ACTUPC",
            f"{eq}_ACTPL",
            f"{eq}_ACTRMPC",
            f"{eq}_SLSIFT",
            "EQL_STGCCL",
            f"{eq}E_UCRTP",
            f"{eq}N_UCRTP",
            f"{eq}N_UCRTC",
            f"{eq}E_ASHAR",
            f"{eq}L_ASHAR",
            f"{eq}G_ASHAR",
        ]
    )

    if obmac == "YES":
        equations.extend(
            [
                "eq_sdlogic",
                "eq_sudupt",
                "eq_sdslant",
                "eq_sdminon",
                "eq_sudload",
                "eq_sudtime",
                "eq_sudpll",
            ]
        )

    if f"{duc}{solmip}".upper() == "YESYES":
        equations.extend(["eq_sdind_1", "eq_sdind_0"])

    if def_uc_flobet:
        equations.extend([f"{eq}G_UCMAX", f"{eq}G_UCSUMAX"])

    if def_com_cstbal:
        equations.append("EQ_OBJBAL")

    if powerflo.upper() == "YES":
        equations.extend(
            [
                f"{eq}_GR_POWFLO",
                f"{eq}_GR_PTDFLO",
                f"{eq}_GR_GENALL",
                f"{eq}_GR_DEMALL",
                f"{eq}_GR_XBND",
                f"{eq}_GR_VIRTCAP",
                f"{eq}_GR_VIRTBND",
            ]
        )

    if def_gr_vargen:
        equations.extend(
            [
                f"{eq}_RL_LOAD",
                f"{eq}_RL_NDIS",
                f"{eq}_RL_STCAP",
                f"{eq}_RL_PKCAP",
                f"{eq}_RL_THMIN",
            ]
        )

    if def_rtc_ms and ecb == "YES":
        equations.extend([f"{eq}_MSNCAP", f"{eq}_MSNCAPB"])

    if def_gg_mm:
        equations.extend(
            [
                "EQ_GG_MFLO",
                "EQ_GG_GAMA",
                "EQ_GG_HLIP",
                "EQ_GG_HLEV",
                "EQ_GG_STEP",
                "EQ_GG_PRIO",
                "EQ_GG_MBND",
                "EQ_GG_PDIF1",
                "EQ_GG_PDIF2",
                "EQ_GG_WEYMST",
                "EQ_GG_WEYMTX",
            ]
        )
