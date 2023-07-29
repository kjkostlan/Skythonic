# Misc formatting.
from . import Azure_nugget

def enumr(txt0): # ENUMerate Resourse type. Different clouds may call it by different names.
    txt = txt0.strip().lower().replace('_','')
    if txt[-1] == 's' and '/' not in txt:
        txt = txt[0:-1]
    if txt in ['vpc', 'vnet'] or ('Microsoft.Network/virtualNetworks'.lower() in txt and '/subnets/' not in txt):
        return 'vnet'
    if txt in ['webgate', 'internetgateway', 'gateway', 'gate', 'networkgate']:
        return 'webgate'
    if txt in ['rtable', 'routetable'] or 'Microsoft.Network/routeTables'.lower() in txt:
        return 'rtable'
    if txt in ['subnet'] or '/subnets/' in txt:
        return 'subnet'
    if txt in ['securitygroup', 'sgroup'] or '/networkSecurityGroups/'.lower() in txt:
        return 'sgroup'
    if txt in ['keypair', 'kpair', 'key', 'secret']:
        return 'kpair'
    if txt in ['instance', 'machine', 'vm', 'virtual_machine', 'virtualmachine'] or '/Microsoft.Compute/virtualMachines/'.lower() in txt:
        return 'machine'
    if txt in ['address', 'addres', 'addresses', 'addresse'] or '/Microsoft.Network/publicIPAddresses/'.lower() in txt:
        return 'address'
    if txt in ['vpcpeer', 'vpcpeering', 'peer', 'peering']:
        return 'peering'
    if txt in ['disk', 'drive', 'diskdrive', 'disk_drive']:
        return 'disk'
    if txt in ['user']:
        return 'user'
    if txt in ['route', 'path', 'pathway']: # Not a top-level resource.
        return 'route'
    if txt in ['policy','policies','policie','iampolicy','iampolicies','iampolicie']:
        return 'IAMpolicy'
    if txt in ['network_interface', 'networkinterface', 'nic'] or '/Microsoft.Network/networkInterfaces/'.lower() in txt:
        return 'nic'
    raise Exception(f'{txt0} is not an understood type or type of id (OR this is a TODO in the code; the id parsing is incomplete).')

def enumloc(txt0):
    # Make sure a location is in Azure-syntax. Will map the AWS location to the matching Azure location, if applicable.
    locs = ['eastus', 'eastus2', 'southcentralus', 'westus2', 'westus3', 'australiaeast', 'southeastasia', 'northeurope',
            'swedencentral', 'uksouth', 'westeurope', 'centralus', 'southafricanorth', 'centralindia', 'eastasia',
            'japaneast', 'koreacentral', 'canadacentral', 'francecentral', 'germanywestcentral', 'norwayeast',
            'polandcentral', 'switzerlandnorth', 'uaenorth', 'brazilsouth', 'centraluseuap', 'qatarcentral',
            'centralusstage', 'eastusstage', 'eastus2stage', 'northcentralusstage', 'southcentralusstage',
            'westusstage', 'westus2stage', 'asia', 'asiapacific', 'australia', 'brazil', 'canada', 'europe',
            'france', 'germany', 'global', 'india', 'japan', 'korea', 'norway', 'singapore', 'southafrica',
            'switzerland', 'uae', 'uk', 'unitedstates', 'unitedstateseuap', 'eastasiastage', 'southeastasiastage',
            'brazilus', 'eastusstg', 'northcentralus', 'westus', 'jioindiawest', 'eastus2euap', 'southcentralusstg',
            'westcentralus', 'southafricawest', 'australiacentral', 'australiacentral2', 'australiasoutheast',
            'japanwest', 'jioindiacentral', 'koreasouth', 'southindia', 'westindia', 'canadaeast', 'francesouth',
            'germanynorth', 'norwaywest', 'switzerlandwest', 'ukwest', 'uaecentral', 'brazilsoutheast']
    txt = txt0.lower().strip()
    for k in ['1','2','3','4']: # AWS-style "us-west-2c" => "us-west-" which later gets processed more.
        for l in ['a','b','c','d']:
            if txt.endswith(k+l):
                txt = txt[0:-2]
    details = ['north', 'west', 'east', 'south', 'central', '1', '2', '3', '4', 'stage']
    nation = txt
    locs_filter = locs
    for d in details:
        if d in nation:
            nation = nation.replace(d, '')
            locs_filter = list(filter(lambda l: d in l, locs_filter))
        else:
            locs_filter = list(filter(lambda l: d not in l, locs_filter))
    greebles = [' ', ',', '-','_','+','/']
    for greeble in greebles:
        nation = nation.replace(greeble,'')

    locs_filter = list(filter(lambda l: nation in l, locs_filter))
    if len(locs_filter) == 1:
        return locs_filter[0]
    elif len(locs_filter) == 0:
        raise Exception('No region match to: '+txt0)
    elif len(locs_filter) > 1:
        raise Exception('Multible region match to: '+txt0+': '+str(locs_filter))

