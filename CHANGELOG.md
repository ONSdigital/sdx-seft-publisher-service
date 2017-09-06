### Unreleased
  - Remove JSON logging

### 1.0.0
  - Explicitly add `mandatory=True` and `immediate=False` to the call to self._channel.basic_publish in `app.publisher`.
  - Use struct logger and convert to python module

### 0.1.0
  - Ensure integrity and version of library dependencies
  - Add codacy badge
  - Add coverage badge
  - Add healthcheck endpoint
