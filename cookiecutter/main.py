"""
Main entry point for the `cookiecutter` command.

The code in this module is also a good example of how to use Cookiecutter as a
library rather than a script.
"""
import logging
import json
from _collections import OrderedDict

# from cookiecutter.generate import generate_files, generate_context
from cookiecutter.generate import generate_files
from cookiecutter.utils.paths import rmtree
from cookiecutter.exceptions import InvalidModeException
from cookiecutter.configs.config_base import get_settings
from cookiecutter.models import Context, Mode, Output, Source
from cookiecutter.repository import update_source
from cookiecutter.parser import get_output

logger = logging.getLogger(__name__)


def cookiecutter(
    template='.',
    no_input=False,
    checkout=None,
    context_file=None,
    context_key=None,
    password=None,
    directory=None,
    existing_context=None,
    extra_context=None,
    replay=None,
    record=None,
    output_dir='.',
    overwrite_if_exists=False,
    skip_if_file_exists=False,
    accept_hooks=True,
    config_file=None,
    env_file=None,
    default_config=False,
    config=None,
):
    """
    Run Cookiecutter just as if using it from the command line.

    :param template: A directory containing a project template directory,
        or a URL to a git repository.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param no_input: Prompt the user at command line for manual configuration?
    :param context_file: The file to load to set the context, ie list of prompts.
        Defaults to nuki.yaml, nukikata.yml, then cookiecutter.json.
    :param context_key: The key to all the context under - defaults to the name
        of the context file minus the file extension.
    :param existing_context: An additional dictionary to use in rendering
        additional prompts.
    :param extra_context: A dictionary of context that overrides default
        and user configuration.
    :param replay: Do not prompt for input, instead read from saved json. If
        ``True`` read from the ``replay_dir``.
        if it exists
    :param output_dir: Where to output the generated project dir into.
    :param password: The password to use when extracting the repository.
    :param directory: Relative path to a cookiecutter template in a repository.
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    :param config_file: User configuration file path.
    :param default_config: Use default values rather than a config file.

    :return Dictionary of output
    """
    settings = get_settings(
        config_file=config_file,
        env_file=env_file,
        config=config,
        default_config=default_config,
    )

    mode = Mode(no_input=no_input, replay=replay, record=record)

    if replay and ((no_input is not False) or (extra_context is not None)):
        err_msg = (
            "You can not use both replay and no_input or extra_context "
            "at the same time."
        )
        raise InvalidModeException(err_msg)

    source = Source(
        template=template,
        checkout=checkout,
        no_input=no_input,
        context_file=context_file,
        password=password,
        directory=directory,
    )

    source = update_source(source=source, settings=settings, mode=mode,)

    # repo_dir, context_file, cleanup = determine_repo_dir(
    #     template=template,
    #     abbreviations=settings.abbreviations,
    #     clone_to_dir=settings.cookiecutters_dir,
    #     checkout=checkout,
    #     no_input=no_input,
    #     context_file=context_file,
    #     password=password,
    #     directory=directory,
    # )

    # template_name = os.path.basename(os.path.abspath(repo_dir))
    # if not context_key:
    #     context_key = os.path.basename(context_file).split('.')[0]

    context = Context(
        context_file=context_file,
        default_context=settings.default_context,
        extra_context=extra_context,
        existing_context=existing_context,
        context_key=context_key,
        tackle_gen=source.tackle_gen,
    )
    get_output(
        c=context, s=source, m=mode, settings=settings,
    )

    # if replay:
    #     if isinstance(replay, bool):
    #         context = load(settings.replay_dir, template_name, context_key)
    #     else:
    #         path, template_name = os.path.split(os.path.splitext(replay)[0])
    #         context = load(path, template_name, context_key)
    #
    # else:
    #     context_file_path = os.path.join(repo_dir, context_file)
    #     logger.debug('context_file is %s', context_file_path)
    #
    #     context = generate_context(
    #         context_file=context_file_path,
    #         default_context=settings.default_context,
    #         extra_context=extra_context,
    #         context_key=context_key,
    #     )
    #
    #     # include template dir or url in the context dict
    #     context[context_key]['_template'] = repo_dir
    #     # include output+dir in the context dict
    #     context[context_key]['_output_dir'] = os.path.abspath(output_dir)
    #
    #     # prompt the user to manually configure at the command line.pyth
    #     # except when 'no-input' flag is set
    #     context[context_key] = prompt_for_config(
    #         context, context_key, existing_context, mode
    #     )
    #
    #     dump(settings.replay_dir, template_name, context, context_key)

    # Create project from local context and project template.
    # generate_files(
    #     repo_dir=source.repo_dir,
    #     context=context.output_dict,
    #     overwrite_if_exists=overwrite_if_exists,
    #     skip_if_file_exists=skip_if_file_exists,
    #     output_dir=output_dir,
    #     context_key=context.context_key,
    #     accept_hooks=accept_hooks,
    # )
    output = Output(
        output_dir=output_dir,
        overwrite_if_exists=overwrite_if_exists,
        skip_if_file_exists=skip_if_file_exists,
        accept_hooks=accept_hooks,
    )

    generate_files(
        o=output, c=context, s=source, m=mode, settings=settings,
    )

    # Cleanup (if required)
    if source.cleanup:
        rmtree(source.repo_dir)

    if isinstance(context, OrderedDict):
        context = json.loads(json.dumps(context))

    return context.output_dict
