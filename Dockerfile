FROM python:3.6

WORKDIR /app
COPY . /app
COPY app/test/test_no_password.pem /app/test
COPY app/test/test_no_password.pub /app/test

EXPOSE 8086
RUN pip3 install --require-hashes -r requirements.txt

CMD  ["python3","main.py"]