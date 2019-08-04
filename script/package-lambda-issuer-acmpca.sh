#! /bin/bash
P=$(pwd)/$(dirname $0)
mkdir -p ../tarz
cd ../lambda-issuer-acmpca
if test $? != 0; then echo ERROR; exit 1; fi
zip -r ../tarz/lambda-issuer-acmpca.zip .
