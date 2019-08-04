import json
import boto3
import time
import base64
import os
import OpenSSL.crypto
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM, dump_publickey

def get_pubkey( req ):
    device_id = req.get_subject().CN

    d = boto3.client('dynamodb')
    s3 = boto3.resource('s3')
    
    response = d.get_item(
        Key={ 'device-id': { 'S' : device_id } },
        TableName='widgiot-public-keys'
    )

    s3_bucket = response['Item']['pubkey-bucket']['S']
    s3_object = response['Item']['pubkey-object']['S']
    content_object = s3.Object(s3_bucket, s3_object)
    file_content = content_object.get()['Body'].read().decode('utf-8')

    return file_content

def provision_certificate( csr, pubkey ):
    acmpca = boto3.client('acm-pca')
    ca_arn = os.environ['ACMPCA_CA_ARN']
        
    # Create the Certificate
    # TODO: Automatically compute days remaining ... somehow?
    cert = acmpca.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        SigningAlgorithm='SHA256WITHRSA',
        Csr=csr,
        Validity={
            'Value': 150,
            'Type': 'DAYS'
        },
        IdempotencyToken='1234'
    )
    
    # Fetch the certificate
    err = 1
    while 1:
        try:
            certificate = acmpca.get_certificate(
                CertificateAuthorityArn=ca_arn,
                CertificateArn=cert['CertificateArn']
            )
            return certificate
        except:
            print("Certificate not ready yet")
            time.sleep(1)


def lambda_handler(event, context):
    print(event)
    print(context)
    csr = base64.b64decode(event['headers']['device-csr'])
    req = load_certificate_request( FILETYPE_PEM, csr )

    pubkey = get_pubkey(req)
    response = provision_certificate(csr, pubkey)

    return response['Certificate']
