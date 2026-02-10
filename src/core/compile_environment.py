import copy
import logging
from typing import Any, Literal

# Setup a specific logger for GAMS environment issues
gams_logger = logging.getLogger("gams_env")


class GamsString(str):
    """
    A string that behaves like a GAMS macro.
    Evaluates to False if it matches specific 'negative' values.
    """

    def __bool__(self):
        # Define your "Falsy" values here
        # Usually: empty string, 'N', 'NO', or undefined macro names
        falsy_values = ["", "N", "NO", "0"]

        # Check if the string itself or its content (if it's a %macro%) is falsy
        normalized = self.upper()
        if normalized in falsy_values:
            return False

        # Also return False if it looks like an undefined macro: "%VAR%"
        if normalized.startswith("%") and normalized.endswith("%"):
            return False

        return True


class CompileEnvironment:
    scopes = Literal["local", "global", "scoped"]

    def __init__(self, globals_dict=None):
        # Global: Reference to a shared dictionary ($setglobal)
        self._globals = globals_dict if globals_dict is not None else {}
        # Scoped: Inherited by children, but isolated ($set)
        self._scoped = {}
        # Local: Specific to THIS file only ($setlocal)
        self._local = {}

    def set_global(self, key, value):
        self._globals[str(key)] = value

    def set_scoped(self, key, value):
        self._scoped[str(key)] = value

    def set_local(self, key, value):
        self._local[str(key)] = value

    def get(self, key):
        key = str(key)
        # GAMS Priority: Local -> Scoped -> Global
        if key in self._local:
            return self._local[key]
        if key in self._scoped:
            return self._scoped[key]
        return self._globals.get(key)

    def fork(self):
        """
        Used in every __init__ of a class. The fork is passed down to children.
        1. Shares Globals.
        2. Copies Scoped (so child can modify without affecting parent).
        3. Local is reset (child doesn't see parent's $setlocal).
        """
        new_env = CompileEnvironment(self._globals)
        new_env._scoped = copy.deepcopy(self._scoped)
        new_env._local = {}

        return new_env

    def is_set(self, key: str) -> bool:
        """
        Mimics GAMS '$IF set [variable]'.
        Checks Local, then Scoped, then Global.
        """
        key = str(key)
        return key in self._local or key in self._scoped or key in self._globals

    def set_if_not_exists(self, key: str, value: Any, scope: scopes):
        """
        Mimics '$IF NOT set VAL $SET VAL 100'.
        """
        if not self.is_set(key):
            if scope == "global":
                self.set_global(key, value)
            elif scope == "local":
                self.set_local(key, value)
            else:
                self.set_scoped(key, value)
            return True
        return False

    def __getattr__(self, name):
        """Allows direct env.var access during compile time with a warning fallback."""
        val = self.get(name)
        if val is None:
            gams_logger.debug(f"GAMS macro '%{name}%' undefined. Returning '%{name}%'.")
            return GamsString(f"%{name}%")
        return GamsString(val)
