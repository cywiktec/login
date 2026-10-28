"""Ordered fallback execution."""


class AllHandlersFailed(RuntimeError):
    def __init__(self, errors):
        super().__init__("all handlers failed: " + "; ".join(f"{n}: {e!r}" for n, e in errors))
        self.errors = errors


class Failover:
    def __init__(self, handlers):
        """handlers: ordered list of (name, callable); the first is the primary."""
        if not handlers:
            raise ValueError("at least one handler is required")
        self.handlers = list(handlers)

    def run(self, *args, **kwargs):
        """Return (handler_name, result) from the first handler that succeeds."""
        errors = []
        for name, handler in self.handlers:
            try:
                return name, handler(*args, **kwargs)
            except Exception as error:
                errors.append((name, error))
        raise AllHandlersFailed(errors)
