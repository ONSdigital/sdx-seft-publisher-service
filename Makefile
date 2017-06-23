dev: check-env
	cd .. && pip3 install -I ./sdx-common
	pip3 install -r requirements.txt

build:
	git clone https://github.com/ONSdigital/sdx-common.git
	pip3 install ./sdx-common
	pip3 install -I -r requirements.txt
	rm -rf sdx-common

start:
	python publisher.py

test:
	pip3 install -I -r test_requirements.txt
	flake8
	python -m unittest tests/*.py

ftp_server:
	python ftp_server.py

fake_ras:
	python fake_ras.py

false_data:
	cd dummy_data && python make_data.py

check-env:
ifeq ($(SDX_HOME),)
	$(error SDX_HOME is not set)
endif
