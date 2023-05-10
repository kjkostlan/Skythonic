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
    if txt in ['vpc'] or txt.startswith('vpc-'):
        return 'vpc'
    if txt in ['webgate', 'internetgateway', 'gateway', 'gate', 'networkgate'] or txt.startswith('igw-'):
        return 'webgate'
    if txt in ['rtable', 'routetable'] or txt.startswith('rtb-'):
        return 'rtable'
    if txt in ['subnet'] or txt.startswith('subnet-'):
        return 'subnet'
    if txt in ['securitygroup', 'sgroup'] or txt.startswith('sg-'):
        return 'sgroup'
    if txt in ['keypair', 'kpair', 'key', 'secret'] or txt.startswith('key-'):
        return 'kpair'
    if txt in ['instance', 'machine'] or txt.startswith('i-'):
        return 'machine'
    if txt in ['address', 'addres', 'addresses', 'addresse'] or txt.startswith('eipalloc-'):
        return 'address'
    if txt in ['vpcpeer', 'vpcpeering', 'peer', 'peering'] or txt.startswith('pcx-'):
        return 'peering'
    if txt in ['user'] or txt.startswith('AID'):
        return 'user'
    if txt in ['route', 'path', 'pathway']: # Not a top-level resource.
        return 'route'
    if txt in ['policy','policies','policie'] or txt.startswith('ANP'):
        return 'policy'
    raise Exception(f'{txt0} is not an understood AWS resource type.')

def obj2id(obj_desc): # Gets the ID from a description.
    if type(obj_desc) is str:
        return obj_desc
    the_id = None
    avoid = {'DhcpOptionsId','OwnerId','AvailabilityZoneId', 'ImageId'} #Tricky since some objects have multible ids
    priority = ['InstanceId', 'RouteTableId', 'SubnetId'] # Order matters here for objects with multible id's.
    for kp in priority:
        if kp in obj_desc:
            return obj_desc[kp]
    kys = obj_desc.keys()
    for ky in kys:
        if ky not in avoid and ky.endswith('Id'):
            the_id = obj_desc[ky]
            break
    if the_id is None:
        print('This is the confusing object:', obj_desc)
        raise Exception("Can't extract the ID.")
    return the_id

def id2obj(the_id, assert_exist=True):
    if type(the_id) is dict:
        return the_id # Already a description.
    try:
        if the_id.startswith('igw-'):
            return ec2c.describe_internet_gateways(InternetGatewayIds=[the_id])['InternetGateways'][0]
        elif the_id.startswith('vpc-'):
            return ec2c.describe_vpcs(VpcIds=[the_id])['Vpcs'][0]
        elif the_id.startswith('subnet-'):
            return ec2c.describe_subnets(SubnetIds=[the_id])['Subnets'][0]
        elif the_id.startswith('key-'): #Only needs the name.
            return ec2c.describe_key_pairs(KeyPairIds=[the_id])['KeyPairs'][0]
        elif the_id.startswith('sg-'):
            return ec2c.describe_security_groups(GroupIds=[the_id])['SecurityGroups'][0]
        elif the_id.startswith('rtb-'):
            return ec2c.describe_route_tables(RouteTableIds=[the_id])['RouteTables'][0]
        elif the_id.startswith('i-'):
            return ec2c.describe_instances(InstanceIds=[the_id])['Reservations'][0]['Instances'][0]
        elif the_id.startswith('eipalloc-'):
            return ec2c.describe_addresses(AllocationIds=[the_id])['Addresses'][0]
        elif the_id.startswith('pcx-'):
            return ec2c.describe_vpc_peering_connections(VpcPeeringConnectionIds=[the_id])['VpcPeeringConnections'][0]
        elif the_id.startswith('AID'): # Have to filter manually (I think)
            x = iam.list_users()['Users']
            for xi in x:
                if xi['UserId']==the_id:
                    return xi
        else:
            raise Exception('TODO: handle this case:', the_id)
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
