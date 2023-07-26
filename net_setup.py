# Scripts that setup common machines and simple networks.
import sys, time
import vm, covert, proj
from waterworks import eye_term, fittings, plumber

proj.platform_import_modules(sys.modules[__name__], ['cloud_core', 'cloud_format', 'cloud_query', 'cloud_vm', 'cloud_permiss'])
platform = proj.which_cloud().lower().strip()

def simple_vm(vm_name, private_ip, subnet_id, securitygroup_id, key_name, public_ip_id, the_region):
    # Creates a new key if need be, but the subnet and securitygroup must be already made.
    # Returns inst_id, None, fname.
    if platform=='aws':
        inst_networkinter = [{'SubnetId': subnet_id, 'DeviceIndex': 0, 'PrivateIpAddress': private_ip,
                              'AssociatePublicIpAddress': False, 'Groups': [securitygroup_id]}]
        # ami-0735c191cf914754d; ami-0a695f0d95cefc163; ami-0fcf52bcf5db7b003
        vm_params = {'ImageId':cloud_vm.ubuntu_aim_image(), 'InstanceType':'t2.micro',
                     'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter,
                     'KeyName':key_name}
        inst_id = covert.vm_dangerkey(vm_name, vm_params, key_name)
        cloud_core.assoc(inst_id, addr_id)
        return inst_id
    elif platform=='azure':
        from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet, VirtualNetworkGateway, RouteTable, Route, NetworkSecurityGroup, PublicIPAddress, NetworkInterface # DEBUG.
        from . import Azure_nugget # DEBUG (will move these to Azure_core).
        nic = NetworkInterface(id="", location=location, ip_configurations=[{"name": "my_ip_config", "subnet": {"id": subnet_id}, "public_ip_address": {"id": public_ip_id}}])
        nic.network_security_group = Azure_nugget.resource_client.resources.get_by_id(securitygroup_id, api_version=Azure_nugget.api_version)
        nic = network_client.network_interfaces.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, "my_nic", nic).result()

        #vm = VirtualMachine(location=location, os_profile=OSProfile(computer_name=vm_name, admin_username=username, linux_configuration={"ssh": {"public_keys": [{"path": "/home/{}/.ssh/authorized_keys".format(username), "key_data": public_key}]}}))
        #vm.storage_profile = StorageProfile(os_disk={"os_type": "Linux", "name": os_disk_name, "create_option": "FromImage"}, image_reference=ImageReference(publisher="Canonical", offer="UbuntuServer", sku="20_04-lts-gen2", version="latest"))
        #vm.hardware_profile = {"vm_size": vm_size}
        #vm.network_profile = {"network_interfaces": [{"id": nic.id}]}
        #vm = compute_client.virtual_machines.begin_create_or_update(resource_group_name, vm_name, vm).result()
        from azure.mgmt.compute.models import OSProfile, StorageProfile, DataDisk, ImageReference # But these are NOT debug since there are multible levels of params.
        vm_params = {}
        vm_params['location'] = location
        vm_username = 'ubuntu' # The default username across Skythonic for vms.
        # Covert will fill out vm_params['os_profile']
        vm_params['network_profile'] = {"network_interfaces": [{"id": nic.id}]}
        vm_params['hardware_profile'] = {"vm_size": "Standard_DS1_v2"}  # Different options here.
        inst_id = covert.create_vm_dangerkey(vm_name, vm_params, key_name) # Already assoced with the address.
        return inst_id
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    raise Exception('Should have returned inside the code box.')

