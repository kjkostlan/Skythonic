import boto3
import AWS.AWS_format as AWS_format
import plumbing

ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
iam = boto3.client('iam')

def lingers(desc_or_id):
    #desc = AWS_format.id2obj(desc_or_id)
    #instance 'terminated' in str(m.get('State',None)) # Alternative way for machines.
    #peering ['Status']['Code']=='deleted'. #Alternate for deleted.
    if desc_or_id is None:
        return False
    return AWS_format.tag_dict(desc_or_id).get('__deleted__',False)

def filtered_machines(filters): # For some reason describe_instances doesn't return a list of instances.
    x = ec2c.describe_instances() if filters is None else ec2c.describe_instances(Filters=filters)
    machines = []
    for pack in x['Reservations']:
        machines.extend(pack['Instances'])
    return machines

def get_resources(which_types=None, ids=False, include_lingers=False):
    # The most common resources. Filter by which to shave off a few 100 ms from this query.
    # Will not find routes directly, but does find rtables.
    # Will not find tags directly; use get_by_tag.
    out = {}
    splice = type(which_types) is str
    if splice:
        which_types = [which_types]
    if which_types is not None:
        which_types = set([AWS_format.enumr(ty) for ty in which_types])

    if which_types is None or 'vpc' in which_types: # Python only introduced the switch statement in 3.10
        out['vpcs'] = ec2c.describe_vpcs()['Vpcs']
    if which_types is None or 'webgate' in which_types:
        out['webgates'] = ec2c.describe_internet_gateways()['InternetGateways']
    if which_types is None or 'rtable' in which_types:
        out['rtables'] = ec2c.describe_route_tables()['RouteTables']
    if which_types is None or 'subnet' in which_types:
        out['subnets'] = ec2c.describe_subnets()['Subnets']
    if which_types is None or 'sgroup' in which_types:
        out['sgroups'] = ec2c.describe_security_groups()['SecurityGroups']
    if which_types is None or 'kpair' in which_types:
        out['kpairs'] = ec2c.describe_key_pairs()['KeyPairs']
    if which_types is None or 'machine' in which_types:
        out['machines'] = filtered_machines(None)
    if which_types is None or 'address' in which_types:
        out['addresses'] = ec2c.describe_addresses()['Addresses']
    if which_types is None or 'peering' in which_types:
        out['peerings'] = ec2c.describe_vpc_peering_connections()['VpcPeeringConnections']
    if which_types is None or 'user' in which_types:
        out['users'] = iam.list_users()['Users']
    if which_types is None or 'IAMpolicy' in which_types: # Only includes resources with a 'PolicyId'
        out['IAMpolicies'] = list(iam.list_policies()['Policies'])
    if ids:
        for k, v in out.items():
            out[k] = AWS_format.obj2id(k)

    if not include_lingers:
        for k in out.keys():
            out[k] = list(filter(lambda x: not lingers(x), out[k]))

    if splice: # Splice for a str, which is different than a one element collection.
        out = out[list(out.keys())[0]]

    return out

def get_by_tag(rtype, k, v, include_lingers=False): # Returns None if no such resource exists.
    resc = get_resources(rtype, include_lingers)
    for r in resc:
        if AWS_format.tag_dict(r).get(k,None) == v:
            return r

def get_by_name(rtype, name, include_lingers=False): # Convenience fn.
    return get_by_tag(rtype, 'Name', name, include_lingers)

def exists(desc_or_id):
    the_id = AWS_format.obj2id(desc_or_id)
    if type(the_id) is not str:
        raise Exception('Possible bug in obj2id.')
    try:
        desc1 = AWS_format.id2obj(the_id)
        return desc1 is not None and desc1 is not False
    except Exception as e:
        if 'index out of range' in str(e) or 'does not exist' in str(e):
            return False
        raise e

def _default_custom(include_lingers):
    dresc = {}; cresc = {}; resc = get_resources(include_lingers=include_lingers)
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

