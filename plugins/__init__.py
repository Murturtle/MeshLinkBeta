# https://gist.github.com/dorneanu/cce1cd6711969d581873a88e0257e312

import os
import traceback
from importlib import util


class Base:
    """Basic resource class. Concrete resources will inherit from this one
    """
    plugins = []

    # For every class that inherits from the current,
    # the class name will be added to plugins
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.plugins.append(cls)


# Small utility to automatically load modules
def load_module(path):
    name = os.path.split(path)[-1]
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Get current path
path = os.path.abspath(__file__)
dirpath = os.path.dirname(path)

# Get PID for logging
_pid = os.getpid()

for fname in os.listdir(dirpath):
    # Load only "real modules"
    if not fname.startswith('.') and ( not fname.startswith('__')  ) and fname.endswith('.py') and not fname.startswith("lib"):
        try:
            load_module(os.path.join(dirpath, fname))
            print(f"[PID:{_pid}] [INFO] Loaded file {fname}")
        except Exception:
            traceback.print_exc()