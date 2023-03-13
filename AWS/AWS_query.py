import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def get_resources():
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