def default_resources(include_lingers=False):
    # Resources which are part of the default loadout and really shouldn't be modified too much or deleted.
    # Some of these are created automatically upon creating custom resources and also get deleted automatically.
    return _default_custom(include_lingers)[0]

def custom_resources(include_lingers=False):
    # The opposite of default_resources()
    return _default_custom(include_lingers)[1]

def what_needs_these(custom_only=False, include_empty=False, include_lingers=False):
    # Map from resource id to what ids depend on said id.
    # Resources can't be deleted untill all dependencies are deleted.
    x = custom_resources(include_lingers=include_lingers) if custom_only else get_resources(include_lingers=include_lingers)
    out = {}
    def _add(a, b):
        if a not in out:
            out[a] = []
        out[a].append(b)

    for k in x.keys():
        for desc in x[k]:
            the_id = AWS_format.obj2id(desc)
            if include_empty and the_id not in out:
                out[the_id] = []
            if k=='sgroups' and 'VpcId' in desc:
                _add(desc['VpcId'], the_id)
            if k=='webgates' and 'Attachments' in desc:
                for atth in desc['Attachments']:
                    _add(atth['VpcId'], the_id) # one way or two way need?
            if k=='machines': # A big one!
                if 'SecurityGroups' in desc:
                    for sg in desc['SecurityGroups']:
                        _add(sg['GroupId'], the_id)
                #if 'NetworkInterfaces' in desc: #It makes one of these automatically, not sure the delete rules on this.
                #    for nt in desc['NetworkInterfaces']:
                #        _add(nt['NetworkInterfaceId'], the_id)
                if 'SubnetId' in desc:
                    _add(desc['SubnetId'], the_id)
                if 'VpcId' in desc:
                    _add(desc['VpcId'], the_id)
            if k=='rtables' and 'Associations' in desc:
                for asc in desc['Associations']:
                    if 'SubnetId' in asc:
                        #_add(asc['SubnetId'], the_id)
                        _add(id, asc['SubnetId'])
    return out

