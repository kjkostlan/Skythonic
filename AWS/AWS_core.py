# Core AWS functions.
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def assign_name(x, name): #Most everything can be named.
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
    elif type in {'securitygroup', 'sgroup'}:
        x = ec2r.create_security_group(**kwargs)
    elif type in {'keypair'}:
        x = ec2r.create_key_pair(**kwargs)
    elif type in {'instance', 'instances', 'machine', 'machines'}:
        x = ec2r.create_instances(**kwargs)[0]
    elif type in {'address'}:
        x = ec2r.allocate_address(**kwargs)
    else:
        raise Exception('Create ob type unrecognized:'+str(type))
    assign_name(x, name)
    return x

def obj2id(obj_desc): # Gets the ID from the object.
    #(This is a bit tricky since some descs have multible ids)
    if type(obj_desc) is str:
        return obj_desc
    id = None
    avoid = {'DhcpOptionsId','OwnerId','AvailabilityZoneId', 'ImageId'} # TODO: more will be needed.
    priority = ['InstanceId', 'RouteTableId', 'SubnetId'] # Order matters here for objects with multible Id's.
    for kp in priority:
        if kp in obj_desc:
            return obj_desc[kp]
    if 'eni-' in str(obj_desc):
        print('eni- bearing:', obj_desc)
    kys = obj_desc.keys()
    for ky in kys:
        if ky not in avoid and ky.endswith('Id'):
            id = obj_desc[ky]
            break
    if id is None:
        raise Exception("Can't extract the Id.")
    return id

def id2obj(id):
    if type(id) is dict:
        return id # Already a description.
    if id.startswith('igw-'):
        return ec2c.describe_internet_gateways(InternetGatewayIds=[id])['InternetGateways'][0]
    elif id.startswith('vpc-'):
        return ec2c.describe_vpcs(VpcIds=[id])['Vpcs'][0]
    elif id.startswith('subnet-'):
        return ec2c.describe_subnets(SubnetIds=[id])['Subnets'][0]
    elif id.startswith('key-'): #Only needs the name.
        return ec2c.describe_key_pairs(KeyPairIds=[id])['KeyPairs'][0]
    elif id.startswith('sg-'):
        return ec2c.describe_security_groups(GroupIds=[id])['SecurityGroups'][0]
    elif id.startswith('rtb-'):
        return ec2c.describe_route_tables(RouteTableIds=[id])['RouteTables'][0]
    elif id.startswith('i-'):
        return ec2c.describe_instances(InstanceIds=[id])['Instances'][0]
    elif id.startswith('addr-'):
        return ec2c.describe_addresses(AddressIds=[id])['Addresses'][0]
    else:
        raise Exception('TODO: handle this case:', id)

def delete(desc_or_id): # Delete an object given an id OR a description dict.
    id = obj2id(desc_or_id)
    if id.startswith('igw-'):
        attchs = ec2c.describe_internet_gateways(InternetGatewayIds=[id])['InternetGateways'][0]['Attachments']
        for attch in attchs: # Must detach before deletion. TODO: detaching for everything.
            ec2c.detach_internet_gateway(InternetGatewayId=id, VpcId=attch['VpcId'])
        ec2c.delete_internet_gateway(InternetGatewayId=id)
    elif id.startswith('vpc-'):
        ec2c.delete_vpc(VpcId=id)
    elif id.startswith('subnet-'):
        ec2c.delete_subnet(SubnetId=id)
    elif id.startswith('key-'): #Only needs the name.
        ec2c.delete_key_pair(KeyPairId=id)
    elif id.startswith('sg-'):
        ec2c.delete_security_group(GroupId=id)
    elif id.startswith('rtb-'):
        ec2c.delete_route_table(RouteTableId=id)
    elif id.startswith('i-'):
        ec2c.terminate_instances(InstanceIds=[id])
    elif id.startswith('addr-'):
        ec2c.disassociate_address(id) # TODO: fix.
        ec2c.release_address(id)
    else:
        raise Exception('TODO: handle this case:', id)

# TODO: have a generalize "assocate" function.
def assoc_gateway(vpc, gate_id):
    vpc.attach_internet_gateway(InternetGatewayId=gate_id)
def assoc_subnet(vpc, subnet_id):
    vpc.associate_with_subnet(SubnetId=subnet_id)
