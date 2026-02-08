import shutil
from pathlib import Path


def _engine_command_available(command: str) -> bool:
    return bool(Path(command).exists() or shutil.which(command))
