from setuptools import find_packages, setup

with open("gcb/version.txt") as ifp:
    VERSION = ifp.read().strip()

long_description = ""
with open("README.md") as ifp:
    long_description = ifp.read()

setup(
    name="gofp-chatgpt-bot",
    version="0.0.1",
    packages=find_packages(),
    install_requires=["eth-brownie", "pydantic", "moonworm>=0.6.2"],
    extras_require={
        "dev": [
            "black",
            "mypy",
            "isort",
        ],
        "distribute": ["setuptools", "twine", "wheel"],
    },
    description="ChatGPT bot for The Garden of Forking Paths game",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="kompotkot",
    author_email="zenitsws@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires=">=3.8",
    url="https://github.com/kompotkot/gofp-chatgpt-bot",
    entry_points={
        "console_scripts": [
            "gcb=gcb.cli:main",
        ]
    },
    include_package_data=True,
)
