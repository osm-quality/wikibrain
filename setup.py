import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wikibrain",
    version="0.0.6",
    author="Mateusz Konieczny",
    author_email="matkoniecz@gmail.com",
    description="Stores knowledge and data necessary to properly use links from OpenStreetMap to Wikipedia, Wikidata and other Wikimedia projects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/matkoniecz/wikibrain",
    packages=setuptools.find_packages(),
    install_requires = [
        'geopy>=1.11.0',
        'nose>=1.3.7',
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
