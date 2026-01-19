import copy
from types import SimpleNamespace
from typing import Any, Literal


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

    def snapshot(self) -> SimpleNamespace:
        """
        Creates a static dictionary of ALL current variables.
        Will be called if variable values need to be accessed at execution time.
        If a variable is changes multiple times within a class, multiple instances of snapshot can be stored for later access at execution time.
        This mimics how GAMS substitutes values into code at compile time.
        """
        # Combine Global, Scoped, and Local into one static map
        # Priority: Globals < Scoped < Local
        current_state = {}
        current_state.update(self._globals)
        current_state.update(self._scoped)
        current_state.update(self._local)
        return SimpleNamespace(**current_state)

    def is_set(self, key: str) -> bool:
        """
        Mimics GAMS '$IF set [variable]'.
        Checks Local, then Scoped, then Global.
        """
        key = str(key)
        # Check Local
        if key in self._local:
            return True
        # Check Scoped
        if key in self._scoped:
            return True
        # Check Global
        if key in self._globals:
            return True
        return False

    def set_if_not_exists(self, key: str, value: Any, scope: Literal[scopes]):
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
        val = self.get(name)
        if val is None:
            raise AttributeError(f"GAMS variable '{name}' not found in any scope.")
        return val
