# sdx-seft-publisher-service

``sdx-seft-publisher-service`` is a microservice for publishing SEFT files from an internal file location to RAS (Respondent Accounts Service).

The service accesses files in an FTP server then sends them on to a given endpoint.

## Installation
### Publisher
Carry out the following inside a python virtual Environment

To inside requirements.txt, including the sdx-common library pulled from github
$ make build

If you wish to use a local version of sdx-common use pip from it's Location
$ pip install ./sdx-common

Or if you have the `SDX_HOME` environment set and both sdx-seft-publisher-service and sdx-common are in that location you can run to install your local version
$ make dev

To run the publisher
$ make start

### FTP_server



## Configuration

The following envioronment variables can be set:

| Environment variable      | example                                 | Description
|---------------------------|-----------------------------------------|---------------
| FTP_HOST 127.0.0.1        | ``127.0.0.1``                           | IP address of the FTP server
| FTP_PORT                  | ``2122``                                | PORT that the FTP server is running on
| FTP_LOGIN                 | ``ons``                                 | Login for FTP server
| FTP_PASSWORD              | ``ons``                                 | Password for FTP server
| RAS_URL                   | ``http://localhost:8080/upload/bres/1/``| Base URL to send files to



RAS_URL = os.getenv('RAS_URL', "http://localhost:8080/upload/bres/1/")


### Contributing

See [CONTRIBUTING](CONTRIBUTING) for details.

### License

Copyright ©‎ 2016, Office for National Statistics (https://www.ons.gov.uk)

Released under MIT license, see [LICENSE](LICENSE) for details.
