from __future__ import annotations

import logging
from typing import Any, Literal

import pandas as pd
from pydantic import TypeAdapter, ValidationError

from utils.config import EnvironmentVariableSchema

# Setup a specific logger for GAMS environment issues
gams_logger = logging.getLogger(__name__)

ScopeType = Literal["local", "global", "scoped"]


class CompileEnvironment:
    def __init__(self, globals_dict: dict[str, Any] | None = None) -> None:
        # Global: Reference to a shared dictionary ($setglobal)
        self._globals: dict[str, Any] = globals_dict if globals_dict is not None else {}
        # Scoped: Inherited by children, but isolated ($set)
        self._scoped: dict[str, Any] = {}
        # Local: Specific to THIS file only ($setlocal)
        self._local: dict[str, Any] = {}

    def _validate_assignment(self, key: str, value: Any) -> None:
        """Validates incoming key/value pairs, checking both python names and Pydantic aliases."""
        target_field = None

        # Look for a direct match OR an alias match
        for field_name, field_info in EnvironmentVariableSchema.model_fields.items():
            if key == field_name or key == field_info.alias:
                target_field = field_info
                break

        # If a matching field/alias is found, validate its type
        if target_field is not None:
            expected_type = target_field.annotation
            try:
                TypeAdapter(
                    expected_type, config={"arbitrary_types_allowed": True}
                ).validate_python(value)
            except ValidationError as e:
                gams_logger.error(
                    f"Type validation failed for environment variable '{key}': {e}"
                )
                raise
        else:
            # Handle strictly missing/undefined variables
            error_msg = f"Security/Type Risk: '{key}' is not defined in EnvironmentVariableSchema. All environment variables must be explicitly registered."
            gams_logger.error(error_msg)
            raise KeyError(error_msg)

    def set_global(self, key: str, value: Any) -> None:
        self._validate_assignment(key, value)
        self._globals[key] = value

    def set_scoped(self, key: str, value: Any) -> None:
        self._validate_assignment(key, value)
        self._scoped[key] = value

    def set_local(self, key: str, value: Any) -> None:
        self._validate_assignment(key, value)
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

    def get(self, key: str, no_local: bool = False) -> Any:
        # GAMS Priority: Local -> Scoped -> Global
        if key in self._local and not no_local:
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
        new_env._scoped = self._scoped.copy()
        new_env._local = {}

        return new_env

    def is_set(self, key: str) -> bool:
        """
        Mimics GAMS '$IF set [variable]'.
        Checks Local, then Scoped, then Global.
        """
        if key in self._local:
            val = self._local[key]
        elif key in self._scoped:
            val = self._scoped[key]
        elif key in self._globals:
            val = self._globals[key]
        else:
            return False

        # Return False if value is %key%
        return not self.is_default(key, val)

    def is_default(self, key: str, val: Any) -> bool:
        """Checks if the value is the default %<key>%"""
        return bool(
            isinstance(val, str)
            and val.startswith("%")
            and val.endswith("%")
            and val.upper() == f"%{key.upper()}%"
        )

    def is_set_local(self, key: str) -> bool:
        """
        Mimics GAMS '$IF SETLOCAL [variable]'.
        Checks only the Local
        """
        if key in self._local:
            val = self._local[key]
        else:
            return False

        # Return False if value is %key%
        return not (
            isinstance(val, str)
            and val.startswith("%")
            and val.endswith("%")
            and val.upper() == f"%{key.upper()}%"
        )

    def is_set_scoped(self, key: str) -> bool:
        """.
        Checks only the Scoped
        """
        if key in self._scoped:
            val = self._scoped[key]
        else:
            return False

        # Return False if value is %key%
        return not self.is_default(key, val)

    def is_set_global(self, key: str) -> bool:
        """
        Mimics GAMS '$IF SETGLOBAL [variable]'.
        Checks only the Global.
        """
        if key in self._globals:
            val = self._globals[key]
        else:
            return False

        # Return False if value is %key%
        return not self.is_default(key, val)

    def set_if_not_exists(self, key: str, value: Any, scope: ScopeType) -> bool:
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

    def __getattr__(self, name: str) -> Any:
        """Allows direct env.var access during compile time with a warning fallback."""
        val = self.get(name)
        # Fallback for undefined compile time variables. GAMS macro names are
        # always referenced in upper case throughout the TIMES source, so echo
        # back the upper-case form to match GAMS's own undefined-macro echo
        # (e.g. "%FIXBOH%"), not the lower-case Python attribute name.
        if val is None:
            upper_name = name.upper()
            gams_logger.debug(
                f"GAMS macro '%{upper_name}%' undefined. Returning '%{upper_name}%'."
            )
            return f"%{upper_name}%"
        return val

    def get_test_state(self) -> pd.DataFrame:
        """Returns the current state of variables categorized by scope."""
        data = []
        scopes = {"GLOBAL": self._globals, "SCOPED": self._scoped, "LOCAL": self._local}

        for scope_name, var_dict in scopes.items():
            for name, val in var_dict.items():
                data.append({"name": name, "scope": scope_name, "value": val})
        return pd.DataFrame(data)
