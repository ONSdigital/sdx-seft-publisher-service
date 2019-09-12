### Unreleased
  - Greatly improved logging
  - Reworked deletion logic so the file is deleted once the delivery confirmation has occured
  - Use sdc-cryptography for encryption instead of custom solution that was there previously
  - Update a number of packages to remove deprecation warning that happened on encryption
  - Drop support for python 3.4

### 1.3.0 2019-09-04
  - Greatly improved logging
  - Reworked deletion logic so the file is deleted once the delivery confirmation has occured

### 1.2.2 2019-07-17
  - Updated urllib 3 to version 1.24.2
  - Improve start up logging
  
### 1.2.1 2019-02-28
  - Improve logging messages in ftpclient

### 1.2.0 2017-11-21
  - Remove sdx-common logging
  - Changes to menifest to allow deployment to Dev Cloud Foundry

### 1.1.0 2017-11-01
  - Removed unchanging configurable variables.

### 1.0.2
  - Downgrade structlog - to fix issue with tornado

### 1.0.1
  - Remove JSON logging

### 1.0.0
  - Explicitly add `mandatory=True` and `immediate=False` to the call to self._channel.basic_publish in `app.publisher`.
  - Use struct logger and convert to python module

### 0.1.0
  - Ensure integrity and version of library dependencies
  - Add codacy badge
  - Add coverage badge
  - Add healthcheck endpoint
