# Virtal machine tools specific to aws.
import time, os, re, requests, paramiko
import file_io, covert
import AWS.AWS_format as AWS_format
import waterworks.eye_term as eye_term
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def our_vm_id():
    # The instance_id of our machine; None if in the cloud shell.
    x = requests.get('http://169.254.169.254/latest/meta-data/instance-id').content.decode().strip()

    #x = requests.get('http://169.254.169.254/latest/meta-data/ami-id').content.decode().strip()
    if 'i-' not in x or 'resource not found' in x.lower():
        return None
    return x
    #stuff = ec2c.describe_instances(Filters=[{'Name': 'image-id','Values': [x]}])
    #return stuff['Reservations'][0]['Instances'][0]['InstanceId']

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

try: # Precompute.
    _imgs
except:
    _imgs = [None]
def ubuntu_aim_image(precompute=True):
    # Attemts to return the latest "stable" minimal AIM Ubuntu image.
    if not precompute or _imgs[0] is None:
        filters = [{'Name':'name','Values':['*ubuntu*']}, {'Name': 'state', 'Values': ['available']}]
        filters.append({'Name':'architecture','Values':['x86_64']})
        imgs0 = ec2c.describe_images(Filters=filters, Owners=['amazon'])['Images']
        filter_fn = lambda d:d.get('Public',False) and d.get('ImageType',None)=='machine' and 'pro' not in d.get('Name',None) and 'minimal' in d.get('Name',None)
        imgs = list(filter(filter_fn, imgs0))
        _imgs[0] = {'Ubuntu':imgs}
    else:
        imgs = _imgs[0]['Ubuntu']

    if len(imgs)==0:
        raise Exception('No matching images to a basic Ubuntu filter.')
    imgs_sort = list(sorted(imgs,key=lambda d:d.get('CreationDate', '')))

    only_supported = list(filter(lambda im: 'Description' in im and 'UNSUPPORTED' not in im['Description'] and 'LTS' in im['Description'], imgs_sort))
    by_version = {}
    for im in only_supported:
        _v = re.findall('\d+\.\d+', im.get('Description', ''))
        if len(_v)>0:
            vnum = _v[0]
            if vnum not in by_version:
                by_version[vnum] = []
            by_version[vnum].append(im)
    kys = list(sorted(by_version.keys(), key=lambda k:float(k)))

    im = by_version[kys[-1]][0]
    return im['ImageId']

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
