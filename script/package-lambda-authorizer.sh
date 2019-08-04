#! /bin/bash
P=$(pwd)/$(dirname $0)
mkdir -p ../tarz
cd ../lambda-authorizer
zip -r ../tarz/lambda-authorizer.zip .
