#! /bin/sh

SCRIPTDIR=$(dirname $0)
INT_CA_DIR=${SCRIPTDIR}/../intermediate-ca
if test -d ${INT_CA_DIR}; then echo ERROR Intermediate CA directory already exists. Bailing.; exit 1; fi
if test ! -d ${SCRIPTDIR}/../root-ca; then echo ERROR: Root CA not created. Bailing.; exit 1; fi

PRODUCT=widgiot

mkdir -p ${INT_CA_DIR}
cd ${SCRIPTDIR}/../intermediate-ca

mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial

echo 1001 > db/crlnumber

openssl req -new                      \
    -config ${PRODUCT}-ca.conf        \
    -out ${PRODUCT}-ca.csr            \
    -keyout private/${PRODUCT}-ca.key \
    -batch                            \
    -passout pass:nopass

pushd ${SCRIPTDIR}/../root-ca/

openssl ca \
    -config root-ca.conf                   \
    -in ../${PRODUCT}-ca/${PRODUCT}-ca.csr \
    -out ${PRODUCT}-ca.crt                 \
    -extensions sub_ca_ext                 \
    -batch                                 \
    -passin pass:nopass

cp ${PRODUCT}-ca.crt ../${PRODUCT}-ca
cp root-ca.crt ../${PRODUCT}-ca #for ease of operation when issuing aws cert
