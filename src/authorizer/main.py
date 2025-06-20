"""
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

Lambda function to decompose Infineon based certificate manifest(s) and begin
the import processing pipeline
"""
import base64
import re
import os
import boto3
import OpenSSL.crypto
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM, dump_publickey

def get_pubkey( req ):
    """
    Fetch the public key from the DynamoDB table.
    """
    device_id = req.get_subject().CN
    d = boto3.client('dynamodb')

    response = d.get_item(
        Key={ 'device-id': { 'S' : device_id } },
        TableName=os.environ['SECRETFREE_TABLENAME']
    )

    return response['Item']['pubkey']['S']

def lambda_handler(event, context):
    """
    Main routine
    """
    principal_id = "user|a1b2c3d4"

    # Get the public key from the CSR
    device_csr = base64.b64decode(event['headers']['device-csr']).decode('utf-8')
    req = load_certificate_request( FILETYPE_PEM, device_csr )
    req_pubkey = req.get_pubkey()
    req_pubkey_pem = dump_publickey( FILETYPE_PEM, req_pubkey )

    # Get the public key from Dynamo. Load and then dump to format proper
    # Whole certificate is base64 encoded for maintaining textual integrity
    ori_pubkey_pem = base64.b64decode(get_pubkey(req))
    pubbuf = OpenSSL.crypto.load_publickey(FILETYPE_PEM, ori_pubkey_pem)
    ori_pubkey_pem = dump_publickey( FILETYPE_PEM, pubbuf)

    print(ori_pubkey_pem)
    print(req_pubkey_pem)

    if ori_pubkey_pem == req_pubkey_pem:
        # Return 201 and respond w sigv4 uri to signed certificate
        tmp = event['methodArn'].split(':')
        apiGatewayArnTmp = tmp[5].split('/')
        account_id = tmp[4]

        policy = AuthPolicy(principal_id, account_id)
        policy.restApiId = apiGatewayArnTmp[0]
        policy.region = tmp[3]
        policy.stage = apiGatewayArnTmp[1]
        policy.allowMethod(HttpVerb.POST, "/new")
        policy.allowMethod(HttpVerb.POST, "/proto")

        # Finally, build the policy
        authResponse = policy.build()

        return authResponse
    else:
        raise Exception('Unauthorized')
    
class HttpVerb:
    GET     = "GET"
    POST    = "POST"
    PUT     = "PUT"
    PATCH   = "PATCH"
    HEAD    = "HEAD"
    DELETE  = "DELETE"
    OPTIONS = "OPTIONS"
    ALL     = "*"

class AuthPolicy(object):
    """
    The AWS account id the policy will be generated for. This is used to
    create the method ARNs.
    """
    account_id = ""
    """The principal used for the policy, this should be a unique identifier for the end user."""
    principal_id = ""
    """The policy version used for the evaluation. This should always be '2012-10-17'"""
    version = "2012-10-17"
    """The regular expression used to validate resource paths for the policy"""
    path_regex = "^[/.a-zA-Z0-9-\*]+$"

    """
    these are the internal lists of allowed and denied methods. These are lists
    of objects and each object has 2 properties: A resource ARN and a nullable
    conditions statement.
    the build method processes these lists and generates the approriate
    statements for the final policy
    """
    allowMethods = []
    denyMethods = []

    restApiId = "*"
    """The API Gateway API id. By default this is set to '*'"""
    region = "*"
    """The region where the API is deployed. By default this is set to '*'"""
    stage = "*"
    """The name of the stage used in the policy. By default this is set to '*'"""

    def __init__(self, principal, awsAccountId):
        self.awsAccountId = awsAccountId
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []

    def _addMethod(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resourcePattern = re.compile(self.path_regex)
        if not resourcePattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.path_regex)

        if resource[:1] == "/":
            resource = resource[1:]

        resourceArn = ("arn:aws:execute-api:" +
            self.region + ":" +
            self.awsAccountId + ":" +
            self.restApiId + "/" +
            self.stage + "/" +
            verb + "/" +
            resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })

    def _getEmptyStatement(self, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }

        return statement

    def _getStatementForEffect(self, effect, methods):
        """
        This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy.
        """
        statements = []

        if len(methods) > 0:
            statement = self._getEmptyStatement(effect)

            for curMethod in methods:
                if curMethod['conditions'] is None or len(curMethod['conditions']) == 0:
                    statement['Resource'].append(curMethod['resourceArn'])
                else:
                    conditionalStatement = self._getEmptyStatement(effect)
                    conditionalStatement['Resource'].append(curMethod['resourceArn'])
                    conditionalStatement['Condition'] = curMethod['conditions']
                    statements.append(conditionalStatement)

            statements.append(statement)

        return statements

    def allowAllMethods(self):
        """
        Adds a '*' allow to the policy to authorize access to all methods of an API
        """
        self._addMethod("Allow", HttpVerb.ALL, "*", [])

    def denyAllMethods(self):
        """
        Adds a '*' allow to the policy to deny access to all methods of an API
        """
        self._addMethod("Deny", HttpVerb.ALL, "*", [])

    def allowMethod(self, verb, resource):
        """
        Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy
        """
        self._addMethod("Allow", verb, resource, [])

    def denyMethod(self, verb, resource):
        """
        Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy
        """
        self._addMethod("Deny", verb, resource, [])

    def allowMethodWithConditions(self, verb, resource, conditions):
        """
        Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here:
        http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition
        """
        self._addMethod("Allow", verb, resource, conditions)

    def denyMethodWithConditions(self, verb, resource, conditions):
        """
        Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here:
        http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition
        """
        self._addMethod("Deny", verb, resource, conditions)

    def build(self):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
            (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId' : self.principalId,
            'policyDocument' : {
                'Version' : self.version,
                'Statement' : []
            }
        }

        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Allow",
                                                                                 self.allowMethods))
        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Deny",
                                                                                 self.denyMethods))

        return policy
