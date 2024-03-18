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

[There is page at Wikidata](https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases) listing Wikidata issues and provided for Wikidata community so they can fix oproblematic cases.

Search for `too_abstract_or_wikidata_bugs` and disable that to get more errors caused by Wikidata.

See also and [my step by step list](https://www.wikidata.org/wiki/User:Mateusz_Konieczny#Ontology_on_Wikidata_is_systematically_broken)

# Development

`bash reinstall.sh`

can be used to run linter, tests and reinstall it

## Reformat code to follow Python coding standards

`autopep8 --in-place --max-line-length=420 --recursive .`

[PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)

## Detect code style issues

`pylint **/*.py --include-naming-hint=y --variable-rgx="^[a-z][a-z0-9]*((_[a-z0-9]+)*)?$" --argument-rgx="^[a-z][a-z0-9]*((_[a-z0-9]+)*)?$" --disable=R0902,C0103,C0301,C0114,C0115,C0116,C0121,W0613,R0911,R0912,R0913,R0915,C0302,C1803,R1710,W0719,R1705,C0411,W1514,E1136`

E1136 is hopelessly buggy, see https://github.com/pylint-dev/pylint/issues/1498#issuecomment-1872189118

Disable W1514 as such OS are not supported anyway by me and it is fixed by https://peps.python.org/pep-0686/ making UTF8 default everywhere.

Disables rule `C0103` with many false positives (too eager to convert variables into constants).

Disables R0902 as this does not seem to be an actual problem to me.

Disables C0411 as low priority decoration.

Disables C1803 as unwanted syntactic sugar (reconsider after pressing issues are eliminated)

Disables R1705 - as unclear what is wrong with else after return

Disables C0301 complaining about long lines (TODO: reenable? consider, see autopep allowing long lines above).

Disables W0613 complaining about unused arguments. (TODO: reenable? consider)

Disables R0911, R0912, R0913, R0914, R0915, C0302 complaining about complexity/size of code. (TODO: reenable)

Disables C0114, C0115, C0116 asking for docstrings (TODO: reenable)

Disables C0121 complaining about `== None` (TODO: learn about why it is bad)

Disables R1710 asking for explicit returning of `None`

Disables W0719 asking for more specific exceptions
