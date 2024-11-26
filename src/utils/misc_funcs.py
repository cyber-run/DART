import os, psutil

def set_realtime_priority():
    try:
        p = psutil.Process(os.getpid())
        if psutil.WINDOWS:
            p.nice(psutil.REALTIME_PRIORITY_CLASS)
        elif psutil.LINUX or psutil.MACOS:
            # Set a high priority; be cautious with setting it to -20 (maximum priority)
            p.nice(-10)  # Modify this value as needed
        else:
            print("Platform not supported for priority setting.")
    except Exception as e:
        print(f"Error setting priority: {e}")

def num_to_range(num, inMin, inMax, outMin, outMax):
    angle = outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))

    # Min/Max value based on out min/max
    angle = max(outMin, min(outMax, angle))

    return angle