#! /bin/bash
#
#
# Script to test deploy - pass it the API Gateway endpoint and it will
# do the rest for you.
#
# If you are using CA Subject defined beyond the POC then change them herein.
#

function help() {
    echo ./test-deploy.sh <issuer-endpoint>
    exit 0
}

function begin() {
}

function end() {
    exit 0
}

if test x"$1" == x; then
    echo you must supply the endpoint for your test
    echo and if you do not supply a correct endpoint the curl call will fail miserably

    help
    exit 1
else
    endpoint=$1
fi

epoch=$(date -j -f "%a %b %d %T %Z %Y" "`date`" "+%s")
subj="/C=US/ST=VA/L=Anywhere/O=Automatra/OU=WidgIoT us-east-1/CN=${epoch}"
mkdir ${epoch} && pushd ${epoch}
cwd=$(pwd)
openssl genrsa -out ${epoch}.key 2048
openssl req -new \
            -key ${epoch}.key.pem \
            -out ${epoch}.csr.pem \
            -subj "${subj}"

payload=$(base64 ${epoch}.csr)
header="device-csr: ${payload}"

echo fetching certificate...
curl -s -o ${epoch}.crt.pem --header "${header}" ${endpoint}

openssl rsa                      \
        -inform PEM              \
        -outform DER             \
        -infile ${epoch}.key.pem \
        -outfile ${epoch}.key.der

openssl x509                     \
        -inform PEM              \
        -outform DER             \
        -infile ${epoch}.crt.pem \
        -outfile ${epoch}.crt.der

popd

echo Your files have been generated:

echo PEM Private key : ${cwd}/${epoch}.key.pem
echo PEM CSR         : ${cwd}/${epoch}.csr.pem
echo PEM Certificate : ${cwd}/${epoch}.crt.pem

echo If you need to use certificate and key in DER format, here they
echo are:

echo DER Private key : ${cwd}/${epoch}.key.der
echo DER Certificate : ${cwd}/${epoch}.crt.der

