from setuptools import setup, find_packages

setup(
    name="latex_parser",
    version="0.1.0",
    package_dir={"": "."},  # Changed from "src" to "." since package is in root
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=open("requirements.txt").read().splitlines(),
    python_requires=">=3.7",
    url="https://github.com/mrlooi/latex-parser.git",
)
