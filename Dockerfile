FROM python:3.6

WORKDIR /
COPY . /
COPY app/test/test_no_password.pem /test
COPY app/test/test_no_password.pub /test

EXPOSE 8086
RUN pip3 install --require-hashes -r requirements.txt

CMD  ["python3","main.py"]