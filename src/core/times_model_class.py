# times_model_class.py

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List

from gamspy import Container

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment


@dataclass(frozen=True)
class GamsCodeChunk:
    module_name: str
    phase: str
    gams_source: str
    code: str


class TimesModelClass:
    """
    Central orchestrator / shared state ("tc") for the TIMES model embedding workflow.
    """

    def __init__(
        self,
        env: "CompileEnvironment",
        output_compile: Path,
        output_execute: Path,
        test: bool,
    ):
        self.env = env
        self.execution_list = []
        self.output_compile = output_compile
        self.output_execute = output_execute
        self.test_run = test
        self.compile_states = {}
        # self.container = Container(debugging_level="keep")
        self.container = Container()
        self.logger = logging.getLogger("TimesModel")

        # Ordered list of registered modules
        self._modules: List[GamsClass] = []

        # Optional: collect embedded code for debugging / traceability
        self._gams_chunks: List[GamsCodeChunk] = []

    def register_module(self, module: GamsClass) -> None:
        """Register a module object."""
        if not isinstance(module, GamsClass):
            raise TypeError(
                f"Object {module} does not implement the required TIMES interface."
            )
        self._modules.append(module)

    # -----------------------
    # Code embedding helpers
    # -----------------------
    def add_gams_code(
        self,
        module: GamsClass,
        phase: str,
        code: str,
    ) -> None:
        """
        Add raw GAMS code into the Container with a traceable header.
        """

        header = (
            f"\n* ============================================================\n"
            f"* {module.module_name} :: {phase}\n"
            f"* source: {module.gams_source}\n"
            f"* ============================================================\n"
        )

        self.container.addGamsCode(header + code)
        self._gams_chunks.append(
            GamsCodeChunk(module.module_name, phase, module.gams_source, code)
        )

    def dump_generated_gams(self, path: str = "generated_times.gms") -> None:
        """
        Write the currently generated GAMS code to a file for inspection.
        """
        gms = self.container.generateGamsString()
        with open(path, "w", encoding="utf-8") as f:
            f.write(gms)

    def save_test_state(self, env, checkpoint):
        """
        Saves the state of all compile time variables for later testing.

        :param self: Description
        :param env: Description
        :param checkpoint: name of the checkpoint
        """
        state = env.get_test_state()
        self.compile_states[checkpoint] = state

    # -----------------------
    # Orchestration phases
    # -----------------------
    def initialization(self) -> None:
        """Modules are initialized / compiled within their __init__ method. Only used to write GDX state after compilation."""
        # self.container.write(self.output_compile, eps_to_zero=False)
        self.container.addGamsCode(f"execute_unload '{self.output_compile}';")

    def enqueue(self, func, *args, **kwargs):
        """Adds a function call to the end of the execution queue."""
        self.execution_list.append((func, args, kwargs))

    def run(self):
        """Executes all queued functions in order."""
        self.logger.info("Phase: run")
        for func, args, kwargs in self.execution_list:
            func(*args, **kwargs)
        # self.container.write(self.output_execute, eps_to_zero=False)
        self.container.addGamsCode(f"execute_unload '{self.output_execute}';")

    # -----------------------
    # Utils
    # -----------------------
    def defined(self, symbol) -> bool:
        return symbol.upper() in self.container.listSymbols() and (
            self.container[symbol.upper()].number_records > 0
        )
