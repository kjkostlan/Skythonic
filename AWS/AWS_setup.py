# Tools to set up some common kinds of resources
import boto3
import AWS.AWS_core as AWS_core
import vm
import time
ec2r = boto3.resource('ec2'); ec2c = boto3.client('ec2')

def simple_vm(vm_name, private_ip, subnet_id, securitygroup_id, key_name):
    # Creates a new key if need be, but the subnet and securitygroup must be already made.
    inst_networkinter = [{'SubnetId': subnet_id, 'DeviceIndex': 0, 'PrivateIpAddress': private_ip,
                          'AssociatePublicIpAddress': False, 'Groups': [securitygroup_id]}]
    vm_params = {'ImageId':'ami-0735c191cf914754d', 'InstanceType':'t2.micro',
                 'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter,
                 'KeyName':key_name}

    key_mat = None
    try:
        key_pair = AWS_core.create('keypair', key_name, raw_object=True) #key_pair = AWS_core.create('keypair', 'Private Public', KeyName='ec2-keypair')#ec2.create_key_pair(KeyName='ec2-keypair')
        key_mat = key_pair.key_material
    except Exception as e:
        if 'The keypair already exists' not in str(e)+repr(e): # Key already exists
            raise e

    inst_id = AWS_core.create('machine', vm_name, **vm_params)

    pem_fname = vm.danger_key(inst_id, key_name, key_mat)
    if key_mat is not None:
        print('Machine set up and key saved to:', pem_fname)

    # TODO new cmds run on the fresh machine: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html
    return inst_id

def wait_and_attach_address(machine_id, address_id):
    # TODO: build this into the AWS_core function.
    addr = AWS_core.id2obj(address_id)
    f_try = lambda: AWS_core.assoc(addr['AllocationId'], machine_id) #ec2c.associate_address(AllocationId=addr['AllocationId'],InstanceId=inst_id)
    f_catch = lambda e:"The pending instance" in repr(e) and "is not in a valid state" in repr(e)
    msg = 'Waiting for machine: '+machine_id+' to start'
    AWS_core.loop_try(f_try, f_catch, msg, delay=4)

def setup_jumpbox(basename='jumpbox', subnet_zone='us-west-2c'): # The jumpbox is much more configurable than the cloud shell.
    # Note: for some reason us-west-2d fails for this vm, so us-west-2c is the default.
    vpc_id = AWS_core.create('VPC', 'Hub', CidrBlock='10.100.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    print('VPC set up')

    webgate_id = AWS_core.create('webgate', basename+'_gate') # AWS_core.create_internet_gateway()
    AWS_core.assoc(vpc_id, webgate_id) #ec2c.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=webgate_id)
    routetable_id = AWS_core.create('rtable', basename+'_rtable', VpcId=vpc_id)
    ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='0.0.0.0/0',GatewayId=webgate_id) #route = AWS_core.create('route', 'To the wild blue yonder', DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id) #routetable.create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id)
    subnet_id = AWS_core.create('subnet',basename+'_subnet',CidrBlock='10.100.250.0/24', VpcId=vpc_id, AvailabilityZone=subnet_zone) #ec2.create_subnet(CidrBlock='172.16.1.0/24', VpcId=vpc.id)
    AWS_core.assoc(routetable_id, subnet_id) #ec2c.associate_route_table(RouteTableId=routetable_id, SubnetId=subnet_id)
    securitygroup_id = AWS_core.create('securitygroup', basename+'_sGroup', GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc_id)#ec2.create_security_group(GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc.id)
    ec2c.authorize_security_group_ingress(GroupId=securitygroup_id, CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22) #securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
    print('routing set up')

    key_name = 'basic_keypair'
    inst_id = simple_vm(basename+'_VM', '10.100.250.100', subnet_id, securitygroup_id, key_name)

    addr = AWS_core.create('address', basename+'_address', Domain='vpc')
    wait_and_attach_address(inst_id, addr)

    cmd = vm.ssh_cmd(inst_id, addr, True)
    print('Use this to ssh:',cmd)
    print('Yes past the security warning (safe to do in this particular case) and ~. to leave ssh session.')
    return inst_id, cmd

def setup_threetier(key_name='basic_keypair', old_vpcname='Hub', new_vpc_name='Spoke1', subnet_zone='us-west-2c'):
    vpc_id = AWS_core.create('VPC', new_vpc_name, CidrBlock='10.101.0.0/16')
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})

    webgate_id = AWS_core.create('webgate', vpc_name+'_gate')
    AWS_core.assoc(vpc_id, webgate_id)

    vpcs = AWS_query.get_resources()['vpcs']
    old_vpc_id = None
    for vpc in vpcs:
        if AWS_core.tag_dict(vpc).get('Name', None)==old_vpcname:
            old_vpc_id = AWS_core.obj2id(vpc)
    if old_vpc_id is None:
        raise Exception('Cannot find this vpc name:'+old_vpcname)

    routetable_id = AWS_core.create('rtable', 'Spoke1_rtable', VpcId=vpc_id)

    basenames = ['web', 'app', 'db']
    subnet_cidrs = ['10.101.101.0/24', '10.101.102.0/24', '10.101.103.0/24']
    ips =          ['10.101.101.100',  '10.101.102.100',  '10.101.103.100']
    inst_ids = []
    cmds = []
    for i in range(3):
        ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='0.0.0.0/0',GatewayId=webgate_id)
        subnet_id = AWS_core.create('subnet',basenames[i],CidrBlock=subnet_cidrs[i], VpcId=vpc_id, AvailabilityZone=subnet_zone)
        AWS_core.assoc(routetable_id, subnet_id)

        # They have different security groups for different types of servers, so we will do so as well rather than use only one for all three:
        #https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
        securitygroup_id = AWS_core.create('securitygroup', basenames[i]+'_sGroup', GroupName='SSH-ONLY'+basenames[i], Description='only allow SSH traffic', VpcId=vpc_id)
        ec2c.authorize_security_group_ingress(GroupId=securitygroup_id, CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
        print('routing set up', basenames[i])

        inst_ids.append(simple_vm(basenames[i], ips[i], subnet_id, securitygroup_id, key_name))
        print('VM launched', basenames[i])

    for i in range(3): # Break up the loops so that the instances are bieng started up concurrently.
        addr = AWS_core.create('address', basenames[i]+'_address', Domain='vpc')
        wait_and_attach_address(inst_ids[i], addr)

        cmds.append(vm.ssh_cmd(inst_id, addr, True))

    #The gateway is the VpcPeeringConnectionId
    peering_id = AWS_core.create('vpcpeer', VpcId=old_vpc_id, PeerVPCId=vpc_id) #AWS_core.assoc(old_vpc_id, vpc_id)
    rtables = ec2c.describe_route_tables()['RouteTables']
    old_rtable_id = None
    for rt in rtables:
        if old_vpc_id in str(rt):
            old_rtable_id = AWS_core.id2obj(old_vpc_id)
    if old_rtable_id is None:
        raise Exception("cant find VPC peering old route table.")
    ec2c.create_route(RouteTableId=old_rtable_id, DestinationCidrBlock='10.101.0.0/16',GatewayId=peering_id)
    ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='10.100.0.0/16',GatewayId=peering_id)

    #TODO: C. Test the peering connection and routing by pinging the VMs web, app, and db, from the jumpbox.
    return cmds
