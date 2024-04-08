import time
import ctypes
from ctypes.wintypes import LARGE_INTEGER

kernel32 = ctypes.windll.kernel32

INFINITE = 0xFFFFFFFF
WAIT_FAILED = 0xFFFFFFFF
CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x00000002

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

# Main function
if __name__ == "__main__":
    try:
        while True:
            ms_time = 2  # 1ms
            # Original time.sleep()
            start_time = time.perf_counter()
            time.sleep(ms_time / 1000)
            print(f"time.sleep(0.004) took: {1000*(time.perf_counter() - start_time)} ms")

            # ctypes sleep
            perf_sleeper = PerfSleeper()

            start_time = time.perf_counter()
            perf_sleeper.sleep_ms(ms_time)
            print(f"ctyped WaitableTimer sleep 4ms took: {1000*(time.perf_counter() - start_time)} ms")

    except KeyboardInterrupt:
        print("Exiting\n")
