# https://gist.github.com/dorneanu/cce1cd6711969d581873a88e0257e312

import os
import traceback
from importlib import util
import plugins.liblogger as logger


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


path = os.path.abspath(__file__)
dirpath = os.path.dirname(path)

enabled_file = os.path.join(os.getcwd(), 'plugins', 'plugins-enabled')
enabled = set()

if os.path.exists(enabled_file):
    try:
        with open(enabled_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                enabled.add(line)
    except Exception:
        traceback.print_exc()
else:
    logger.warn("No plugins-enabled file found")
    exit(1)

for fname in os.listdir(dirpath):
    if fname.startswith('.') or fname.startswith('__') or not fname.endswith('.py'):
        continue
    if fname.startswith('lib'):
        continue

    base = fname[:-3]
    if base not in enabled:
        logger.infoimportant(f"Plugin {base} not enabled")
        continue

    try:
        load_module(os.path.join(dirpath, fname))
        logger.info("Loaded file "+fname)
    except Exception:
        traceback.print_exc()