#! /bin/bash
P=$(dirname $0)
mkdir -p ${P}/../tarz
cd ../lambda-issuer-iotcore
if test $? != 0; then echo ERROR; exit 1; fi
zip -r ../tarz/lambda-issuer-iotcore.zip .
