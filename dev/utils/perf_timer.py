import sys

if sys.platform != 'win32':
    from time import perf_counter
    try:
        from time import perf_counter_ns
    except ImportError:
        def perf_counter_ns():
            """perf_counter_ns() -> int

            Performance counter for benchmarking as nanoseconds.
            """
            return int(perf_counter() * 10**9)
else:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    kernel32.QueryPerformanceFrequency.argtypes = (
        wintypes.PLARGE_INTEGER,) # lpFrequency

    kernel32.QueryPerformanceCounter.argtypes = (
        wintypes.PLARGE_INTEGER,) # lpPerformanceCount

    _qpc_frequency = wintypes.LARGE_INTEGER()
    if not kernel32.QueryPerformanceFrequency(ctypes.byref(_qpc_frequency)):
        raise ctypes.WinError(ctypes.get_last_error())
    _qpc_frequency = _qpc_frequency.value

    def perf_counter_ns():
        """perf_counter_ns() -> int

        Performance counter for benchmarking as nanoseconds.
        """
        count = wintypes.LARGE_INTEGER()
        if not kernel32.QueryPerformanceCounter(ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return (count.value * 10**9) // _qpc_frequency

    def perf_counter():
        """perf_counter() -> float

        Performance counter for benchmarking.
        """
        count = wintypes.LARGE_INTEGER()
        if not kernel32.QueryPerformanceCounter(ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return count.value / _qpc_frequency