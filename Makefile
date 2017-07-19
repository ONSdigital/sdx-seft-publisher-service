.PHONY: build clean test

build:
	git clone -b 0.7.0 https://github.com/ONSdigital/sdx-common.git
	pip3 install ./sdx-common
	pip3 install -r requirements.txt
	rm -rf sdx-common

test: build
	pip3 install -r test_requirements.txt
	flake8 --exclude lib .
	python3 -m unittest app/test/test_*.py

clean:
	rm -rf sdx-common
