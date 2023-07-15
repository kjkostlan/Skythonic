# Virtal machine tools specific to aws.
import time, os, re, requests, paramiko
import covert
import Azure.Azure_format as Azure_format
from waterworks import eye_term, file_io

def our_vm_id():
    # The instance_id of our machine; None if in the cloud shell.
    TODO

def get_ip(x): # Address or machine.
    if type(x) is str and '.' in x: # Actually an ip address.
        return x
    if type(x) is str:
        x = Azure_format.id2obj(x)
    TODO # Other cases.
    raise Exception('Cannot find the ip for: '+Azure_format.obj2id(x))

def get_region_name():
    return boto3.session.Session().region_name

try: # Precompute.
    _imgs
except:
    _imgs = [None]
def ubuntu_aim_image(precompute=True):
    # Attemts to return the latest "stable" minimal AIM Ubuntu image.
    TODO

def restart_vm(instance_id):
    if instance_id is None:
        raise Exception('None instance.')
    if type(instance_id) is list or type(instance_id) is tuple: # Many at once should be faster in parallel?
        instance_ids = [AWS_format.obj2id(iid) for iid in instance_id]
    else:
        instance_ids = [AWS_format.obj2id(instance_id)]
    TODO

def start_vm(instance_id): # Idemootent if already started.
    instance_id = Azure_format.obj2id(instance_id)
    in_state = TODO
    if in_state == 'terminated':
        raise Exception(f'The instance {instance_id} has been terminated and can never ever be used again.')
    TODO
