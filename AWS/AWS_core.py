# Lower level AWS functions. Simplifies some aspects of the API, but not designed to cover every last case.
import time
import boto3
import AWS.AWS_format as AWS_format
import AWS.AWS_query as AWS_query
import waterworks.plumber as plumber
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
iam = boto3.client('iam')
try:
    logs # A simple way to report output without needing to print it.
except:
    logs = []
    delete_user_input_check = [True] # Safety.

def add_tags(desc_or_id, d, ignore_none_desc=False):
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
            add_tags(AWS_format.id2obj(desc_or_id), d, ignore_none_desc)
        else:
            ec2c.create_tags(Tags=tags,Resources=[desc_or_id])
    else: # Actual objects, which are rarely worked with.
        if 'ec2.KeyPair' in str(type(desc_or_id)): # Random variations in the API...
            add_tags(desc_or_id.key_pair_id, d, ignore_none_desc)
        else:
            if desc_or_id is None and ignore_none_desc:
                return # Race conditions when deleting things (probably).
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
        _error_state = {}
        def _catch_err_f(e):
            if 'Address' in str(e) and 'is in use' in str(e): # Attempt to resolve this error.
                # Can this happen just after machine deletion?
                inter_we_specify = kwargs['NetworkInterfaces'][0]
                subnet_id = inter_we_specify['SubnetId']
                address_we_want = inter_we_specify['PrivateIpAddress']
                subnet_interfaces = ec2c.describe_network_interfaces(Filters=[{'Name': 'subnet-id','Values': [subnet_id]}])['NetworkInterfaces']
                for subn_i in subnet_interfaces:
                    if subn_i['PrivateIpAddress'] == address_we_want:
                        if 'Attachment' in subn_i:
                            iid = subn_i['Attachment']['InstanceId']
                            import AWS.AWS_clean as AWS_clean # TODO: annoying circular dependency.
                            if AWS_clean.has_been_deleted(iid):
                                _error_state['zombie_vm_id'] = iid
                                _error_state['t1'] = time.time()
                                return True
                        elif 'instance' not in str(subn_i):
                            if 'zombie_vm_id' in _error_state: # It can appear cleaned up but still need a delay.
                                if time.time()-_error_state['t1']<64:
                                    return True
                                else:
                                    print('A zombie instance was bieng deleted, but even after its attachment half-cleread and a further 64 seconds it is still not letting us on.')

            return False
        x = plumber.loop_try(lambda: ec2r.create_instances(**kwargs)[0], _catch_err_f, 'Creating a machine with a PrivateIP of a recently deleted machine.', delay=4)
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
    plumber.loop_try(f, f_catch, msg, delay=4)
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
    the_id = AWS_format.obj2id(desc_or_id)
    if the_id is None:
        raise Exception('None ID')

    if delete_user_input_check[0]:
        x = input('\033[95mType "delete" to confirm this AND ALL FUTURE deletions for this Python session:\033[0m').lower().strip()
        if x=='delete':
            delete_user_input_check[0] = False
        else:
            raise Exception('Once-per-session deletion confirmation denied by user.')

    if the_id.startswith('igw-'):
        attchs = ec2c.describe_internet_gateways(InternetGatewayIds=[the_id])['InternetGateways'][0]['Attachments']
        for attch in attchs: # Not sure if this is needed.
            ec2c.detach_internet_gateway(InternetGatewayId=the_id, VpcId=attch['VpcId'])
        ec2c.delete_internet_gateway(InternetGatewayId=the_id)
    elif the_id.startswith('vpc-'):
        ec2c.delete_vpc(VpcId=the_id)
    elif the_id.startswith('subnet-'):
        ec2c.delete_subnet(SubnetId=the_id)
    elif the_id.startswith('key-'): #Only needs the name.
        ec2c.delete_key_pair(KeyPairId=the_id)
    elif the_id.startswith('sg-'):
        ec2c.delete_security_group(GroupId=the_id)
    elif the_id.startswith('rtb-'):
        ec2c.delete_route_table(RouteTableId=the_id)
    elif the_id.startswith('i-'):
        stop_first = True
        if stop_first:
            try:
                ec2c.stop_instances(InstanceIds=[the_id], Force=True)
            except Exception as e:
                if 'IncorrectInstanceState' not in str(e): # Common source of noise.
                    print('Warning: error on force-stop instance, will still proceed to terminate:',str(e))
        ec2c.terminate_instances(InstanceIds=[the_id])
    elif the_id.startswith('eipalloc-'): # These are addresses
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
    elif the_id.startswith('pcx-'):
        ec2c.delete_vpc_peering_connection(VpcPeeringConnectionId=the_id)
    elif the_id.startswith('AID'):
        uname = AWS_format.id2obj(desc_or_id)['UserName']
        policies = iam.list_attached_user_policies(UserName=uname)['AttachedPolicies']
        for p in policies:
            iam.detach_user_policy(UserName=uname, PolicyArn=p['PolicyArn'])
        kys = iam.list_access_keys(UserName=uname)['AccessKeyMetadata']
        for k in kys:
            iam.delete_access_key(UserName=uname, AccessKeyId=k['AccessKeyId'])
        iam.delete_user(UserName=uname)
    else:
        raise Exception('TODO: handle this case:', the_id)

    try: # Some resources linger. Mark them with __deleted__.
        add_tags(the_id, {'__deleted__':True}, ignore_none_desc=True)
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

def modify_attribute(desc_or_id, k, v):
    # TODO: fill out this function more.
    the_id = AWS_format.obj2id(desc_or_id)
    ty = AWS_format.enumr(the_id)
    if ty == 'vpc':
        ec2c.modify_vpc_attribute(VpcId=the_id, **{k:v})
    else:
        TODO # More cases please!

def create_route(rtable_id, dest_cidr, gateway_id):
    # TODO: This is a niche function, which should be refactors/abstracted.
    ec2c.create_route(RouteTableId=rtable_id, DestinationCidrBlock=dest_cidr,GatewayId=gateway_id)

def install_these():
    # What to install on a jumpbox?
    return ['apt aws']
