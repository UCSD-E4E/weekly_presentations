''' Presentation Configuration
'''
import datetime as dt
import json
import logging
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

import pytz
import schema
import yaml
from git import Repo

config_schema = schema.Schema(
    {
        'projects': {
            str: {
                'name': str,
                'latex': str,
                'branch': str,
                'assignees': [str],
            }
        },
        'schedule': {
            str: [str]
        }
    }
)


def main():
    """Main Presentation Configuration
    """
    # Configure loggers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    date_fmt = '%Y-%m-%dT%H:%M:%S'
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    error_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s'
                                        ' - %(message)s', datefmt=date_fmt)
    console_handler.setFormatter(error_formatter)
    root_logger.addHandler(console_handler)
    logging.Formatter.converter = time.gmtime

    # Set timezone
    timezone = pytz.timezone('America/Los_Angeles')
    exec_timestamp = dt.datetime.now(timezone)

    # Read schedule from schedule.yml
    with open('config.yml', 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    config = config_schema.validate(data)
    root_logger.info('Using config %s', json.dumps(config))

    # allow assert - we want the action to fail if the current week is not supported
    raw_schedule: Dict[str, List[str]] = config['schedule']
    full_schedule = {dt.datetime.fromisoformat(
        key): value for key, value in raw_schedule.items()}
    future_schedule = {date: sequence
                       for date, sequence in full_schedule.items()
                       if date > exec_timestamp}
    root_logger.info('Configuring git user')
    _exec_cmd(
        ['git', 'config', 'user.email', 'e4e@ucsd.edu']
    )
    _exec_cmd(
        ['git', 'config', 'user.name', 'E4E GitHub Actions']
    )

    root_logger.info('Setting next execute date')
    if len(future_schedule) <= 0:
        _set_next_execute_date(None)
        return
    next_date = min(future_schedule.keys())
    _set_next_execute_date(next_date)

    current_projects: List[str] = future_schedule[next_date]
    root_logger.info('Current Projects: %s', str(current_projects))
    projects: Dict = config['projects']
    all_call_projects: Set[str] = set(
        projects.keys()).difference(current_projects)
    root_logger.info('All Call Projects: %s', str(all_call_projects))

    __clear_announcements(next_date)

    __update_latex(current_projects, projects, all_call_projects)

    # Create the appropriate branches
    __create_branches(current_projects, projects, next_date.date())


def _set_next_execute_date(presentation_date: Optional[dt.date]):
    logger = logging.getLogger('_set_next_execute_date')
    if presentation_date:
        logger.info('Setting next execute date %s',
                    presentation_date.isoformat())
    else:
        logger.info('Disabling cron')

    latex_build_file = Path('.github/workflows/latex_build.yml')
    create_branch_file = Path('.github/workflows/create_project_branches.yml')

    if not presentation_date:
        build_time = None
        next_project_create_time = None
        commit_msg = 'ci: Disables next execution'
    else:
        build_time = presentation_date - dt.timedelta(minutes=30)
        next_project_create_time = presentation_date + dt.timedelta(hours=12)
        commit_msg = f'ci: updates next execution for {presentation_date.isoformat()}'

    _set_cron_string(latex_build_file, build_time)
    _set_cron_string(create_branch_file, next_project_create_time)

    repo = Repo('.')
    if len(repo.index.diff(None)) == 0:
        return

    _exec_cmd(
        ['git', 'add', latex_build_file.as_posix()]
    )

    _exec_cmd(
        ['git', 'add', create_branch_file.as_posix()]
    )
    _exec_cmd(
        ['git', 'commit', '-m', commit_msg]
    )


def _set_cron_string(file_to_modify, execute_time: dt.datetime):
    if not execute_time:
        new_cron_string = '59 23 29 4 6'
        desc = 'This is basically never'
    else:
        utc_dt: dt.date = execute_time.astimezone(pytz.utc)
        new_cron_string = utc_dt.strftime('%M %H %d %m *')
        desc = f'Executes at {execute_time.isoformat()}'

    with open(file_to_modify, 'r', encoding='utf-8') as handle:
        file_contents = ''.join(handle.readlines())
    regex = r"- cron: '(.*)' # (.*)"
    subst = f"- cron: '{new_cron_string}' # {desc}"

    result = re.sub(regex, subst, file_contents, 1)

    with open(file_to_modify, 'w', encoding='utf-8') as handle:
        handle.write(result)


def __clear_announcements(presentation_date: dt.date):
    logger = logging.getLogger('Clear Announcements')
    logger.info('Clearning annoumcements')
    with open('announcements.tex', 'w', encoding='utf-8') as handle:
        handle.write(
            f'% Announcements for {presentation_date.isoformat()}\n'
            '% \\begin{frame}{Announcements}\n'
            '%     \\begin{itemize}\n'
            '%         \\item\n'
            '%     \\end{itemize}\n'
            '% \\end{frame}\n'
        )
    repo = Repo('.')
    if len(repo.index.diff(None)) == 0:
        return

    _exec_cmd(
        ['git', 'add', 'announcements.tex']
    )

    _exec_cmd(
        ['git', 'commit', '-m', 'fix: Clears announcements']
    )


def __update_latex(current_projects: List[str], projects: Dict, all_call_projects: Set[str]):
    logger = logging.getLogger('Update Latex')
    logger.info('Updating LaTex')
    logger.info('Setting All Call Sequence')
    with open('active_all_call.tex', 'w', encoding='utf-8') as handle:
        if len(all_call_projects) == 0:
            handle.write(f'\\item None\n')
        for project in all_call_projects:
            handle.write(f'\\item {projects[project]["name"]}\n')

    logger.info('Setting Active Sequence')
    with open('active_order.tex', 'w', encoding='utf-8') as handle:
        for project in current_projects:
            handle.write(f'\\item {projects[project]["name"]}\n')

    logger.info('Setting Active Sections')
    with open('active_sections.tex', 'w', encoding='utf-8') as handle:
        for project in current_projects:
            handle.write(f'\\section{{{projects[project]["name"]}}}\n')
            handle.write(f'\\include{{{projects[project]["latex"]}}}\n')

    _exec_cmd(
        [
            'git', 'add',
            'active_all_call.tex',
            'active_order.tex',
            'active_sections.tex'
        ]
    )
    repo = Repo('.')
    if len(repo.index.diff(None)) == 0:
        return
    _exec_cmd([
        'git', 'commit',
        '-m', f'feat!: Configures presentation for {", ".join(current_projects)}'
    ])
    _exec_cmd([
        'git', 'push'
    ])
    _exec_cmd([
        'git', 'pull'
    ])


def __create_branches(current_projects: List[str],
                      projects: Dict,
                      presentation_date: dt.date):
    logger = logging.getLogger('Create Branches')
    logger.info('Creating Branches')

    logger.info('Deleting Images')
    path_to_rm: List[Path] = []
    for img in Path('images').rglob('*'):
        if not img.is_file():
            continue
        if img.name == 'README.md':
            continue
        path_to_rm.append(img)

    for path in path_to_rm:
        _exec_cmd(
            ['git', 'rm', path.as_posix()]
        )

    logger.info('Writing Project Slides')
    for project in current_projects:
        project_params = projects[project]
        # Reset the slides
        with open('base_project.tex', 'r', encoding='utf-8') as reference_handle, \
                open(project_params['latex'] + '.tex', 'w', encoding='utf-8') as target_handle:
            for line in reference_handle:
                target_handle.write(line)
        _exec_cmd(
            ['git', 'add', project_params['latex'] + '.tex']
        )

    repo = Repo('.')
    if len(repo.index.diff(repo.head.commit)) == 0:
        return
    _exec_cmd(
        ['git', 'commit', '-m', 'fix: Resetting slides']
    )
    _exec_cmd(
        ['git', 'push']
    )
    _exec_cmd(
        ['git', 'pull']
    )

    logger.info('Creating branches and PRs')
    for project in current_projects:
        project_params = projects[project]
        branch_name = f'{project_params["branch"]}_{presentation_date.isoformat()}'
        _exec_cmd(
            ['git', 'checkout', 'main']
        )
        _exec_cmd(
            ['git', 'checkout', '-b', branch_name]
        )

        # Reset the slides
        with open('base_project.tex', 'r', encoding='utf-8') as reference_handle, \
                open(project_params['latex'] + '.tex', 'w', encoding='utf-8') as target_handle:
            target_handle.write(
                f'% Slides for {presentation_date.isoformat()}\n')
            for line in reference_handle:
                target_handle.write(line)
        _exec_cmd(
            ['git', 'add', project_params['latex'] + '.tex']
        )
        if len(repo.index.diff(repo.head.commit)) == 0:
            return
        _exec_cmd(
            ['git', 'commit', '-m', 'fix: Adds date']
        )

        _exec_cmd(
            ['git', 'push', '--set-upstream', 'origin', branch_name]
        )
        _exec_cmd([
            'git', 'push'
        ])

        command = [
            'gh', 'pr', 'create',
            '-B', 'main',
            '-t', project_params['name'],
            '-d',
            '-H', branch_name,
            '-b', (f'Weekly presentation slides for {project_params["name"]} for '
                   f'{presentation_date.isoformat()}')
        ]
        for assignee in project_params['assignees']:
            command.extend(('-a', assignee))
        _exec_cmd(
            command
        )


def _exec_cmd(cmd: Sequence[str]):
    # only exec if GH_TOKEN is defined, i.e. in GitHub Actions
    logger = logging.getLogger('_exec_cmd')
    logger.info('Exec `%s`', shlex.join(cmd))
    if 'GH_TOKEN' in os.environ:
        try:
            subprocess.check_call(
                args=cmd,
                env=os.environ.copy()
            )
        except subprocess.CalledProcessError as exc:
            logger.exception(exc)
            logger.critical(exc.stdout)
            logger.critical(exc.stderr)
            logger.info(os.environ['GH_TOKEN'][-4:])
            raise exc


if __name__ == '__main__':
    main()
