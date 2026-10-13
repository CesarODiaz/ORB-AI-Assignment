"""Package metadata. The local model is prepared by orb_build during pip install."""

from setuptools import setup

setup(
    name="orb-atelier",
    version="1.0.0",
    description="ORB Atelier intake agent with a local llama3.2 model",
    packages=["orb_agent"],
    python_requires=">=3.11",
)