def setup_jumpbox(basename='jumpbox', the_region='us-west-2c', user_name='BYOC', key_name='BYOC_keypair'): # The jumpbox is much more configurable than the cloud shell.
    # Note: for some reason us-west-2d fails for this vm, so us-west-2c is the default.
    if platform=='aws':
        vpc_id = cloud_core.create_once('VPC', user_name+'_Service', True, CidrBlock='10.200.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
    elif platform=='azure':
        _addr = {"address_prefixes": ['10.200.0.0/16']}
        vpc_id = cloud_core.create_once('VPC', user_name+'_Service', True, address_space=_addr, location=cloud_format.enumloc(the_region))
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    if platform=='aws':
        cloud_core.modify_attribute(vpc_id, 'EnableDnsSupport', {'Value': True})
        cloud_core.modify_attribute(vpc_id, 'EnableDnsHostnames', {'Value': True})
    elif platform=='azure':
        cloud_core.modify_attribute(vpc_id, 'enable_dns_support', True)
        cloud_core.modify_attribute(vpc_id, 'enable_dns_hostnames', True)
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    if platform=='aws':
        subnet_id = cloud_core.create_once('subnet', user_name+'_'+basename+'_subnet', True, CidrBlock='10.200.250.0/24', VpcId=vpc_id, AvailabilityZone=the_region)
    elif platform=='azure':
        subnet_id = cloud_core.create_once('subnet', user_name+'_'+basename+'_subnet', True, address_prefix='10.200.250.0/24', vnet_id=vpc_id)
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    if platform=='aws':
        webgate_id = cloud_core.create_once('webgate', user_name+'_'+basename+'_gate', True)
        cloud_core.assoc(vpc_id, webgate_id)
    elif platform=='azure':
        pass # Crucial diffference from AWS: Azure does not have internet gateways, they are kind of like an extra step.
        #ip_configurations=[{"subnet": {"id": subnet_id}}]
        #sku = {'name':'Basic', 'tier':'Basic'} # Include this?
        #webgate_id = cloud_core.create_once('webgate', user_name+'_'+basename+'_gate', True, location=cloud_format.enumloc(the_region), ip_configurations=ip_configurations, sku=sku)
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    if platform=='aws':
        routetable_id = cloud_core.create_once('rtable', user_name+'_'+basename+'_rtable', True, VpcId=vpc_id) # TODO: Use the default one.
        cloud_core.create_route(rtable_id=routetable_id, dest_cidr='0.0.0.0/0', gateway_id=webgate_id)
    elif platform=='azure':
        routetable_id = cloud_core.create_once('rtable', user_name+'_'+basename+'_rtable', True, location=the_region)
        cloud_core.connect_to_internet(routetable_id, vpc_id)
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    cloud_core.assoc(routetable_id, subnet_id)

    if platform == 'aws':
        securitygroup_id = cloud_core.create_once('securitygroup', user_name+'_'+basename+'_sGroup', True, GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc_id)
    elif platform == 'azure':
        securitygroup_id = cloud_core.create_once('securitygroup', user_name+'_'+basename+'_sGroup', True, location=the_region)
        cloud_core.assoc(vpc_id, securitygroup_id)
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    cloud_permiss.authorize_ingress(securitygroup_id, '0.0.0.0/0', 'tcp', port0=22, port1=22)

    if platform == 'aws':
        addr_id = cloud_core.create_once('address', user_name+'_'+basename+'_address', True, Domain='vpc')
    elif platform == 'azure':
        addr_id = TODO
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)
    inst_id = simple_vm(user_name+'_'+basename+'_VM', '10.200.250.100', subnet_id, securitygroup_id, key_name, addr_id, the_region)

    ssh_bash = vm.ssh_bash(inst_id, True)

    print(f'---Setting up {proj.which_cloud()} on the jump box (WARNING: long term secret credentials posted to VM)---')
    region_name = the_region
    if region_name[-1] in 'abcd':
        region_name = region_name[0:-1]

    #tubo = vm.upgrade_os(inst_id, printouts=True)
    tubo = vm.install_package(inst_id, 'apt python3')
    for pk_name in ['apt net-tools', 'apt netcat', 'apt vim', 'apt tcpdump', 'apt ping']:
        tubo = vm.install_package(tubo, pk_name)
    for pk_name in ['skythonic', 'host-list']:
        tubo = vm.install_custom_package(tubo, pk_name)
    for package_cmd in cloud_core.install_these():
        tubo = vm.install_package(tubo, package_cmd, user_name=user_name)
    cloud_vm.restart_vm(inst_id)

    print("\033[38;5;208mJumpbox appears to be setup and working (minus a restart which is happening now).\033[0m")
    return ssh_bash, inst_id

