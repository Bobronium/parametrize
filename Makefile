.PHONY: all clean format flake8 mypy test coverage install update

all: flake8 mypy test

format:
	isort parametrize tests
	black parametrize tests

flake8:
	flake8 parametrize tests

mypy:
	mypy parametrize

test:
	pytest tests --cov=parametrize

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
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf poetry.lock
