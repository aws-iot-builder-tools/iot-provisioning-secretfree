

### Verifying the ACM Setup

In this test, you issue a client certificate from ACM PCA by
constructing a private key and CSR manually on your workstation to
understand how ACM PCA issues certificates, the mechanics of
registering the generated certificate to AWS IoT Core, and linking
up the Thing and Policy with the certificate.

**NOTE** to verify one-offs you can also use the script
[test-deploy.sh](script/test-deploy.sh).


```bash
CERTIFICATE_AUTHORITY_ARN=$1
cd ~/ti-provisioning
mkdir test_client_1
cd test_client_1
openssl genrsa -out test_client_1.key 2048
openssl req -new \
            -key test_client_1.key \
            -out test_client_1.csr \
            -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=${PRODUCT}-${REGION}/CN=test_client_1"
```

Submit the CSR to ACM and retrieve the certificate.  In the end to
end, the Lambda function performs this act after signature
verification.

```bash
tc1_cert_arn=$(aws acm-pca issue-certificate \
                           --certificate-authority-arn ${CERTIFICATE_AUTHORITY_ARN} \
                           --csr file://test_client_1.csr \
                           --signing-algorithm "SHA256WITHRSA" \
                           --validity Value=364,Type="DAYS" \
                           --idempotency-token 1234     \
                           --region ${REGION} --output text --query CertificateArn)
    
aws acm-pca get-certificate \
            --certificate-authority-arn ${CERTIFICATE_AUTHORITY_ARN} \
            --certificate-arn ${tc1_cert_arn} \
            --output text \
            --region us-east-1 > test_client_1.pem
```

Import the certificate to AWS IoT Core.  In the end to end, the
Lambda function performs this act after CSR submission and
certificate retrieval.

```bash
    tc1_cert_iot_arn=$(aws iot register-certificate                     \
                           --certificate-pem file://test_client_1.pem   \
                           --ca-certificate-pem file://../widgiot-ca/useast1-widgiot-ca.pem \
                           --query certificateArn --output text --region us-east-1)
    tc1_cert_iot_id=$(echo $tc1_cert_iot_arn | cut -f2 -d /)
    aws iot update-certificate                               \
        --certificate-id $tc1_cert_iot_id                       \
        --new-status ACTIVE \
        --region us-east-1
```

Create the thing and policy.

```bash
aws iot create-thing                  \
    --output text  --region ${REGION} \
    --thing-name test_client_1        \
    --query thingArn
    
aws iot attach-thing-principal        \
    --output text  --region ${REGION} \
    --thing-name test_client_1        \
    --principal ${tc1_cert_iot_arn}
```

```json
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action":["iot:*", "greengrass:*"],
        "Resource": ["*"]
      }]
    }
```

```bash
aws iot ${REGION} create-policy                         \
    --policy-name test_client_1_policy                  \
    --policy-document file://test_client_1_policy.json  \
    --query policyArn --region ${REGION}
     
aws iot ${REGION} attach-principal-policy               \
    --policy-name test_client_1_policy                  \
    --principal ${tc1_cert_iot_arn}                     \
    --region ${REGION}
```

Checkout and configure the AWS IoT SDK for Python and use the
private key, certificate, and endpoint.
\\#+end<sub>src</sub>

Then use the AWS IoT Device SDK for Python to test the
connectivity.

```bash
endpoint=$(aws iot describe-endpoint \
    --endpoint-type iot:Data-ATS \
    --region ${REGION} \
    --query endpointAddress \
    --output text)

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
```


## Running with an Edge Device


If you would like to simulate an edge device using Python, then 

The reference implementation uses the TI CC3220SF.  However, if you do
not have this device then you [Run the Python Test Script](#run-the-python-test-script).
Otherwise, jump to [Run the Texas Instruments CC3220SF](#run-the-texas-instruments-cc3220sf).



## Local testing: AWS Device SDK for Python

The AWS Device SDK for Python includes several test scripts that help
you understand how to interoperate with AWS IoT with Python programs.

If you have not deployed the system yet, please see [Where to
Start](#where-to-start) before continuing.

1. Change directory to the scripts directory.
2. Identify the API Gateway endpoint to want to use to provision the
   certificate. If configured, you can use your [Vanity
   URL](#vanity-domain-names).
3. Generate your private key and download your certificate using the
   `test-deploy.sh` script.
   
   In the first line, assign the endpoint URL value to the variable
   ENDPOINT.
   
   ```bash
   $ ENDPOINT=<your endpoint here>
   $ cd ~/iot-provisioning-secretfree/script
   $ ./test-deploy.sh ${ENDPOINT}
   ```

3. Change directory to your home directory.  Alternatively, change
   directory to a specific directory to where you clone or check out
   source repositories.
   
   ```bash
   $ cd ~
   ```
4. Clone the repository for the [AWS IoT Device SDK for
   Python](https://github.com/aws/aws-iot-device-sdk-python).
   
   ```bash
   $ git clone https://github.com/aws/aws-iot-device-sdk-python
   ```
