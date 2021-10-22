## AWS Certificate Manager Provisioning

**NOTE** only follow this section if you want to provision certificates
with ACM PCA.

With AWS IoT Provisioning, in order to use the provisioning
template, the invocation will need to be made by AWS Lambda. No PKI
work is required for this section since the process uses AWS IoT to
issue the certificate on our behalf, and JITP is not availabile for
AWS IoT issued certificates.

In this section, we install and configure AWS Certificate Manager
for Private Certificate Authority.

At the time of writing, AWS Certificate Manager for Private
Certificate Authority allows configuring a Subuordinate CA only.
This means we need to define the certificate hierarchy while
keeping in mind multi-region.  There are several choices based on
blast radius confinement techniques. In the case of this
demonstration, we will create a Root CA, an Intermediate CA
representing a product line. Subordinate CAs are then imported on a
per-region to facilitate per-region registration; later, each CA is
to be individually registered with AWS IoT.

We first need to create the certificate hierarchy (roughly taken
from Bulletproof SSL and TLS - for more information, check that
book).

### Root Certificate Authority

When creating a root certificate, this means it's the root certificate
for your organziation. Usually, you will want a verifiable issuer
such as Amazon, Thawte, etcetera.  Since we would not want to do this
for prototyping, the root authority will be self-signed.  **Do not do
this for production workloads. You should have a verifiable root CA
issuer give you an intermediate that represents your entity**.

#### Root Certificate Short Story

