.PHONY: build dev start test

dev: check-env
	if pip list | grep sdx-common; \
	then \
		cd .. && pip3 uninstall -y sdx-common && pip3 install -I ./sdx-common; \
	else \
		cd .. && pip3 install -I ./sdx-common; \
	fi;

	pip3 install -r requirements.txt

build:
	pip3 install -r requirements.txt

test: dev
	pip3 install -r test_requirements.txt
	flake8 --exclude lib .
	python3 -m unittest */tests/*.py

start:
	./app/main.py

check-env:
ifeq ($(SDX_HOME),)
	$(error SDX_HOME is not set)
endif
