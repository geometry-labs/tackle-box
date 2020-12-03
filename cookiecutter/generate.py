"""Functions for generating a project from a project template."""
import fnmatch
import logging
import os
import shutil

from binaryornot.check import is_binary
from jinja2 import FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError, UndefinedError

from cookiecutter.render.environment import StrictEnvironment
from cookiecutter.exceptions import (
    FailedHookException,
    NonTemplatedInputDirException,
    OutputDirExistsException,
    UndefinedVariableInTemplate,
)
from cookiecutter.utils.find import find_template
from cookiecutter.hooks import run_hook
from cookiecutter.utils.paths import rmtree, make_sure_path_exists
from cookiecutter.utils.context_manager import work_in

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cookiecutter.models import Context, Mode, Source, Output
    from cookiecutter.configs import Settings


logger = logging.getLogger(__name__)


def is_copy_only_path(path, context, context_key='cookiecutter'):
    """Check whether the given `path` should only be copied and not rendered.

    Returns True if `path` matches a pattern in the given `context` dict,
    otherwise False.

    :param path: A file-system path referring to a file or dir that
        should be rendered or just copied.
    :param context: cookiecutter context.
    """
    try:
        for dont_render in context[context_key]['_copy_without_render']:
            if fnmatch.fnmatch(path, dont_render):
                return True
    except KeyError:
        return False

    return False


def generate_file(project_dir, c: 'Context', o: 'Output'):
    """Render filename of infile as name of outfile, handle infile correctly.

    Dealing with infile appropriately:

        a. If infile is a binary file, copy it over without rendering.
        b. If infile is a text file, render its contents and write the
           rendered infile to outfile.

    Precondition:

        When calling `generate_file()`, the root template dir must be the
        current working directory. Using `utils.work_in()` is the recommended
        way to perform this directory change.

    :param project_dir: Absolute path to the resulting generated project.
    :param infile: Input file to generate the file from. Relative to the root
        template dir.
    :param context: Dict for populating the cookiecutter's variables.
    :param env: Jinja2 template execution environment.
    """
    logger.debug('Processing file %s', o.infile)

    # Render the path to the output file (not including the root project dir)
    outfile_tmpl = o.env.from_string(o.infile)

    from cookiecutter.render import build_render_context

    render_context = build_render_context(c)

    outfile = os.path.join(project_dir, outfile_tmpl.render(**render_context))
    file_name_is_empty = os.path.isdir(outfile)
    if file_name_is_empty:
        logger.debug('The resulting file name is empty: %s', outfile)
        return

    if o.skip_if_file_exists and os.path.exists(outfile):
        logger.debug('The resulting file already exists: %s', outfile)
        return

    logger.debug('Created file at %s', outfile)

    # Just copy over binary files. Don't render.
    logger.debug("Check %s to see if it's a binary", o.infile)
    if is_binary(o.infile):
        logger.debug('Copying binary %s to %s without rendering', o.infile, outfile)
        shutil.copyfile(o.infile, outfile)
    else:
        # Force fwd slashes on Windows for get_template
        # This is a by-design Jinja issue
        infile_fwd_slashes = o.infile.replace(os.path.sep, '/')

        # Render the file
        try:
            tmpl = o.env.get_template(infile_fwd_slashes)
        except TemplateSyntaxError as exception:
            # Disable translated so that printed exception contains verbose
            # information about syntax error location
            exception.translated = False
            raise
        rendered_file = tmpl.render(**render_context)

        # Detect original file newline to output the rendered file
        # note: newline='' ensures newlines are not converted
        with open(o.infile, 'r', encoding='utf-8', newline='') as rd:
            rd.readline()  # Read the first line to load 'newlines' value

            # Use `_new_lines` overwrite from context, if configured.
            newline = rd.newlines
            if c.input_dict[c.context_key].get('_new_lines', False):
                newline = c.input_dict[c.context_key]['_new_lines']
                logger.debug('Overwriting end line character with %s', newline)

        logger.debug('Writing contents to file %s', outfile)

        with open(outfile, 'w', encoding='utf-8', newline=newline) as fh:
            fh.write(rendered_file)

    # Apply file permissions to output file
    shutil.copymode(o.infile, outfile)


def render_and_create_dir(dirname, c: 'Context', o: 'Output'):
    """Render name of a directory, create the directory, return its path."""
    name_tmpl = o.env.from_string(dirname)

    from cookiecutter.render import build_render_context

    render_context = build_render_context(c)
    rendered_dirname = name_tmpl.render(render_context)
    # rendered_dirname = name_tmpl.render(**c.input_dict)

    dir_to_create = os.path.normpath(os.path.join(o.output_dir, rendered_dirname))

    logger.debug(
        'Rendered dir %s must exist in output_dir %s', dir_to_create, o.output_dir
    )

    output_dir_exists = os.path.exists(dir_to_create)

    if output_dir_exists:
        if o.overwrite_if_exists:
            logger.debug(
                'Output directory %s already exists, overwriting it', dir_to_create
            )
        else:
            msg = 'Error: "{}" directory already exists'.format(dir_to_create)
            raise OutputDirExistsException(msg)
    else:
        make_sure_path_exists(dir_to_create)

    return dir_to_create, not output_dir_exists


def ensure_dir_is_templated(dirname):
    """Ensure that dirname is a templated directory name."""
    if '{{' in dirname and '}}' in dirname:
        return True
    else:
        raise NonTemplatedInputDirException


