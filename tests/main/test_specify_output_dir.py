"""Tests for cookiecutter's output directory customization feature."""
import pytest

from tackle import main


@pytest.fixture
def context():
    """Fixture to return a valid context as known from a cookiecutter.json."""
    return {
        'cookiecutter': {
            'email': 'raphael@hackebrot.de',
            'full_name': 'Raphael Pierzina',
            'github_username': 'hackebrot',
            'version': '0.1.0',
        }
    }


@pytest.fixture
def output_dir(tmpdir):
    """Fixture to prepare test output directory."""
    return str(tmpdir.mkdir('output'))


@pytest.fixture
def template(tmpdir):
    """Fixture to prepare test template directory."""
    template_dir = tmpdir.mkdir('template')
    template_dir.join('cookiecutter.json').ensure(file=True)
    return str(template_dir)


@pytest.fixture
def template_renderable(tmpdir):
    """Fixture to prepare test template directory."""
    template_dir = tmpdir.mkdir('template')
    template_dir.join('cookiecutter.json').ensure(file=True)
    return str(template_dir)


@pytest.fixture(autouse=True)
def mock_gen_context(mocker, context):
    """Fixture. Automatically mock cookiecutter's function with expected output."""
    mocker.patch('cookiecutter.main.generate_context', return_value=context)


@pytest.fixture(autouse=True)
def mock_prompt(mocker):
    """Fixture. Automatically mock cookiecutter's function with expected output."""
    mocker.patch('cookiecutter.main.prompt_for_config')


@pytest.fixture(autouse=True)
def mock_replay(mocker):
    """Fixture. Automatically mock cookiecutter's function with expected output."""
    mocker.patch('cookiecutter.main.dump')


def test_api_invocation(mocker, template, output_dir, context):
    """Verify output dir location is correctly passed."""
    mock_gen_files = mocker.patch('cookiecutter.main.generate_files')

    main.tackle(template, output_dir=output_dir)

    mock_gen_files.assert_called_once_with(
        repo_dir=template,
        context=context,
        overwrite_if_exists=False,
        skip_if_file_exists=False,
        output_dir=output_dir,
        context_key='cookiecutter',
        accept_hooks=True,
    )


def test_default_output_dir(mocker, template, context):
    """Verify default output dir is current working folder."""
    mock_gen_files = mocker.patch('cookiecutter.main.generate_files')

    main.tackle(template)

    mock_gen_files.assert_called_once_with(
        repo_dir=template,
        context=context,
        overwrite_if_exists=False,
        skip_if_file_exists=False,
        output_dir='.',
        context_key='cookiecutter',
        accept_hooks=True,
    )
