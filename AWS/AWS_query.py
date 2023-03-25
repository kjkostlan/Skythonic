import boto3
import AWS.AWS_format as AWS_format

ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
iam = boto3.client('iam')

def get_resources(ids=False, which_keys=None):
    # The most common resources. Filter by which to shave off a few 100 ms from this query.
    out = {}

    if which_keys is not None and type(which_keys) is not str:
        which_keys = set([wc.lower() for wc in which_keys])

    def _hit(kys):
        if type(which_keys) is str:
            return which_keys.lower() in kys
        return which_keys is None or len(which_keys.intersection, kys)>0

    if _hit({'vpc'}): # Python only intruduced the switch statement in 3.10
        out['vpcs'] = ec2c.describe_vpcs()['Vpcs']
    if _hit({'webgate','internetgateway'}):
        out['webgates'] = ec2c.describe_internet_gateways()['InternetGateways']
    if _hit({'rtable','routetable'}):
        out['rtables'] = ec2c.describe_route_tables()['RouteTables']
    if _hit({'subnet'}):
        out['subnets'] = ec2c.describe_subnets()['Subnets']
    #if _hit({'route'}): # Routes are part of route tables, not so much standalones.
    #    x = ec2r.create_route(**kwargs)
    if _hit({'securitygroup', 'sgroup'}):
        out['sgroups'] = ec2c.describe_security_groups()['SecurityGroups']
    if _hit({'keypair'}):
        out['kpairs'] = ec2c.describe_key_pairs()['KeyPairs']
    if _hit({'instance', 'instances', 'machine', 'machines'}):
        machines = []
        for pack in ec2c.describe_instances()['Reservations']:
            machines = machines+pack['Instances']
        out['machines'] = machines
    if _hit({'address'}):
        out['addresses'] = ec2c.describe_addresses()['Addresses']
    if _hit({'vpcpeer','vpcpeering'}):
        out['peerings'] = ec2c.describe_vpc_peering_connections()['VpcPeeringConnections']
    if _hit({'user','users'}):
        out['users'] = iam.list_users()['Users']
    #out['tags'] = ec2c.describe_tags()['Tags'] # Contains other stuff we can query that instead (I think).

    if ids:
        for k, v in out.items():
            out[k] = AWS_format.obj2id(k)

    if type(which_keys) is str: # SPlice for a str, which is different than a one element set.
        out = out[list(out.keys())[0]]

    return out

def get_by_name(rtype, name):
    # None if the resource doesn't exist.
    resc = get_resources(False, rtype)
    for r in resc:
        if AWS_format.tag_dict(r).get('Name',None) == name:
            if rtype in {'instance', 'instances', 'machine', 'machines'} and 'terminated' in str(r['State']):
                continue # Don't include those terminated machines that hang around.
            return r
    return None

def _default_custom():
    dresc = {}; cresc = {}; resc = get_resources()
    for k in resc.keys():
        dresc[k] = []; cresc[k] = []
        for x in resc[k]:
            if k == 'rtables' and 'Associations' in x and len(x['Associations'])>0 and x['Associations'][0]['Main']:
                dresc[k].append(x)
            elif k == 'vpcs' and x['IsDefault']:
                dresc[k].append(x)
            elif k == 'sgroups' and x['GroupName']=='default':
                dresc[k].append(x) # Every VPC makes a default security group.
            else:
                cresc[k].append(x)
    return dresc, cresc

def default_resources():
    # Resources which are part of the default loadout and really shouldn't be modified too much or deleted.
    # Some of these are created automatically upon creating custom resources and also get deleted automatically.
    return _default_custom()[0]

def custom_resources():
    # The opposite of default_resources()
    return _default_custom()[1]

def what_needs_these(custom_only=False, include_empty=False): # What Ids depend on us for each Id. Depend on means can't delete.
    # (It is messy to use the deps map).
    x = custom_resources() if custom_only else get_resources()
    out = {}
    def _add(a, b):
        if a not in out:
            out[a] = []
        out[a].append(b)

    for k in x.keys():
        for desc in x[k]:
            id = AWS_format.obj2id(desc)
            if include_empty and id not in out:
                out[id] = []
            if k=='sgroups' and 'VpcId' in desc:
                _add(desc['VpcId'], id)
            if k=='webgates' and 'Attachments' in desc:
                for atth in desc['Attachments']:
                    _add(atth['VpcId'], id) # one way or two way need?
            if k=='machines': # A big one!
                if 'SecurityGroups' in desc:
                    for sg in desc['SecurityGroups']:
                        _add(sg['GroupId'], id)
                #if 'NetworkInterfaces' in desc: #It makes one of these automatically, not sure the delete rules on this.
                #    for nt in desc['NetworkInterfaces']:
                #        _add(nt['NetworkInterfaceId'], id)
                if 'SubnetId' in desc:
                    _add(desc['SubnetId'], id)
                if 'VpcId' in desc:
                    _add(desc['VpcId'], id)
            if k=='rtables' and 'Associations' in desc:
                for asc in desc['Associations']:
                    if 'SubnetId' in asc:
                        #_add(asc['SubnetId'], id)
                        _add(id, asc['SubnetId'])
    return out
