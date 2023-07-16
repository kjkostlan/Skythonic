import os
from . import Azure_format, Azure_nugget

def lingers(desc_or_id):
    #Do all cloud providors have this lingering resource problem?
    if desc_or_id is None:
        return False
    return Azure_format.tag_dict(desc_or_id).get('__deleted__',False)

def get_resources(which_types=None, ids=False, include_lingers=False, filters=None):
    # The most common resources. Filter by which to shave off a few 100 ms from this query.
    # Will not find routes directly, but does find rtables.
    # Will not find tags directly; use get_by_tag.
    kwargs = {}
    if filters is not None:
        if type(filters) is dict: # Filters must be a list.
            filters = [filters]
        kwargs = {'Filters':filters}
    out = {}
    splice = type(which_types) is str
    if splice:
        which_types = [which_types]
    if which_types is not None:
        which_types = set([Azure_format.enumr(ty) for ty in which_types])

    if which_types is None or 'vpc' in which_types or 'vnet' in which_types: # Python only introduced the switch statement in 3.10
        out['vpcs'] = list([Azure_format.id2obj(x) for x in Azure_nugget.network_client.virtual_networks.list_all()])
    if which_types is None or 'webgate' in which_types:
        out['webgates'] = TODO
    if which_types is None or 'rtable' in which_types:
        out['rtables'] = TODO
    if which_types is None or 'subnet' in which_types:
        out['subnets'] = TODO
    if which_types is None or 'sgroup' in which_types:
        out['sgroups'] = TODO
    if which_types is None or 'kpair' in which_types:
        out['kpairs'] = TODO
    if which_types is None or 'machine' in which_types:
        out['machines'] = TODO
    if which_types is None or 'address' in which_types:
        out['addresses'] = TODO
    if which_types is None or 'peering' in which_types:
        out['peerings'] = TODO
    if which_types is None or 'user' in which_types:
        out['users'] = TODO
    if which_types is None or 'IAMpolicy' in which_types: # Only includes resources with a 'PolicyId'
        out['IAMpolicies'] = TODO
    if ids:
        for k, v in out.items():
            out[k] = Azure_format.obj2id(k)

    if not include_lingers:
        for k in out.keys():
            out[k] = list(filter(lambda x: not lingers(x), out[k]))

    if splice: # Splice for a str, which is different than a one element collection.
        out = out[list(out.keys())[0]]
    return out

def get_by_tag(rtype, k, v, include_lingers=False): # Returns None if no such resource exists.
    resc = get_resources(rtype, include_lingers)
    for r in resc:
        if Azure_format.tag_dict(r).get(k,None) == v:
            return r

def get_by_name(rtype, name, include_lingers=False): # Convenience fn.
    return get_by_tag(rtype, 'Name', name, include_lingers)

def exists(desc_or_id):
    the_id = Azure_format.obj2id(desc_or_id)
    if type(the_id) is not str:
        raise Exception('Possible bug in obj2id.')
    try:
        desc1 = Azure_format.id2obj(the_id)
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
            TODO
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
            TODO
    return out

