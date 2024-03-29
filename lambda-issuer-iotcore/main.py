import json
import boto3
import time
import base64
import os
import sys
import OpenSSL.crypto
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM, dump_publickey

def provision_certificate( csr ):
    iot = boto3.client('iot')

    try:
        return iot.create_certificate_from_csr( certificateSigningRequest=csr.decode('ascii'),
                                                setAsActive=True )
    except Exception as e:
        print("Certificate issue failed: ", e)
        return None

    return None

# The certificate is already deployed.
def deploy_certificate( certificate ):
    return None

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
        iot.describe_thing( thingName = device_id )
        thing_name = device_id
    except:
        print( "Thing [{}] does not exist. Will create.".format( device_id ) )

    if ( thing_name == None ):
        try:
            iot.create_thing( thingName = device_id )
            thing_name = device_id
        except:
            print( "Thing [{}] does not exist and failed to create.".format( device_id ) )
            return False

    # Attach the Thing to the Certificate.
    try:
        iot.attach_thing_principal( thingName = thing_name, principal = certificate_arn )
    except:
        return False

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
    print(policy_document.format( region, account ))
    try:
        iot.get_policy( policyName = policy_name )
    except:
        create_policy = True

    if ( create_policy == True ):
        iot.create_policy( policyName = policy_name,
                           policyDocument = policy_document.format( region, account ) )

    iot.attach_policy( policyName = policy_name, target = certificate_arn )

def lambda_handler(event, context):
    csr = base64.b64decode(event['headers']['device-csr'])
    req = load_certificate_request( FILETYPE_PEM, csr )
    device_id = req.get_subject().CN
    response = provision_certificate( csr )
    region = context.invoked_function_arn.split(":")[3]
    account = context.invoked_function_arn.split(":")[4]

    # Send the certificate to AWS IoT. We assume the issuing CA has already
    # been registered.
    if response is None:
        return None

    certificate_body = response['certificatePem']
    certificate_arn = response['certificateArn']

    # Create the Thing object and attach to the deployed certificate

    response = deploy_thing( device_id, certificate_arn )

    # The entire transaction failed, so report failure.
    if ( response == False ):
        return None

    # Create the Policy if necessary, and attach the created Policy (or
    # existing Policy) to the Thing.

    deploy_policy( certificate_arn, region, account )
    if ( response == False ):
        return None

    # Return the certificate to API Gateway.
    
    return certificate_body
