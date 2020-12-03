# -*- coding: utf-8 -*-

"""Operator plugin that inherits a base class and is made available through `type`."""
from __future__ import unicode_literals
from __future__ import print_function

from typing import Union, List
import os
import logging

from cookiecutter.models import BaseHook

logger = logging.getLogger(__name__)


class ListdirOperator(BaseHook):
    """
    Operator for `listdir`. Lists the contents of a directory.

    :param path: String or list to directories to list
    :param sort: Boolean to sort the output
    :param ignore_hidden_files: Boolean to ignore hidden files

    :return: A list of contents of the `path` if input is string,
        A map with keys of items if input `path` is list.
    """

    type: str = 'listdir'
    ignore_hidden_files: bool = False
    path: Union[List[str], str]
    sort: bool = False

    def execute(self):
        if isinstance(self.path, str):
            files = os.listdir(os.path.expanduser(self.path))
            if self.sort:
                files.sort()
            if self.ignore_hidden_files:
                return [f for f in files if not f.startswith('.')]
            else:
                return files

        if isinstance(self.path, list):
            contents = {}
            for i in self.path:
                contents[i] = os.listdir(os.path.expanduser(i))
                if self.sort:
                    contents[i].sort()
            return contents
