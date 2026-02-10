# src/core/base_class.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List

from gamspy import Set

from .utils import expand_set

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass


class GamsClass(ABC):
    def __init__(self, tc: "TimesModelClass", env: "CompileEnvironment") -> None:
        self.env: CompileEnvironment = env.fork()
        self.snapshot: Dict[str, Any] = self.env.snapshot()
        self._sub_modules: Dict[str, GamsClass] = {}  # Dict containing sub modules

    def include(self, module_instance: GamsClass) -> None:
        """
        Mimics $include or $batinclude.
        Registers the child so it can be executed later in the 'run' phase.
        """
        self._sub_modules[module_instance.module_name] = module_instance

    def add_records_to_universe_item(
        self, tc: "TimesModelClass", records: List
    ) -> None:
        """
        ITEM is a UniverseSet
        GAMSPy does not support adding records to UniverseSet
        We use ITEMADD as a workaround

        If symbol ITEMADD exists, existing records are merged with new records.
        If symbol ITEMADD does not exist, it will be created with given records.

        Example:
            SET ITEM / OBJ /;

            add_records_to_universe_item(records=['OBJ'])
        """
        if "ITEMADD" in tc.container.listSymbols():
            itemadd = tc.container["ITEMADD"]
            expand_set(itemadd, records)
        else:
            Set(tc.container, name="ITEMADD", records=records)

    @abstractmethod
    def compile(self, tc: "TimesModelClass") -> None:
        """Must be implemented by every translated module."""
        pass
