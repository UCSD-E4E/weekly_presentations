''' Presentation Configuration
'''
import datetime as dt
import subprocess
from typing import Dict, List, Set, Tuple

import pytz
import schema
import yaml

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
            int: [str]
        }
    }
)


def main():
    """Main Presentation Configuration
    """
    timezone = pytz.timezone('America/Los_Angeles')
    exec_timestamp = dt.datetime.now(timezone)
    calendar_tuple = exec_timestamp.isocalendar()
    next_weeknum = calendar_tuple[1] + 1

    # Read schedule from schedule.yml
    with open('config.yml', 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    config = config_schema.validate(data)

    # allow assert - we want the action to fail if the current week is not supported
    schedule = config['schedule']
    assert next_weeknum in schedule

    current_projects: List[str] = schedule[next_weeknum]
    print(current_projects)
    projects: Dict = config['projects']
    all_call_projects: Set[str] = set(
        projects.keys()).difference(current_projects)
    print(all_call_projects)
    subprocess.check_call(
        ['git', 'config', 'user.email', 'e4e@ucsd.edu']
    )
    subprocess.check_call(
        ['git', 'config', 'user.name', 'E4E GitHub Actions']
    )

    __update_latex(current_projects, projects, all_call_projects)

    # Create the appropriate branches
    __create_branches(current_projects, projects, calendar_tuple)


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

    subprocess.check_call(
        [
            'git', 'add',
            'active_all_call.tex',
            'active_order.tex',
            'active_sections.tex'
        ]
    )
    subprocess.check_call([
        'git', 'commit',
        '-m', f'feat!: Configures presentation for {current_projects}'
    ])
    subprocess.check_call([
        'git', 'push'
    ])


def __create_branches(current_projects: List[str],
                      projects: Dict,
                      calendar_tuple: Tuple):
    current_year = calendar_tuple[0]
    next_weeknum = calendar_tuple[1] + 1

    for project in current_projects:
        project_params = projects[project]
        branch_name = f'{project_params["branch"]}_{current_year}_{next_weeknum}'
        subprocess.check_call(
            ['git', 'checkout', 'main']
        )
        subprocess.check_call(
            ['git', 'checkout', '-b', branch_name]
        )
        # Reset the slides
        with open('base_project.tex', 'r', encoding='utf-8') as reference_handle, \
                open(project_params['latex'] + '.tex', 'w', encoding='utf-8') as target_handle:
            target_handle.write(
                f'% Slides for {current_year} Week {next_weeknum}\n')
            for line in reference_handle:
                target_handle.write(line)
        subprocess.check_call(
            ['git', 'add', project_params['latex'] + '.tex']
        )
        subprocess.check_call(
            ['git', 'commit', '-m', 'fix: Resetting slides']
        )
        subprocess.check_call(
            ['git', 'push', '--set-upstream', 'origin', branch_name]
        )
        command = [
            'gh', 'pr', 'create',
            '-B', 'main',
            '-t', project_params['name'],
            '-d',
            '-H', branch_name,
            '-b', f'Weekly presentation slides for {project_params["name"]}'
        ]
        for assignee in project_params['assignees']:
            command.extend(('-a', assignee))
        subprocess.check_call(
            command
        )


if __name__ == '__main__':
    main()
