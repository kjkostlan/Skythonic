# Misc formatting.
from . import Azure_nugget

def enumr(txt0): # ENUMerate Resourse type. Different clouds may call it by different names.
    txt = txt0.strip().lower().replace('_','')
    if txt[-1] == 's':
        txt = txt[0:-1]
    if txt in ['vpc', 'vnet'] or 'Microsoft.Network/virtualNetworks' in txt:
        return 'vnet'
    if txt in ['webgate', 'internetgateway', 'gateway', 'gate', 'networkgate']:
        return 'webgate'
    if txt in ['rtable', 'routetable']:
        return 'rtable'
    if txt in ['subnet']:
        return 'subnet'
    if txt in ['securitygroup', 'sgroup']:
        return 'sgroup'
    if txt in ['keypair', 'kpair', 'key', 'secret']:
        return 'kpair'
    if txt in ['instance', 'machine']:
        return 'machine'
    if txt in ['address', 'addres', 'addresses', 'addresse']:
        return 'address'
    if txt in ['vpcpeer', 'vpcpeering', 'peer', 'peering']:
        return 'peering'
    if txt in ['user']:
        return 'user'
    if txt in ['route', 'path', 'pathway']: # Not a top-level resource.
        return 'route'
    if txt in ['policy','policies','policie','iampolicy','iampolicies','iampolicie']:
        return 'IAMpolicy'
    raise Exception(f'{txt0} is not an understood type (OR this is a TODO in the code; we need to parse id strings).')

def obj2id(obj_desc): # Gets the ID from a description.
    if type(obj_desc) is str:
        return obj_desc
    elif type(obj_desc) is dict:
        return obj_desc['id']
    elif hasattr(obj_desc, 'serialize'):
        return obj_desc.serialize()['id'] # Azures uses these to make a dict representation.
    raise Exception('Azure obj2id fail on type: '+str(type(obj_desc)))

def id2obj(the_id, assert_exist=True):
    # Also converts non-dict objects to dicts similar to describe_xyz in AWS.
    if type(the_id) is dict:
        return the_id # Already a description.
    if type(the_id) is str:
        TODO # ids to objects TODO go here.
    if hasattr(the_id, 'serialize'):
        return the_id.serialize() # Azures uses these to make a dict representation.
    raise Exception('Azure id2obj fail on type: '+str(type(the_id)))
to_dict = id2obj # Alternate name for converting Azure objects to dict.

def tag_dict(desc_or_id):
    the_id = obj2id(desc_or_id)
    resource = Azure_nugget.resource_client.resources.get_by_id(the_id, api_version='2023-04-01')
    return resource.tags
