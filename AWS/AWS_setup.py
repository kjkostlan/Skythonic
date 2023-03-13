# Tools to set up some common kinds of resources
import boto3
import AWS.AWS_core as AWS_core
def setup_jumpbox(): # The jumpbox is much more configurable than the cloud shell.
    ec2r = boto3.resource('ec2')
    ec2c = boto3.client('ec2')
    vpc = AWS_core.create('VPC', 'jumpbox_VPC', CidrBlock='10.100.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
    ec2c.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
    ec2c.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )

    internetgateway = AWS_core.create('webgate', 'jumpbox_gate') # AWS_core.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)
    routetable = AWS_core.create('rtable', 'jumpbox_rtable', VpcId=vpc.id)
    routetable.create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id) #route = AWS_core.create('route', 'To the wild blue yonder', DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id) #routetable.create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id)
    subnet = AWS_core.create('subnet','jumpbox_subnet',CidrBlock='10.100.250.0/24', VpcId=vpc.id) #ec2.create_subnet(CidrBlock='172.16.1.0/24', VpcId=vpc.id)
    routetable.associate_with_subnet(SubnetId=subnet.id)
    securitygroup = AWS_core.create('securitygroup', 'jumpbox_sGroup', GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc.id)#ec2.create_security_group(GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc.id)
    securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
    key_pair = ec2c.create_key_pair(KeyName='jumpbox_keypair') #key_pair = AWS_core.create('keypair', 'Private Public', KeyName='ec2-keypair')#ec2.create_key_pair(KeyName='ec2-keypair')
    KeyPairOut = str(key_pair['KeyMaterial'])
    outfile = open('jumpbox_privatekey.pem', 'w')
    outfile.write(KeyPairOut)
    outfile.close()

    inst_networkinter = [{'SubnetId': subnet.id, 'DeviceIndex': 0, 'PrivateIpAddress': '10.100.250.100',
                          'AssociatePublicIpAddress': False, 'Groups': [securitygroup.group_id]}]

    vm_params = {'ImageId':'ami-0735c191cf914754d', 'InstanceType':'t2.micro',
                 'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter, 'KeyName':'jumpbox_keypair'}
    x = AWS_core.create('machines', 'jumpbox_VM',**vm_params)
    addr = AWS_core.create('address', 'jumpbox_address', Domain='vpc')
    ec2.associate_address(AllocationId=addr['AllocationId'],InstanceId=x.id)

    cmd = 'ssh -i jumpbox_privatekey.pem ubuntu@'+str(addr['PublicIp'])
    print('Use this:',cmd)
    # TODO: chmod 600 jump*
    return x, cmd
#ssh -i jumpbox_privatekey.pem ubuntu@<ip>