To initialize the root authority, use the `demo/script/root-ca.sh`
script. The script does not require any parameters if you want to use
the demo defaults (see [Long Story](#root-certificate-long-story)).

Jump to the [Intermediate Certificate
Authority](intermediate-certificate-authority) section when completed.

#### Root Certificate Long Story

Create the base directory.  You can create the root directory name
whatever you like, but let's pretend you work for a company named
`widgies` with product name `widgiot`.  Note that we are working in a
UNIX-like environment so if you're running Windows, instantiate a
small EC2 instance to do your work.

```bash
cd ~ && mkdir -p provisioning/root-ca
cd provisioning/root-ca
mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber
```

Create the root-ca.conf file.  There is a challenge here that you need
to be aware.  When you are issuing CSRs for clients, the policy at the
CA level must meet the demands at the CSR level. For example, if you
want to put Locality (L) in the Subject, it must be defined in this
OpenSSL configuration as at least optional.  Accordingly, while we may
not issue the CA with locality, the client certificate *may* always
issue with locality.

This is an example Root CA using a domain that the author owns.  You
will need to modify this template with your target domain.

    [default]
    name                    = root-ca
    domain_suffix           = automatra.net
    aia_url                 = http://$name.$domain_suffix/$name.crt
    crl_url                 = http://$name.$domain_suffix/$name.crl
    ocsp_url                = http://ocsp.$name.$domain_suffix:9080
    default_ca              = ca_default
    name_opt                = utf8,esc_ctrl,multiline,lname,align
    
    [ca_dn]
    countryName             = "US"
    organizationName        = "Automatra"
    commonName              = "Root CA"
    
    [ca_default]
    home                    = .
    database                = $home/db/index
    serial                  = $home/db/serial
    crlnumber               = $home/db/crlnumber
    certificate             = $home/\$name.crt
    private_key             = $home/private/$name.key
    RANDFILE                = $home/private/random
    new_certs_dir           = $home/certs
    unique_subject          = no
    copy_extensions         = none
    default_days            = 3650
    default_crl_days        = 365
    default_md              = sha256
    policy                  = policy_c_o_match
    
    [policy_c_o_match]
    countryName             = match
    stateOrProvinceName     = optional
    organizationName        = match
    organizationalUnitName  = optional
    commonName              = supplied
    localityName            = optional
    emailAddress            = optional
    
    [req]
    default_bits            = 4096
    encrypt_key             = yes
    default_md              = sha256
    utf8                    = yes
    string_mask             = utf8only
    prompt                  = no
    distinguished_name      = ca_dn
    req_extensions          = ca_ext
    
    [ca_ext]
    basicConstraints        = critical,CA:true
    keyUsage                = critical,keyCertSign,cRLSign
    subjectKeyIdentifier    = hash
    [sub_ca_ext]
    authorityInfoAccess     = @issuer_info
    authorityKeyIdentifier  = keyid:always
    basicConstraints        = critical,CA:true,pathlen:0
    crlDistributionPoints   = @crl_info
    extendedKeyUsage        = clientAuth,serverAuth
    keyUsage                = critical,keyCertSign,cRLSign
    nameConstraints         = @name_constraints
    subjectKeyIdentifier    = hash
    
    [crl_info]
    URI.0                   = $crl_url
    [issuer_info]
    caIssuers;URI.0         = $aia_url
    OCSP;URI.0              = $ocsp_url
    
    [name_constraints]
    permitted;DNS.0=example.com
    permitted;DNS.1=example.org
    excluded;IP.0=0.0.0.0/0.0.0.0
    excluded;IP.1=0:0:0:0:0:0:0:0/0:0:0:0:0:0:0:0
    [ocsp_ext]
    authorityKeyIdentifier  = keyid:always
    basicConstraints        = critical,CA:false
    extendedKeyUsage        = OCSPSigning
    keyUsage                = critical,digitalSignature
    subjectKeyIdentifier    = hash

##### Root CA: quick


##### Root CA: details

Create the private key for the Root CA.

```bash
openssl req -new                         \
            -config  root-ca.conf        \
            -out     root-ca.csr         \
            -keyout  private/root-ca.key \
            -passout pass:nopass
```

Create the self-signed certificate.  Note the **selfsign** flag.  In
production, you will NOT do this.

```bash
openssl ca -selfsign            \
           -config root-ca.conf \
           -in root-ca.csr      \
           -out root-ca.crt     \
           -extensions ca_ext   \
           -batch               \
           -passin pass:nopass
```

Create the private key and CSR for OCSP.

```bash
openssl req -new                                                \
            -newkey   rsa:2048                                  \
            -subj    "/C=US/O=Automatra/CN=OCSP Root Responder" \
            -keyout  private/root-ocsp.key                      \
            -out     root-ocsp.csr                              \
            -batch                                              \
            -passout pass:nopass
```

Issue the OCSP certificate.

```bash
openssl ca -config     root-ca.conf  \
           -in         root-ocsp.csr \
           -out        root-ocsp.crt \
           -extensions ocsp_ext      \
           -days       30            \
           -batch                    \
           -passin     pass:nopass
```

The Root CA and OCSP certificate has been issued.

### Intermediate Certificate Authority

Create structure for the WidgIoT Intermediate Certificate.
WidgIoT is the example name we are giving for demonstration
purposes.

First, initialize the database for the Intermediate CA.

```bash
cd ~ && mkdir -p provisioning/intermediate-ca
cd provisioning/intermediate-ca
mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber
```

Use the configuration file for the Intermediate CA representing the
WidgIoT product line.  The meaning of this entire configuration is
beyond the scope of this README and should be analyzed by referencing
the aforementioned book.

The file is at (demo/intermediate-ca/widgiot-ca.conf).


The following command creates the private key and generate the CSR for
the WidgIoT product line.  This command is in file
(demo/intermediate-ca/intermediate-ca.sh).

```bash
openssl req -new                           \
            -config widgiot-ca.conf        \
            -out widgiot-ca.csr            \
            -keyout private/widgiot-ca.key \
            -batch                         \
            -passout pass:nopass
```

Have the root CA issue the intermediate CA.  This command is in file
(demo/intermediate-ca/intermediate-ca.sh)

```bash
cd ../root-ca/
openssl ca -config root-ca.conf \
           -in ../widgiot-ca/widgiot-ca.csr \
           -out widgiot-ca.crt \
           -extensions sub_ca_ext \
           -batch \
           -passin pass:nopass
cp widgiot-ca.crt ../widgiot-ca
cp root-ca.crt ../widgiot-ca #for ease of operation when issuing aws cert
```

Next, we will be creating the Device Issuer CA which means working
with ACM PCA.

### Device Issuer Certificate Authority

Create and change to directory for managing the ACM PCA issued
certificates.

```bash
cd ~ && mkdir -p provisioning/widgiot-ca
cd provisioning/widgiot-ca
```

Create an S3 bucket policy for the CRL lists that will be used by the
cloudy Private CA.

In your shell, define your `PREFIX` name.  Amazon S3 is a *global*
service which means bucket names must me globally unique.  In this
case, we will use the author's GitHub ID.

```bash
PREFIX=rpcme
```

The bucket policy must applied to constrain access to ACM PCA since,
at least at this time, only ACM PCA requires access.  Note that PREFIX
and REGION are variant based on your semantic meaning and intent.
Meaning, PREFIX is wholly variant based on your product.  The REGION
is variant based on your primary REGION; even though Amazon S3 is a
global service, the 'seeded' region should be named (or else it is
inferred).


    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "acm-pca.amazonaws.com"
          },
          "Action": [
            "s3:PutObject",
            "s3:PutObjectAcl",
            "s3:GetBucketAcl",
            "s3:GetBucketLocation"
          ],
          "Resource": [
            "arn:aws:s3:::PREFIX-acm-pca-crl-REGION-widgiot/*",
            "arn:aws:s3:::PREFIX-acm-pca-crl-REGION-widgiot"
          ]
        }
      ]
    }

Create the bucket.

```bash

BUCKET=${PREFIX}-acm-pca-crl-${REGION}-widgiot

aws s3api create-bucket \
    --bucket ${BUCKET}  \
    --query  Location   \
    --region ${REGION}
```

Apply the policy.

```bash
aws s3api put-bucket-policy \
    --bucket ${BUCKET}      \
    --policy file://../conf/s3-${REGION}-widgiot-ca.json
```

Create the input text for the CA configuration.

