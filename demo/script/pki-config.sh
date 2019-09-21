#! /bin/bash

REGION=us-east-1
PRODUCT=widgiot
UNIQ=elberger

cd ..
mkdir aws-ca
cd aws-ca

aws s3api create-bucket \
    --bucket ${UNIQ}-acm-pca-crl-${REGION}-${PRODUCT}" \
    --query Location \
    --region ${REGION}

aws s3api put-bucket-policy \
    --bucket ${UNIQ}-acm-pca-crl-${REGION}-${PRODUCT} \
    --policy file://../conf/s3-${REGION}-${PRODUCT}-ca.json

CA_ARN=$(aws acm-pca create-certificate-authority \
                                --certificate-authority-configuration file://${REGION}-${PRODUCT}-config.txt \
                                --revocation-configuration file://${REGION}-${PRODUCT}-revoke-config.txt \
                                --certificate-authority-type "SUBORDINATE" \
                                --idempotency-token 98256344 \
                                --output text \
                                --region ${REGION} \
                                --query CertificateAuthorityArn)

aws acm-pca get-certificate-authority-csr \
    --certificate-authority-arn ${CA_ARN} \
    --output text \
    --region ${REGION} \
    > ${REGION}-${PRODUCT}-ca.csr

cd ../${PRODUCT}-ca

openssl ca \
    -config ${PRODUCT}-ca.conf \
    -in ../aws-ca/${REGION}-${PRODUCT}-ca.csr \
    -out ${REGION}-${PRODUCT}-ca.crt \
    -extensions sub_ca_ext \
    -batch \
    -passin pass:nopass

openssl x509 -in useast1-widgiot-ca.crt -out ${REGION}-${PRODUCT}-ca.pem -outform PEM

openssl x509 -in ${PRODUCT}-ca.crt -out ${PRODUCT}-ca.pem -outform PEM

openssl x509 -in ../root-ca/root-ca.crt -out root-ca.pem -outform PEM

cat ${PRODUCT}-ca.pem root-ca.pem >  ${REGION}-${PRODUCT}-ca-chain.pem

aws acm-pca import-certificate-authority-certificate \
    --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
    --certificate file://${REGION}-${PRODUCT}-ca.pem \
    --certificate-chain file://${REGION}-${PRODUCT}-ca-chain.pem \
    --region ${REGION}

code=$(aws iot get-registration-code \
           --query registrationCode \
           --region ${REGION} --output text \
           --query registrationCode )

openssl genrsa -out useast1-verification-request.key 2048

openssl req -new \
        -key ${REGION}-verification-request.key \
        -out ${REGION}-verification-request.csr \
        -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=${PRODUCT}-${REGION}/CN=$code"

# request the certificate from ACM
        
CERTIFICATE_ARN=$(aws acm-pca issue-certificate \
                      --certificate-authority-arn  ${CA_ARN} \
                      --csr file://${REGION}-verification-request.csr \
                      --signing-algorithm "SHA256WITHRSA" \
                      --validity Value=364,Type="DAYS" \
                      --idempotency-token 1234     \
                      --region ${REGION} --output text \
                      --query CertificateArn)

aws acm-pca get-certificate \
    --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
    --certificate-arn ${CERTIFICATE_ARN} \
    --output text --region ${REGION} > verification.pem

TODO

aws iot register-ca-certificate \
               --ca-certificate file://${REGION}-${PRODUCT}-ca.pem \
               --verification-cert file://verification.pem \
               --set-as-active \
               --query certificateArn \
               --output text --region ${REGION}
