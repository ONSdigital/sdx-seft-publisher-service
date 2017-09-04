# sdx-seft-publisher-service

[![Build Status](https://travis-ci.org/ONSdigital/sdx-seft-publisher-service.svg?branch=master)](https://travis-ci.org/ONSdigital/sdx-seft-publisher-service) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/475f9da4585c411fbbc1ac803ce2baf5)](https://www.codacy.com/app/ons-sdc/sdx-seft-publisher-service?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ONSdigital/sdx-seft-publisher-service&amp;utm_campaign=Badge_Grade) [![Code Coverage](https://codecov.io/gh/ONSdigital/sdx-seft-publisher-service/branch/master/graph/badge.svg)](https://codecov.io/gh/ONSdigital/sdx-seft-publisher-service)

Microservice for publishing SEFT files from internal to RAS

## What is this for?

This service takes files produced by internal systems and publishes them out to the ONS RAS platform running in the cloud. The legacy internal systems do not currently have the ability to publish directly so this service provides a service layer shim to enable the files to be moved as required.

Once the internal systems are fully redeveloped this service will be either retired or retooled and integrated into the new platform.

## Getting started

_TBD_

## Configuration

| Environment variable          | Default   | Description
| --------------------          | -------   | -----------
| SEFT_RABBITMQ_HOST            | localhost |
| SEFT_RABBITMQ_PORT            | 5672      |
| SEFT_PUBLISHER_RABBIT_QUEUE   | `Seft.CollectionInstruments` | Outgoing queue to publish to
| SEFT_RABBIT_EXCHANGE          | `message` | RabbitMQ exchange to use
| PORT                          | -         | Service port
| SEFT_FTP_HOST                 | 127.0.0.1 | Source host
| SEFT_FTP_PORT                variables | 2121      | Source port
| SEFT_FTP_USER                 | user      | Source user
| SEFT_FTP_PASS                 | password  | Source password
| RAS_SEFT_PUBLIC_KEY           |           | Destination encryption key
| SDX_SEFT_PRIVATE_KEY          |           | Local signing key
| SDX_SEFT_PRIVATE_KEY_PASSWORD |           | Signing key password
| SEFT_FTP_INTERVAL_MS          | 1800000   | Source polling interval (milliseconds)
| SEFT_RABBITMQ_DEFAULT_PASS    | rabbit    |
| SEFT_RABBITMQ_DEFAULT_USER    | rabbit    |
| SEFT_RABBITMQ_DEFAULT_VHOST   | `/`       |

_TBC_

## Run
python -m app.main

## Test

To run the tests in a Cloudfoundry environment:

```shell
$ cf push seft-publisher-unittest
$ cf logs seft-publisher-unittest --recent
```

### License

Copyright ©‎ 2016, Office for National Statistics (https://www.ons.gov.uk)

Released under MIT license, see [LICENSE](LICENSE) for details.
