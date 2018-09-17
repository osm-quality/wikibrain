Stores knowledge and data necessary to properly use links from OpenStreetMap to Wikipedia, Wikidata and other Wikimedia projects.

# Running tests

```nosetests3``` or ```python3 -m unittest```


# Publishing new version

- run tests (see section above)
- bump version in `setup.py` file in the top directory
- from the top directory run `python3 setup.py sdist bdist_wheel`
- to upload to PyPi, from the top directory run `twine upload dist/*`
- one can make local install, without publishing to PyPi. Run from `dist` folder command like `pip3 install --user <recent package>.whl`