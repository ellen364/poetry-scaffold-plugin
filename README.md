# poetry-scaffold-plugin

A Poetry plugin that installs and configures default dev dependencies, so you don't have to.

Get nice tools. Avoid the tedious boilerplate of setting up a project.

v0.1.0 is a preview and relies on the preview of Poetry's new plugin system. Expect rough edges.

## What you get

The packages and configuration in poetry-scaffold-plugin were inspired by, but diverge from, Claudio Jolowicz's series on [Hypermodern Python](https://cjolowicz.github.io/posts/hypermodern-python-01-setup/).

- Testing
  - [pytest](https://docs.pytest.org/) for testing
  - [coverage](https://coverage.readthedocs.io/) measures test coverage and identifies untested lines of code
  - [pytest-cov](https://pytest-cov.readthedocs.io/) adds nice coverage reports to pytest output
  - [pytest-mock](https://github.com/pytest-dev/pytest-mock/) makes it more convenient to use mocks (e.g. adds a mocker fixture)
  - [hypothesis](https://hypothesis.readthedocs.io/) helps find edge cases that break your code
- Linting and formatting
  - [black](https://black.readthedocs.io/) formats your code
  - [isort](https://pycqa.github.io/isort/) sorts import statements
  - [flake8](https://flake8.pycqa.org/) catches common mistakes and suggests good Python practices
  - [flake8-bugbear](https://github.com/PyCQA/flake8-bugbear) catches even more issues
  - [mypy](https://mypy.readthedocs.io/) checks type annotations
  - [semgrep](https://github.com/returntocorp/semgrep) looks for common security problems
  - [pre-commit](https://pre-commit.com/) runs checks (and automatically fixes what it can) before committing
- Niceties
  - [pdbpp](https://github.com/pdbpp/pdbpp) works like the standard pdb debugger but has extra features like "sticky" mode
  - [ipython](https://ipython.readthedocs.io/) provides a nicer shell for those interactive experimentation sessions

The linting is especially opinionated. If it's too much, or clashes with your house style, try deleting B9 from the extend-select section in setup.cfg.

The mypy settings are more lenient. The pre-commit hook will check type annotations that you've added, but won't demand you use type annotations.

## Requirements

- Poetry 1.2 (preview)

Poetry will add support for plugins in v1.2, currently in preview. To try poetry-scaffold-plugin, you must install Poetry >=1.2.0a2

Updating from Poetry v1.1 to the preview can't be done via Poetry's `self update`. Instead, use the new Poetry installer script. See the [master version of the installer docs](https://python-poetry.org/docs/master/#installation) for more information. (Don't use the v1.1 docs, which refer to the old installer.)

## Installation

After installing the Poetry preview, the new `poetry plugin` commands will be available. To install the plugin:

```bash
$ poetry plugin add poetry-scaffold-plugin
```

**Note:** Poetry plugins are installed in your global Poetry environment, not the project environment.

## Usage

```bash
$ poetry new my-project && cd my-project
$ poetry scaffold
```

Poetry's built-in `poetry new` provides a standard project layout. poetry-scaffold-plugin's `poetry scaffold` provides the dev dependencies and configuration.

There are no customisable settings in v0.1.0. Your project's configuration can be tweaked in the usual way, by modifying pyproject.toml, setup.cfg and pre-commit-config.yaml.