def setup_threetier(key_name='BYOC_keypair', jbox_name='BYOC_jumpbox_VM', new_vpc_name='BYOC_Spoke1', the_region='us-west-2c'):
    vpc_id = cloud_core.create_once('VPC', new_vpc_name, True, CidrBlock='10.201.0.0/16')
    cloud_core.modify_attribute(vpc_id, 'EnableDnsSupport', {'Value': True})
    cloud_core.modify_attribute(vpc_id, 'EnableDnsHostnames', {'Value': True})

    webgate_id = cloud_core.create_once('webgate', new_vpc_name+'_gate', True)
    cloud_core.assoc(vpc_id, webgate_id)

    def _nameget(ty, name):
        x = cloud_query.get_by_name(ty, name)
        if x is None:
            raise Exception(f'Cannot find this name: {name}; make sure setup_jumpbox has been called.')
        return cloud_format.obj2id(x)

    jbox_id = _nameget('machine',jbox_name)
    jbox_subnet_id = cloud_format.id2obj(jbox_id)['SubnetId']
    jbox_vpc_id = cloud_format.id2obj(jbox_subnet_id)['VpcId']
    rtables = cloud_query.get_resources('rtable')
    matching_rtable_ids = []
    for rt in rtables: # TODO: better connectivity querying.
        for a in rt.get('Associations', []):
            if a.get('SubnetId',None)==jbox_subnet_id:
                matching_rtable_ids.append(cloud_format.obj2id(rt))
    if len(matching_rtable_ids)==1:
        jbox_rtable_id = matching_rtable_ids[0]
    elif len(matching_rtable_ids)>1:
        raise Exception('Too many routetables match the Jumbbox.')
    elif len(matching_rtable_ids)==0:
        raise Exception('Too few routetables match the Jumpbox')

    print('Jumpbox machine ID:', jbox_id, jbox_subnet_id, jbox_vpc_id)
    routetable_id = cloud_core.create_once('rtable', new_vpc_name+'_rtable', True, VpcId=vpc_id)

    basenames = ['BYOC_web', 'BYOC_app', 'BYOC_db']
    subnet_cidrs = ['10.201.101.0/24', '10.201.102.0/24', '10.201.103.0/24']
    ips =          ['10.201.101.100',  '10.201.102.100',  '10.201.103.100']
    inst_ids = []
    cmds = []
    for i in range(3):
        cloud_core.create_route(routetable_id, '0.0.0.0/0', webgate_id)
        subnet_id = cloud_core.create_once('subnet',basenames[i], True, CidrBlock=subnet_cidrs[i], VpcId=vpc_id, AvailabilityZone=the_region)
        cloud_core.assoc(routetable_id, subnet_id)

        # They have different security groups for different types of servers, so we will do so as well rather than use only one for all three:
        #https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
        securitygroup_id = cloud_core.create_once('securitygroup', basenames[i]+'_sGroup', True, GroupName='From Hub'+basenames[i], Description='Allow Hub Ip cidr', VpcId=vpc_id)
        cloud_permiss.authorize_ingress(securitygroup_id, '10.0.0.0/8', '-1', 22, 22)
        cloud_permiss.authorize_ingress(securitygroup_id, '0.0.0.0/0', 'tcp', 22, 22)
        if i==0:
            cloud_permiss.authorize_ingress(securitygroup_id, '0.0.0.0/0', 'tcp', 443, 443) # BYOC_web accepts https traffic from https (port 443).
        inst_id = simple_vm(basenames[i], ips[i], subnet_id, securitygroup_id, key_name)
        #_ = vm.upgrade_os(inst_id, printouts=True)
        inst_ids.append(inst_id)

    for i in range(3): # Break up the loops so that the instances are bieng started up concurrently.
        addr = cloud_core.create_once('address', basenames[i]+'_address', True, Domain='vpc')
        cloud_core.assoc(inst_ids[i], addr)
        #vm.update_apt(inst_ids[i], printouts=True, full_restart_here=True)
        cmds.append(vm.ssh_bash(inst_ids[i], True))

    for i in range(3):
        inst_id = inst_ids[i]

        tubo = vm.install_package(inst_id, 'apt mysql-client', printouts=True)
        for pk_name in ['apt net-tools', 'apt netcat', 'apt vim', 'apt tcpdump', 'apt ping']:
            tubo = vm.install_package(tubo, pk_name, printouts=True)
    vm.install_custom_package(inst_ids[1], 'app-server')
    vm.install_package(inst_ids[0], 'apt apache')
    vm.install_custom_package(inst_ids[0], 'web-server')
    vm.install_package(inst_ids[2], 'apt mysql-server', printouts=True)

    #The gateway is the VpcPeeringConnectionId
    peering_id = cloud_core.create_once('vpcpeer', 'BYOC_3lev_peer', True, VpcId=jbox_vpc_id, PeerVpcId=vpc_id) #cloud_core.assoc(jbox_vpc_id, vpc_id)
    rtables = cloud_query.get_resources('rtables')

    print("Creating route on hub rtable id:", jbox_rtable_id)
    cloud_core.create_route(jbox_rtable_id, '10.201.0.0/16', peering_id)

    print("Creating route on Spoke1 rtable id:", routetable_id)
    cloud_core.create_route(routetable_id, '10.200.0.0/16', peering_id)

    # Testing time:
    jbox_id = cloud_format.obj2id(fittings.flat_lookup(cloud_query.get_resources('machine'), 'VpcId', jbox_vpc_id, assert_range=[1, 65536])[0])
    print(f'Testing ssh ping from machine {jbox_id}')

    #TODO: C. Test the peering connection and routing by pinging the VMs web, app, and db, from the jumpbox.
    is_ssh = cloud_vm.our_vm_id() != jbox_id # TODO: True in the cloud shell, False if we are in the jumpbox.
    tubo = vm.patient_ssh_pipe(jbox_id, printouts=True) if is_ssh else eye_term.MessyPipe('bash', None, printouts=True)
    ping_check = '0% packet loss'
    test_pairs = [['ping -c 2 localhost',ping_check]]
    for ip in ips:
        test_pairs.append([f'ping -c 2 {ip}', ping_check])
    p = plumber.Plumber(tubo, [], {}, [], test_pairs, fn_override=None, dt=2.0)
    p.run()
    tubo.API('ping -c 2 localhost')
    for ip in ips:
        cmd = f'ping -c 2 {ip}'
        tubo.API(cmd, timeout=16)

    tubo.close()
    #if 'packet loss' not in txt:
    #    print('WARNING: Cant extract ping printout to test.')
    #elif '50% packet loss' in txt or '100% packet loss' in txt:
    #    print('WARNING: Packets lost in test')

    print('Check the above ssh ping test')
    print('Restarting the three new vms as a final step.')
    cloud_vm.restart_vm(inst_ids)
    print("\033[38;5;208mThree tier appears to be setup and working (minus an instance restart which is happening now).\033[0m")
    return cmds
