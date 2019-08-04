cd ..
mkdir aws-ca
cd aws-ca

aws s3api create-bucket \
    --bucket "elberger-acm-pca-crl-useast1-widgiot" \
    --query Location \
    --region us-east-1

aws s3api put-bucket-policy \
    --bucket elberger-acm-pca-crl-useast1-widgiot \
    --policy file://../conf/s3-useast1-widgiot-ca.json

CERTIFICATE_AUTHORITY_ARN=$(aws acm-pca create-certificate-authority --output text\
                                --certificate-authority-configuration file://useast1-widgiot-config.txt \
                                --revocation-configuration file://useast1-widgiot-revoke-config.txt \
                                --certificate-authority-type "SUBORDINATE" \
                                --idempotency-token 98256344 \
                                --region us-east-1 \
                                --query CertificateAuthorityArn)

aws acm-pca get-certificate-authority-csr \
    --certificate-authority-arn ${CERTIFICATE_AUTHORITY_ARN} \
    --output text \
    --region us-east-1 \
    > useast1-widgiot-ca.csr
    #+end_srd

    Issue the CA certificate using the Intermediate CA.

    #+begin_src bash :mkdirp yes :tangle ../../iot-provisioning-secretfree/demo/script/pki-config.sh

cd ../widgiot-ca

openssl ca \
    -config widgiot-ca.conf \
    -in ../aws-ca/useast1-widgiot-ca.csr \
    -out useast1-widgiot-ca.crt \
    -extensions sub_ca_ext \
    -batch \
    -passin pass:nopass

openssl x509 -in useast1-widgiot-ca.crt -out useast1-widgiot-ca.pem -outform PEM

openssl x509 -in widgiot-ca.crt -out widgiot-ca.pem -outform PEM

openssl x509 -in ../root-ca/root-ca.crt -out root-ca.pem -outform PEM

cat widgiot-ca.pem root-ca.pem >  useast1-widgiot-ca-chain.pem

aws acm-pca import-certificate-authority-certificate \
    --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
    --certificate file://useast1-widgiot-ca.pem \
    --certificate-chain file://useast1-widgiot-ca-chain.pem \
    --region us-east-1

code=$(aws iot get-registration-code \
           --query registrationCode \
           --region us-east-1 --output text \
           --query registrationCode )

openssl genrsa -out useast1-verification-request.key 2048

openssl req -new \
        -key useast1-verification-request.key \
        -out useast1-verification-request.csr \
        -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=WidgIoT us-east-1/CN=$code"

# request the certificate from ACM
        
CERTIFICATE_ARN=$(aws acm-pca issue-certificate \
                      --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
                      --csr file://useast1-verification-request.csr \
                      --signing-algorithm "SHA256WITHRSA" \
                      --validity Value=364,Type="DAYS" \
                      --idempotency-token 1234     \
                      --region us-east-1 --output text \
                      --query CertificateArn)

aws acm-pca get-certificate \
    --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
    --certificate-arn ${CERTIFICATE_ARN} \
    --output text --region us-east-1 > verification.pem

TODO

aws iot register-ca-certificate \
               --ca-certificate file://useast1-widgiot-ca.pem \
               --verification-cert file://verification.pem \
               --set-as-active \
               --query certificateArn \
               --output text --region us-east-1
