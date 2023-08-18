# Scripts that setup common machines and simple networks.
import sys, time
import vm, covert, proj
from waterworks import eye_term, fittings, plumber

proj.platform_import_modules(sys.modules[__name__], ['cloud_core', 'cloud_format', 'cloud_query', 'cloud_vm', 'cloud_permiss'])
platform = proj.which_cloud().lower().strip()

try:
    debug_skip_install # Still installs ping tot test basic network configs.
except:
    debug_skip_install = False

def simple_vm_createonce(vm_name, private_ip, subnet_id, securitygroup_id, key_name, public_ip_id, the_region, az_nic_name):
    # Creates a new key if need be, but the subnet and securitygroup must be already made.
    # Returns inst_id, None, fname.
    if platform=='aws':
        inst_networkinter = [{'SubnetId': subnet_id, 'DeviceIndex': 0, 'PrivateIpAddress': private_ip,
                              'AssociatePublicIpAddress': False, 'Groups': [securitygroup_id]}]
        vm_params = {'ImageId':cloud_vm.ubuntu_aim_image(), 'InstanceType':'t2.micro',
                     'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter,
                     'KeyName':key_name}
        inst_id = covert.create_once_vm_dangerkey(vm_name, vm_params, key_name)
        cloud_core.assoc(inst_id, public_ip_id)
        return inst_id
    elif platform=='azure':
        from Azure import Azure_query, Azure_format
        inst_id1 = Azure_query.get_by_name('machine', vm_name)
        if inst_id1 is not None:
            print(f'Azure VM already created ({vm_name}); skipping the setup.')
            return Azure_format.obj2id(inst_id1)
        from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet, VirtualNetworkGateway, RouteTable, Route, NetworkSecurityGroup, PublicIPAddress, NetworkInterface # DEBUG.
        from Azure import Azure_nugget, Azure_format # DEBUG (will move making a nic to Azure_core).
        ip_config = [{"name": az_nic_name, "subnet": {"id": subnet_id}, "public_ip_address": {"id": public_ip_id}, "private_ip_address":private_ip, "private_ip_allocation_method":'Static'}]
        nic = NetworkInterface(id="", location=Azure_format.enumloc(the_region), ip_configurations=ip_config)
        nic = Azure_nugget.network_client.network_interfaces.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, az_nic_name, nic).result()
        print('Adding the network security group:', securitygroup_id)
        nic.network_security_group = {'id': securitygroup_id}
        Azure_nugget.network_client.network_interfaces.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, az_nic_name, nic).result()

        #vm = VirtualMachine(location=location, os_profile=OSProfile(computer_name=vm_name, admin_username=username, linux_configuration={"ssh": {"public_keys": [{"path": "/home/{}/.ssh/authorized_keys".format(username), "key_data": public_key}]}}))
        #vm.storage_profile = StorageProfile(os_disk={"os_type": "Linux", "name": os_disk_name, "create_option": "FromImage"}, image_reference=ImageReference(publisher="Canonical", offer="UbuntuServer", sku="20_04-lts-gen2", version="latest"))
        #vm.hardware_profile = {"vm_size": vm_size}
        #vm.network_profile = {"network_interfaces": [{"id": nic.id}]}
        #vm = compute_client.virtual_machines.begin_create_or_update(resource_group_name, vm_name, vm).result()
        from azure.mgmt.compute.models import OSProfile, StorageProfile, DataDisk # But these are NOT debug since there are multible levels of params.
        vm_params = {}
        vm_params['location'] = Azure_format.enumloc(the_region)
        # Covert will fill out vm_params['os_profile']
        vm_params['network_profile'] = {"network_interfaces": [{"id": nic.id}]}
        vm_params['hardware_profile'] = {"vm_size": "Standard_DS1_v2"}  # Different options here.
        os_disk_name = vm_name+'-osdisk' # Aesthetic (I think).
        vm_params['storage_profile'] = StorageProfile(os_disk={"os_type": "Linux", "name": os_disk_name, "create_option": "FromImage"}, image_reference=cloud_vm.ubuntu_aim_image(the_region))
        inst_id = covert.create_once_vm_dangerkey(vm_name, vm_params, key_name) # Already assoced with the address.
        return inst_id
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)

    raise Exception('Should have returned inside the code box.')

