# src/core/base_class.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass


class GamsClass(ABC):
    module_name: str
    gams_source: str

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment) -> None:
        self.env: CompileEnvironment = env.fork()
        self.tc: TimesModelClass = tc
        self._sub_modules: dict[str, GamsClass] = {}  # Dict containing sub modules

    def include(self, module_instance: GamsClass) -> None:
        """
        Mimics $include or $batinclude.
        Registers the child so it can be executed later in the 'run' phase.
        """
        self._sub_modules[module_instance.module_name] = module_instance

    def add_records_to_universe_item(self, records: list[str]) -> None:
        """
        ITEM is a UniverseSet
        GAMSPy does not support adding records to UniverseSet


        Example:
            SET ITEM / OBJ /;
            add_records_to_universe_item(records=['OBJ'])
        """
        dummy = self.tc.intdefault
        for uel in records:
            dummy[uel].where[False] = False  # type: ignore[index]

    @abstractmethod
    def compile(self) -> None:
        """Must be implemented by every translated module."""
