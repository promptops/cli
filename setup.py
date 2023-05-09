from setuptools import setup, find_packages
import os


def get_long_description():
    """#PromptOps
Your CLI assistant. Ask questions, get shell commands.
"""


def get_version():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "promptops", "version.py"
    )
    g = {}
    with open(path) as fp:
        exec(fp.read(), g)
    return g["__version__"]


setup(
    name="promptops",
    version=get_version(),
    description="Your CLI assistant. Ask questions, get shell commands.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="CtrlStack inc.",
    url="https://promptops.com/",
    project_urls={
        "Documentation": "https://docs.promptops.com/cli",
        "Changelog": "https://docs.promptops.com/en/stable/changelog.html",
        "Live demo": "https://promptops.com/",
    },
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=False,
    python_requires=">=3.7",
    install_requires=[
        "colorama~=0.4.6",
        "requests~=2.29.0",
        "websockets~=11.0.2",
        "detect-secrets~=1.4.0",
        "prompt-toolkit~=3.0.38",
        "numpy~=1.24.3",
        "setuptools",
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
        "Intended Audience :: Developers",
        "Intended Audience :: SRE",
    ],
)
