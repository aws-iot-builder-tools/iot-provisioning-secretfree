#! /bin/bash
D=$(dirname $0)
cd ${D}
P=$(pwd)

echo D: ${D}
echo P: ${P}

mkdir -p ${P}/../tarz
mkdir -p /tmp/pyopenssl
pushd /tmp/pyopenssl

# get all the files for the module and dependencies

docker run \
       -v "$PWD":/var/task lambci/lambda:build-python3.6 /bin/bash \
       -c "mkdir python && pip install pyOpenSSL==19.0.0 -t python/; exit"

zip -r ${P}/../tarz/lambda-layer-pyopenssl.zip .
popd
rm -rf /tmp/pyopenssl
