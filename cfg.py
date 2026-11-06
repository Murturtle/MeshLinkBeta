import os
from pathlib import Path
import re
import stat
import tempfile

import yaml


config = {}


def sync_revision(config_path="config.yml", revision_path="rev"):
    """Copy the installed revision into config without reformatting user settings."""
    revision = int(Path(revision_path).read_text(encoding="utf-8").strip())
    if revision < 0:
        raise ValueError("The installed revision must be nonnegative")
    if config.get("rev") == revision:
        return revision

    path = Path(config_path)
    with path.open(encoding="utf-8", newline="") as file:
        original = file.read()
    updated, count = re.subn(
        r"(?m)^(rev:[ \t]*)[0-9]+([ \t]*(?:#[^\r\n]*)?)(\r?)$",
        lambda match: match[1] + str(revision) + match[2] + match[3],
        original,
    )
    if count != 1:
        raise ValueError("Expected one top-level integer rev setting in config.yml")

    _write_config(path, updated)
    config["rev"] = revision
    return revision


def add_missing_options(config_path="config.yml", example_path=None):
    """Append missing top-level defaults while keeping existing settings intact."""
    path = Path(config_path)
    if example_path is None:
        example_path = path.parent / "config-example.yml"
        if not example_path.exists():
            example_path = path.parent / "config-example copy.yml"
    defaults = yaml.safe_load(Path(example_path).read_text(encoding="utf-8"))
    with path.open(encoding="utf-8", newline="") as file:
        original = file.read()
    current = yaml.safe_load(original)
    if not isinstance(defaults, dict) or not isinstance(current, dict):
        raise ValueError("Config and example config must contain YAML mappings")

    missing = {key: value for key, value in defaults.items() if key not in current}
    if not missing:
        return []

    newline = "\r\n" if "\r\n" in original else "\n"
    addition = yaml.safe_dump(missing, sort_keys=False, allow_unicode=True)
    # Keep the original text verbatim; serialize only the new defaults.
    updated = original + ("" if original.endswith("\n") else newline)
    updated += newline + "# Settings added from the example config" + newline
    updated += addition.replace("\n", newline)
    # A YAML document end marker or unusual document layout must not hide defaults.
    if yaml.safe_load(updated) != {**current, **missing}:
        raise ValueError("Could not append defaults to config.yml")
    _write_config(path, updated)
    config.update(missing)
    return list(missing)


def _write_config(path, updated):
    """Replace atomically so an interrupted write cannot truncate the config."""
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
        ) as file:
            temporary_path = Path(file.name)
            os.chmod(temporary_path, stat.S_IMODE(path.stat().st_mode))
            file.write(updated)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
