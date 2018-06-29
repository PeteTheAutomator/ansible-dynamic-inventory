#!/usr/bin/env python

import os
import sys
import time
import boto3
from argparse import ArgumentParser

ACCESS_KEY = os.environ['ACCESS_KEY']
SECRET_KEY = os.environ['SECRET_KEY']
SESSION_TOKEN = os.environ['SESSION_TOKEN']
REGION = os.environ['REGION']


def argument_parser():
    parser = ArgumentParser(description='AWS CodeBuild Manager - starts project builds and captures the output')
    parser.add_argument('-p', '--project', help='the name of the CodeBuild project', required=True)
    return vars(parser.parse_args())


class CodeBuildManager:
    def __init__(self):
        self.client = boto3.client('codebuild',
                                   aws_access_key_id=ACCESS_KEY,
                                   aws_secret_access_key=SECRET_KEY,
                                   aws_session_token=SESSION_TOKEN,
                                   region_name=REGION)

    def get_projects(self):
        response = self.client.list_projects(sortBy='NAME', sortOrder='DESCENDING')
        return response

    def get_project_builds(self, project_name):
        response = self.client.list_builds_for_project(projectName=project_name, sortOrder='DESCENDING')
        return response

    def get_build_details(self, build_id):
        response = self.client.batch_get_builds(ids=[build_id])
        return response

    def start_build(self, project_name):
        response = self.client.start_build(projectName=project_name)
        return response


class CloudWatchLogsManager:
    def __init__(self):
        self.client = boto3.client('logs',
                                   aws_access_key_id=ACCESS_KEY,
                                   aws_secret_access_key=SECRET_KEY,
                                   aws_session_token=SESSION_TOKEN,
                                   region_name=REGION)

    def get_event_logs(self, log_group_name, log_stream_name):
        response = self.client.get_log_events(logGroupName=log_group_name,
                                              logStreamName=log_stream_name,
                                              startFromHead=True)
        return response


class Build:
    def __init__(self, project_name):
        self.project_name = project_name
        self.cbm = CodeBuildManager()
        self.cwlm = CloudWatchLogsManager()
        self.build_id = None
        self.build_details = None
        self.build_status = None
        self.log_group_name = None
        self.log_stream_name = None

    def create(self):
        project_list = self.cbm.get_projects()['projects']
        if self.project_name not in project_list:
            print('no such project: {0}'.format(self.project_name))
            sys.exit(1)

        response = self.cbm.start_build(self.project_name)
        self.build_id = response['build']['id']

    def get_details(self):
        self.build_details = self.cbm.get_build_details(self.build_id)['builds'][0]
        self.build_status = self.build_details['buildStatus']
        self.log_group_name = self.build_details['logs']['groupName']
        self.log_stream_name = self.build_details['logs']['streamName']
        return self.build_status

    @property
    def current_phase(self):
        if 'phaseStatus' in self.build_details['phases'][-1]:
            phase_status = self.build_details['phases'][-1]
        else:
            phase_status = 'N/A'

        return self.build_details['phases'][-1]['phaseType'], phase_status

    def get_build_logs(self):
        results = []
        if self.log_group_name and self.log_stream_name:
            response = self.cwlm.get_event_logs(self.log_group_name, self.log_stream_name)
            if len(response['events']) > 0:
                for e in response['events']:
                    results.append(e['message'].strip())

        return results


if __name__ == "__main__":
    args = argument_parser()
    b = Build(project_name=args['project'])
    b.create()
    time.sleep(10)
    while b.get_details() == 'IN_PROGRESS':
        phase_details = b.current_phase
        phase_status = phase_details[0]
        phase_type = phase_details[1]
        print 'Phase: {0} - {1}'.format(b.current_phase[0], b.current_phase[1])
        time.sleep(10)

    logs = b.get_build_logs()
    for log in logs:
        print log
