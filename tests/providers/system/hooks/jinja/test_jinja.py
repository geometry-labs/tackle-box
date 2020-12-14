# -*- coding: utf-8 -*-

"""Tests dict input objects for `cookiecutter.prompt` module."""
import os

from cookiecutter.main import cookiecutter


def test_provider_system_hook_jinja(change_dir):
    """Verify the hook call works properly."""
    if os.path.exists('things.py'):
        os.remove('things.py')

    context = cookiecutter(
        '.', context_file='nuki.yaml', no_input=True, output_dir=str(tmpdir)
    )
    assert context['foo'] == 'bar'
    if os.path.exists('things.py'):
        os.remove('things.py')
