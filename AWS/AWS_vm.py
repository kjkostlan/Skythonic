# Virtal machine tools specific to aws.
import paramiko, time, os
import file_io
import AWS.AWS_format as AWS_format
import eye_term, covert
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def get_ip(x): # Address or machine.
    if type(x) is str and '.' in x: # Actually an ip address.
        return x
    if type(x) is str:
        x = AWS_format.id2obj(x)
    if 'PublicIp' in x:
        return x['PublicIp']
    if 'PublicIpAddress' in x:
        return x['PublicIpAddress']
    raise Exception('Cannot find the ip for: '+AWS_format.obj2id(x))

def get_region_name():
    return boto3.session.Session().region_name

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    eye_term.bprint('Warning: TODO: implement this auto-update Skythonic function.')

try: # Precompute.
    _imgs
except:
    _imgs = [None]
def ubuntu_aim_image():
    # Attemts to return the latest "stable" minimal AIM Ubuntu image.
    if _imgs[0] is None:
        filters = [{'Name':'name','Values':['*ubuntu*']}, {'Name': 'state', 'Values': ['available']}]
        filters.append({'Name':'architecture','Values':['x86_64']})
        imgs0 = ec2c.describe_images(Filters=filters, Owners=['amazon'])['Images']
        filter_fn = lambda d:d.get('Public',False) and d.get('ImageType',None)=='machine' and 'pro' not in d.get('Name',None) and 'minimal' in d.get('Name',None)
        imgs = list(filter(filter_fn, imgs0))
        _imgs[0] = {'Ubuntu':imgs}
    imgs = _imgs[0]['Ubuntu']

    if len(imgs)==0:
        raise Exception('No matching images to this body of filters.')
    imgs_sort = list(sorted(imgs,key=lambda d:d.get('CreationDate', '')))
    return imgs_sort[-1]['ImageId']

def restart_vm(instance_id):
    if instance_id is None:
        raise Exception('None instance.')
    if type(instance_id) is list or type(instance_id) is tuple: # Many at once should be faster in parallel?
        instance_ids = [AWS_format.obj2id(iid) for iid in instance_id]
    else:
        instance_ids = [AWS_format.obj2id(instance_id)]
    ec2c.reboot_instances(InstanceIds=instance_ids)

def start_vm(instance_id): # Idemootent if already started.
    instance_id = AWS_format.obj2id(instance_id)
    in_state = AWS_format.id2obj(instance_id)['State']['Name']
    if in_state == 'terminated':
        raise Exception(f'The instance {instance_id} has been terminated and can never ever be used again.')
    ec2c.start_instances(InstanceIds=[instance_id])
