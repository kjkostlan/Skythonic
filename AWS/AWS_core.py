# Lower level AWS functions. Simplifies some aspects of the API, but not designed to cover every last case.
import time, requests
import boto3
import AWS.AWS_format as AWS_format
import AWS.AWS_query as AWS_query
import eye_term
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
iam = boto3.client('iam')
try:
    logs # A simple way to report output without needing to print it.
except:
    logs = []

def add_tags(desc_or_id, d):
    #botocore.exceptions.ClientError: An error occurred (InvalidInstanceID.NotFound) when calling the CreateTags operation: The instance ID 'i-0fb7af9af917db726' does not exist
    tags = [{'Key':str(k),'Value':str(d[k])} for k in d.keys()]
    if type(desc_or_id) is dict:
        if 'UserId' in desc_or_id: # Users arr handleded differently.
            iam.tag_user(UserName=desc_or_id['UserName'],Tags=tags)
        else:
            id = AWS_format.obj2id(desc_or_id)
            ec2c.create_tags(Tags=tags,Resources=[id])
    elif type(desc_or_id) is str:
        if desc_or_id.startswith('AID'): # Users arr handleded differently.
            add_tags(AWS_format.id2obj(desc_or_id), d)
        else:
            ec2c.create_tags(Tags=tags,Resources=[desc_or_id])
    else: # Actual objects, which are rarely worked with.
        if 'ec2.KeyPair' in str(type(desc_or_id)): # Random variations in the API...
            add_tags(desc_or_id.key_pair_id, d)
        else:
            desc_or_id.create_tags(Tags=tags)

def create(rtype0, name, **kwargs):
    # Returns the ID, which is commonly introduced into other objects.
    raw = False # needed for keypairs.
    if kwargs.get('raw_object', False): # Generally discouraged to work with.
        raw = True
    if 'raw_object' in kwargs:
        del kwargs['raw_object']
    rtype = AWS_format.enumr(rtype0)
    if rtype == 'vpc': # Python introduced "switch" in 3.10 but AWS shell is 3.7
        x = ec2r.create_vpc(**kwargs)
        x.wait_until_available()
    elif rtype == 'webgate':
        x = ec2r.create_internet_gateway(**kwargs)
    elif rtype == 'rtable':
        x = ec2r.create_route_table(**kwargs)
    elif rtype == 'subnet':
        x = ec2r.create_subnet(**kwargs)
    elif rtype == 'route':
        x = ec2r.create_route(**kwargs)
    elif rtype =='sgroup':
        x = ec2r.create_security_group(**kwargs)
    elif rtype == 'kpair':
        kwargs['KeyName'] = name # one of those irregularities in their API.
        x = ec2r.create_key_pair(**kwargs)
    elif rtype =='machine':
        x = ec2r.create_instances(**kwargs)[0]
    elif rtype == 'address':
        x = ec2c.allocate_address(**kwargs)
    elif rtype == 'user':
        kwargs['UserName'] = name
        x = iam.create_user(**kwargs)['User']
    elif rtype == 'peering':
        x = ec2c.create_vpc_peering_connection(**kwargs)['VpcPeeringConnection']
        ec2c.accept_vpc_peering_connection(VpcPeeringConnectionId=x['VpcPeeringConnectionId'])
    else:
        raise Exception('Create ob type unrecognized: '+rtype0)

    f = lambda: add_tags(x, {'Name':name, '__Skythonic__':True})
    f_catch = lambda e: 'does not exist' in repr(e).lower()
    msg = 'created a resource of type '+rtype+' waiting for it to start existing.'
    eye_term.loop_try(f, f_catch, msg, delay=4)
    if raw: # Generally discouraged to work with, except for keypairs.
        return x
    elif type(x) is dict:
        return AWS_format.obj2id(x)
    else:
        return x.id

def create_once(rtype, name, printouts, **kwargs):
    # Creates a resource unless the name is already there.
    # Returns the created or already-there resource.
    r0 = AWS_query.get_by_name(rtype, name)
    do_print = printouts is not None and printouts is not False
    if printouts is True:
        printouts = ''
    elif type(printouts) is str:
        printouts = printouts+' '
    if r0 is not None:
        if do_print:
            print(str(printouts)+'already exists:', rtype, name)
        if AWS_format.enumr(rtype) == 'machine':
            ec2c.start_instances(InstanceIds=[AWS_format.obj2id(r0)])
        return AWS_format.obj2id(r0)
    else:
        out = create(rtype, name, **kwargs)
        if do_print:
            print(str(printouts)+'creating:', rtype, name)
        return out

