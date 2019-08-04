#! /bin/bash
CERTIFICATE_AUTHORITY_ARN=$1
cd ~/ti-provisioning
mkdir test_client_1
cd test_client_1
openssl genrsa -out test_client_1.key 2048
openssl req -new \
        -key test_client_1.key \
        -out test_client_1.csr \
        -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=WidgIoTus-east- 1/CN=test_client_1"

tc1_cert_arn=$(aws acm-pca issue-certificate \
                   --certificate-authority-arn ${CERTIFICATE_AUTHORITY_ARN} \
                   --csr file://test_client_1.csr \
                   --signing-algorithm "SHA256WITHRSA" \
                   --validity Value=364,Type="DAYS" \
                   --idempotency-token 1234     \
                   --region us-east-1 --output text --query CertificateArn)

aws acm-pca get-certificate \
    --certificate-authority-arn ${CERTIFICATE_AUTHORITY_ARN} \
    --certificate-arn ${tc1_cert_arn} \
    --output text \
    --region us-east-1 > test_client_1.pem

tc1_cert_iot_arn=$(aws iot register-certificate                     \
                       --certificate-pem file://test_client_1.pem   \
                       --ca-certificate-pem file://../widgiot-ca/useast1-widgiot-ca.pem \
                       --query certificateArn --output text --region us-east-1)
tc1_cert_iot_id=$(echo $tc1_cert_iot_arn | cut -f2 -d /)
aws iot update-certificate                               \
    --certificate-id $tc1_cert_iot_id                       \
    --new-status ACTIVE \
    --region us-east-1

aws iot create-thing                  \
    --output text  --region us-east-1 \
    --thing-name test_client_1        \
    --query thingArn

aws iot attach-thing-principal        \
    --output text  --region us-east-1 \
    --thing-name test_client_1        \
    --principal ${tc1_cert_iot_arn}

aws iot ${REGION} create-policy                                               \
    --policy-name test_client_1_policy                                        \
    --policy-document file://test_client_1_policy.json                        \
    --query policyArn --region us-east-1
 
aws iot ${REGION} attach-principal-policy \
    --policy-name test_client_1_policy \
    --principal ${tc1_cert_iot_arn} --region us-east-1

endpoint=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --region us-east-1 --query endpointAddress --output text)
wget https://www.amazontrust.com/repository/AmazonRootCA1.pem
cd ..
git clone https://github.com/aws/aws-iot-device-sdk-python
cd aws-iot-device-sdk-python/samples/basicPubSub/
sudo pip3 install AWSIoTPythonSDK --upgrade
python3 basicPubSub.py \
        -e $endpoint \
        -k ../../../test_client_1/test_client_1.key \
        -c ../../../test_client_1/test_client_1.pem \
        -r ../../../test_client_1/AmazonRootCA1.pem