```json
{
    "KeyAlgorithm":     "RSA_2048",
    "SigningAlgorithm": "SHA256WITHRSA",
    "Subject": {
        "Country":            "US",
        "Organization":       "Automatra",
        "OrganizationalUnit": "WidgIoT us-east-1",
        "State":              "VA",
        "Locality":           "Anywhere",
        "CommonName":         "us-east-1.widgiot.automatra.net"
    }
}
```

Create the input text for the CA revocation list.

```json
{
    "CrlConfiguration": {
        "Enabled":          true,
        "ExpirationInDays": 7,
        "CustomCname": "    some_name.crl",
        "S3BucketName":     "PREFIX-acm-pca-crl-REGION-widgiot"
    }
}
```

You are responsible for ensuring that the input text for the
revocation list is applicable.


Create a new CA for us-east-1.  Note documentation at
<https://docs.aws.amazon.com/acm-pca/latest/userguide/PcaCreateCa.html>
says to use —tags but it's not a valid flag for this operation.

```bash
CRT_AUTH_ARN=$(aws acm-pca create-certificate-authority \
                   --certificate-authority-configuration file://${REGION}-widgiot-config.txt \
                   --revocation-configuration file://${REGION}-widgiot-revoke-config.txt \
                   --certificate-authority-type "SUBORDINATE" \
                   --idempotency-token 98256344 \
                   --region ${REGION} \
                   --query CertificateAuthorityArn) \
                   --output text
```

Get the CSR from the cloud.  note that the CertificateAuthorityArn
will be unique and the previous command should capture the output
and have it applied to the forthcoming command.

```bash
aws acm-pca get-certificate-authority-csr \
    --certificate-authority-arn ${CRT_AUTHARN} \
    --output text \
    --region ${REGION} \
    > ${REGION}-widgiot-ca.csr
```
    
Issue the CA certificate using the Intermediate CA.  

```bash
cd ../widgiot-ca
    
openssl ca -config     widgiot-ca.conf                    \
           -in         ../aws-ca/${REGION}-widgiot-ca.csr \
           -out        ${REGION}-widgiot-ca.crt           \
           -extensions sub_ca_ext                         \
           -batch -passin pass:nopass
    
openssl x509 -in      ${REGION}-widgiot-ca.crt \
             -out     ${REGION}-widgiot-ca.pem \
             -outform PEM

openssl x509 -in widgiot-ca.crt \
             -out widgiot-ca.pem \
             -outform PEM
    
openssl x509 -in      ../root-ca/root-ca.crt \
             -out     root-cpem \
             -outform PEM
    
cat widgiot-ca.pem root-ca.pem > ${REGION}-widgiot-ca-chain.pem
```

Two distinct events have happened at this point.  First, the parent
issuer granted the CA under the authorized security context. NOTE that
this event is fraught with peril and must be WHOLLY portected.

Second, the authoritative chain has been concatenated.  This is a
lesser event which is more administrative but underlines the authority
chain.  ACM PCA is concerned with the CA and the authority chain.

```bash

aws acm-pca import-certificate-authority-certificate \
            --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
            --certificate                file://${REGION}-widgiot-ca.pem \
            --certificate-chain          file://${REGION}-widgiot-ca-chain.pem \
            --region                     ${REGION}
```

Import the CA to AWS IoT Core.  Start by requesting an import
code.

```bash
code=$(aws iot get-registration-code \
               --query registrationCode \
               --region ${REGION} --output text \
               --query registrationCode )
```

Construct the CSR with the import code.

```bash
openssl genrsa -out useast1-verification-request.key 2048
    
openssl req -new \
            -key ${REGION}-verification-request.key \
            -out ${REGION}-verification-request.csr \
            -subj "/C=US/ST=VA/L=Anywhere/O=Automatra/OU=WidgIoT us-east-1/CN=$code"
    
# request the certificate from ACM
            
CERTIFICATE_ARN=$(aws acm-pca issue-certificate \
                      --certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
                      --csr file://useast1-verification-request.csr \
                      --signing-algorithm "SHA256WITHRSA" \
                      --validity Value=364,Type="DAYS" \
                      --idempotency-token 1234     \
                      --region us-east-1 --output text \
                      --query CertificateArn)
    
aws acm-pca get-certificate \
--certificate-authority-arn  ${CERTIFICATE_AUTHORITY_ARN} \
        --certificate-arn ${CERTIFICATE_ARN} \
        --output text --region ${REGION} > verification.pem
```

Before adding the CA to AWS IoT Core, there are several things
that must be put into place first:

-   Common **IoT policy** for the application WidgIoT.  We will
    constrain WidgIot to use one ephemeral topic and device
    shadow. This will be constrained by client ID which is same as
    Thing ID.
The CA that resides in ACM PCA must also reside in AWS IoT
Core. When configuring your application to be global using the
multi-region provisioning pattern, this CA must be registered in
every region.

```bash
aws iot register-ca-certificate --ca-certificate file://useast1-widgiot-ca.pem \
                                --verification-cert file://verification.pem \
                                --set-as-active \
                                --query certificateArn \
                                --output text --region ${REGION}
```
