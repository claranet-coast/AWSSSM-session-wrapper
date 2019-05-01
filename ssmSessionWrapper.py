#!/usr/bin/env python3

# MIT License
# 
# Copyright (c) 2019 Mattia Lambertini
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import boto3
import argparse
import pprint
import subprocess
from botocore.exceptions import ProfileNotFound,NoRegionError,ClientError 

DEBUG=False
PROFILE=''
REGION=''

def get_instances_by_state(ec2, state):
    ''' Return ec2 instances in the desidered state '''
    if DEBUG:
        print ("[DEBUG] Running ec2 describe_instances")
    try:
        res = ec2.describe_instances(Filters=[{
            'Name': 'instance-state-name', 
            'Values': [state]
        }])
    except ClientError as err:
        print (f"[Err] {err}")
        raise Exception()
    return res

def find_InstanceName(tags):
    ''' Return the value of the Tag Name '''
    name = ""
    for tag in tags:
        if tag['Key'] == 'Name':
            name = tag['Value']
    return name

def build_instance_list(descr_instances_output):
    ''' Return a list of dictionaries {name: instanceName, id: instanceId} '''
    if DEBUG:
        print ("[DEBUG] Create instance list")
    instances=[]
    if DEBUG:
        pp.pprint(descr_instances_output)
    for item in descr_instances_output:
        instanceId = item['Instances'][0]['InstanceId']
        instanceName = find_InstanceName(item['Instances'][0]['Tags'])
        instances.append({'name': instanceName, 'id': instanceId})
    return instances

def get_user_choice(instances):
    ''' Print instances on screen and asks user which one 
        she/he wants to connect to '''
    print ("List of running instances:")
    for idx,instance in enumerate(instances):
        print (f"[{idx}]: {instance['name']} - {instance['id']}")
    inumber = -1
    while inumber not in range(len(instances)):
        try:
            inumber = int(input("Type the number of the instance you want to connect to: "))
        except ValueError:
            print (f"[ERR] The selection must be a number between 0 and {len(instances)-1}")
    return inumber

def connect_by_ssm(instance_id):
    ''' Run ssm client on the given instance id '''
    print(f"Connecting to {instance_id}")
    ssm_command = ["aws", "ssm", "start-session", "--target", instance_id]
    if PROFILE:
       ssm_command.extend(['--profile', PROFILE])
    subprocess.call(ssm_command)

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", dest='profile', help="AWS profile")
    parser.add_argument("--region", dest='region', help="AWS region")
    args = parser.parse_args()
    global PROFILE
    PROFILE = args.profile
    global REGION
    REGION = args.region
    if PROFILE is None:
        print ("[INFO] No profile given, using standard authentication chain")

def init_aws_session():
    session = None
    if PROFILE != '':
        try:
            if REGION is None:
                if DEBUG:
                    print (f"[DEBUG] Creating AWS Session with profile {PROFILE}")
                session = boto3.Session(profile_name=PROFILE)
            else:
                if DEBUG:
                    print (f"[DEBUG] Creating AWS Session with profile {PROFILE} and specified region {REGION}")
                print ("setting region")
                session = boto3.Session(profile_name=PROFILE, region_name=REGION)
        except ProfileNotFound:
            print (f"The profile '{PROFILE}' has not been found. Exiting..")
    else:
        if REGION is None:
            if DEBUG:
                print (f"[DEBUG] Creating AWS Session from default chain")
            session = boto3.session.Session()
        else:
            if DEBUG:
                print (f"[DEBUG] Creating AWS Session from default chain and specified region {REGION}")
            session = boto3.session.Session(region_name=REGION)
    return session

def main():
    parse_arguments()
    # init AWS session
    session = init_aws_session()
    ec2 = None
    try:
        if DEBUG:
            print ("[DEBUG] Create EC2 Client")
        ec2 = session.client('ec2')
    except NoRegionError:
        print ("[Err] No region specified")
        raise Exception("Unable To continue")
    running_instances_attr = get_instances_by_state(ec2, 'running') 
    instances = build_instance_list(running_instances_attr['Reservations'])
    inumber = int(get_user_choice(instances))
    connect_by_ssm(instances[inumber]['id'])


try:

    if __name__ == "__main__":
        if DEBUG:
            pp = pprint.PrettyPrinter(indent=1)
        main()

except KeyboardInterrupt:
    print ("\nSIGINT Received. Exiting..")
except Exception as err:
    print (f"[ERR] {err}")
finally:
    sys.exit(0)
