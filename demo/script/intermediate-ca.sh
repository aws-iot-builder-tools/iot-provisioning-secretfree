cd ../intermediate-ca
mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber

openssl req -new \
    -config widgiot-ca.conf \
    -out widgiot-ca.csr \
    -keyout private/widgiot-ca.key \
    -batch \
    -passout pass:nopass

cd ../root-ca/
openssl ca \
    -config root-ca.conf \
    -in ../widgiot-ca/widgiot-ca.csr \
    -out widgiot-ca.crt \
    -extensions sub_ca_ext \
    -batch \
    -passin pass:nopass
cp widgiot-ca.crt ../widgiot-ca
cp root-ca.crt ../widgiot-ca #for ease of operation when issuing aws cert
