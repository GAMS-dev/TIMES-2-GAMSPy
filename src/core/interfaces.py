from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .times_model_class import TimesModelClass


@runtime_checkable
class TimesModule(Protocol):
    """The mandatory blueprint for all TIMES modules."""

    def initialize_preload(self, tc: "TimesModelClass") -> None: ...

    def initialize_postload(self, tc: "TimesModelClass") -> None: ...

    def run(self, tc: "TimesModelClass") -> None: ...
