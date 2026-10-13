"""Build backend that prepares llama3.2 after the package is built.

pip does not run custom install commands anymore. This hook runs while
``pip install -r requirements.txt`` builds the project, in the project folder.
"""

import os
import subprocess
import sys
from pathlib import Path

from setuptools.build_meta import (  # noqa: F401
    build_sdist,
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_editable,
    prepare_metadata_for_build_wheel,
)
from setuptools.build_meta import build_editable as _build_editable
from setuptools.build_meta import build_wheel as _build_wheel


def _configure_llm() -> None:
    if os.environ.get("ORB_SKIP_LLM_SETUP") == "1":
        return
    root = Path.cwd()
    if not (root / "orb_agent" / "llm_setup.py").exists():
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call([sys.executable, "-m", "orb_agent.llm_setup"], cwd=root, env=env)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    result = _build_editable(wheel_directory, config_settings, metadata_directory)
    _configure_llm()
    return result


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    result = _build_wheel(wheel_directory, config_settings, metadata_directory)
    _configure_llm()
    return result
