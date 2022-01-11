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
python3 -m "nose"
# twine upload dist/* # to upload to PyPi
