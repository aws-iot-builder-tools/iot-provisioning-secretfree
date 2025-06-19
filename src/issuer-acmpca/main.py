"""
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

Lambda function to decompose Infineon based certificate manifest(s) and begin
the import processing pipeline
"""
import json
import time
import base64
import os
import string
import random
import logging
import boto3
from botocore.exceptions import ClientError
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM

logger = logging.getLogger()
logger.setLevel("INFO")

def provision_certificate( csr ):
    """
    Create the Certificate - duration 150 days - very arbitrary
    TODO: pull the Value up to environment variable driven duration
    TODO: pull up the SigningAlgorithm to include RSA256 as well as
          the two ECC curves
    TODO: Figure out a better way to deal with this idempotency token
    """

    acmpca = boto3.client('acm-pca')
    ca_arn = os.environ['ACMPCA_CA_ARN']
    cert_validity_days = int(os.environ('CERT_VALIDITY_DAYS'))

    cert = acmpca.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        SigningAlgorithm='SHA256WITHRSA',
        Csr=csr,
        Validity={
            'Value': cert_validity_days,
            'Type': 'DAYS'
        },
        IdempotencyToken=''.join(random.choice(string.ascii_lowercase) for i in range(10))
    )

    # Fetch the certificate
    # TODO: this is wildly unacceptable, needs a backoff with iteration cutoff
    while 1:
        try:
            certificate= acmpca.get_certificate(
                CertificateAuthorityArn=ca_arn,
                CertificateArn=cert['CertificateArn']
            )
            return certificate
        except ClientError as error:
            error_code = error.response['Error']['Code']
            error_message = error.response['Error']['Message']
            logger.error("Certificate not ready yet: %s: %s.", error_code, error_message)
            time.sleep(1)
    return None

def deploy_certificate( certificate ):
    iot = boto3.client('iot')

    try:
        # TODO:  pull up values for setAsActive and status to environment variables
        response = iot.register_certificate( certificatePem=certificate,
                                             status='ACTIVE' )
        return response['certificateArn']
    except ClientError as error:
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        logger.error("Could not register certificate: %s: %s.", error_code, error_message)
        raise error

# The deploy_thing function assumes a unique identifier for a given SKU.
# Since this can be a certificate reissue, an existing Thing will be attached
# to the newly issued certificate.  Deactivation of existing attached certificates
# is outside the bounds of this operation.

def deploy_thing( device_id, certificate_arn ):
    iot = boto3.client('iot')

    # Identify if an existing Thing exists with the device ID. If yes, then use
    # that Thing for certificate attachment.  Otherwise, create a new Thing.

    thing_name = None

    try:
        iot.describe_thing(thingName=device_id)
        thing_name = device_id
    except ClientError as error:
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        logger.info("Thing [%s] does not exist. Will create: %s: %s.",
                    device_id, error_code, error_message)
        try:
            iot.create_thing(thingName=device_id)
            thing_name = device_id
        except ClientError as error_cr:
            error_code = error_cr.response['Error']['Code']
            error_message = error_cr.response['Error']['Message']
            logger.info("Thing [%s] does not exist and failed to create. %s: %s.",
                        device_id, error_code, error_message)
            raise error_cr

    # Attach the Thing to the Certificate.
    try:
        iot.attach_thing_principal( thingName = thing_name, principal = certificate_arn )
    except ClientError as error:
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        logger.info("Thing [%s] failed to attach to principal [%s]. %s: %s.",
                    device_id, certificate_arn, error_code, error_message)
        raise error
    return True

# The deploy_policy function is an example for deploying a single
# policy for a given SKU. For simplicity, the policy is the same as
# what is deployed for the Python example from the Onboard Wizard.

def deploy_policy( certificate_arn, region, account ):
    policy_name = os.environ["SKUNAME"]
    iot = boto3.client('iot')
    create_policy = False
    
    policy_document = '''{{
  "Version": "2012-10-17",
  "Statement": [
    {{
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Receive"
      ],
      "Resource": [
        "arn:aws:iot:{0}:{1}:topic/sdk/test/java",
        "arn:aws:iot:{0}:{1}:topic/sdk/test/Python",
        "arn:aws:iot:{0}:{1}:topic/topic_1",
        "arn:aws:iot:{0}:{1}:topic/topic_2"
      ]
    }},
    {{
      "Effect": "Allow",
      "Action": [
        "iot:Subscribe"
      ],
      "Resource": [
        "arn:aws:iot:{0}:{1}:topicfilter/sdk/test/java",
        "arn:aws:iot:{0}:{1}:topicfilter/sdk/test/Python",
        "arn:aws:iot:{0}:{1}:topicfilter/topic_1",
        "arn:aws:iot:{0}:{1}:topicfilter/topic_2"
      ]
    }},
    {{
      "Effect": "Allow",
      "Action": [
        "iot:Connect"
      ],
      "Resource": [
        "arn:aws:iot:{0}:{1}:client/sdk-java",
        "arn:aws:iot:{0}:{1}:client/basicPubSub",
        "arn:aws:iot:{0}:{1}:client/sdk-nodejs-*"
      ]
    }}
  ]
}}'''

    try:
        iot.get_policy( policyName = policy_name )
    except:
        create_policy = True

    if ( create_policy == True ):
        response = iot.create_policy( policyName = policy_name,
                                      policyDocument = policy_document.format( region, account ) )
        if ( response == None ): return None

    try:
        iot.attach_policy( policyName = policy_name, target = certificate_arn )
    except:
        return False

def lambda_handler(event, context):
    # Whoami and Whatami is important for construction region sensitive ARNs
    region = context.invoked_function_arn.split(":")[3]
    account = context.invoked_function_arn.split(":")[4]

    csr = base64.b64decode(event['headers']['device-csr'])
    req = load_certificate_request( FILETYPE_PEM, csr )
    device_id = req.get_subject().CN
    response = provision_certificate( csr )

    certificate = response['Certificate']

    # Send the certificate to AWS IoT. We assume the issuing CA has already
    # been registered.

    certificate_arn = deploy_certificate( certificate )
    if certificate_arn is None:
        return None

    # Create the Thing object and attach to the deployed certificate

    response = deploy_thing( device_id, certificate_arn )
    if response is False:
        return None

    # Create the Policy if necessary, and attach the created Policy (or
    # existing Policy) to the Thing.

    response = deploy_policy( certificate_arn, region, account )
    if response is False:
        return None

    # Return the certificate to API Gateway.
    iot = boto3.client('iot')
    endpoint = iot.describe_endpoint(endpointType = 'iot:Data-ATS')
    payload = { 'certificate': certificate,
                'endpoint': endpoint['endpointAddress'] }
    return json.dumps(payload)
