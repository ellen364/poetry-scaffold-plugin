import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from cleo.application import Application
from cleo.testers.command_tester import CommandTester
from hypothesis import example, given
from hypothesis import strategies as st
from hypothesis_fspaths import fspaths

from poetry_scaffold_plugin.plugins import (
    ScaffoldCommand,
    ScaffoldException,
    add_pyproject_tools,
    copy_config_files,
    find_templates_path,
    is_git_repo,
)


@pytest.fixture
def scaffold_command_tester():
    application = Application()
    application.add(ScaffoldCommand())
    command = application.find("scaffold")
    return CommandTester(command)


@pytest.fixture
def tmp_templates_path(tmp_path):
    """Path to a temporary templates directory."""
    templates_path = tmp_path / "templates"
    templates_path.mkdir()

    Path(templates_path / ".gitignore").write_text("template")
    Path(templates_path / ".pre-commit-config.yaml").write_text("template")
    Path(templates_path / "setup.cfg").write_text("template")

    return templates_path


@pytest.fixture
def tmp_empty_path(tmp_path):
    """Path to a temporary, empty directory."""
    dst_dir = tmp_path / "destination"
    dst_dir.mkdir()
    return dst_dir


class TestHelpers:
    def test_is_git_repo__git_dir(self, tmp_path):
        """Expect True when there's a .git directory in the specified path."""
        git = tmp_path / ".git"
        git.mkdir()

        assert is_git_repo(tmp_path) is True

    def test_is_git_repo__rev_parse(self, mocker, tmp_path):
        """Expect True when no .git directory but git rev-parse succeeds."""
        mocker.patch("subprocess.run")  # pretend it's run successfully

        assert is_git_repo(tmp_path) is True

    def test_is_git_repo__false(self, mocker, tmp_path):
        """Expect False when no .git directory and git rev-parse fails."""
        m = mocker.patch("subprocess.run")
        m.side_effect = subprocess.CalledProcessError(returncode=1, cmd="")

        assert is_git_repo(tmp_path) is False


class TestFindTemplatesPath:
    @given(
        # fspaths generates anything accepted by open(), while Path accepts a smaller
        # range of values. fspaths possibly not the best strategy for this case
        file_paths=st.lists(
            fspaths(allow_pathlike=False).filter(lambda fp: not isinstance(fp, bytes)),
            min_size=1,
        )
    )
    @example(file_paths=[])
    def test_not_one_candidate_path(self, file_paths):
        """Expect exception when search doesn't produce exactly 1 candidate."""
        # Hypothesis and pytest fixtures can interact unpredictably, so use context
        # manager instead of mocker
        with patch("poetry.utils.env.SitePackages.find") as mock_find:
            mock_find.return_value = [Path(path) for path in file_paths]
            with pytest.raises(ScaffoldException):
                find_templates_path()

    def test_one_existent_path(self, tmp_path):
        """
        Expect templates path to be returned when default templates directory exists.
        """
        templates_path = tmp_path / "templates"
        templates_path.mkdir()
        with patch("poetry.utils.env.SitePackages.find") as mock_find:
            mock_find.return_value = [tmp_path]

            actual = find_templates_path()
            assert templates_path == actual

    @given(
        # fspaths generates anything accepted by open(), while Path accepts a smaller
        # range of values. fspaths possibly not the best strategy for this case
        file_path=fspaths(allow_pathlike=False).filter(
            lambda fp: not isinstance(fp, bytes)
        )
    )
    def test_no_templates_directory(self, file_path):
        """Expect exception when can't find default templates directory."""
        with patch("poetry.utils.env.SitePackages.find") as mock_find:
            mock_find.return_value = [Path(file_path)]
            with pytest.raises(ScaffoldException):
                find_templates_path()


class TestCopyConfigFiles:
    def test_copy_files(self, tmp_templates_path, tmp_empty_path):
        """
        Expect all template files to be copied to the initially empty destination
        directory.
        """
        copy_config_files(tmp_templates_path, tmp_empty_path)

        template_files = sorted(path.name for path in tmp_templates_path.iterdir())
        destination_files = sorted(path.name for path in tmp_empty_path.iterdir())
        assert template_files == destination_files

    def test_dont_clobber_file(self, tmp_templates_path, tmp_empty_path):
        """
        Expect destination directory to contain all the template files. Contents of
        setup.cfg should not have been replaced.
        """
        initial_content = "custom project config"
        Path(tmp_empty_path / "setup.cfg").write_text(initial_content)

        copy_config_files(tmp_templates_path, tmp_empty_path)

        template_files = sorted(path.name for path in tmp_templates_path.iterdir())
        destination_files = sorted(path.name for path in tmp_empty_path.iterdir())
        assert template_files == destination_files
        assert Path(tmp_empty_path / "setup.cfg").read_text() == initial_content

    def test_outcome_success(self, tmp_templates_path, tmp_empty_path):
        """Expect outcome object to have messages about the created files."""
        outcome = copy_config_files(tmp_templates_path, tmp_empty_path)

        assert sorted(outcome.success) == [
            "Created .gitignore",
            "Created .pre-commit-config.yaml",
            "Created setup.cfg",
        ]
        assert outcome.error == []

    def test_outcome_couldnt_find(self, tmp_empty_path):
        """
        Expect outcome object to have messages about the directory that can't be found.
        """
        outcome = copy_config_files(Path("bad_path"), tmp_empty_path)

        assert outcome.success == []
        assert outcome.error == [
            "Couldn't find bad_path",
        ]

    def test_outcome_couldnt_write(self, tmp_templates_path, mocker):
        """
        Expect outcome object to have messages about the files that can't be created.
        """
        m = mocker.patch("shutil.copyfile")
        m.side_effect = OSError

        outcome = copy_config_files(tmp_templates_path, Path("bad_path"))

        assert outcome.success == []
        assert sorted(outcome.error) == [
            "Couldn't write bad_path/.gitignore",
            "Couldn't write bad_path/.pre-commit-config.yaml",
            "Couldn't write bad_path/setup.cfg",
        ]


