from pathlib import Path
from setuptools import setup, find_packages
import os


def get_long_description():
    # fmt: off
    """#PromptOps
Your CLI assistant. Ask questions, get shell commands.
"""
    # fmt: on


def get_version():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promptops", "version.py")
    g = {}
    with open(path) as fp:
        exec(fp.read(), g)
    return g["__version__"]


setup(
    name="promptops",
    version=get_version(),
    description="Your CLI assistant. Ask questions, get shell commands.",
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    author="CtrlStack inc.",
    url="https://promptops.com/",
    project_urls={
        "Documentation": "https://docs.promptops.com/cli",
        "Changelog": "https://docs.promptops.com/en/stable/changelog.html",
        "Live demo": "https://promptops.com/",
    },
    license='GPLv3',
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=False,
    python_requires=">=3.9",
    install_requires=[
        "colorama~=0.4.6",
        "requests~=2.31.0",
        "websockets~=11.0.3",
        "detect-secrets~=1.4.0",
        "prompt-toolkit~=3.0.38",
        "numpy~=1.25.0",
        "pyperclip~=1.8.2",
        "thefuzz~=0.19.0",
        "psutil~=5.9.5",
        "wcwidth~=0.2.6",
        "boto3~=1.26.159",
        "kubernetes~=26.1.0",
        "urllib3>=1.26,<2",  # kubernetes uses google-auth which has urllib3<2
        "setuptools~=68.0.0",
        "pip",
    ],
    entry_points="""
        [console_scripts]
        promptops=promptops.main:entry_main
        um=promptops.main:entry_alias
        qq=promptops.main:entry_alias
    """,
    setup_requires=[],
    extras_require={},
    tests_require=[],
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
    ],
)
