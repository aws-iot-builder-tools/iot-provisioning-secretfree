#! /bin/bash

SKUNAME=$1
DEVICES=../devices
if test ! -d ${DEVICES}; then mkdir -p ${DEVICES}; fi

# NOTE This would be on the network processor; the private key would
# already be created and the CSR would be a SimpleLink SDK call.

for i in {1..5}; do

    #echo Generating private key for device [$i]
    #openssl genrsa -out ../devices/e2e_$i.key 2048

    echo Generating certificate for device [$i]
    openssl req -nodes -x509 -sha256 -newkey rsa:2048 \
            -keyout ../devices/e2e_$i.key \
            -out ../devices/e2e_$i.sig.crt \
            -days 365 \
            -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=WidgIoT/CN=$i" \
            -batch -passin pass:nopass
            
    # This gets derived by the line test probe
    echo Deriving public key from private key for device [$i]
    openssl rsa -in $DEVICES/e2e_$i.key -pubout > $DEVICES/e2e_$i.pub

    echo Registering device [$i] to DynamoDB
    pubkey=$(cat $DEVICES/e2e_$i.pub | base64)
    aws dynamodb put-item --table-name $SKUNAME-iot-provisioning-secretfree \
        --item "{\"device-id\": {\"S\": \"$i\"}, \"pubkey\": {\"S\":\"$pubkey\"}}"
        
done
