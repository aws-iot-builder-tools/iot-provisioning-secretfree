"""
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

Utility lambda layer unit testing
"""
import os
import io
import json
import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

from pytest import raises

from moto import mock_aws, settings
from botocore.exceptions import ClientError
from boto3 import resource, client

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID
from cryptography import x509

from src.issuer_iotcore.main import get_cn_attribute

@mock_aws(config={
    "core": {
        "mock_credentials": True,
        "reset_boto3_session": False,
        "service_whitelist": None,
    },
    'iot': {'use_valid_cert': True}})
class TestIssuerIotcore(TestCase):
    """Unit tests for the aws_utils common function module"""
    def setUp(self):
        self.rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.ec_key = ec.generate_private_key(curve=ec.SECP384R1())

    def test_pos_get_cn_attribute_ec(self):
        """get the cn attr of an ec derived csr"""
        cn = str(uuid.uuid4())
        builder = x509.CertificateSigningRequestBuilder()
        builder = builder.subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
        builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        request = builder.sign(self.ec_key, hashes.SHA256())
        request_payload = request.public_bytes(Encoding.PEM)
        assert get_cn_attribute(csr=request_payload) == cn

    def test_pos_get_cn_attribute_rsa(self):
        """get the cn attr of an rsa derived csr"""
        pass

    def tearDown(self):
        pass
