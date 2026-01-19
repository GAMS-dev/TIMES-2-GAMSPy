# src/core/base_class.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass


class GamsClass(ABC):
    def __init__(self, tc: TimesModelClass, env: CompileEnvironment) -> None:
        self.env: CompileEnvironment = env.fork()
        self.snapshot: Dict[str, Any] = self.env.snapshot()
        self._sub_modules: Dict[str, GamsClass] = {}  # Dict containing sub modules

    def include(self, module_instance: GamsClass) -> None:
        """
        Mimics $include or $batinclude.
        Registers the child so it can be executed later in the 'run' phase.
        """
        self._sub_modules[module_instance.module_name] = module_instance

    @abstractmethod
    def compile(self, tc: TimesModelClass) -> None:
        """Must be implemented by every translated module."""
        pass

    @abstractmethod
    def run(self, tc: TimesModelClass) -> None:
        """Must be implemented by every translated module."""
        pass