def assocs(desc_or_id, with_which_type, filter_exists=True):
    #Gets associations of desc_or_id with_which_type. Returns a list.
    ty = AWS_format.enumr(with_which_type)
    the_id = AWS_format.obj2id(desc_or_id)
    desc = AWS_format.id2obj(desc_or_id)

    # Nested switchyard:
    out = None
    if the_id.startswith('igw-'):
        if ty == 'webgate':
            raise Exception('Internet gateways are not associated with thier own kind.')
        if ty in ['user','address','kpair','sgroup','peering','IAMpolicy']:
            raise Exception(f'Internet gateways cannot be directly associated with {ty}s.')
        if ty=='vpc':
            out = [a['VpcId'] for a in desc['Attachments']]
        if ty=='subnet':
            out = []
            for att in desc.get('Attachments', []):
                out.extend(att.get('SubnetIds', []))
        if ty=='rtable':
            out = []
            rtables = get_resources('rtable')
            for rtable in rtables:
                for route in rtable['Routes']:
                    if route.get('GatewayId',None) == the_id:
                        out.append(AWS_format.obj2id(rtable))
                        break
        if ty=='machine':
            vpcs = assocs(the_id, 'vpc')
            out = []
            for vpc_id in vpcs:
                out.extend([AWS_format.obj2id(m) for m in filtered_machines([{'Name': 'vpc-id','Values': [vpc_id]}])])
    elif the_id.startswith('vpc-'):
        if ty == 'vpc':
            out = []
            filter0 = {'Name': 'accepter-vpc-info.vpc-id','Values': [the_id]}
            filter1 = {'Name': 'requester-vpc-info.vpc-id','Values': [the_id]}
            peerings = ec2c.describe_vpc_peering_connections(Filters=[filter0])['VpcPeeringConnections']
            peerings = peerings+ec2c.describe_vpc_peering_connections(Filters=[filter1])['VpcPeeringConnections']
            for peering in peerings:
                id0 = AWS_format.obj2id(peering['requesterVpcInfo'])
                id1 = AWS_format.obj2id(peering['accepterVpcInfo'])
                if id0==the_id:
                    out.append(id1)
                if id1==the_id:
                    out.append(id0)
        if ty in ['user','address','kpair','IAMpolicy']:
            raise Exception(f'VPCs cannot be directly associated with {ty}s.')
        if ty=='sgroup':
            out = [AWS_format.obj2id(s) for s in ec2c.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [the_id]}])['SecurityGroups']]
        if ty=='webgate':
            gates = ec2c.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id','Values': [the_id]}])['InternetGateways']
            out = [AWS_format.obj2id(gate) for gate in gates]
        if ty=='machine':
            out = [AWS_format.obj2id(m) for m in filtered_machines([{'Name': 'vpc-id', 'Values': [the_id]}])]
        if ty=='subnet':
            subnets = ec2c.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [the_id]}])['Subnets']
            out = [AWS_format.obj2id(s) for s in subnets]
        if ty=='peering':
            filter0 = {'Name': 'accepter-vpc-info.vpc-id','Values': [the_id]}
            filter1 = {'Name': 'requester-vpc-info.vpc-id','Values': [the_id]}
            peerings = ec2c.describe_vpc_peering_connections(Filters=[filter0])['VpcPeeringConnections']
            peerings = peerings+ec2c.describe_vpc_peering_connections(Filters=[filter1])['VpcPeeringConnections']
            out = [AWS_format.obj2id(p) for p in peerings]
        if ty=='rtable':
            rtables = ec2c.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [the_id]}])['RouteTables']
            out = [AWS_format.obj2id(rtable) for rtable in rtables]
    elif the_id.startswith('subnet-'):
        if ty == 'subnet':
            raise Exception('Subnets cannot be associated with thier own kind.')
        if ty in ['user','kpair','peering','IAMpolicy']:
            raise Exception(f'subnets cannot be directly associated with {ty}s.')
        if ty=='vpc':
            out = [desc['VpcId']]
        if ty=='rtable':
            rtables = ec2c.describe_route_tables(Filters=[{'Name': 'association.subnet-id','Values': [the_id]}])['RouteTables']
            #rtables+ec2c.describe_route_tables(Filters=[{'Name': 'subnet-id','Values': [the_id]}])['RouteTables']
            out = [AWS_format.obj2id(x) for x in rtables]
        if ty=='webgate':
            out = []
            for rtable_id in assocs(desc_or_id, 'rtable'):
                f0 = {'Name': 'route-table-id','Values': [rtable_id]}
                rtables1 = ec2c.describe_route_tables(Filters=[f0])['RouteTables']
                for rtable1 in rtables1:
                    for route1 in rtable1['Routes']:
                        if 'GatewayId' in rtable1:
                            out.append(rtable1['GatewayId'])
        if ty=='address':
            out = []
            addresses = get_resources('addresses')
            for address in addresses:
                if plumbing.in_cidr(address['PublicIp'], desc['CidrBlock']):
                    out.append(AWS_format.obj2id(address))
        if ty=='sgroup':
            interfaces = ec2c.describe_network_interfaces(Filters=[{'Name': 'subnet-id', 'Values': [the_id]}])['NetworkInterfaces']
            out = []
            for inf in interfaces:
                for grs in inf['Groups']:
                    if type(grs) is list: # Singular vs plural confusion.
                        out.extend([AWS_format.obj2id(gr) for gr in groups])
                    elif 'GroupId' not in grs:
                        raise Exception('No group id in group?')
                    out.append(AWS_format.obj2id(grs))
        if ty=='machine':
            #        if ty=='subnet':
            #            out = [ni['SubnetId'] for ni in desc['NetworkInterfaces']]
            out = [AWS_format.obj2id(inst) for inst in filtered_machines([{'Name': 'subnet-id', 'Values': [the_id]}])]
    elif the_id.startswith('key-'): #Only needs the name.
        if ty == 'kpair':
            raise Exception('Keypairs are not associated with thier own kind.')
        if ty in ['webgate','vpc','subnet','sgroup','rtable','address','peering','user','IAMpolicy']:
            raise Exception(f'Security groups cannot be directly associated with {ty}s.')
        kname = desc['KeyName'] # Names of keypairs are unique.
        if ty=='machine':
            out = []
            insts = get_resources('machines')
            for idesc in insts:
                if idesc.get('KeyName', []) == kname:
                    out.append(AWS_format.obj2id(idesc))
    elif the_id.startswith('sg-'):
        if ty == 'sgroup':
            raise Exception('Security groups are not associated with thier own kind.')
        if ty in ['kpair','webgate','user','rtable','address','peering','IAMpolicy']:
            raise Exception(f'Security groups cannot be directly associated with {ty}s.')
        if ty=='vpc':
            out = [desc['VpcId']]
        if ty=='machine':
            out = []
            insts = get_resources('machines')
            for idesc in insts:
                if the_id in [sg['GroupId'] for sg in idesc['SecurityGroups']]:
                    out.append(AWS_format.obj2id(idesc))
        if ty=='subnet':
            out = []
            ifaces = ec2c.describe_network_interfaces(Filters=[{'Name': 'group-id','Values': [the_id]}])['NetworkInterfaces']
            for iface in ifaces:
                out.append(iface['SubnetId'])
    elif the_id.startswith('rtb-'):
        if ty == 'rtable':
            raise Exception('Route tables are not associated with thier own kind.')
        if ty in ['kpair','sgroup','user','machine','IAMpolicy']:
            raise Exception(f'Route tables cannot be directly associated with {ty}s.')
        pairs = [['peering','VpcPeeringConnectionId'], ['webgate','GatewayId'], ['subnet','SubnetId'], ['vpc', 'VpcId']]
        for p in pairs:
            if ty == p[0]:
                out = []
                for a in desc['Associations']:
                    if p[1] in a:
                        out.append(a[p[1]])
                if p[1] in desc:
                    out.append(desc[p[1]])
                for route in desc['Routes']:
                    if p[1] in route and '-' in route[p[1]]: # Sometimes the "Id" isn't actually an ID.
                        out.append(route[p[1]])
        if ty=='address':
            addresses = get_resources('addresses')
            out = []
            for addr in addresses:
                for route in desc['Routes']:
                    if plumbing.in_cidr(addr['PublicIp'], route['DestinationCidrBlock']):
                        out.append(AWS_format.obj2id(addr))
                        break
    elif the_id.startswith('i-'):
        if ty == 'machine':
            raise Exception('Machines cannot be associated with thier own kind.')
        if ty in ['peering', 'rtable','user', 'IAMpolicy']:
            raise Exception(f'Instances cannot be directly associated with {ty}s.')
        if ty=='vpc':
            out = [desc['VpcId']]
        if ty=='webgate':
            out = assocs(desc['VpcId'], 'webgate')
        if ty=='subnet':
            out = [ni['SubnetId'] for ni in desc['NetworkInterfaces']]
        if ty=='kpair':
            key_name = desc['KeyName']
            kpair = ec2c.describe_key_pairs(KeyNames=[key_name])['KeyPairs'][0]
            out = [AWS_format.obj2id(kpair)]
        if ty=='sgroup':
            out = [AWS_format.obj2id(s) for s in desc['SecurityGroups']]
        if ty=='address':
            out = []
            for addr in get_resources('address'):
                if addr.get('PublicIp', '404') == desc.get('PublicIpAddress', 'four-oh-four') or addr.get('PrivateIp', '404') == desc.get('PrivateIpAddress', 'four-oh-four'):
                    out.append(AWS_format.obj2id(addr))
    elif the_id.startswith('eipalloc-'): # These are addresses
        if ty == 'address':
            raise Exception('Addresses cannot be associated with thier own kind.')
        if ty in ['vpc', 'kpair', 'peering','IAMpolicy', 'sgroup', 'user']:
            raise Exception(f'Addresses cannot be directly associated with {ty}s.')
        if ty=='machine':
            out = [desc['InstanceId']] if 'InstanceId' in desc else []
        if ty=='rtable':
            public_ip = desc['PublicIp']
            cidrs = plumbing.enclosing_cidrs(desc['PublicIp'])
            out = []
            for cidr_or_ip in cidrs: # The filter is dumb and only looks for a string match.
                rtables = ec2c.describe_route_tables(Filters=[{'Name': 'route.destination-cidr-block','Values': [cidr_or_ip]}])['RouteTables']
                out.extend([AWS_format.obj2id(rtable) for rtable in rtables])
        if ty=='webgate':
            raise Exception('Addresses cannot be directly associated with internet gateways.')
        if ty=='subnet':
            subnets = get_resources('subnets')
            out = []
            for subnet in subnets:
                if plumbing.in_cidr(desc['PublicIp'],subnet['CidrBlock']):
                    out.append(AWS_format.obj2id(subnet))
    elif the_id.startswith('pcx-'):
        if ty == 'peering':
            raise Exception('Peering connections cannot be associated with thier own kind.')
        if ty in ['machine','webgate','subnet','kpair','sgroup','address','IAMpolicy']:
            raise Exception(f'Peerings cannot be directly associated with {ty}s.')
        if ty=='vpc':
            out = [desc['RequesterVpcInfo']['VpcId'], desc['AccepterVpcInfo']['VpcId']]
        if ty=='rtables':
            rtables = get_resources('rtables')
            out = []
            for rtable in rtables:
                for route in rtable['Routes']:
                    if route.get('VpcPeeringConnectionId', None) == the_id:
                        out.append(AWS_format.obj2id(rtable))
    elif the_id.startswith('AID'):
        if ty in ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address', 'peering']:
            raise Exception(f'Users cannot be directly associated with {ty}s.')
        if ty == 'user':
            raise Exception('Users cannot be associated with thier own kind (except in real life).')
        if ty=='IAMpolicy':
            policies = iam.list_attached_user_policies(UserName=desc['UserName'])['AttachedPolicies']
            out = []
            for policy in policies:
                try:
                    out.append(AWS_format.obj2id(policy))
                except:
                    pass
    elif the_id.startswith('arn:'):
        if ty in ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address', 'peering']:
            raise Exception(f'IAMpolicies cannot be directly associated with {ty}s.')
        if ty == 'IAMpolicy':
            raise Exception('IAMpolicies cannot be associated with thier own kind.')
        if ty == 'user':
            users = iam.list_entities_for_policy(PolicyArn=desc['Arn'],EntityFilter='User')['PolicyUsers']
            out = [AWS_format.obj2id(user) for user in users]
    else:
        if the_id.startswith('ANP'):
            raise Exception('IAMpolicies must be addressed with the ARN not the PolicyId; this is because the former "acts" more like an ID.')
        raise Exception(f'TODO: handle this case {the_id} (type is {AWS_format.enumr(the_id)}).')
    if out is None:
        raise Exception(f'Does not understand pair (likely TODO in this assocs function) {the_id} ({AWS_format.enumr(the_id)}) vs {ty}')
    for o in out:
        if type(o) is dict:
            raise Exception(f'Bug in this code, need to include obj2id call for {the_id} ({AWS_format.enumr(the_id)}) vs {ty}')
        try:
            oty = AWS_format.enumr(o)
        except Exception as e:
            raise Exception(f'Bug in this code or AWS_format.enumr for {the_id}<=>{ty} queries: recieved a resource-id {o} which may be malformed or unrecognized by our code.')
        if oty != ty:
            raise Exception(f'Bug in this code for {the_id}<=>{ty} queries. Requested type is {ty} but recieved a resource-id {o} with type {AWS_format.enumr(o)}.')
    out = list(set(out)); out.sort()
    if filter_exists:
        out1 = []
        for o in out:
            if exists(o):
                out1.append(o)
        out = out1
    return out
