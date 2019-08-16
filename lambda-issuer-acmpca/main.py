import json
import boto3
import time
import base64
import os
import OpenSSL.crypto
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM, dump_publickey

def provision_certificate( csr ):
    acmpca = boto3.client('acm-pca')
    ca_arn = os.environ['ACMPCA_CA_ARN']
        
    # Create the Certificate - duration 150 days - very arbitrary
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
    response = provision_certificate( csr )

    return response['Certificate']
