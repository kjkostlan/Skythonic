# Virtal machine tools specific to aws.
import time, os, re, requests, paramiko
import covert
from . import Azure_format, Azure_nugget
from azure.mgmt.compute.models import ImageReference
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

def start_vm(instance_id): # Idempotent if already started.
    instance_id = Azure_format.obj2id(instance_id)
    in_state = TODO
    if in_state == 'terminated':
        raise Exception(f'The instance {instance_id} has been terminated and can never ever be used again.')
    TODO

def ubuntu_aim_image(location):
    # Find a good image.
    debug_mode = False
    if not debug_mode:
        # TODO: dynamically figure out the image. This may be difficult.
        #Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:22.04.202307250
        return ImageReference(publisher="Canonical", offer="0001-com-ubuntu-server-jammy", sku="22_04-lts-gen2", version="latest")

    # LRS = Locally redundent storage. GRS = Geo Replicated Storage. LRS cheaper but a bit less reliable.
    # Stuff below is debuggy:
    print('Finding a nice ubuntu image...')

    #https://stackoverflow.com/questions/69661889/in-azure-i-wanted-to-get-sku-list-for-a-specific-vm-using-python-sdk
    skus = list(Azure_nugget.storage_client.skus.list())
    #for sku in skus:
    #    print('sku:',sku)
    print('First sku:', skus[0].capabilities[0])
    #print(dir(skus[0]))

    #images = list(Azure_nugget.compute_client.virtual_machine_images.list_offers(location=Azure_format.enumloc(location), publisher_name='Canonical'))

    #image_id_parts = images[0].id.split('/')
    #sku_index = image_id_parts.index('Skus') + 1

    print('Len of images:', len(images))
    for image in images:
        the_id = image.id
        print('Image is:', image)
        #print(image.id)
        #print(Azure_nugget.compute_client.virtual_machine_images.get(the_id))
        #print(Azure_nugget.compute_client.images.get(resource_group_name=None, ))
        #print(image.name)
    #https://stackoverflow.com/questions/56467045/azure-python-sdk-list-of-os
    print('...done')
    raise Exception('Debug mode enabled')
