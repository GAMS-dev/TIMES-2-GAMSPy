from __future__ import annotations

import copy
import logging
from typing import Any, Literal

import pandas as pd

# Setup a specific logger for GAMS environment issues
gams_logger = logging.getLogger("gams_env")

ScopeType = Literal["local", "global", "scoped"]


class CompileEnvironment:
    def __init__(self, globals_dict: dict[str, Any] | None = None) -> None:
        # Global: Reference to a shared dictionary ($setglobal)
        self._globals: dict[str, str] = globals_dict if globals_dict is not None else {}
        # Scoped: Inherited by children, but isolated ($set)
        self._scoped: dict[str, str] = {}
        # Local: Specific to THIS file only ($setlocal)
        self._local: dict[str, str] = {}

    def set_global(self, key: str, value: str) -> None:
        self._globals[key] = value

    def set_scoped(self, key: str, value: str) -> None:
        self._scoped[key] = value

    def set_local(self, key: str, value: str) -> None:
        self._local[key] = value

    def drop_local(self, key: str) -> bool:
        """
        Removes a local compile-time variable ($setlocal).

        Returns True if the local variable existed and was removed,
        otherwise False.
        """
        key = str(key)
        if key in self._local:
            del self._local[key]
            return True
        return False

    def get(self, key: str) -> str | None:
        # GAMS Priority: Local -> Scoped -> Global
        if key in self._local:
            return self._local[key]
        if key in self._scoped:
            return self._scoped[key]
        return self._globals.get(key)

    def fork(self) -> CompileEnvironment:
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
        if key in self._local:
            val = self._local[key]
        elif key in self._scoped:
            val = self._scoped[key]
        elif key in self._globals:
            val = self._globals[key]
        else:
            return False

        # Return False if value is %key%
        if isinstance(val, str) and val.startswith("%") and val.endswith("%"):
            if val.upper() == f"%{key}%":
                return False

        return True

    def is_set_local(self, key: str) -> bool:
        """
        Mimics GAMS '$IF SETLOCAL [variable]'.
        Checks only the Local
        """
        key = str(key)
        val = self._local[key]

        if val is None:
            return False

        # Return False if value is %key%
        if isinstance(val, str) and val.startswith("%") and val.endswith("%"):
            if val.upper() == f"%{key}%":
                return False

        return True

    def is_set_global(self, key: str) -> bool:
        """
        Mimics GAMS '$IF SETGLOBAL [variable]'.
        Checks only the Global.
        """
        key = str(key)
        val = self._globals[key]

        if val is None:
            return False

        # Return False if value is %key%
        if isinstance(val, str) and val.startswith("%") and val.endswith("%"):
            if val.upper() == f"%{key}%":
                return False

        return True

    def set_if_not_exists(self, key: str, value: str, scope: ScopeType) -> bool:
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

    def __getattr__(self, name: str) -> str:
        """Allows direct env.var access during compile time with a warning fallback."""
        val = self.get(name)
        # Fallback for undefined compile time variables
        if val is None:
            gams_logger.debug(f"GAMS macro '%{name}%' undefined. Returning '%{name}%'.")
            return f"%{name}%"
        return val

    def get_test_state(self) -> pd.DataFrame:
        """Returns the current state of variables categorized by scope."""
        data = []
        scopes = {"GLOBAL": self._globals, "SCOPED": self._scoped, "LOCAL": self._local}

        for scope_name, var_dict in scopes.items():
            for name, val in var_dict.items():
                data.append({"name": name, "scope": scope_name, "value": val})
        return pd.DataFrame(data)