def obj2id(obj_desc): # Gets the ID from a description.
    if type(obj_desc) is str:
        return obj_desc
    elif type(obj_desc) is dict:
        if 'id' in obj_desc:
            return obj_desc['id']
        if 'Skythonic_extracted_id' in obj_desc:
            return obj_desc['Skythonic_extracted_id']
        if 'properties' in obj_desc:
            if 'vmSize' in str(obj_desc) and 'osProfile' in str(obj_desc): # Found a VM!
                vm_name = obj_desc['properties']['osProfile']['computerName']
                resource_group_name = obj_desc['properties']['storageProfile']['osDisk']['managedDisk']['id'].split('/')[4] # Somewhat brittle? Other ways to get the rgroup exist.
                vm = Azure_nugget.compute_client.virtual_machines.get(resource_group_name, vm_name)
                return vm.id
            if 'resourceGuid' in obj_desc['properties'] and 'virtualNetworkPeerings' in obj_desc['properties']:
                raise Exception('resourceGuides are very mysterious (vnets; sometimes [properties][subnets][0][id][all but last two pieces] would work).')
        print('Uh ho obj desc is:', obj_desc)
        raise Exception('Cannot extract the id for object-as-dict with keys:'+str(obj_desc.keys()))
    elif hasattr(obj_desc, 'id'): # Does this ever lead us astray?
        return obj_desc.id
    elif hasattr(obj_desc, 'serialize'):
        return obj2id(obj_desc.serialize()) # Azures uses these to make a dict representation.
    raise Exception('Azure obj2id fail on type: '+str(type(obj_desc)))

def id2obj(the_id, assert_exist=True):
    # Also converts non-dict objects to dicts similar to describe_xyz in AWS.
    if type(the_id) is dict:
        return the_id # Already a description.
    if type(the_id) is str:
        x = Azure_nugget.try_versions(Azure_nugget.resource_client.resources.get_by_id, the_id)
        out = x.serialize()
        if 'id' not in out:
            out['id'] = x.id
        return out
    if hasattr(the_id, 'serialize'):
        x = the_id.serialize() # Azures uses these to make a dict representation.
        if 'id' not in x and hasattr(the_id, 'id'): # Disks serialize() seems to eliminate both the name and the id from the JSON, so adding in id can help.
            x['Skythonic_extracted_id'] = the_id.id
        return x
    raise Exception('Azure id2obj fail on type: '+str(type(the_id)))
to_dict = id2obj # Alternate name for converting Azure objects to dict.

def tag_dict(desc_or_id):
    the_id = obj2id(desc_or_id)
    resource = Azure_nugget.try_versions(Azure_nugget.resource_client.resources.get_by_id, the_id)
    return {} if resource.tags is None else resource.tags
