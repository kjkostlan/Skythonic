# Misc formatting.
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
iam = boto3.client('iam')

def enumr(txt0):
    # Resource enum.
    txt = txt0.strip().lower().replace('_','')
    if txt[-1] == 's':
        txt = txt[0:-1]
    if txt in ['vpc'] or id.startswith('vpc-'):
        return 'vpc'
    if txt in ['webgate', 'internetgateway', 'gateway', 'gate', 'networkgate'] or txt.startswith('igw-'):
        return 'webgate'
    if txt in ['rtable', 'routetable'] or id.startswith('rtb-'):
        return 'rtable'
    if txt in ['subnet'] or id.startswith('subnet-'):
        return 'subnet'
    if txt in ['securitygroup', 'sgroup'] or id.startswith('sg-'):
        return 'sgroup'
    if txt in ['keypair', 'kpair', 'key', 'secret'] or id.startswith('key-'):
        return 'kpair'
    if txt in ['instance', 'machine'] or id.startswith('i-'):
        return 'machine'
    if txt in ['address', 'addres', 'addresses', 'addresse'] or id.startswith('eipalloc-'):
        return 'address'
    if txt in ['vpcpeer', 'vpcpeering', 'peer', 'peering'] or id.startswith('pcx-'):
        return 'peering'
    if txt in ['user'] or id.startswith('AID'):
        return 'user'
    if txt in ['route', 'path', 'pathway']: # Not a top-level resource.
        return 'route'
    if txt in ['policy','policies','policie'] or id.startswith('ANP'):
        return 'policy'
    raise Exception(f'{txt0} is not an understood AWS resource type.')

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
        print('This is the object:', obj_desc)
        raise Exception("Can't extract the Id.")
    return id

def id2obj(id, assert_exist=True):
    if type(id) is dict:
        return id # Already a description.
    try:
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
        elif id.startswith('pcx-'):
            return ec2c.describe_vpc_peering_connections(VpcPeeringConnectionIds=[id])['VpcPeeringConnections'][0]
        elif id.startswith('AID'): # Have to filter manually (I think)
            x = iam.list_users()['Users']
            for xi in x:
                if xi['UserId']==id:
                    return xi
        else:
            raise Exception('TODO: handle this case:', id)
    except Exception as e:
        if not assert_exist and 'does not exist' in repr(e):
            return None
        else:
            raise e

def tag_dict(desc_or_id):
    # The clumsy Key Value pairs => a Python dict.
    desc = id2obj(desc_or_id)
    if 'UserName' in desc and 'UserId' in desc:
        tags = iam.list_user_tags(UserName=desc['UserName'])['Tags']
    else:
        tags = desc.get('Tags',[])
    out = {}
    for tag in tags:
        out[tag['Key']] = tag['Value']
    return out
