# sdx-seft-publisher-service

[![Build Status](https://travis-ci.org/ONSdigital/sdx-seft-publisher-service.svg?branch=master)](https://travis-ci.org/ONSdigital/sdx-seft-publisher-service) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/475f9da4585c411fbbc1ac803ce2baf5)](https://www.codacy.com/app/ons-sdc/sdx-seft-publisher-service?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ONSdigital/sdx-seft-publisher-service&amp;utm_campaign=Badge_Grade)

``sdx-seft-publisher-service`` is a microservice for publishing SEFT files from an internal file location to RAS (Respondent Accounts Service).

The service accesses files in an FTP server then sends them on to a given endpoint.

## Installation
Carry out the following inside a python virtual Environment from inside this respository

To install the dependencies in requirements.txt, including the sdx-common library pulled from github:

    $ make build

If you wish to use a local version of sdx-common use pip from it's location:

    $ pip install -I ./sdx-common

OR if you have the `SDX_HOME` environment variable set and both sdx-seft-publisher-service and sdx-common are in that location, you can run the following to install your local version:

    $ make dev

### Publisher

To run the publisher:

    $ make start

### FTP_server

To run the dummy FTP server:

    $ make ftp_server

By default the FTP server runs on `'127.0.0.1'` at port 2121

### Fake RAS

To run the dummy RAS endpoint:

    $ make fake_ras

The dummy RAS is hosted at `'0.0.0.0'` on port 8080.

The only useful endpoint is at `'/upload/<survey>/<ce>/<filename>'` which is where publisher sends it's files by default

### Dummy Data

To generate dummy data for the publisher to use

  $ make false_data

### Testing

To run flake8 and the test scripts:

    $ make test

## Configuration

The following envioronment variables can be set:

| Environment variable      | example                                 | Description
|---------------------------|-----------------------------------------|---------------
| FTP_HOST                  | ``127.0.0.1``                           | IP address of the FTP server
| FTP_PORT                  | ``2122``                                | PORT that the FTP server is running on
| FTP_LOGIN                 | ``ons``                                 | Login for FTP server
| FTP_PASSWORD              | ``ons``                                 | Password for FTP server
| RAS_URL                   | ``http://localhost:8080/upload/bres/1/``| Base URL to send files to
| RETRIEVED_FILE_TYPES      | ``['.xlsx', '.png']``                   | File types that will be retrieved from the FTP

### License

Copyright ©‎ 2016, Office for National Statistics (https://www.ons.gov.uk)

Released under MIT license, see [LICENSE](LICENSE) for details.
