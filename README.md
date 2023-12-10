Stores knowledge and data necessary to properly use links from OpenStreetMap to Wikipedia, Wikidata and Wikimedia Commons.

# Installation

It has a very unfortunate dependecies - sorry for that, pull requests improving this situation are welcome.

- first you need to clone, modify and install as a python package [this thing](https://codeberg.org/matkoniecz/osm_handling_config) - pull request providing cache location in a better way (config file? environment variable?) is welcome

Finally, install packages in a standard way (providing config and this should be the only steps, sorry):

`pip3 install wikibrain`

Or 

```
git clone https://github.com/matkoniecz/wikibrain.git
cd wikibrain
pip3 install -r requirements.txt
```

# Running tests

`python3 -m unittest`

# Fixing Wikidata

Search for `too_abstract_or_wikidata_bugs` and disable that to get more errors caused by Wikidata.

See also and [my step by step list](https://www.wikidata.org/wiki/User:Mateusz_Konieczny#Ontology_on_Wikidata_is_systematically_broken)

## Reformat code to follow Python coding standards

`autopep8 --in-place --max-line-length=420 --recursive .`

[PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)

## Detect code style issues

`pylint **/*.py --include-naming-hint=y --variable-rgx=^[a-z][a-z0-9]*((_[a-z0-9]+)*)?$ --argument-rgx=^[a-z][a-z0-9]*((_[a-z0-9]+)*)?$ --disable=C0103`

It includes a workaround for bug [#2018](https://github.com/PyCQA/pylint/issues/2018) and disables rule `C0103` with many false positives (too eager to convert variables into constants).
