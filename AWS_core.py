# Core AWS functions.
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def assign_name(x, name):
    x.create_tags(Tags=[{'Key': 'Name', 'Value': name}])

def create(type, name, **kwargs):
    type = type.lower()
    if type in {'vpc'}: # Python only intruduced the switch statement in 3.10
        x = ec2r.create_vpc(**kwargs)
        x.wait_until_available()
    elif type in {'webgate','internetgateway'}:
        x = ec2r.create_internet_gateway(**kwargs)
    elif type in {'rtable','routetable'}:
        x = ec2r.create_route_table(**kwargs)
    elif type in {'subnet'}:
        x = ec2r.create_subnet(**kwargs)
    elif type in {'route'}:
        x = ec2r.create_route(**kwargs)
    elif type in {'securitygroup'}:
        x = ec2r.create_security_group(**kwargs)
    elif type in {'keypair'}:
        x = ec2r.create_key_pair(**kwargs)
    elif type in {'instance', 'instances', 'machine', 'machines'}:
        x = ec2r.create_instances(**kwargs)
    else:
        raise Exception('Create ob type unrecognized:'+str(type))
    assign_name(x, name)
    return x

def delete(obj_or_id):
    # Delete an object given an id OR a description dict.
    if type(obj_or_id) is dict:
        avoid = {'DhcpOptionsId','OwnerId','AvailabilityZoneId'} # TODO: more will be needed.
        kys = obj_or_id.keys()
        for ky in kys:
            if ky not in avoid and ky.endswith('Id'):
                id = obj_or_id[ky]
                break
        if type(id) is dict:
            raise Exception('Cant extract the Id')
    else:
        id = obj_or_id
    if id.startswith('igw-'):
        attchs = ec2c.describe_internet_gateways(InternetGatewayIds=[id])['InternetGateways'][0]['Attachments']
        for attch in attchs: # Must detach before deletion.
            ec2c.detach_internet_gateway(InternetGatewayId=id, VpcId=attch['VpcId'])
        ec2c.delete_internet_gateway(InternetGatewayId=id)
    elif id.startswith('vpc-'):
        ec2c.delete_vpc(VpcId=id)
    elif id.startswith('subnet-'):
        ec2c.delete_subnet(SubnetId=id)
    elif id.startswith('key-'): #Only needs the name.
        ec2c.delete_key_pair(KeyId=id)
        #ky_nm = ec2c.describe_internet_gateways(KeyId=[id])['KeyPairs'][0]['key_name']
        #ec2c.delete_key_pair(KeyName=ky_nm)
    elif id.startswith('sg-'):
        ec2c.delete_securit_group(GroupId=id)
    else:
        raise Exception('TODO: handle this case:', id)

# TODO: have a generalize "assocate" function.
def assoc_gateway(vpc, gate_id):
    vpc.attach_internet_gateway(InternetGatewayId=gate_id)
def assoc_subnet(vpc, subnet_id):
    vpc.associate_with_subnet(SubnetId=subnet_id)
