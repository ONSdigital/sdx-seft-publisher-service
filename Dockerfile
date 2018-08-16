FROM python:3.6
WORKDIR /app
EXPOSE 8086
CMD  ["python3","main.py"]
COPY requirements.txt /app/requirements.txt
RUN pip3 install --require-hashes -r requirements.txt
COPY . /app