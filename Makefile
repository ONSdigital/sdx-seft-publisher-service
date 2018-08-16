.PHONY: build clean test

build:
	pip3 install --require-hashes -r requirements.txt

test: build
	pip3 install -r test_requirements.txt
	flake8 --exclude lib .
	python3 -m unittest app/test/test_*.py

start:
	python main.py
