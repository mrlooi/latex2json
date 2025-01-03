from setuptools import setup, find_packages

setup(
    name="tex-to-json",
    version="0.1.0",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    python_requires=">=3.7",
    url="https://github.com/mrlooi/latex-parser.git",
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
        ]
    },
)
