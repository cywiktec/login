class ShutdownManager:
    def __init__(self):
        self._callbacks = []
        self._shutdown = False

    def register(self, callback):
        if self._shutdown:
            raise RuntimeError("shutdown has already started")
        self._callbacks.append(callback)

    def shutdown(self):
        if self._shutdown:
            return

        self._shutdown = True
        errors = []
        for callback in reversed(self._callbacks):
            try:
                callback()
            except Exception as error:
                errors.append(error)

        if errors:
            raise RuntimeError("one or more shutdown callbacks failed") from errors[0]