def setup_jumpbox(basename='jumpbox', the_region='us-west-2c', user_name='BYOC', key_name='BYOC_keypair'): # The jumpbox is much more configurable than the cloud shell.
    # Note: for some reason us-west-2d fails for this vm, so us-west-2c is the default.
    vm_name = user_name+'_'+basename+'_VM'
    if platform=='azure':
        vm_name = vm_name.replace('_','0') # Why the !@#$ do they not allow underscores.
        if len(vm_name)>64:
            raise Exception('Oops the vm_name was too long because the user_name or basename is too long.')

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

    cloud_permiss.authorize_ingress(securitygroup_id, '0.0.0.0/0', 'tcp', port0=22, port1=22, priority=100)

    if platform == 'aws':
        addr_id = cloud_core.create_once('address', user_name+'_'+basename+'_address', True, Domain='vpc')
    elif platform == 'azure':
        # What does this do? dns_settings=PublicIPAddressDnsSettings(domain_name_label="your-domain-label")
        addr_id = cloud_core.create_once('address', user_name+'_'+basename+'_address', True, location=the_region, public_ip_allocation_method='Dynamic', idle_timeout_in_minutes=4)
    else:
        raise Exception('TODO get net_setup working on this cloud platform: '+platform)
    inst_id = simple_vm_createonce(vm_name, '10.200.250.100', subnet_id, securitygroup_id, key_name, addr_id, the_region, 'jumpbox_nic')

    ssh_bash = vm.ssh_bash(inst_id, True)

    print(f'---Setting up {proj.which_cloud()} on the jump box (WARNING: long term secret credentials posted to VM)---')
    region_name = the_region
    if region_name[-1] in 'abcd':
        region_name = region_name[0:-1]

    if debug_skip_install:
        print("WARNING: DEBUG installation of packages skipped (ping will still be installed and thus work across the peering).")
        tubo = vm.install_packages(inst_id, 'apt ping', printouts=True, user_name=user_name)
    else:
        #tubo = vm.upgrade_os(inst_id, printouts=True)
        tubo = vm.install_packages(inst_id, 'apt python3', user_name=user_name, tests=[['python3\nprint(id)\nquit()', '<built-in function id>']])
        for pk_name in ['apt net-tools', 'apt netcat', 'apt vim', 'apt tcpdump']:
            tubo = vm.install_packages(tubo, pk_name, user_name=user_name)
        tubo = vm.install_packages(tubo, 'apt ping', user_name=user_name, tests=[['ping -c 1 localhost', '0% packet loss']])
        for pk_name in ['skythonic', 'host-list']:
            tubo = vm.install_custom_package(tubo, pk_name, user_name=user_name)
        if platform == 'aws':
            tubo = vm.install_packages(tubo, 'apt aws-cli', user_name=user_name, tests=[['aws ec2 describe-vpcs --output text', 'CIDRBLOCKASSOCIATIONSET']])
            tubo = vm.install_packages(tubo, 'pip boto3', user_name=user_name, tests=[["python3\nimport boto3\nboto3.client('ec2').describe_vpcs()\nquit()","'Vpcs': [{'CidrBlock'"]])
        elif platform == 'azure':
            for package_cmd in ['pip azure-core', 'pip azure-identity', 'pip paramiko', 'pip azure-mgmt-resource', 'pip azure-mgmt-compute', 'pip azure-mgmt-storage', 'pip azure-mgmt-network', 'pip install azure-mgmt-storage', 'azure-cli']:
                tubo = vm.install_packages(tubo, package_cmd, user_name=user_name)
                tubo.close()
            from Azure import Azure_permiss # TODO: also put AWS permission fns into AWS_permiss.
            Azure_permiss.empower_vm(inst_id)
        else:
            raise Exception('TODO get net_setup working on this cloud platform: '+platform)
    cloud_vm.restart_vm(inst_id)

    print("\033[38;5;208mJumpbox appears to be setup and working (minus a restart which is happening now).\033[0m")
    return ssh_bash, inst_id

