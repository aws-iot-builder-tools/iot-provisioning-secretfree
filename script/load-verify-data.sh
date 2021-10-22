#! /bin/bash

if test $# != 1; then
    echo Parameter 1 must be the SKUNAME. Use the same SKUNAME that you used for the installation.
    exit 1
fi

SKUNAME=$1
DEVICES=$(dirname $0)/../devices/verify
if test ! -d ${DEVICES}; then mkdir -p ${DEVICES}; fi

# NOTE This would be on the network processor; the private key would
# already be created and the CSR would be a SimpleLink SDK call.

for i in {1..5}; do
    echo \*\*\* Generating set $i

    echo Generating certificate request for device [$i]
    openssl req -nodes -sha256 -newkey rsa:2048 \
            -keyout ${DEVICES}/e2e_$i.key \
            -out ${DEVICES}/e2e_$i.csr \
            -days 365 \
            -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=${SKUNAME}/CN=$i" \
            -batch -passin pass:nopass \
            > /dev/null 2>&1
            
    if test $? != 0; then
       echo Error hard stop.
       exit 1
    fi

    # This gets derived by the line test probe
    echo Deriving public key from private key for device [$i]
    openssl rsa -in $DEVICES/e2e_$i.key -pubout -out $DEVICES/e2e_$i.pub

    if test $? != 0; then
       echo Error hard stop.
       exit 1
    fi

    echo Registering device [$i] to DynamoDB
    pubkey=$(base64 --wrap 0 $DEVICES/e2e_$i.pub)
    aws dynamodb put-item --table-name $SKUNAME-iot-provisioning-secretfree \
        --item "{\"device-id\": {\"S\": \"$i\"}, \"pubkey\": {\"S\":\"$pubkey\"}}" \
        > /dev/null 2>&1
    if test $? != 0; then
       echo Error hard stop.
       exit 1
    fi

done
