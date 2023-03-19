# Tools to set up some common kinds of resources
import boto3
import AWS.AWS_core as AWS_core
import vm
import time
ec2r = boto3.resource('ec2'); ec2c = boto3.client('ec2')

def default_vm_params(subnet_id, securitygroup_id, key_name):
    inst_networkinter = [{'SubnetId': subnet_id, 'DeviceIndex': 0, 'PrivateIpAddress': '10.100.250.100',
                          'AssociatePublicIpAddress': False, 'Groups': [securitygroup_id]}]
    vm_params = {'ImageId':'ami-0735c191cf914754d', 'InstanceType':'t2.micro',
                 'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter,
                 'KeyName':key_name}
    # TODO for installation: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html
    return vm_params

def setup_jumpbox(basename='jumpbox', subnet_zone='us-west-2c'): # The jumpbox is much more configurable than the cloud shell.
    # Note: for some reason us-west-2d fails.
    vpc_id = AWS_core.create('VPC', basename+'_VPC', CidrBlock='10.100.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
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

    ky_name = basename+'_keypair'
    key_pair = AWS_core.create('keypair', ky_name, raw_object=True) #key_pair = AWS_core.create('keypair', 'Private Public', KeyName='ec2-keypair')#ec2.create_key_pair(KeyName='ec2-keypair')
    print('key set up')

    vm_params = default_vm_params(subnet_id, securitygroup_id, ky_name)
    inst_id = AWS_core.create('machine', basename+'_VM',**vm_params)

    pem_fname = vm.danger_key(inst_id, ky_name, key_pair.key_material)
    print('Machine set up and key saved to:', pem_fname)

    addr = AWS_core.id2obj(AWS_core.create('address', basename+'_address', Domain='vpc'))
    f_try = lambda: AWS_core.assoc(addr['AllocationId'], inst_id) #ec2c.associate_address(AllocationId=addr['AllocationId'],InstanceId=inst_id)
    f_catch = lambda e:"The pending instance" in repr(e) and "is not in a valid state" in repr(e)
    msg = 'Waiting for machine: '+inst_id+' to start'
    AWS_core.loop_try(f_try, f_catch, msg, delay=4)

    cmd = vm.ssh_cmd(inst_id, addr, True)
    print('Use this to ssh:',cmd)
    print('Yes past the security warning (safe to do in this particular case) and ~. to leave ssh session.')
    return inst_id, cmd
