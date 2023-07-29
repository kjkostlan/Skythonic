# Virtal machine tools specific to aws.
import time, os, re, requests, paramiko
import covert
from . import Azure_format, Azure_nugget
from azure.mgmt.compute.models import ImageReference
from waterworks import eye_term, file_io

def our_vm_id():
    # The instance_id of our machine; None if in the cloud shell.
    TODO

def get_ip(vmachine): # Address or machine.
    x = vmachine
    if type(x) is str and len(x)<64: # Idempotent if actually an IP address.
        x1 = x.replace('db8','')
        for c in '0123456789.:':
            x1 = x1.replace(c,'')
        if len(x1) == 0: # IPV4 or IPV6 address detected.
            return x

    # Get the address id in a *very* roundabout way:
    vm_id = Azure_format.obj2id(x)
    the_vm = Azure_nugget.compute_client.virtual_machines.get(resource_group_name=vm_id.split('/')[4], vm_name=vm_id.split('/')[-1])
    nic_id = the_vm.network_profile.network_interfaces[0].id
    nic = Azure_nugget.network_client.network_interfaces.get(resource_group_name=nic_id.split('/')[4], network_interface_name=nic_id.split('/')[-1])
    addr_id = nic.serialize()['properties']['ipConfigurations'][0]['properties']['publicIPAddress']['id']

    public_ip = Azure_nugget.network_client.public_ip_addresses.get(addr_id.split('/')[4], addr_id.split('/')[-1])
    print('Public ip is:', public_ip.ip_address)
    return public_ip.ip_address
    '''
    vm_info = compute_client.virtual_machines.get(
        resource_group_name, vm_name, expand='instanceView'
    )
    # Fetch the first network interface and its primary IP configuration.
    network_interface = vm_info.network_profile.network_interfaces[0]
    ip_configuration = network_interface.ip_configurations[0]
    public_ip = ip_configuration.public_ip_address
    '''

    #print('Getting ip:', x)
    #TODO # Other cases.
    #raise Exception('Cannot find the ip for: '+Azure_format.obj2id(x))

def get_region_name():
    return boto3.session.Session().region_name

try: # Precompute.
    _imgs
except:
    _imgs = [None]
def ubuntu_aim_image(precompute=True):
    # Attemts to return the latest "stable" minimal AIM Ubuntu image.
    TODO

def shutdown_vm(instance_id):
    instance_id = Azure_format.obj2id(instance_id)
    resource_group_name = instance_id.split("/")[4]
    vm_name = instance_id.split("/")[-1]
    Azure_nugget.compute_client.virtual_machines.begin_power_off(resource_group_name, vm_name)

def start_vm(instance_id): # Idempotent if already started.
    instance_id = Azure_format.obj2id(instance_id)
    resource_group_name = instance_id.split("/")[4]
    vm_name = instance_id.split("/")[-1]
    Azure_nugget.compute_client.virtual_machines.begin_start(resource_group_name, vm_name)

def restart_vm(instance_id):
    instance_id = Azure_format.obj2id(instance_id)
    resource_group_name = instance_id.split("/")[4]
    vm_name = instance_id.split("/")[-1]
    Azure_nugget.compute_client.virtual_machines.begin_restart(resource_group_name, vm_name)

def ubuntu_aim_image(location):
    # Find a good image.
    debug_mode = False
    if not debug_mode:
        # TODO: dynamically figure out the image. This may be difficult.
        # Query cmds by this (can be sent to grep to filter and takes 60 seconds to list all:
        #    az vm image list-skus --location westus --publisher Canonical --offer RHEL --output table
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
