import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, MutableMapping

from cleo.commands.command import Command
from poetry.core.pyproject.toml import PyProjectTOML
from poetry.core.semver.exceptions import ParseConstraintError
from poetry.exceptions import PoetryException
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.utils.env import EnvManager
from tomlkit import loads


class ScaffoldException(Exception):
    pass


@dataclass
class Outcome:
    success: List[str] = field(default_factory=list)
    error: List[str] = field(default_factory=list)


def is_git_repo(path: Path) -> bool:
    """Check whether directory is already a git repository."""
    if Path(path / ".git").exists():
        return True

    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        return False

    return True


def find_templates_path() -> Path:
    """Search for the default config templates path."""
    system_env = EnvManager.get_system_env(naive=True)
    candidates = system_env.site_packages.find("poetry_scaffold_plugin")
    if len(candidates) != 1:
        raise ScaffoldException()

    templates_path = Path(candidates[0] / "templates")
    if templates_path.exists():
        return templates_path
    else:
        raise ScaffoldException()


def install_dev_dependencies(dependencies: List[str]) -> None:
    """Add dev dependencies to pyproject.toml and install them."""
    try:
        argv = ["poetry", "add", "--group", "dev", *dependencies]
        subprocess.run(argv)
    except (
        subprocess.CalledProcessError,
        PoetryException,
        ParseConstraintError,
    ) as error:
        raise ScaffoldException(error)


def copy_config_files(src_dir: Path, dst_dir: Path) -> Outcome:
    """Copy template config files to project, without clobbering existing config."""
    outcome = Outcome()
    if not src_dir.exists():
        outcome.error.append(f"Couldn't find {src_dir}")
        return outcome

    for src_path in src_dir.iterdir():
        file_name = src_path.name

        dst_path = dst_dir / file_name
        if dst_path.exists():
            outcome.error.append(f"{file_name} exists in destination. Skipping.")
            continue

        try:
            shutil.copyfile(src_path, dst_path)
        except OSError:
            outcome.error.append(f"Couldn't write {dst_path}")
        else:
            outcome.success.append(f"Created {file_name}")

    return outcome


def add_pyproject_tools(pyproject_path: Path, config_path: Path) -> None:
    """Append tool config to pyproject.toml, without clobbering existing config."""
    pyproject = PyProjectTOML(pyproject_path)
    config: MutableMapping = loads(config_path.read_text())
    for k, v in config["tool"].items():
        if k not in pyproject.data["tool"]:
            pyproject.data["tool"][k] = v

    pyproject.save()


class ScaffoldCommand(Command):
    """
    CLI logic for the scaffold command.

    Accept options, run commands in specific order and reports outcomes to user. Most
    implementation logic is deferred to helper functions.
    """

    name = "scaffold"
    description = "Install and configure standard dev dependencies."

    def handle(self) -> None:
        self.line("Scaffolding...")
        project_path = Path.cwd()  # assume user wants to scaffold cwd
        try:
            templates_path = find_templates_path()
        except ScaffoldException:
            self.line("\n<error>Can't access default templates. Exiting.</>")
            sys.exit(1)

        default_deps = [
            # Test tools
            "pytest",
            "coverage[toml]",
            "pytest-cov",
            "pytest-mock",
            "hypothesis",
            # Linting + formatting
            "black",
            "isort",
            "flake8",
            "flake8-bugbear",
            "mypy",
            "semgrep",
            "pre-commit",
            # Niceties
            "pdbpp",
            "ipython",
        ]

        self.line("\nInstalling dependencies")
        try:
            install_dev_dependencies(default_deps)
        except ScaffoldException:
            self.line("<error>Couldn't install dependencies. Exiting.</>")
            sys.exit(1)

        self.line("\nCopying config files")
        outcome = copy_config_files(templates_path, project_path)
        for error in outcome.error:
            self.line(f"<warning>{error}</>")
        for success in outcome.success:
            self.line(success)

        self.line("\nAdding tools config to pyproject.toml")
        add_pyproject_tools(
            project_path / "pyproject.toml",
            templates_path / "pyproject.toml",
        )

        if not is_git_repo(project_path):
            self.line("\nInitialising git repo")
            try:
                subprocess.run(["git", "init"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                self.line(
                    "<warning>Couldn't initialise git repo. "
                    + "Skipping pre-commit hooks.</>"
                )
            else:
                self.line("Installing pre-commit hooks")
                try:
                    subprocess.run(
                        ["poetry", "run", "pre-commit", "install"],
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    self.line("<warning>Couldn't install pre-commit hooks</>")


def factory():
    return ScaffoldCommand()


class ScaffoldPlugin(ApplicationPlugin):
    """
    Register plugin.

    Let command loader defer loading of command until it's called.
    """

    def activate(self, application):
        application.command_loader.register_factory("scaffold", factory)
