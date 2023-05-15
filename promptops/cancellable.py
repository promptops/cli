from concurrent import futures


class ThreadPoolExecutor(futures.ThreadPoolExecutor):
    def __init__(self, max_workers=None, thread_name_prefix="", initializer=None, initargs=()):
        super().__init__(max_workers, thread_name_prefix, initializer, initargs)
        self._futures = []
        self._active = True

    def submit(self, fn, *args, **kwargs):
        future = super().submit(fn, *args, **kwargs)
        self._futures.append(future)
        return future

    def shutdown(self, wait: bool = ..., *, cancel_futures: bool = ...) -> None:
        self._active = False
        for future in self._futures:
            future.cancel()
        super().shutdown(wait, cancel_futures=cancel_futures)

    def cancellable_callback(self, fn):
        def wrapper(*args, **kwargs):
            if self._active:
                return fn(*args, **kwargs)

        return wrapper

    def is_active(self):
        return self._active
