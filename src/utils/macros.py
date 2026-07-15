# macros.py

from __future__ import annotations


class Macros:
    def __init__(self) -> None:
        self._active: dict[str, bool] = {}

    # ICOST
    @property
    def obj_icost_active(self) -> bool:
        return self._active.get("OBJ_ICOST", False)

    @obj_icost_active.setter
    def obj_icost_active(self, value: bool) -> None:
        self._active["OBJ_ICOST"] = value

    def obj_icost(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_icost_active:
            return f"OB_ICOST({r},{p},{m},{y})"
        return f"OBJ_ICOST({r},{y},{p},{m})"

    # ISUB
    @property
    def obj_isub_active(self) -> bool:
        return self._active.get("OBJ_ISUB", False)

    @obj_isub_active.setter
    def obj_isub_active(self, value: bool) -> None:
        self._active["OBJ_ISUB"] = value

    def obj_isub(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_isub_active:
            return f"OB_ISUB({r},{p},{m},{y})"
        return f"OBJ_ISUB({r},{y},{p},{m})"

    # ITAX
    @property
    def obj_itax_active(self) -> bool:
        return self._active.get("OBJ_ITAX", False)

    @obj_itax_active.setter
    def obj_itax_active(self, value: bool) -> None:
        self._active["OBJ_ITAX"] = value

    def obj_itax(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_itax_active:
            return f"OB_ITAX({r},{p},{m},{y})"
        return f"OBJ_ITAX({r},{y},{p},{m})"

    # FOM
    @property
    def obj_fom_active(self) -> bool:
        return self._active.get("OBJ_FOM", False)

    @obj_fom_active.setter
    def obj_fom_active(self, value: bool) -> None:
        self._active["OBJ_FOM"] = value

    def obj_fom(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_fom_active:
            return f"OB_FOM({r},{p},{m},{y})"
        return f"OBJ_FOM({r},{y},{p},{m})"

    # FSB
    @property
    def obj_fsb_active(self) -> bool:
        return self._active.get("OBJ_FSB", False)

    @obj_fsb_active.setter
    def obj_fsb_active(self, value: bool) -> None:
        self._active["OBJ_FSB"] = value

    def obj_fsb(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_fsb_active:
            return f"OB_FSB({r},{p},{m},{y})"
        return f"OBJ_FSB({r},{y},{p},{m})"

    # FTX
    @property
    def obj_ftx_active(self) -> bool:
        return self._active.get("OBJ_FTX", False)

    @obj_ftx_active.setter
    def obj_ftx_active(self, value: bool) -> None:
        self._active["OBJ_FTX"] = value

    def obj_ftx(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_ftx_active:
            return f"OB_FTX({r},{p},{m},{y})"
        return f"OBJ_FTX({r},{y},{p},{m})"

    # DCOST
    @property
    def obj_dcost_active(self) -> bool:
        return self._active.get("OBJ_DCOST", False)

    @obj_dcost_active.setter
    def obj_dcost_active(self, value: bool) -> None:
        self._active["OBJ_DCOST"] = value

    def obj_dcost(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_dcost_active:
            return f"OB_DCC({r},{p},{m},{y})"
        return f"OBJ_DCOST({r},{y},{p},{m})"

    # DLAGC
    @property
    def obj_dlagc_active(self) -> bool:
        return self._active.get("OBJ_DLAGC", False)

    @obj_dlagc_active.setter
    def obj_dlagc_active(self, value: bool) -> None:
        self._active["OBJ_DLAGC"] = value

    def obj_dlagc(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_dlagc_active:
            return f"OB_DLC({r},{p},{m},{y})"
        return f"OBJ_DLAGC({r},{y},{p},{m})"

    # ACOST
    @property
    def obj_acost_active(self) -> bool:
        return self._active.get("OBJ_ACOST", False)

    @obj_acost_active.setter
    def obj_acost_active(self, value: bool) -> None:
        self._active["OBJ_ACOST"] = value

    def obj_acost(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_acost_active:
            return f"OB_ACT({r},{p},{m},{y})"
        return f"OBJ_ACOST({r},{y},{p},{m})"

    # FCOST
    @property
    def obj_fcost_active(self) -> bool:
        return self._active.get("OBJ_FCOST", False)

    @obj_fcost_active.setter
    def obj_fcost_active(self, value: bool) -> None:
        self._active["OBJ_FCOST"] = value

    def obj_fcost(self, r: str, y: str, p: str, c: str, s: str, m: str) -> str:
        if self.obj_fcost_active:
            return f"OB_FCOS({r},{p},{c},{s},{m},{y})"
        return f"OBJ_FCOST({r},{y},{p},{c},{s},{m})"

    # FDELV
    @property
    def obj_fdelv_active(self) -> bool:
        return self._active.get("OBJ_FDELV", False)

    @obj_fdelv_active.setter
    def obj_fdelv_active(self, value: bool) -> None:
        self._active["OBJ_FDELV"] = value

    def obj_fdelv(self, r: str, y: str, p: str, c: str, s: str, m: str) -> str:
        if self.obj_fdelv_active:
            return f"OB_FDEL({r},{p},{c},{s},{m},{y})"
        return f"OBJ_FDELV({r},{y},{p},{c},{s},{m})"

    # FTAX
    @property
    def obj_ftax_active(self) -> bool:
        return self._active.get("OBJ_FTAX", False)

    @obj_ftax_active.setter
    def obj_ftax_active(self, value: bool) -> None:
        self._active["OBJ_FTAX"] = value

    def obj_ftax(self, r: str, y: str, p: str, c: str, s: str, m: str) -> str:
        if self.obj_ftax_active:
            return f"OB_FTAX({r},{p},{c},{s},{m},{y})"
        return f"OBJ_FTAX({r},{y},{p},{c},{s},{m})"


macro_config = Macros()
