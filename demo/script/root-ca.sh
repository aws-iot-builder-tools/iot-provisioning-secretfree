#! /bin/bash
rel=$(dirname $0)
cd $rel
mkdir -p ti-provisioning/root-ca
cd ../root-ca
mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber

#! /bin/bash
openssl req -new                    \
        -config root-ca.conf        \
        -out root-ca.csr            \
        -keyout private/root-ca.key \
        -passout pass:nopass

openssl ca -selfsign \
    -config root-ca.conf \
    -in root-ca.csr \
    -out root-ca.crt \
    -extensions ca_ext \
    -batch \
    -passin pass:nopass

openssl req -new \
    -newkey rsa:2048 \
    -subj "/C=US/O=Automatra/CN=OCSP Root Responder" \
    -keyout private/root-ocsp.key \
    -out root-ocsp.csr \
    -batch \
    -passout pass:nopass

openssl ca \
    -config root-ca.conf \
    -in root-ocsp.csr \
    -out root-ocsp.crt \
    -extensions ocsp_ext \
    -days 30 \
    -batch \
    -passin pass:nopass
