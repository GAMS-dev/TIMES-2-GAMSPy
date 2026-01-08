# times_model_class.py
#   - 1 Python file per original GAMS file.
#   - Each file exports ONE module object: `module`
#   - Each module has three phases:
#       * initialize_preload(tc):   build/declare/compile-time-ish blocks that must run BEFORE data load
#       * initialize_postload(tc):  compile-time-ish blocks that must run AFTER central data load
#       * run(tc):                  execution-time blocks (solve, report, etc.)

import logging
from dataclasses import dataclass
from typing import List, Optional

from gamspy import Container

from .config import TimesConfig
from .interfaces import TimesModule


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

    def __init__(self, config: TimesConfig):
        self.config = config
        self.container = Container()
        self.logger = logging.getLogger("TimesModel")

        # Ordered list of registered modules
        self._modules: List[TimesModule] = []

        # Optional: collect embedded code for debugging / traceability
        self._gams_chunks: List[GamsCodeChunk] = []

    def register_module(self, module: TimesModule) -> None:
        """Register a module object."""
        if not isinstance(module, TimesModule):
            raise TypeError(
                f"Object {module} does not implement the required TIMES interface."
            )
        self._modules.append(module)

    # -----------------------
    # Code embedding helpers
    # -----------------------
    def add_gams_code(
        self,
        *,
        module_name: str,
        phase: str,
        gams_source: str,
        code: str,
        batinclude_args: Optional[List[str]] = None,
    ) -> None:
        """
        Add raw GAMS code into the Container with a traceable header.

        In GAMS, $BATINCLUDE does compile-time textual substitution (e.g., %1, %2) even if the
        included statements are execution-time. In GAMSPy, emulate such substitution by using
        tc.add_gams_code(..., batinclude_args=[...]) when needed. This is a *string
        substitution* helper on the Python side.
        """
        if batinclude_args:
            for i, arg in enumerate(batinclude_args, start=1):
                code = code.replace(f"%{i}", str(arg))

        header = (
            f"\n* ============================================================\n"
            f"* {module_name} :: {phase}\n"
            f"* source: {gams_source}\n"
            f"* ============================================================\n"
        )

        self.container.addGamsCode(header + code)
        self._gams_chunks.append(GamsCodeChunk(module_name, phase, gams_source, code))

    def dump_generated_gams(self, path: str = "generated_times.gms") -> None:
        """
        Write the currently generated GAMS code to a file for inspection.
        """
        gms = self.container.generateGamsString()
        with open(path, "w", encoding="utf-8") as f:
            f.write(gms)

    # -----------------------
    # Orchestration phases
    # -----------------------
    def initialize_preload(self) -> None:
        """Pre-load phase (declarations that must exist before data load)."""
        self.logger.info("Phase: initialize_preload (before data load)")
        for mod in self._modules:
            mod.initialize_preload(self)

    def initialize_postload(self) -> None:
        """Post-load compile-like phase."""
        self.logger.info("Phase: initialize_postload (after data load)")
        for mod in self._modules:
            mod.initialize_postload(self)

    def run(self) -> None:
        """Execution phase (preprocessing / solve / reporting / etc.)."""
        self.logger.info("Phase: run")
        for mod in self._modules:
            mod.run(self)
