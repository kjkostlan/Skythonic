# Tools to set up some common kinds of resources
import boto3
import AWS.AWS_core as AWS_core
import time
def setup_jumpbox(basename='jumpbox'): # The jumpbox is much more configurable than the cloud shell.
    ec2r = boto3.resource('ec2')
    ec2c = boto3.client('ec2')
    vpc_id = AWS_core.create('VPC', basename+'_VPC', CidrBlock='10.100.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
    ec2c.modify_vpc_attribute( VpcId = vpc_id , EnableDnsSupport = { 'Value': True } )
    ec2c.modify_vpc_attribute( VpcId = vpc_id , EnableDnsHostnames = { 'Value': True } )
    print('VPC set up')

    webgate_id = AWS_core.create('webgate', basename+'_gate') # AWS_core.create_internet_gateway()
    ec2c.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=webgate_id)
    routetable_id = AWS_core.create('rtable', basename+'_rtable', VpcId=vpc_id)
    ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='0.0.0.0/0',GatewayId=webgate_id) #route = AWS_core.create('route', 'To the wild blue yonder', DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id) #routetable.create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id)
    subnet_id = AWS_core.create('subnet',basename+'_subnet',CidrBlock='10.100.250.0/24', VpcId=vpc_id) #ec2.create_subnet(CidrBlock='172.16.1.0/24', VpcId=vpc.id)
    ec2c.associate_route_table(RouteTableId=routetable_id, SubnetId=subnet_id) #routetable.associate_with_subnet(SubnetId=subnet_id)
    securitygroup_id = AWS_core.create('securitygroup', basename+'_sGroup', GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc_id)#ec2.create_security_group(GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc.id)
    ec2c.authorize_security_group_ingress(GroupId=securitygroup_id, CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22) #securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
    print('routing set up')

    inst_networkinter = [{'SubnetId': subnet_id, 'DeviceIndex': 0, 'PrivateIpAddress': '10.100.250.100',
                          'AssociatePublicIpAddress': False, 'Groups': [securitygroup_id]}]
    ky_name = basename+'_keypair'
    key_pair = AWS_core.create('keypair', KeyName=ky_name, raw_object=True) #key_pair = AWS_core.create('keypair', 'Private Public', KeyName='ec2-keypair')#ec2.create_key_pair(KeyName='ec2-keypair')
    print('key set up')

    # TODO: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html
    vm_params = {'ImageId':'ami-0735c191cf914754d', 'InstanceType':'t2.micro',
                 'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter, 'KeyName':ky_name}
    f_try = lambda: AWS_core.create('machines', basename+'_VM',**vm_params)
    f_catch = lambda: 'is not supported in your requested Availability Zone' in f_try
    msg = 'Random not supported AZ errors, retrying'
    x_id = AWS_core.loop_try(f_try, f_catch, msg, delay=4)
    pem_fname = vm.danger_key(x_id, ky_name, key_pair['key_material'], include_direct_pem_file=True)
    print('Machine set up and key saved to:', pem_fname)

    addr = AWS_core.id2obj(AWS_core.create('address', basename+'_address', Domain='vpc'))
    f_try = lambda: ec2c.associate_address(AllocationId=addr['AllocationId'],InstanceId=x_id)
    f_catch = lambda e:"The pending instance" in repr(e) and "is not in a valid state" in repr(e)
    msg = 'Waiting for machine:'+x_id+' to start'
    AWS_core.loop_try(f_try, f_catch, msg, delay=4)

    cmd = vm.ssh_cmd(x_id, addr, True)
    print('Use this to ssh:',cmd)
    return x_id, cmd

#ssh -i jumpbox_privatekey.pem ubuntu@<ip>
