# Core AWS functions.
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def assign_name(x):
    x.create_tags(Tags=[{'Key': 'Name', 'Value': name}])

def create_ob(type, name, **kwargs):
    type = type.lower9)
    if type in {'vpc'}: # Python only intruduced the switch statement in 3.10
        x = ec2r.create_vpc(**kwargs)
        x.wait_until_available()
    elif type in {'webgate','internetgateway'}:
        x = ec2r.create_internet_gateway(kwargs)
    elif type in {'rtable','routetable'}:
        x = ec2r.create_route_table()
    elif type in {'subnet'}:
        x = ec2r.create_subnet(**kwargs)
    elif type in {'route'}:
        x = ec2r.create_route(**kwargs)
    elif type in {'securitygroup'}:
        x = ec2r.create_security_group(**kwargs)
    elif type in {'keypair'}:
        x = ec2r.create_key_pair(**kwargs)
    elif type in {'instance', 'instances', 'machine', 'machines'}:
        x = ec2r.create_instances(**kwargs)
    else:
        raise Exception('Create ob type unrecognized:'+str(type))
    assign_name(x)
    return x



# TODO: have a generalize "assocate ob" function.
def assoc_gateway(vpc, gate_id):
    vpc.attach_internet_gateway(InternetGatewayId=gate_id)
def assoc_subnet(vpc, subnet_id):
    vpc.associate_with_subnet(SubnetId=subnet_id)
