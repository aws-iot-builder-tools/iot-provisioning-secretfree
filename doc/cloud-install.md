# System Implementation and Deployment

## Prerequisites

The majority of the installation is performed through
CloudFormation. However, **you must configure the certificate issuer
and device yourself**.  Meaning, you need to choose the issuer (ACM
PCA or AWS IoT Core) the implement the device firmware for your
target microcontroller.

### Certificate Issuer

The System Design section expressed that you may use ACM PCA or
AWS IoT for issuing certificates. For large scale production
systems, it is strongly recommended you use ACM PCA to enable
global provisioning.

ACM PCA setup and configuration is not done through CloudFormation
since the issuer certificate must be issued by a parent CA that is
outside ACM PCA operation. As such, the process can be varying in
nature.  The Demonstration section shows a "self-signed" issuer CA
chain configuration that can be used for testing purposes.

### Device

The device must have firmware implemented, or is using a peripheral, that:

1.  Can derive the public key from the device identity private key.
2.  Can issue a CSR signed by the device identity private key.

### CloudFormation

The system is deployed using CloudFormation. The CloudFormation
template is at [cfn/secretfree.yml](cfn/secretfree.yml).

The CloudFormation result emits three values.  These values are
exported in case you wish to build upon them.  Specifically, an
importer to the DynamoDB table may later be developed, in which
case the target database would need to be known.

- ProvisioningTableArn
- ProvisioningTableStream
- ProvisioningTableName

The remaining CloudFormation sections are **Resources** where the
parent node is `Resources.`

<a id="orgaaaa270"></a>

## AWS Lambda: Layer: pyOpenSSL

In this framework, two Lambda functions are implemented that use
the pyOpenSSL library.  Today, it is most natural to package
libraries into Layers and then apply the Layer to the lambda
function.  The library also contains natively compiled code which
requires building either on EC2 or in a container.  We will be
building the layer in a container.

In this section, create the pyOpenSSL Lambda function layer.  The
current version is **TODO**.  You must have `docker` installed and
running to perform the following. If you cannot have docker, you
will need to perform this work manually on Amazon Linux with
`pyenv`.

The script that creates the payload for the layer is
[script/package-lambda-layer-pyopenssl.sh](script/package-lambda-layer-pyopenssl.sh).

The zip file produced by the package script gets installed by the
CloudFormation template by the **pyOpensslLayer** resource.

<a id="org6e7346b"></a>

## AWS Lambda: Lambda Authorizer for API Gateway

In this section, we deploy the Lambda Authorizer Lambda Function.  The
bulk of the authorizer code was taken from the [python blueprint on
Github](https://github.com/awslabs/aws-apigateway-lambda-authorizer-blueprints/blob/master/blueprints/python/api-gateway-authorizer-python.py). The
Custom Authorizer interrogates the header value that includes the
Device ID and the Signature.

The main source for the Lambda Authorizer is at [lambda-authorizer/main.py](lambda-authorizer/main.py).

The code must be zipped up in preparation for submitting the
payload as part of the Lambda function deployment.

    P=$(pwd)/$(dirname $0)
    mkdir -p ../tarz
    cd ../lambda-authorizer
    zip -r ../tarz/lambda-authorizer.zip .

The code deployment requires the pointer to the DynamoDB Table
since the public key must be fetched.  When installing the Lambda
function, three resources must be implemented:

-   Invoke permission: what can invoke this lambda function
-   Role: what this lambda function can do outside its immediate
    scope
-   Payload: the lambda function definition itself

To understand the deployment, see the CloudFormation resources for
**PerSkuLambdaAuthorizer**,
**PerSkuLambdaAuthorizerInvokePermissions**, and
**PerSkuLambdaAuthorizerExecutionRole**.

<a id="orgb7177d3"></a>

## AWS Lambda: ACM based certificate issuance

The code for certificate issuance by ACM is at
[lambda-issuer-acmpca/main.py](lambda-issuer-acmpca/main.py).

The following diagram describes the execution flow for ACM PCA
issuance, followed by an explanation of main steps. Note that this
flow occurs after the [Lambda
Authorizer](aws-lambda:-lambda-authorizer-for-api-gateway) completes
successfully.

The code must be zipped up in preparation for submitting the
payload as part of the Lambda function deployment.  This script is at
[script/package-lambda-issuer-acmpca.sh](script/package-lambda-issuer-acmpca.sh).

## AWS Lambda: AWS IoT Core based certificate issuance

The system provides a mechanism to provision certificates through IoT
Core.  The mechanism is meant for prototyping only.  The reason is for
production workloads it is recommended to use multi-region
deployment. At this time, IoT Core issues certificates cannot be
replicated to multiple regions.

The lambda function is invoked by API Gateway via the **proto**
resource with POST verb.  The CSR payload is passed to the Lambda
function by transform.

The code must be zipped up in preparation for submitting the payload
as part of the Lambda function deployment.  This script is at
[script/package-lambda-issuer-iotcore.sh](script/package-lambda-issuer-iotcore.sh).

## API Gateway Endpoint, Resource, Method, Model, and Response

API Gateway is used to manage the plumbing for the device POST to
the cloud composed of a basic header parameter of a CSR payload.

Once created, then we will create the resource upon which IoT
devices will call with POST and the CSR payload in the header.  The
reason the CSR is in the header is the public key derived from the
signature on the CSR will be used for the custom authorizer, and the
only way to pass it to the custom authorizer is the header.

The API is installed using the CloudFormation script.

## Upload and Deployment

Several scripts have been added to aid in the deployment process.
The template and lambda function payloads must be staged to Amazon
S3. After staging, you can invoke CloudFormation using the uploaded
template.

First, invoke the `build-and-upload.sh` script.  This script invokes
the scripts to build the layer and lambda function packages
described in the previous section.  It also ensures you have an S3
bucket created.

The script has relatively sane defaults.  If you are running in
EC2, you will likely need to override these values.

-   `PREFIX`: the same value as `$USER` in your command line
    environment.  If you find that the S3 bucket name is not usique,
    you will need to override this value.
-   `REGION`: the same value configured for your default AWS
    credential.

If you are configuring for use with AWS IoT Core (recommended for
prototyping or evaluation), and running from your local system, you
would invoke the following:

    ./build-and-upload.sh

If you are configuring this with ACM PCA (strongly recommended for
multi-region production environments).  First you need to get the
Arn.  The best way to search for that might me the CA's
CommonName.  For example, when having the Common Name
`us-east-1.widgiot.automatra.net`, we could find it by:

    COMMON_NAME=${1:=us-east-1.widgiot.automatra.net}
    CertificateAuthorityArn=$(aws acm-pca list-certificate-authorities \
                                  --query "CertificateAuthorities[?CertificateAuthorityConfiguration.Subject.CommonName=='${COMMON_NAME}'].Arn" \
                                  --output text)

This script is named get-pcmcia-ca-arn.sh in scripts/ for your convenience.

The first argument, which is
the ACM PCA CA Arn, must be applied to the command line, for example:

```bash
./build-and-upload.sh ${CertificateAuthorityArn}
```

And if you want to override the SKUNAME and possibly the target
REGION, the command line would be configured like:

```bash
SKUNAME=superUniquePrefix REGION=us-west-2 ./build-and-upload.sh ${CertificateAuthorityArn}
```
