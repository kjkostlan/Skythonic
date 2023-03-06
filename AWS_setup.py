# Setup aws test.
import boto3
from . import AWS_core
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
vpc = AWS_core.create_ob('VPC', 'VPC0', CidrBlock='172.16.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
ec2c.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
ec2c.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )

internetgateway = AWS_core.create_ob('webgate', 'the gate') # AWS_core.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)
routetable = AWS_core.create_ob('rtable', 'my one-entry table') #vpc.create_route_table() #
route = AWS_core.create_ob('route', 'To the wild blue yonder', DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id) #routetable.create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=internetgateway.id)
subnet = AWS_core.create_ob('subnet','This is a subnet',CidrBlock='172.16.1.0/24', VpcId=vpc.id) #ec2.create_subnet(CidrBlock='172.16.1.0/24', VpcId=vpc.id)
routetable.associate_with_subnet(SubnetId=subnet.id)
securitygroup = AWS_core.create_ob('securitygroup','It is somewhat secure', GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc.id)#ec2.create_security_group(GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc.id)
securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
outfile = open('ec2-keypair.pem', 'w')
key_pair = AWS_core.create_ob('keypair', 'Private Public', KeyName='ec2-keypair')#ec2.create_key_pair(KeyName='ec2-keypair')
KeyPairOut = str(key_pair.key_material)
outfile.write(KeyPairOut)

inst_networkinter = [{'SubnetId': subnet.id, 'DeviceIndex': 0,
                      'AssociatePublicIpAddress': True, 'Groups': [securitygroup.group_id]}]

vm_params = {'ImageId':'ami-0de53d8956e8dcf80', 'InstanceType'='t2.micro',
               'MaxCount'=1, 'MinCount'=1,'NetworkInterfaces'=inst_networkinter,KeyName='ec2-keypair'}
AWS_core.create_ob('machines', 'The tenth-of-a-core machine',vm_params)
