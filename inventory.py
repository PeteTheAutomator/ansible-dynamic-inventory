#!/usr/bin/env python

# Use this code snippet in your app.
# If you need more information about configurations or implementing the sample code, visit the AWS docs:   
# https://aws.amazon.com/developers/getting-started/python/

from argparse import ArgumentParser
import boto3
from botocore.exceptions import ClientError
from boto3 import resource
import json
import yaml


def argument_parser():
    parser = ArgumentParser(description='Ansible dynamic inventory')
    parser.add_argument('--list', help='list', action="store_true")
    parser.add_argument('--host', help='host', required=False)
    args = parser.parse_args()
    return vars(args)


def get_local_vars(filename='env_vars.yml'):
    fh = open(filename, 'r')
    fh_raw = fh.read()
    fh.close()
    d = yaml.load(fh_raw)
    return d


def get_dynamo_vars():
    dynamodb_resource = resource('dynamodb')
    table = dynamodb_resource.Table('ansible-vars')
    response = table.get_item(Key={'service': 'capsule'})
    return response['Item']['vars']


def get_secret():
    secret_name = "test"
    endpoint_url = "https://secretsmanager.eu-west-2.amazonaws.com"
    region_name = "eu-west-2"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name,
        endpoint_url=endpoint_url
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
    else:
        # Decrypted secret using the associated KMS CMK
        # Depending on whether the secret was a string or binary, one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return secret
        else:
            #binary_secret_data = get_secret_value_response['SecretBinary']
            return False
            
        # Your code goes here. 

'''
secrets = get_secret()
plain_vars = get_dynamo_vars()

vars = json.loads(secrets)
vars.update(json.loads(plain_vars))
'''

if __name__ == '__main__':
    args = argument_parser()
    if args['list']:
        vars = get_local_vars()

        inventory = {
            'default': {
                'hosts': ['localhost'],
                'vars': vars
            }
        }

        print(json.dumps(inventory))

