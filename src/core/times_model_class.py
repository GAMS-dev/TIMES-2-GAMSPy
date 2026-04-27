# times_model_class.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Literal, ParamSpec

from gamspy import Container, Options, Set

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment

GamsPhase = Literal["init", "run"]
P = ParamSpec("P")


class TimesModelClass:
    """
    Central orchestrator / shared state ("tc") for the TIMES model embedding workflow.
    """

    r: Set
    c: Set
    cg: Set
    cg1: Set
    cg2: Set
    com: Set
    com1: Set
    com2: Set
    com_grp: Set
    cur: Set
    curr: Set
    sow: Set
    w: Set
    costagg: Set
    costcat: Set
    allyear: Set
    all_reg: Set
    all_r: Set
    all_ts: Set
    reg: Set
    item: Set
    year: Set
    ll: Set
    impexp: Set
    in_out: Set
    ie: Set
    io: Set
    lim: Set
    lim_type: Set
    bnd_type: Set
    j: Set
    jj: Set
    bd: Set
    costype: Set
    p: Set
    prc: Set
    uc_cost: Set

    def __init__(
        self,
        env: CompileEnvironment,
        output_compile: Path,
        output_execute: Path,
        test: bool,
    ):
        self.env = env
        self.execution_list: list[
            tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]
        ] = []
        self.output_compile = output_compile
        self.output_execute = output_execute
        self.test_run = test
        self.compile_states: dict[str, Any] = {}
        # self.container = Container(debugging_level="keep")
        self.container = Container()
        self._solve_options: Options
        self.logger = logging.getLogger("TimesModel")

        # Ordered list of registered modules
        self._modules: List[GamsClass] = []

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
        phase: GamsPhase,
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

    def dump_generated_gams(self, path: str = "generated_times.gms") -> None:
        """
        Write the currently generated GAMS code to a file for inspection.
        """
        gms = self.container.generateGamsString()
        with open(path, "w", encoding="utf-8") as f:
            f.write(gms)

    def save_test_state(self, env: CompileEnvironment, checkpoint: str) -> None:
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

    def enqueue(
        self, func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """Adds a function call to the end of the execution queue."""
        self.execution_list.append((func, args, kwargs))

    def run(self) -> None:
        """Executes all queued functions in order."""
        self.logger.info("Phase: run")
        for func, args, kwargs in self.execution_list:
            func(*args, **kwargs)
        # self.container.write(self.output_execute, eps_to_zero=False)
        self.container.addGamsCode(f"execute_unload '{self.output_execute}';")

    # -----------------------
    # Utils
    # -----------------------
    def defined(self, symbol: str) -> bool:
        return symbol.upper() in self.container.listSymbols() and (
            self.container[symbol.upper()].number_records > 0
        )
