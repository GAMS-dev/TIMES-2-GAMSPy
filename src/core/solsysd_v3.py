# solsysd_v3.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * SOLSYSD.V3 - define system label mappings
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolsysdV3(GamsClass):
    """Translation unit for solsysd.v3."""

    module_name: str = "solsysd_v3"
    gams_source: str = "solsysd.v3"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        mode: str,
        map: bool,
        base_name: str = "",
        index_block: str = "",
        extra_index: str = "",
        suffix: str = "",
        symbol_prefixes: Sequence[str] | None = None,
        set_name: str = "SYSUC",
        set_prefix: str = "",
        labels: Sequence[str] | None = None,
    ):
        self.env = env.fork()
        self.tc = tc
        self.mode = mode
        self.base_name = base_name
        self.index_block = index_block
        self.extra_index = extra_index
        self.suffix = suffix
        self.symbol_prefixes = list(symbol_prefixes or [])
        self.set_name = set_name
        self.map = map
        self.set_prefix = set_prefix
        self.labels = list(labels or [])
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.mode == "SYSUC":
            code = self._build_sysuc_block()
        elif self.mode == "SYMBOL":
            code = self._build_symbol_block()
        else:
            raise ValueError(f"Unknown mode for SolsysdV3: {self.mode}")

        if code:
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=code,
            )
            # TODO: The next line is in place only because this file has not been translated yet. Once done, this should be removed.
            self.tc.sysuc = self.tc.container["SYSUC"]  # type: ignore
            if self.mode == "SYSUC" and self.map:
                self.tc.Sysucmap = self.tc.container["SYSUCMAP"]  # type: ignore

    def _build_sysuc_block(self) -> str:
        set_entries: list[str] = []
        map_entries: list[str] = []

        for label in self.labels:
            if label == "":
                continue

            set_entries.append(f"{self.set_prefix}{label} '{label}'")
            map_entries.append(f"{self.set_prefix}{label}.{label}")

        if not set_entries:
            return ""

        return rf"""
$onMulti
 SET {self.set_name} / {", ".join(set_entries)} /

 {f"SET {self.set_name}MAP({self.set_name},*) / {', '.join(map_entries)} /" if self.map else ""}

 ;
$offMulti
"""

    def _build_symbol_block(self) -> str:
        blocks: list[str] = []

        for sym_prefix in self.symbol_prefixes:
            symbol_name = f"{sym_prefix}{self.base_name}"
            if not self.tc.defined(symbol_name):
                continue

            blocks.append(
                rf"""{symbol_name}({self.index_block}{self.extra_index}SYSUC{self.suffix})$=SUM(SYSUCMAP(SYSUC,U2),{symbol_name}({self.index_block}{self.extra_index}U2{self.suffix}));
{symbol_name}({self.index_block}{self.extra_index}U2{self.suffix})$(NOT SYSUC(U2))=0;"""
            )

        return "\n".join(blocks) + ("\n" if blocks else "")
