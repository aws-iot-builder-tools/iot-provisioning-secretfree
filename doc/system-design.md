
# System Design

The system design defines and puts into context the components that
fulfill roles in the certificate provisioning process in the AWS
Cloud.  The following diagram describes the system components and
their relationships.  Each component has a letter which labels the
component described in the following section **System
Components**. Each component has at least one relationship which at
least one number. The number serves as a label for an action, usually
directional, between two components.

Note that there is consideration for latent certificate retrieval in
the case where the response payload may not be retrieved sufficiently
by the client where instead of the certificate response there is a
pre-signed S3 URL response where the certificate can be retrieved with
the https client and retried in the case of poor network connectivity.

Note that there is consideration for provisioning parity to occur
between ACM PCA and AWS IoT Core provisioning where all provisioning
aspects occur at the time of certificate provisioning. The challenge
in this case is the latent replication of provisioned artifacts across
regions when the client acquires a regional endpoint that may not yet
have the required resources. Further, it may cause complication with
the global provisioning pattern.

## Issuing with ACM PCA

The execution architecture for issuing certificates using ACM PCA is
defined by the following diagram.

![Secretless-ACMPCA.png](img/Secretless-ACMPCA.png)

1. The PKI Admin would have received a CSR from ACM PCA and a *parent
   issuer* then issues the certificate.  The PKI Admin then submits
   the issued certificate to ACM PCA.
2. The PKI Admin must register the issued CA certificate to every
   region where there device may connect.
3. The "device admin" is an abstract role for anyone who has the
   accountability for retrieving the device-id/pubkey payload from the
   manufacturing site and importing those pairs to DynamoDB.
4. The device is powered on, and the device notices that there is no
   provisioned certificate to a slot on the secure serialized flash.
   This triggers the routine for constructing the CSR according the
   product's design. The CSR is POST to API Gateway as a custom header
   value device-csr to endpoint method `/new`.
5. API Gateway received the POST and identifies the method as being
   configured with an Authorizer.  The header value (the CSR) is
   passed to the authorizer for evaluation. The authorizer will read
   the CSR subject value for CN for the device ID.
6. The lambda function attempts to retrieve the public key for the
   device-id enscribed to the CN value. DynamoDB returns the value
   when the device-id exists.  Upon receiving the public key value,
   the lambda function compares that to the CSR signature's public key
   value.  When the public key compares favorably, the lambda function
   issues a 200 response.  Otherwise:  404 is issued when the
   relating pubkey to the device-id is not found, and an access denied
   (GET CODE) when the key does not compare favorably.
7. When the authorizer returns a 200, then the method invokes the
   lambda function responsible for issuing the certificate.  The very
   same CSR is passed along to the lambda function.
8. The AWS Lambda function passes the CSR to ACM PCA for a target CA.
   When all subject line and issuance duration requirements have been
   met, then ACM PCA issues the certificate. Certificate issuance
   may take several seconds, so the lambda function waits until
   issuance completes and retrieves the payload.  The lambda function
   returns the certificate payload under code 200, and returns empty
   string with code 500 otherwise.  The reason for 500 is that it is
   expected that ACM PCA would issue the certificate if all conditions
   are met.  API Gateway consumes the response and passes it along to
   the client; the client should interrogate that a 200 or otherwise
   has been received, and upon a 200 persist the payload to the
   appropriate nonvolatile memory resource.
9. Before the certificate is sent back to API Gateway in step 8, the
   certificate is registered and related objects are instantiated in
   the IoT Core registry.
10. The device recogizes that there is a client certificate available
   to use for authentication. The client attempts to connect to the
   AWS IoT Core endpoint for the first time.
   
   *Note*: there is room for customization in the payload response
   from API Gateway to also include the region-sensitive connectivity
   endpoint.  This value should be saved to NVM for future
   connections.

## Issuing with AWS IoT Core

The execution architecture for issuing certificates using AWS IoT Core
is defined by the following diagram.  Note that issuing certificates
using this method precludes you using the global provisioning pattern
so it should not be considered for large scale provisioning where
global connectivity and resiliency is required.

Note that the authorization steps 1-5 remain the same as ACM PCA
issuance steps 1-6 (with the exception of PKI admin activities) so
they will not be restated here.

![Secretless-IoT.png](img/Secretless-IoT.png)

6. Upon receiving the CSR, the certificate issuer lambda creates the
   certificate with AWS IoT Core using the CSR.  Once done, the lambda
   creates the Thing based on the device-id value represented by the
   CN in the certificate subject.  The policy most often is consistent
   across all things in the particular product line. If already found,
   the certificate is paired with the found policy; otherwise, the
   lambda creates the policy according to the application's
   requirements and links.  Further invocation does not require a
   policy.
7. At this point, all components are created and the certificate has
   been activated, so further connectivity occurs normally.

## Certificate Rotation

The system can partipate in certificate rotation activities. Anytime
the host code interacts with the API Gateway endpoint and the
authenticator identifies the host as having a valid identity that can
participate in the system, the system will issue a certificate.

The system can participate in Intermediate CA rotation use cases when
using ACMPCA.  When the Intermediate CA must be rotated, the PKI
Administrator can perform the required tasks to initiate the new
Intermediate CA to ACMPCA, change the configured Intermediate CA in
the ACMPCA issuer Lambda function, revoke the current Intermediate CA,
and trigger cascading revocation so all reconnecting devices can
fallback to certificate reissue when authentication fails upon host
code connection.

## Multiple Region

The system can partipate in multiple region activation
activities. Notably, there should be one domain name that the host coe
should be sing to connect to the system, using Route53 to dynamically
route depending on route latency.

To achieve Multi Region in this case, the Intermediate CA issued from
every ACMPCA instance in every region must be multi region replicated
for every participating IoT Core service.

The Multi Region pattern can then be implemented when the certificate
gets registered to AWS IoT Core.  Note that the same patterns are used
for certificate rotation in the case where the new certificate is
registered and the old certificate is revoked.
