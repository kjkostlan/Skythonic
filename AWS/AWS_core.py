# Core AWS functions.
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

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
        return ec2c.describe_instances(InstanceIds=[id])['Reservations'][0]['Instances'][0]
    elif id.startswith('eipalloc-'):
        return ec2c.describe_addresses(AllocationIds=[id])['Addresses'][0]
    else:
        raise Exception('TODO: handle this case:', id)

def assign_name(x, name): #Most everything can be named.
    if type(name) is not str:
        raise Exception('Name must be a string.')
    if type(x) is dict:
        id = obj2id(x)
        ec2c.create_tags(Tags=[{'Key': 'Name', 'Value': name}],Resources=[id])
    else:
        x.create_tags(Tags=[{'Key': 'Name', 'Value': name}])

def create(rtype, name, **kwargs):
    # Returns the ID, which is commonly introduced into other objects.
    rtype = rtype.lower()
    if rtype in {'vpc'}: # Python only intruduced the switch statement in 3.10
        x = ec2r.create_vpc(**kwargs)
        x.wait_until_available()
    elif rtype in {'webgate','internetgateway'}:
        x = ec2r.create_internet_gateway(**kwargs)
    elif rtype in {'rtable','routetable'}:
        x = ec2r.create_route_table(**kwargs)
    elif rtype in {'subnet'}:
        x = ec2r.create_subnet(**kwargs)
    elif rtype in {'route'}:
        x = ec2r.create_route(**kwargs)
    elif rtype in {'securitygroup', 'sgroup'}:
        x = ec2r.create_security_group(**kwargs)
    elif rtype in {'keypair'}:
        x = ec2r.create_key_pair(**kwargs)
    elif rtype in {'instance', 'instances', 'machine', 'machines'}:
        x = ec2r.create_instances(**kwargs)[0]
    elif rtype in {'address'}:
        x = ec2c.allocate_address(**kwargs)
    else:
        raise Exception('Create ob type unrecognized: '+rtype)
    #if type not in {'address'}:
    assign_name(x, name)
    #elif name is not None and name != '':
    #    print('Warning: Cannot tag a name to: '+type)
    if kwargs.get('raw_object', False): # Generally discouraged to work with.
        return x
    elif type(x) is dict:
        return obj2id(x)
    else:
        return x.id

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
    elif id.startswith('eipalloc-'): # These are addresses
        desc = id2obj(desc_or_id)
        ec2c.release_address(AllocationId=desc['AllocationId'])
        #if 'PublicIp' in desc:
        #    ec2c.disassociate_address(PublicIp=desc['PublicIp'])
        #    ec2c.release_address(PublicIp=desc['PublicIp'])
        #elif 'AssociationId' in desc:
        #    ec2c.disassociate_address(AssociationId=desc['AssociationId'])
        #    ec2c.release_address(AssociationId=desc['AssociationId'])
        #else:
        #    raise Exception('Cannot hook onto: '+str(desc))
    else:
        raise Exception('TODO: handle this case:', id)

# TODO: have a generalize "assocate" function.
def assoc_gateway(vpc, gate_id):
    vpc.attach_internet_gateway(InternetGatewayId=gate_id)
def assoc_subnet(vpc, subnet_id):
    vpc.associate_with_subnet(SubnetId=subnet_id)
