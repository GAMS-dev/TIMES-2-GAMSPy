# solsysd_v3.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * SOLSYSD.V3 - define system label mappings
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Parameter, Set, Sum, sparse

from core.base_class import GamsClass
from core.utils import SET_OR_ALIAS, expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class SolsysdSysucConfig:
    """$BATINCLUDE solsysd.v3 SYSUC %P2% %P3% <labels>"""

    # %P2%: EOLCOM "!" keeps SYSUCMAP, ",%" comments it out
    map: bool
    # %P3%
    set_prefix: str
    # %4 ...: one SYSUC element per label
    labels: tuple[str, ...]


@dataclass
class SolsysdSymbolConfig:
    """$BATINCLUDE solsysd.v3 %P1% ! %P3% %P4% <index prefix> ..."""

    # %P1%
    base_name: str
    # (%1, %2) pairs: leading index of the symbol, and its name prefix
    targets: tuple[tuple[tuple[SET_OR_ALIAS, ...], str], ...]
    # %P3%: index between the leading index and SYSUC
    mid_index: tuple[SET_OR_ALIAS, ...] | tuple[()] = ()
    # %P4%: index after SYSUC
    suffix_index: tuple[SET_OR_ALIAS, ...] | tuple[()] = ()


class SolsysdV3(GamsClass):
    """Translation unit for solsysd.v3."""

    module_name: str = "solsysd_v3"
    gams_source: str = "solsysd.v3"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: SolsysdSysucConfig | SolsysdSymbolConfig,
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        # $GOTO %1
        if isinstance(self.config, SolsysdSysucConfig):
            self._label_sysuc(self.config)
        elif isinstance(self.config, SolsysdSymbolConfig):
            self._label_symbol(self.config)
        else:
            raise TypeError(
                f"Unexpected config type for SolsysdV3: {type(self.config).__name__}"
            )

    def _label_sysuc(self, cc: SolsysdSysucConfig) -> None:
        g = self.tc
        m = g.container

        # (%P3%%1, %1): element + text for SYSUC, element pair for SYSUCMAP
        records = [(f"{cc.set_prefix}{label}", label) for label in cc.labels]

        # SET %P1% / %P3%%1 %1 /
        if g.sysuc is None:
            g.sysuc = Set(m, name="SYSUC", records=records)
        else:
            expand_set(g.sysuc, records)

        if not cc.map:
            return

        # %P1%MAP(%P1%,*) / %P3%%1.%1 /
        if g.Sysucmap is None:
            g.Sysucmap = Set(m, name="SYSUCMAP", domain=[g.sysuc, "*"], records=records)
        else:
            expand_set(g.Sysucmap, records)

    def _label_symbol(self, cc: SolsysdSymbolConfig) -> None:
        g = self.tc
        for index, prefix in cc.targets:
            name = f"{prefix}{cc.base_name}"
            # $IF DEFINED %2%P1%
            if not g.defined(name):
                continue
            g.enqueue(self._exec_remap, cc=cc, sym=g.get_parameter(name), index=index)

    def _exec_remap(
        self,
        cc: SolsysdSymbolConfig,
        sym: Parameter,
        index: tuple[SET_OR_ALIAS, ...],
    ) -> None:
        g = self.tc
        sysuc, u2 = g.sysuc, g.u2
        pre = [*index, *cc.mid_index]
        post = cc.suffix_index

        # %2%P1%(%1%P3%SYSUC%P4%)$=SUM(SYSUCMAP(SYSUC,U2),%2%P1%(%1%P3%U2%P4%));
        sym[*pre, sysuc, *post] = sparse(
            Sum(g.Sysucmap[sysuc, u2], sym[*pre, u2, *post])
        )
        # %2%P1%(%1%P3%U2%P4%)$(NOT SYSUC(U2))=0;
        sym[*pre, u2, *post].where[~sysuc[u2]] = 0
