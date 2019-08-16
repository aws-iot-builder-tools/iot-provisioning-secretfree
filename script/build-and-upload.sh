#! /bin/bash
P=$(pwd)/$(dirname $0)

if test -z $1; then
    echo ERROR: SKUNAME not defined
    exit 1
else
    SKUNAME=$1
fi

if test -z $2; then
    ACMPCA=0
    ACMPCA_ARN=UNDEF
else
    ACMPCA=1
    ACMPCA_ARN=$2
fi

if test -f ~/.aws/config; then
    DEFAULT_REGION=$(grep ^region ~/.aws/config | tr -s ' = ' ' ' | cut -d' ' -f2)
fi

REGION=${REGION:=${DEFAULT_REGION}}
BUCKET=${SKUNAME}-iot-secretfree-cfn

echo "REGION:  ${REGION}"
echo "SKUNAME: ${SKUNAME}"
echo "ACMPCA:  ${ACMPCA}"
echo "BUCKET:  ${BUCKET}"

echo ""

echo Building Lambda layer
${P}/package-lambda-layer-pyopenssl.sh

echo Building Authorizer Lambda function
${P}/package-lambda-authorizer.sh

echo Building ACMPCA issuer Lambda function
${P}/package-lambda-issuer-acmpca.sh

echo Building AWS IoT Core issuer Lambda function
${P}/package-lambda-issuer-iotcore.sh

echo Verifying staging S3, making if necessary 
bucket_check=$(aws s3api head-bucket --bucket ${BUCKET} 2>&1 | xargs echo | sed -e 's/.*(\(...\)).*/\1/')

echo Check completed.

if test x"${bucket_check}" == x"404"; then
  echo The bucket prefix you have chosen is OK.
  make_bucket=1
elif test x"${bucket_check}" == x"403"; then
  echo The bucket prefix you have chosen is taken by another AWS Account.
  echo Choose another.
  exit 1
else
  echo The bucket prefix you have chosen already exists in your account.  We will use it!
  make_bucket=0
fi


if test ${make_bucket} == 1; then
    echo Creating S3 bucket [${BUCKET}]
    bucket=$(aws s3api create-bucket --output text \
                 --bucket "${BUCKET}" \
                 --query Location)
    if test $? != 0; then
        echo Error creating bucket.  It could have been an itermittent problem.
        echo Please try again.
    fi

    my_ip=$(curl https://ipinfo.io/ip --stderr /dev/null)

    cat <<EOF > /tmp/bucket-policy.json
{
  "Version": "2012-10-17",
  "Id": "S3PolicyId1",
  "Statement": [
    {
      "Sid": "IPAllow",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::${BUCKET}/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "${my_ip}/32"
        }
      }
    }
  ]
}
EOF

    echo Constraining bucket access to this specific device

    aws s3api put-bucket-policy --bucket ${BUCKET} --policy file:///tmp/bucket-policy.json

fi

echo Staging files to S3
aws s3 cp ${P}/../cfn/secretfree.yml \
    s3://${BUCKET}/secretfree.yml

aws s3 cp ${P}/../tarz/lambda-layer-pyopenssl.zip \
    s3://${BUCKET}/lambda-layer-pyopenssl.zip

aws s3 cp ${P}/../tarz/lambda-authorizer.zip \
    s3://${BUCKET}/lambda-authorizer.zip

aws s3 cp ${P}/../tarz/lambda-issuer-acmpca.zip \
    s3://${BUCKET}/lambda-issuer-acmpca.zip

aws s3 cp ${P}/../tarz/lambda-issuer-iotcore.zip \
    s3://${BUCKET}/lambda-issuer-iotcore.zip

echo Invoking CloudFormation

URL=https://${BUCKET}.s3.amazonaws.com/secretfree.yml
stack_id=$(aws cloudformation create-stack --output text \
               --stack-name ${SKUNAME}-iot-provisioning-secretfree \
               --template-url "${URL}" \
               --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
               --parameters ParameterKey=TemplateBucket,ParameterValue=${BUCKET} \
                            ParameterKey=SkuName,ParameterValue=${SKUNAME} \
                            ParameterKey=AcmPcaCaArn,ParameterValue=${ACMPCA_ARN} \
               --query StackId)

if test -z "${stack_id}"; then
    echo ERROR cloudformation invocation failed
    exit 1
fi

echo stack_id is [${stack_id}]
deployment_status=CREATE_IN_PROGRESS

while test "${deployment_status}" == "CREATE_IN_PROGRESS"; do
    echo deployment status: $deployment_status ... wait three seconds
    sleep 3
    
    deployment_status=$(aws cloudformation describe-stacks \
                            --stack-name ${SKUNAME}-iot-provisioning-secretfree \
                            --query "Stacks[?StackName=='${SKUNAME}-iot-provisioning-secretfree'].StackStatus" \
                            --output text)
done

echo deployment status: $deployment_status