def assocs(desc_or_id, with_which_type, filter_exists=True):
    #Gets associations of desc_or_id with_which_type. Returns a list.
    ty = Azure_format.enumr(with_which_type)
    the_id = Azure_format.obj2id(desc_or_id)
    ty0 = Azure_format.enumr(with_which_type)
    desc = Azure_format.id2obj(desc_or_id)

    # Nested switchyard:
    out = None
    if ty0 == 'webgate':
        if ty == 'webgate':
            raise Exception('Internet gateways are not associated with thier own kind.')
        if ty in ['user','address','kpair','sgroup','peering','IAMpolicy']:
            raise Exception(f'Internet gateways cannot be directly associated with {ty}s.')
        if ty=='vpc' or ty == 'vnet':
            TODO
        if ty=='subnet':
            TODO
        if ty=='rtable':
            TODO
        if ty=='machine':
            TODO
    elif ty0 == 'vpc' or ty0 == 'vnet':
        if ty == 'vpc' or ty == 'vnet':
            TODO
        if ty in ['user','address','kpair','IAMpolicy']:
            raise Exception(f'VPCs cannot be directly associated with {ty}s.')
        if ty=='sgroup':
            TODO
        if ty=='webgate':
            TODO
        if ty=='machine':
            TODO
        if ty=='subnet':
            TODO
        if ty=='peering':
            TODO
        if ty=='rtable':
            TODO
    elif ty0 == 'subnet':
        if ty == 'subnet':
            raise Exception('Subnets cannot be associated with thier own kind.')
        if ty in ['user','kpair','peering','IAMpolicy']:
            raise Exception(f'subnets cannot be directly associated with {ty}s.')
        if ty=='vpc' or ty == 'vnet':
            TODO
        if ty=='rtable':
            TODO
        if ty=='webgate':
            TODO
        if ty=='address':
            TODO
        if ty=='sgroup':
            TODO
        if ty=='machine':
            TODO
    elif ty == 'kpair': #Only needs the name.
        if ty == 'kpair':
            raise Exception('Keypairs are not associated with thier own kind.')
        if ty in ['webgate','vpc','vnet', 'subnet','sgroup','rtable','address','peering','user','IAMpolicy']:
            raise Exception(f'Security groups cannot be directly associated with {ty}s.')
        if ty=='machine':
            TODO
    elif ty == 'sgroup':
        if ty == 'sgroup':
            raise Exception('Security groups are not associated with thier own kind.')
        if ty in ['kpair','webgate','user','rtable','address','peering','IAMpolicy']:
            raise Exception(f'Security groups cannot be directly associated with {ty}s.')
        if ty=='vpc' or ty == 'vnet':
            TODO
        if ty=='machine':
            TODO
        if ty=='subnet':
            TODO
    elif ty == 'rtable':
        if ty == 'rtable':
            raise Exception('Route tables are not associated with thier own kind.')
        if ty in ['kpair','sgroup','user','machine','IAMpolicy']:
            raise Exception(f'Route tables cannot be directly associated with {ty}s.')
        if ty in ['peering', 'webgate', 'subnet', 'vpc', 'vnet']:
            TODO
        if ty=='address':
            TODO
    elif ty0 == 'machine':
        if ty == 'machine':
            raise Exception('Machines cannot be associated with thier own kind.')
        if ty in ['peering', 'rtable','user', 'IAMpolicy']:
            raise Exception(f'Instances cannot be directly associated with {ty}s.')
        if ty=='vpc' or ty == 'vnet':
            TODO
        if ty=='webgate':
            TODO
        if ty=='subnet':
            TODO
        if ty=='kpair':
            TODO
        if ty=='sgroup':
            TODO
        if ty=='address':
            TODO
    elif the_id.startswith('eipalloc-'): # These are addresses
        if ty == 'address':
            raise Exception('Addresses cannot be associated with thier own kind.')
        if ty in ['vpc', 'vnet', 'kpair', 'peering','IAMpolicy', 'sgroup', 'user']:
            raise Exception(f'Addresses cannot be directly associated with {ty}s.')
        if ty=='machine':
            out = TODO
        if ty=='rtable':
            TODO
        if ty=='webgate':
            raise Exception('Addresses cannot be directly associated with internet gateways.')
        if ty=='subnet':
            TODO
    elif ty0=='peering':
        if ty == 'peering':
            raise Exception('Peering connections cannot be associated with thier own kind.')
        if ty in ['machine','webgate','subnet','kpair','sgroup','address','IAMpolicy']:
            raise Exception(f'Peerings cannot be directly associated with {ty}s.')
        if ty=='vpc' or ty =='vnet':
            TODO
        if ty=='rtables':
            TODO
    elif ty0=='user':
        if ty in ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address', 'peering']:
            raise Exception(f'Users cannot be directly associated with {ty}s.')
        if ty == 'user':
            raise Exception('Users cannot be associated with thier own kind (except in real life).')
        if ty=='IAMpolicy':
            TODO
    elif ty0=='IAMpolicy':
        if ty in ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address', 'peering']:
            raise Exception(f'IAMpolicies cannot be directly associated with {ty}s.')
        if ty == 'IAMpolicy':
            raise Exception('IAMpolicies cannot be associated with thier own kind.')
        if ty == 'user':
            users = iam.list_entities_for_policy(PolicyArn=desc['Arn'],EntityFilter='User')['PolicyUsers']
            out = [Azure_format.obj2id(user) for user in users]
    else:
        raise Exception(f'TODO: handle this case {the_id} (type is {Azure_format.enumr(the_id)}).')
    if out is None:
        raise Exception(f'Does not understand pair (likely TODO in this assocs function) {the_id} ({Azure_format.enumr(the_id)}) vs {ty}')
    for o in out:
        if type(o) is dict:
            raise Exception(f'Bug in this code, need to include obj2id call for {the_id} ({Azure_format.enumr(the_id)}) vs {ty}')
        try:
            oty = Azure_format.enumr(o)
        except Exception as e:
            raise Exception(f'Bug in this code or Azure_format.enumr for {the_id}<=>{ty} queries: recieved a resource-id {o} which may be malformed or unrecognized by our code.')
        if oty != ty:
            raise Exception(f'Bug in this code for {the_id}<=>{ty} queries. Requested type is {ty} but recieved a resource-id {o} with type {Azure_format.enumr(o)}.')
    out = list(set(out)); out.sort()
    if filter_exists:
        out1 = []
        for o in out:
            if exists(o):
                out1.append(o)
        out = out1
    return out