def DEBUG_tubo(instance_id):
    # Why does it hang here but not over there?
    print('creating tubo for:', instance_id)
    vm.patient_ssh_pipe(instance_id, printouts=True, binary_mode=False)
    import time
    time.sleep(10)
    raise Exception('DEBUG TUBO did it create the tubo?')

def setup_threetier(key_name='BYOC_keypair', jbox_name='BYOC_jumpbox_VM', new_vpc_name='BYOC_Spoke1', the_region='us-west-2c', user_name='BYOC'):

    if platform=='azure':
        jbox_name = jbox_name.replace('_','0') # Why the !@#$ do they not allow underscores.
        if len(jbox_name)>64:
            raise Exception('Oops the vm_name was too long because the user_name or basename is too long.')

    if platform=='aws':
        vpc_id = cloud_core.create_once('VPC', new_vpc_name, True, CidrBlock='10.201.0.0/16')
        cloud_core.modify_attribute(vpc_id, 'EnableDnsSupport', {'Value': True})
        cloud_core.modify_attribute(vpc_id, 'EnableDnsHostnames', {'Value': True})
    elif platform=='azure':
        _addr = {"address_prefixes": ['10.201.0.0/16']}
        vpc_id = cloud_core.create_once('VPC', new_vpc_name, True, address_space=_addr, location=cloud_format.enumloc(the_region))
        cloud_core.modify_attribute(vpc_id, 'enable_dns_support', True)
        cloud_core.modify_attribute(vpc_id, 'enable_dns_hostnames', True)
    else:
        raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)

    if platform=='aws':
        webgate_id = cloud_core.create_once('webgate', new_vpc_name+'_gate', True)
        cloud_core.assoc(vpc_id, webgate_id)
    elif platform=='azure':
        pass # Azure needs no internet gateways.
    else:
        raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)

    def _nameget(ty, name):
        x = cloud_query.get_by_name(ty, name)
        if x is None:
            raise Exception(f'Cannot find this name: {name}; make sure setup_jumpbox has been called.')
        return cloud_format.obj2id(x)

    rtables = cloud_query.get_resources('rtable')
    jbox_id = _nameget('machine',jbox_name)
    if platform=='aws':
        jbox_subnet_id = cloud_format.id2obj(jbox_id)['SubnetId']
        jbox_vpc_id = cloud_format.id2obj(jbox_subnet_id)['VpcId']
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
        routetable_id = cloud_core.create_once('rtable', new_vpc_name+'_rtable', True, VpcId=vpc_id)
    elif platform=='azure':
        # TODO: rtable queries to test that things are working as in AWS.
        # TODO (here and other places): Build up and use the assoc function instead.
        from Azure import Azure_nugget
        resource_group_name = jbox_id.split('/')[4]
        #print('The jumpbox is:', cloud_format.id2obj(jbox_id))
        nic_id = cloud_format.id2obj(jbox_id)['properties']['networkProfile']['networkInterfaces'][0]['id']
        nic_name = nic_id.split('/')[-1]
        nic = Azure_nugget.network_client.network_interfaces.get(resource_group_name, nic_name)
        jbox_subnet_id = nic.ip_configurations[0].subnet.id
        jbox_vpc_id = nic.ip_configurations[0].subnet.id.split('/subnets/')[0]
        routetable_id = cloud_core.create_once('rtable', new_vpc_name+'_rtable', True, location=the_region)
        cloud_core.connect_to_internet(routetable_id, vpc_id)
    else:
        raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)

    print('Jumpbox machine ID:', jbox_id, 'Subnet ID:', jbox_subnet_id, 'route table ID:', jbox_vpc_id)

    basenames = ['BYOC_web', 'BYOC_app', 'BYOC_db']
    subnet_cidrs = ['10.201.101.0/24', '10.201.102.0/24', '10.201.103.0/24']
    private_ips =  ['10.201.101.100',  '10.201.102.100',  '10.201.103.100']
    az_nics = [bn + '_nic' for bn in basenames]
    inst_ids = []
    cmds = []
    addrs = []

    for i in range(3): # Break up the loops so that the instances are bieng started up concurrently.
        addrs.append(None)
        if platform == 'aws':
            addrs[i] = cloud_core.create_once('address', basenames[i]+'_address', True, Domain='vpc')
        elif platform == 'azure':
            # What does this do? dns_settings=PublicIPAddressDnsSettings(domain_name_label="your-domain-label")
            addrs[i] = cloud_core.create_once('address', basenames[i]+'_address', True, location=the_region, public_ip_allocation_method='Dynamic', idle_timeout_in_minutes=4)
        #cloud_core.assoc(inst_ids[i], addrs[i]) # Will be done in the simple_vm_createonce function.
        #vm.update_apt(inst_ids[i], printouts=True, full_restart_here=True)

    if platform=='aws':
        cloud_core.create_route(routetable_id, '0.0.0.0/0', webgate_id)
    elif platform=='azure':
        cloud_core.connect_to_internet(routetable_id, vpc_id)
    else:
        raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)

    for i in range(3):

        if platform=='aws':
            subnet_id = cloud_core.create_once('subnet',basenames[i], True, CidrBlock=subnet_cidrs[i], VpcId=vpc_id, AvailabilityZone=the_region)
        elif platform=='azure':
            subnet_id = cloud_core.create_once('subnet',basenames[i], True, address_prefix=subnet_cidrs[i], vnet_id=vpc_id)
        else:
            raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)
        cloud_core.assoc(routetable_id, subnet_id)

        if platform=='aws':
            # They have different security groups for different types of servers, so we will do so as well rather than use only one for all three:
            #https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
            securitygroup_id = cloud_core.create_once('securitygroup', basenames[i]+'_sGroup', True, GroupName='From Hub'+basenames[i], Description='Allow Hub Ip cidr', VpcId=vpc_id)
        elif platform=='azure':
            securitygroup_id = cloud_core.create_once('securitygroup', basenames[i]+'_sGroup', True, location=the_region)
        else:
            raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)

        if i==0:
            cloud_permiss.authorize_ingress(securitygroup_id, '0.0.0.0/0', 'tcp', 443, 443, priority=110) # BYOC_web accepts https traffic from https (port 443).
        cloud_permiss.authorize_ingress(securitygroup_id, '10.0.0.0/8', '-1', 22, 22, priority=101)
        cloud_permiss.authorize_ingress(securitygroup_id, '0.0.0.0/0', 'tcp', 22, 22, priority=100) # SSH.

        if type(addrs[i]) is dict:
            ip_id = addrs[i]['id']
        elif type(addrs[i]) is str:
            ip_id = addrs[i]
        else:
            raise Exception('Problem getting the addres IDs (IDs different from the IPs)')
        inst_id = simple_vm_createonce(basenames[i].replace('_','0') if platform=='azure' else basenames[i], private_ips[i], subnet_id, securitygroup_id, key_name, ip_id, the_region, az_nics[i])
        #_ = vm.upgrade_os(inst_id, printouts=True)
        inst_ids.append(inst_id)
        cmds.append(vm.ssh_bash(inst_id, True))

    #DEBUG_tubo(inst_ids[0])

    if debug_skip_install:
        print("WARNING: DEBUG installation of packages skipped (ping will still be installed and thus work across the peering).")
        for i in range(3):
            tubo = vm.install_packages(inst_ids[i], 'apt ping', printouts=True, user_name=user_name)
    else:
        for i in range(3):
            inst_id = inst_ids[i]

            tubo = vm.install_packages(inst_id, 'apt mysql-client', printouts=True, user_name=user_name)
            for pk_name in ['apt net-tools', 'apt netcat', 'apt vim', 'apt tcpdump', 'apt ping']:
                tubo = vm.install_packages(tubo, pk_name, printouts=True, user_name=user_name)

        vm.install_custom_package(inst_ids[1], 'app-server', printouts=True, user_name=user_name)
        vm.install_packages(inst_ids[0], 'apt apache', printouts=True, user_name=user_name)
        web_s_tests = [['sudo service apache2 start',''], ['curl -k http://localhost', ['apache2', '<div>', '<html']],
                       ['systemctl status apache2.service', ['The Apache HTTP Server', 'Main PID:']]]
        vm.install_custom_package(inst_ids[0], 'web-server', tests=web_s_tests, user_name=user_name)
        vm.install_packages(inst_ids[2], 'apt mysql-server', printouts=True, user_name=user_name)

    if platform=='aws':
        #The gateway is the VpcPeeringConnectionId
        peering_id = cloud_core.create_once('vpcpeer', 'BYOC_3lev_peer', True, VpcId=jbox_vpc_id, PeerVpcId=vpc_id) #cloud_core.assoc(jbox_vpc_id, vpc_id)
        print("Creating route on hub rtable id:", jbox_rtable_id)
        cloud_core.create_route(jbox_rtable_id, '10.201.0.0/16', peering_id)

        print("Creating route on Spoke1 rtable id:", routetable_id)
        cloud_core.create_route(routetable_id, '10.200.0.0/16', peering_id)
    elif platform=='azure':
        # TODO: clumsy, duplicate code here!
        from Azure import Azure_nugget
        peering_name = 'simple_peering'
        peering_params = {
            "allow_virtual_network_access": True,
            "allow_forwarded_traffic": False,
            "allow_gateway_transit": False,
            "use_remote_gateways": False}
        resource_group_name = jbox_vpc_id.split('/')[4]
        peering_to2 = Azure_nugget.network_client.virtual_network_peerings.begin_create_or_update(
            resource_group_name,
            jbox_vpc_id, # From this to the other vpc_id.
            peering_name,
            peering_params).result()
        peering_to1 = Azure_nugget.network_client.virtual_network_peerings.begin_create_or_update(
            resource_group_name,
            vpc_id, # Back to the jbox_vpc_id.
            peering_name,
            peering_params).result()

        route_params = {
            "address_prefix": '10.201.0.0/16',
            "next_hop_type": "VirtualNetworkPeering",
            "next_hop_ip_address": peering_to2.remote_virtual_network.id
        }
        route = network_client.routes.begin_create_or_update(
            resource_group_name,
            route_table_name,
            route_name,
            route_params
        ).result()
        route_params = {
            "address_prefix": '10.200.0.0/16',
            "next_hop_type": "VirtualNetworkPeering",
            "next_hop_ip_address": peering_to1.remote_virtual_network.id
        }
        route = network_client.routes.begin_create_or_update(
            resource_group_name,
            route_table_name,
            route_name,
            route_params
        ).result()
    else:
        raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)

    rtables = cloud_query.get_resources('rtables')

    # Testing time:
    if platform=='aws':
        #jbox_id = cloud_format.obj2id(fittings.flat_lookup(cloud_query.get_resources('machine'), 'VpcId', jbox_vpc_id, assert_range=[1, 65536])[0])
        pass # Don't we already have jbox_id?
    elif platform=='azure':
        #TODO
        pass # Don't we already have jbox_id?
    else:
        raise Exception('TODO get net_setup three tier working on this cloud platform: '+platform)
    print(f'Testing ssh ping from machine {jbox_id}')

    #partial TODO: C. Test the peering connection and routing by pinging the VMs web, app, and db, from the jumpbox.
    is_ssh = cloud_vm.our_vm_id() != jbox_id # TODO: True in the cloud shell, False if we are in the jumpbox.
    tubo = vm.patient_ssh_pipe(jbox_id, printouts=True) if is_ssh else eye_term.MessyPipe('bash', None, printouts=True)
    ping_check = '0% packet loss'
    test_pairs = [['ping -c 2 localhost',ping_check]]
    for ip in private_ips:
        test_pairs.append([f'ping -c 2 {ip}', ping_check])
    p = plumber.Plumber(tubo, [{'tests':test_pairs}], {}, fn_override=None, dt=2.0)
    p.run()
    tubo.API('ping -c 2 localhost')
    for ip in private_ips:
        cmd = f'ping -c 2 {ip}'
        tubo.API(cmd, timeout=16)

    tubo.close()

    print('Check the above ssh ping test')
    print('Restarting the three new vms as a final step.')
    cloud_vm.restart_vm(inst_ids)
    print("\033[38;5;208mThree tier appears to be setup and pinging across the peering (minus an instance restart which is happening now).\033[0m")
    return cmds
