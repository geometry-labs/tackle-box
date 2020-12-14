# -*- coding: utf-8 -*-

"""Tests dict input objects for `cookiecutter.operator.lists` module."""
import os
from tackle.main import tackle


def test_provider_system_hook_lists(change_dir):
    """Verify the hook call works properly."""
    output = tackle('.', no_input=True, context_file='nuki.yaml')

    assert 'donkey' in output['appended_list']
    assert 'donkey' in output['appended_lists']
    assert 'chickens' in output['appended_lists']
