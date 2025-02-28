from setuptools import setup, find_packages

setup(
    name="latex2json",
    version="0.3.0",
    package_dir={"": "."},
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=open("requirements.txt").read().splitlines(),
    python_requires=">=3.7",
    url="https://github.com/mrlooi/latex2json",
)
