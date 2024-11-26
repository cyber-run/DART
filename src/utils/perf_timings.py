import sys
import ctypes
from ctypes.wintypes import LARGE_INTEGER

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
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    # Constants
    INFINITE = 0xFFFFFFFF
    WAIT_FAILED = 0xFFFFFFFF
    CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x00000002

    def perf_counter_ns():
        """perf_counter_ns() -> int
        Performance counter for benchmarking as nanoseconds.
        """
        count = LARGE_INTEGER()
        if not kernel32.QueryPerformanceCounter(ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return (count.value * 10**9) // _qpc_frequency

    def perf_counter():
        """perf_counter() -> float
        Performance counter for benchmarking.
        """
        count = LARGE_INTEGER()
        if not kernel32.QueryPerformanceCounter(ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return count.value / _qpc_frequency

    class PerfSleeper:
        def __init__(self):
            self.handle = kernel32.CreateWaitableTimerExW(
                None, None, CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, 0x1F0003
            )

        def sleep_ms(self, ms_time):
            _ = kernel32.SetWaitableTimer(
                self.handle,
                ctypes.byref(LARGE_INTEGER(int(ms_time * -10000))),
                0,
                None,
                None,
                0,
            )
            _ = kernel32.WaitForSingleObject(self.handle, INFINITE)
            kernel32.CancelWaitableTimer(self.handle)

    # Initialize QPC frequency
    _qpc_frequency = LARGE_INTEGER()
    if not kernel32.QueryPerformanceFrequency(ctypes.byref(_qpc_frequency)):
        raise ctypes.WinError(ctypes.get_last_error())
    _qpc_frequency = _qpc_frequency.value 