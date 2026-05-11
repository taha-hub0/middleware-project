# Chain of Responsibility: işleme adımlarını sırayla zincirlemek için kullanılır.
from typing import Callable, Optional, Tuple


class Step:
    def __init__(self, name: str, handler: Callable[[dict, dict], Optional[dict]]):
        self.name = name
        self.handler = handler
        self._next: Optional["Step"] = None

    def set_next(self, next_step: "Step") -> "Step":
        self._next = next_step
        return next_step

    def handle(self, record: dict, context: dict) -> Optional[dict]:
        result = self.handler(record, context)
        if result is None:
            context["dropped_by"] = self.name
            return None
        if self._next:
            return self._next.handle(result, context)
        return result


def build_chain(step_defs: list[Tuple[str, Callable[[dict, dict], Optional[dict]]]]) -> Step:
    if not step_defs:
        raise ValueError("Pipeline needs at least one step.")
    head = Step(step_defs[0][0], step_defs[0][1])
    current = head
    for name, handler in step_defs[1:]:
        current = current.set_next(Step(name, handler))
    return head
