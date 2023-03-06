import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
vpc_dict = ec2c.describe_vpcs()
tag_dict = ec2c.describe_tags()
gate_dict = ec2c.describe_internet_gateways()

# Don't delete default VPC!
