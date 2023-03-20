import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
import AWS.AWS_core as AWS_core

def get_resources(ids=False):
    # The most common resources.
    out = {}
    out['vpcs'] = ec2c.describe_vpcs()['Vpcs']
    #out['tags'] = ec2c.describe_tags()['Tags'] # Contains other stuff we can query that instead.
    out['sgroups'] = ec2c.describe_security_groups()['SecurityGroups']
    out['subnets'] = ec2c.describe_subnets()['Subnets']
    out['webgates'] = ec2c.describe_internet_gateways()['InternetGateways']
    out['kpairs'] = ec2c.describe_key_pairs()['KeyPairs']
    out['machines'] = ec2c.describe_instances()['Reservations']
    out['rtables'] = ec2c.describe_route_tables()['RouteTables']
    out['addresses'] = ec2c.describe_addresses()['Addresses']
    machines = []
    for pack in ec2c.describe_instances()['Reservations']:
        machines = machines+pack['Instances']
    out['machines'] = machines
    if ids:
        for k, v in out.items():
            out[k] = AWS_core.obj2id(k)
    return out

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
            id = AWS_core.obj2id(desc)
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
