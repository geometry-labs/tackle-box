# -*- coding: utf-8 -*-

"""Tests dict input objects for `cookiecutter.operator.stat` module."""
import os
from tackle.main import tackle


def test_provider_system_hook_split(change_dir):
    """Verify the hook call works properly."""
    output = tackle('.', no_input=True, context_file='nuki.yaml')

    assert output['a_list'] == [['stuff', 'thing'], ['things', 'stuffs']]
    assert output['a_str'] == ['things', 'stuffs']
    assert output['join_a_str'] == 'things.stuffs'
