''' Presentation Configuration
'''
import datetime as dt
import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence, Set

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
    timezone = pytz.timezone('America/Los_Angeles')
    exec_timestamp = dt.datetime.now(timezone)

    # Read schedule from schedule.yml
    with open('config.yml', 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    config = config_schema.validate(data)

    # allow assert - we want the action to fail if the current week is not supported
    raw_schedule: Dict[str, List[str]] = config['schedule']
    full_schedule = {dt.date.fromisoformat(
        key): value for key, value in raw_schedule.items()}
    future_schedule = {date: sequence
                       for date, sequence in full_schedule.items()
                       if date > exec_timestamp.date()}
    assert len(future_schedule) > 0
    next_date = min(future_schedule.keys())

    current_projects: List[str] = future_schedule[next_date]
    print(current_projects)
    projects: Dict = config['projects']
    all_call_projects: Set[str] = set(
        projects.keys()).difference(current_projects)
    print(all_call_projects)
    _exec_cmd(
        ['git', 'config', 'user.email', 'e4e@ucsd.edu']
    )
    _exec_cmd(
        ['git', 'config', 'user.name', 'E4E GitHub Actions']
    )

    __clear_announcements(next_date)

    __update_latex(current_projects, projects, all_call_projects)

    # Create the appropriate branches
    __create_branches(current_projects, projects, next_date)


def __clear_announcements(presentation_date: dt.date):
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
    with open('active_all_call.tex', 'w', encoding='utf-8') as handle:
        for project in all_call_projects:
            handle.write(f'\\item {projects[project]["name"]}\n')

    with open('active_order.tex', 'w', encoding='utf-8') as handle:
        for project in current_projects:
            handle.write(f'\\item {projects[project]["name"]}\n')

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


def __create_branches(current_projects: List[str],
                      projects: Dict,
                      presentation_date: dt.date):

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

    for project in current_projects:
        project_params = projects[project]
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

    repo = Repo('.')
    if len(repo.index.diff(repo.head.commit)) == 0:
        return
    _exec_cmd(
        ['git', 'commit', '-m', 'fix: Resetting slides']
    )
    _exec_cmd(
        ['git', 'push']
    )

    for project in current_projects:
        project_params = projects[project]
        branch_name = f'{project_params["branch"]}_{presentation_date.isoformat()}'
        _exec_cmd(
            ['git', 'checkout', 'main']
        )
        _exec_cmd(
            ['git', 'checkout', '-b', branch_name]
        )

        _exec_cmd(
            ['git', 'push', '--set-upstream', 'origin', branch_name]
        )

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
    print(shlex.join(cmd))
    if 'GH_TOKEN' in os.environ:
        subprocess.check_call(
            args=cmd
        )


if __name__ == '__main__':
    main()
