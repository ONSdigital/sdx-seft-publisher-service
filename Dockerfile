FROM python:3.6

WORKDIR /
COPY . /

EXPOSE 8086
RUN pip3 install --require-hashes -r requirements.txt

CMD  ["python3","main.py"]