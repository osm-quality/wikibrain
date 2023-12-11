#!/bin/bash
set -Eeuo pipefail
IFS=$'\\n\\t'
err_report() {
    echo "Error on line $1"
}
trap 'err_report $LINENO' ERR

rm dist -rf
python3 setup.py sdist bdist_wheel
cd dist
pip3 uninstall wikibrain -y
pip3 install --user *.whl
cd ..

# synch with README
pylint **/*.py --include-naming-hint=y --variable-rgx="^[a-z][a-z0-9]*((_[a-z0-9]+)*)?$" --disable=C0103,C0301,C0114,C0115,C0116,C0121,W0612,W0613,R0904,R0911,R0912,R0913,R0914,R0915,C0302,C1803,R1710,W0719,R1705,C0411 || true

rm wikidata_report.txt || true # may be not present (test it better!)
python3 -m unittest || true # tests may fail, in such case next line may help us to fix this
cat wikidata_report.txt || true # file may be gone
# twine upload dist/* # to upload to PyPi
