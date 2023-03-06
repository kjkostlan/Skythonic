import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def get_resources():
    # The most common resources.
    out = {}
    out['vpcs'] = ec2c.describe_vpcs()
    out['tags'] = ec2c.describe_tags()
    out['webgates'] = ec2c.describe_internet_gateways()
    out['kpairs'] = ec2c.describe_key_pairs()
    out['machines'] = ec2c.describe_instances()
    return out