def _run_hook_from_repo_dir(
    repo_dir, hook_name, project_dir, context, delete_project_on_failure
):
    """Run hook from repo directory, clean project directory if hook fails.

    :param repo_dir: Project template input directory.
    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    :param delete_project_on_failure: Delete the project directory on hook
        failure?
    """
    with work_in(repo_dir):
        try:
            run_hook(hook_name, project_dir, context)
        except FailedHookException:
            if delete_project_on_failure:
                rmtree(project_dir)
            logger.error(
                "Stopping generation because %s hook "
                "script didn't exit successfully",
                hook_name,
            )
            raise


def generate_files(
    o: 'Output', c: 'Context', s: 'Source', m: 'Mode', settings: 'Settings',
):
    """Render the templates and saves them to files.

    :param repo_dir: Project template input directory.
    :param context: Dict for populating the template's variables.
    :param output_dir: Where to output the generated project dir into.
    :param overwrite_if_exists: Overwrite the contents of the output directory
        if it exists.
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    """
    template_dir = find_template(s.repo_dir, c.context_key)
    if template_dir:
        envvars = c.input_dict.get(c.context_key, {}).get('_jinja2_env_vars', {})

        unrendered_dir = os.path.split(template_dir)[1]
        ensure_dir_is_templated(unrendered_dir)
        o.env = StrictEnvironment(
            context=c.input_dict, keep_trailing_newline=True, **envvars
        )
        try:
            project_dir, output_directory_created = render_and_create_dir(
                unrendered_dir, c, o
            )
        except UndefinedError as err:
            msg = "Unable to create project directory '{}'".format(unrendered_dir)
            raise UndefinedVariableInTemplate(msg, err, c.input_dict)

        # We want the Jinja path and the OS paths to match. Consequently, we'll:
        #   + CD to the template folder
        #   + Set Jinja's path to '.'
        #
        #  In order to build our files to the correct folder(s), we'll use an
        # absolute path for the target folder (project_dir)

        project_dir = os.path.abspath(project_dir)
        logger.debug('Project directory is %s', project_dir)

        # if we created the output directory, then it's ok to remove it
        # if rendering fails
        delete_project_on_failure = output_directory_created

        if o.accept_hooks:
            _run_hook_from_repo_dir(
                s.repo_dir,
                'pre_gen_project',
                project_dir,
                c.input_dict,
                delete_project_on_failure,
            )

        with work_in(template_dir):
            o.env.loader = FileSystemLoader('.')

            for root, dirs, files in os.walk('.'):
                # We must separate the two types of dirs into different lists.
                # The reason is that we don't want ``os.walk`` to go through the
                # unrendered directories, since they will just be copied.
                copy_dirs = []
                render_dirs = []

                for d in dirs:
                    d_ = os.path.normpath(os.path.join(root, d))
                    # We check the full path, because that's how it can be
                    # specified in the ``_copy_without_render`` setting, but
                    # we store just the dir name
                    if is_copy_only_path(d_, c.input_dict):
                        copy_dirs.append(d)
                    else:
                        render_dirs.append(d)

                for copy_dir in copy_dirs:
                    indir = os.path.normpath(os.path.join(root, copy_dir))
                    outdir = os.path.normpath(os.path.join(project_dir, indir))
                    outdir = o.env.from_string(outdir).render(**c.input_dict)
                    logger.debug(
                        'Copying dir %s to %s without rendering', indir, outdir
                    )
                    shutil.copytree(indir, outdir)

                # We mutate ``dirs``, because we only want to go through these dirs
                # recursively
                dirs[:] = render_dirs
                for d in dirs:
                    unrendered_dir = os.path.join(project_dir, root, d)
                    try:
                        render_and_create_dir(unrendered_dir, c, o)
                    except UndefinedError as err:
                        if delete_project_on_failure:
                            rmtree(project_dir)
                        _dir = os.path.relpath(unrendered_dir, o.output_dir)
                        msg = "Unable to create directory '{}'".format(_dir)
                        raise UndefinedVariableInTemplate(msg, err, c.input_dict)

                for f in files:
                    o.infile = os.path.normpath(os.path.join(root, f))
                    if is_copy_only_path(o.infile, c.input_dict):
                        outfile_tmpl = o.env.from_string(o.infile)
                        outfile_rendered = outfile_tmpl.render(**c.input_dict)
                        outfile = os.path.join(project_dir, outfile_rendered)
                        logger.debug(
                            'Copying file %s to %s without rendering', o.infile, outfile
                        )
                        shutil.copyfile(o.infile, outfile)
                        shutil.copymode(o.infile, outfile)
                        continue
                    try:
                        generate_file(project_dir, c, o)
                        # o.infile,
                        # c.input_dict,
                        # o.env,
                        # o.skip_if_file_exists,
                        # c.context_key,

                    except UndefinedError as err:
                        if delete_project_on_failure:
                            rmtree(project_dir)
                        msg = "Unable to create file '{}'".format(o.infile)
                        raise UndefinedVariableInTemplate(msg, err, c.input_dict)

        if o.accept_hooks:
            _run_hook_from_repo_dir(
                s.repo_dir,
                'post_gen_project',
                project_dir,
                c.input_dict,
                delete_project_on_failure,
            )

            for o in c.post_gen_hooks:
                o.execute

            logger.debug('Resulting project directory created at %s', project_dir)
            return project_dir
    else:
        if o.accept_hooks:
            _run_hook_from_repo_dir(
                s.repo_dir,
                'post_gen_project',
                '.',  # TODO: This needs context switching
                c.input_dict,
                False,
            )

        for o in c.post_gen_hooks:
            o.execute

        logger.debug('No project directory was created')
        return None
