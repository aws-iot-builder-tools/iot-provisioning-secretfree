## IoT Provisioning Secret-free

![Coverage](.github/coverage.svg)
![pylint](.github/linting.svg)
![samlint](.github/samlint.svg)
![sambuild](.github/sambuild.svg)

This solution enables you to define a process to decouple
manufacturing from the provisioning process while assuring that
private secrets do not have the opportunity to be exposed at any point
throughout supply chain, manufacturing, and on-boarding.

## Table of Contents

* [Where to Start](#where-to-start)
* [Technical Requirements](doc/technical-requirements.md)
* [Process Overview](doc/process-overview.md)
* [System Design](doc/system-design.md)
* [Demonstrations](#demonstrations)
  * [POSIX Demonstration](doc/posix_demo.md)
  * [CC32xx Demonstration](doc/cc32xx_demo.md)

## Where to Start

Managing the credential lifecycle from sunrise to sunset can be
challenging. Identifying the approach early the product development
lifecycle can reduce or completely eliminate credential delivery risk
for when you go into production.

To quickly identify where to start, identify your goal.  It will be
one of the following.

- **Prototyping**.  I want to deploy the system to solution using a
  single AWS region.  I do not know if I want AWS or ACM-PCA
  provisioning yet, so make it simple.
  
  Jump to [Start Prototyping](doc/start-prototyping.md).
- **Prototyping**.  I want to prototype multi-region credential
  provisioning with control over the Certificate Authority issuing the
  certificate using a self-signed Certificate Authority.
  
  Jump to  [Start Multi Region Prototyping](doc/start-multi-region-prototyping.md).
- **Production**. I want to deploy the system for a specific region
  with AWS issuing the certificate.
  
  Jump to [Start Single Region](doc/start-single-region.md).
- **Production**. I want to deploy the system at scale for single or
  multi-region with control over the Certificate Authority issuing the
  certificate.
  
  Jump to  [Start Multi Region Production](doc/start-multi-region-production.md).

After setting up, go to the **Demonstrations** section to experience
the system from a host programming perspective.

## Demonstration

The automation for deploying the code installs both ACM PCA and AWS
IoT based issuance Lambdas. The API Gateway endpoint you invoke
determines the issuer.  If you will be using AWS IoT as the issuer,
skip to the [Test Data Load](#test-data-load) section.

* [POSIX Demonstration](doc/demo_posix.md)
* [CC32xx Demonstration](doc/cc32xx_demo.md)

## License Summary

This sample code is made available under the MIT-0 license. See the LICENSE file.
