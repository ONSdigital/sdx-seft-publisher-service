FROM python:3.6

EXPOSE 8086
RUN mkdir -p /app/logs

COPY app /app
COPY jwt-test-keys /jwt-test-keys
COPY requirements.txt /requirements.txt
COPY startup.sh /startup.sh
COPY Makefile /Makefile

RUN make build

ENTRYPOINT ./startup.sh
