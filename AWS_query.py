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
    return out
