.PHONY: all clean flake mypy isort requirements, lock, sync, pipenv, coverage, build_info

export PIP_CONFIG_FILE=$(shell pwd)/setup.cfg

sources = parametrize
black = black $(sources) tests
flake8 = flake8 $(sources) --show-source
isort = isort $(sources) tests

all: lint flake mypy test

format:
	$(isort)
	$(black)

test:
	pytest tests --cov=parametrize

flake:
	$(flake8)

mypy:
	mypy $(sources)

lint:
	$(isort) --check-only --df
	$(black) --check --diff

coverage: test
	coverage html
	open htmlcov/index.html

install:  # install packages from poetry.lock
	poetry install

update:  # install packages from pyproject.toml and generate poetry.lock (use when add new packages, or update existing)
	poetry update

clean:
	@rm -rf build dist
	@rm -rf `find . -type d -name __pycache__`
	@rm -f `find . -type f -name '*.py[co]'`
	@rm -rf `find . -type d -name .pytest_cache`
	@rm -rf `find . -type d -name .mypy_cache`
	@rm -rf *.egg-info