class TestAddPyprojectTools:
    def test_add_all_sections(self, tmp_path):
        """
        Expect all template tool sections to be written when project's pyproject.toml
        has no tool sections.
        """
        initial_pyproject_content = """\
[tool.poetry]
name = "a-package"
version = "1.0.0"
description = "A very small package."

[tool.poetry.dependencies]
"""
        tools_content = """\
[tool.isort]
profile = "black"

[tool.coverage.run]
branch = true
"""
        pyproject = tmp_path / "pyproject.toml"
        tools_file = tmp_path / "tools.toml"
        pyproject.write_text(initial_pyproject_content)
        tools_file.write_text(tools_content)

        add_pyproject_tools(pyproject, tools_file)

        pyproject_content = pyproject.read_text()
        assert "[tool.isort]" in pyproject_content

    def test_dont_clobber_sections(self, tmp_path):
        """
        Expect missing tool sections to be written to project's pyproject.toml.
        Existing tool sections should be left in place.
        """
        initial_pyproject_content = """\
[tool.poetry]
name = "a-package"
version = "1.0.0"
description = "A very small package."

[tool.isort]
profile = "hug"
"""
        tools_content = """\
[tool.isort]
profile = "black"

[tool.coverage.run]
branch = true
"""
        pyproject = tmp_path / "pyproject.toml"
        tools_file = tmp_path / "tools.toml"
        pyproject.write_text(initial_pyproject_content)
        tools_file.write_text(tools_content)

        add_pyproject_tools(pyproject, tools_file)

        pyproject_content = pyproject.read_text()
        assert 'profile = "hug"' in pyproject_content
        assert "branch = true" in pyproject_content


class TestScaffoldCommand:
    """
    Test CLI, primarily console output and appropriate system exits. Function calls
    are heavily mocked to restrict testing to CLI behaviour.
    """

    def test_successful_run(self, mocker, scaffold_command_tester):
        """
        Expect full output when command is successful and project isn't already a git
        repo.
        """
        expected_text = """\
Scaffolding...

Installing dependencies

Copying config files

Adding tools config to pyproject.toml

Initialising git repo
Installing pre-commit hooks
"""
        for func in (
            "find_templates_path",
            "install_dev_dependencies",
            "copy_config_files",
            "add_pyproject_tools",
        ):
            mocker.patch(f"poetry_scaffold_plugin.plugins.{func}")
        mocker.patch("subprocess.run")
        # Project isn't already a git repo
        m = mocker.patch("poetry_scaffold_plugin.plugins.is_git_repo")
        m.return_value = False

        scaffold_command_tester.execute()
        assert expected_text == scaffold_command_tester.io.fetch_output()

    def test_exit_when_cant_access_templates(self, mocker, scaffold_command_tester):
        """
        Expect command to exit and print error when can't access the template config
        files. (Suggests something is seriously wrong.)
        """
        expected_text = """\
Scaffolding...

Can't access default templates. Exiting.
"""
        m = mocker.patch("poetry_scaffold_plugin.plugins.find_templates_path")
        m.side_effect = ScaffoldException()

        with pytest.raises(SystemExit):
            scaffold_command_tester.execute()
        assert expected_text == scaffold_command_tester.io.fetch_output()

    def test_exit_when_install_fails(self, mocker, scaffold_command_tester):
        """
        Expect command to exit and print error when package installation fails.
        (Suggests something is seriously wrong.)
        """
        expected_text = """\
Scaffolding...

Installing dependencies
Couldn't install dependencies. Exiting.
"""
        mocker.patch("poetry_scaffold_plugin.plugins.find_templates_path")
        m = mocker.patch("poetry_scaffold_plugin.plugins.install_dev_dependencies")
        m.side_effect = ScaffoldException()

        with pytest.raises(SystemExit):
            scaffold_command_tester.execute()
        assert expected_text == scaffold_command_tester.io.fetch_output()
