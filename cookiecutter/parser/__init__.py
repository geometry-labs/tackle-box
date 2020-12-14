# -*- coding: utf-8 -*-

"""Context related items."""
import os
import yaml
import logging
from collections import OrderedDict

from cookiecutter.parser.context import prep_context
from cookiecutter.utils.files import load, dump

from cookiecutter.exceptions import InvalidModeException
from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cookiecutter.models import Context, Mode, Source, Settings, Providers

logger = logging.getLogger(__name__)


def update_context(
    context: 'Context',
    source: 'Source',
    mode: 'Mode',
    settings: 'Settings',
    providers: 'Providers',
) -> OrderedDict:
    """Get output dict and entrypoint into broader parsing of context."""
    _validate_context(context, mode)
    _enrich_context(context, source)

    if mode.replay:
        if isinstance(mode.replay, bool):
            context.output_dict = load(
                settings.replay_dir, source.template_name, context.context_key
            )
            return  # noqa
        else:
            path, template_name = os.path.split(os.path.splitext(mode.replay)[0])
            context.output_dict = load(path, template_name, context.context_key)
            return  # noqa

    if mode.rerun:
        # Rerun will first try to read an existing rerun file and then load it into
        # the override input dict
        if isinstance(mode.rerun, str):
            rerun_path = mode.rerun
            context.override_inputs = _evaluate_rerun(rerun_path, mode)
        if isinstance(mode.rerun, bool):
            rerun_path = os.path.join(
                context.calling_directory,
                '.' + '.'.join([source.template_name, settings.rerun_file_suffix]),
            )
            context.override_inputs = _evaluate_rerun(rerun_path, mode)

    context_file_path = os.path.join(source.repo_dir, source.context_file)
    logger.debug('context_file is %s', context_file_path)

    # prepare_context(c=c, s=s, settings=settings)
    # update_providers(c=c, s=s, settings=settings)

    # Main entrypoint to parse the input.
    prep_context(context=context, mode=mode, source=source, settings=settings)

    if mode.record:
        _output_record(context=context, mode=mode, settings=settings)


def _output_record(context: 'Context', mode: 'Mode', settings: 'Settings'):
    if isinstance(mode.record, bool):
        # Bool indicates dumping def
        dump(
            context.calling_directory,
            context.context_key + '.record',
            context.output_dict,
            settings,
        )

    if isinstance(mode.record, str):
        # Str indicates path to file to dump output to
        if mode.record.startswith('/'):
            dump('/', mode.record, context.output_dict, settings)
        if os.path.exists(Path(mode.record).parent):
            dump(os.curdir, mode.record, context.output_dict, settings)
        else:
            dump(context.calling_directory, mode.record, context.output_dict, settings)


def _evaluate_rerun(rerun_path, mode: 'Mode'):
    if os.path.exists(rerun_path):
        with open(rerun_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        print('No rerun file, will create record and use next time.')
        mode.record = True


def _enrich_context(context: 'Context', source: 'Source'):
    if not context.context_key:
        context.context_key = os.path.basename(source.context_file).split('.')[0]
    if not context.calling_directory:
        context.calling_directory = os.path.abspath(os.path.curdir)


def _validate_context(context: 'Context', mode: 'Mode'):
    if mode.replay and context.overwrite_inputs is not None:
        err_msg = "You can not use both replay and extra_context at the same time."
        raise InvalidModeException(err_msg)
    if mode.replay and mode.rerun:
        err_msg = "You can not use both replay and rerun at the same time."
        raise InvalidModeException(err_msg)