def delete(desc_or_id):
    # Deletes an object (returns True if sucessful, False if object wasn't existing).
    id = AWS_format.obj2id(desc_or_id)

    if id.startswith('igw-'):
        attchs = ec2c.describe_internet_gateways(InternetGatewayIds=[id])['InternetGateways'][0]['Attachments']
        for attch in attchs: # Not sure if this is needed.
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
        stop_first = True
        if stop_first:
            try:
                ec2c.stop_instances(InstanceIds=[id], Force=True)
            except Exception as e:
                if 'IncorrectInstanceState' not in str(e): # Common source of noise.
                    print('Warning: error on force-stop instance, will still proceed to terminate:',str(e))
        ec2c.terminate_instances(InstanceIds=[id])
    elif id.startswith('eipalloc-'): # These are addresses
        desc = AWS_format.id2obj(desc_or_id)
        f = ec2c.disassociate_address; kwargs = {}
        for k in ['AssociationId', 'PublicIp']:
            if k in desc:
                kwargs[k] = desc[k]
        if len(kwargs)==2: # Bug that one can't specify both.
            del kwargs['PublicIp']
        try:
            ec2c.disassociate_address(**kwargs)
        except Exception as e:
            print('Warning: cannot dissoc address, will still proceed with deletion anyway; err=', str(e))
        ec2c.release_address(AllocationId=desc['AllocationId'])
    elif id.startswith('pcx-'):
        ec2c.delete_vpc_peering_connection(VpcPeeringConnectionId=id)
    elif id.startswith('AID'):
        uname = AWS_format.id2obj(desc_or_id)['UserName']
        policies = iam.list_attached_user_policies(UserName=uname)['AttachedPolicies']
        for p in policies:
            iam.detach_user_policy(UserName=uname, PolicyArn=p['PolicyArn'])
        kys = iam.list_access_keys(UserName=uname)['AccessKeyMetadata']
        for k in kys:
            iam.delete_access_key(UserName=uname, AccessKeyId=k['AccessKeyId'])
        iam.delete_user(UserName=uname)
    else:
        raise Exception('TODO: handle this case:', id)

    try: # Some resources linger. Mark them with __deleted__.
        add_tags(id, {'__deleted__':True})
    except Exception as e:
        if 'does not exist' in repr(e):
            return False
        else:
            raise e

    return True

def assoc(A, B, _swapped=False):
    # Association, attachment, etc. Order does not matter unless both directions have meaning.
    # Idempotent (like Clojures assoc).
    A = AWS_format.obj2id(A); B = AWS_format.obj2id(B)
    if A.startswith('vpc-') and B.startswith('igw-'):
        try:
            ec2c.attach_internet_gateway(VpcId=A, InternetGatewayId=B)
        except Exception as e: # TODO: don't duplicate this code. Instead bundle it into a fn if more "already associated" errors exist.
            if 'is already attached' in repr(e) and A in repr(e) and B in repr(e):
                return
            elif 'is already attached' in repr(e):
                raise Exception(' '.join(['Tried to assoc:', A, 'to', B, 'But there is already a different association:', str(list(filter(lambda x:'igw-' in x or 'vpc-' in x, repr(e).split(' '))))]))
            else:
                raise e
    elif A.startswith('subnet-') and B.startswith('rtb-'):
        ec2c.associate_route_table(SubnetId=A, RouteTableId=B)
    elif A.startswith('eipalloc-') and B.startswith('i-'):
        ec2c.associate_address(AllocationId=A,InstanceId=B)
    elif A.startswith('vpc-') and B.startswith('vpc-'): # Peering can be thought of as an association.
        peering = ec2c.create_vpc_peering_connection(VpcId=A, PeerVpcId=B)
        ec2c.accept_vpc_peering_connection(VpcPeeringConnectionId=peering['VpcPeeringConnection']['VpcPeeringConnectionId'])
    elif _swapped:
        raise Exception(f"Don't know how to attach {A} to {B}; this may require updating this function.")
    else:
        assoc(B, A, True)
# def assoc_subnet(vpc, subnet_id): # TODO: how to do this with id?
#    vpc.associate_with_subnet(SubnetId=subnet_id)

def disassoc(A, B, _swapped=False):
    # Opposite of assoc and Idempotent.
    TODO
dissoc = disassoc # For those familiar with Clojure...

def our_vm_id():
    # The instance_id of our machine.
    # Returns None if in the cloud shell.
    #https://www.educba.com/python-curl/
    #https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html#instance-metadata-ex-2
    x = requests.get('http://169.254.169.254/latest/meta-data/ami-id').content.decode()
    if 'Resource not found' in x:
        return None
    if not x.startswith('i-'):
        raise Exception('Error in our_vm_id() fn.')
    return x
