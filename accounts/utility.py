from typing import Any


class CustomEncoder:
    def __call__(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {str(k): self(v) for k, v in obj.items()}
        return obj
