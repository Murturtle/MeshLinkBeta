import os

# Get PID once at module load time
_pid = os.getpid()

def _format_prefix(level):
    """Format log prefix with PID"""
    return f"[PID:{_pid}] [{level}] "

def info(any):
    print(_format_prefix("INFO") + str(any))

def warn(any):
    print("\x1b[31;49m" + _format_prefix("WARN") + str(any) + "\x1b[0m")

def infoimportant(any):
    print("\x1b[33;49m" + _format_prefix("INFO") + str(any) + "\x1b[0m")

def infogreen(any):
    print("\x1b[32;49m" + _format_prefix("INFO") + str(any) + "\x1b[0m")

def infodiscord(any):
    print("\x1b[35;49m" + _format_prefix("DISC") + str(any) + "\x1b[0m")