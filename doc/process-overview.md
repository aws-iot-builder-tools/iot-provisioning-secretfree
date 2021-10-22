# Process Overview

The processes for the device manufacturer span across three areas:
management system deployment, importing public credentials, and
issuing credentials.  The first area initializes the cloud side
infrastructure. The second area defines the process of, on the
manufacturing line, retrieving the public key derived by the immutable
root of trust (private key) on the CC32xx microprocessor, and saving
the public key to storage.  The third area relates to the workflows
for certificate provisioning to the microprocessor as well as AWS IoT,
and the subsequent provisioning of relating artifacts such as the IoT
Thing, Policy, Group, and so forth.

The general premise for this process is, at device initialization by
the consumer, the firmware constructs a Certificate Signing Request
(CSR) and sends the payload, along with the microprocessor serial
number, to a REST endpoint. The endpoint has an custom
authentication method implemented to verify the signature on the
CSR. Upon verification, the CSR is sent to a code block that is
responsible for orchestrating the certificate issuance and
registration with AWS IoT Core. The process that enables this
capability is, at manufacturing time, being able to derive the
public key from the microprocessor, stage on storage, and then later
import to the AWS Cloud.

This paper defines a Proof of Concept and does not in any way infer
that the mechanisms decribed herein have been hardened and are
production ready.  Further, in the demo section, this paper describes
the design and operation for IoT credential provisioning with respect
to the functionality present in the Texas Instruments CC32xx
microcontroller family.  While not the only mechanism applicable to
this microcontroller, this process presents you with the flexibility
and low logistical friction that benefits customers.
