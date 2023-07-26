# Lower level Azure functions.
from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet, VirtualNetworkGateway, RouteTable, Route, NetworkSecurityGroup, PublicIPAddress, NetworkInterface
from . import Azure_query, Azure_format, Azure_nugget
import waterworks.plumber as plumber

try:
    delete_user_input_check
except:
    delete_user_input_check = [True] # Safety.

def add_tags(desc_or_id, tags_to_add, ignore_none_desc=False):
    if not desc_or_id:
        if ignore_none_desc:
            raise Exception('None object')
        return False
    the_id = Azure_format.obj2id(desc_or_id)
    the_obj = Azure_nugget.resource_client.resources.get_by_id(the_id, api_version=Azure_nugget.api_version)

    if the_obj.tags is None:
        the_obj.tags = tags_to_add
    else:
        the_obj.tags.update(tags_to_add)

def create(rtype0, name, **kwargs):
    # Returns the ID, which is commonly introduced into other objects.
    raw = False # needed for keypairs.
    if kwargs.get('raw_object', False): # Generally discouraged to work with.
        raw = True
    if 'raw_object' in kwargs:
        del kwargs['raw_object']
    if not name:
        raise Exception('Name must be non-None')
    rtype = Azure_format.enumr(rtype0)
    if rtype == 'vpc' or rtype == 'vnet':
        vnet_params = VirtualNetwork(**kwargs)
        x0 = Azure_nugget.network_client.virtual_networks.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, name, vnet_params)
        x = x0.result()
    elif rtype == 'webgate':
        # This use-case is unusual for Azure.
        kwargs1 = {**kwargs, 'name':name}
        gateway_params = VirtualNetworkGateway(**kwargs1)
        gateway_params.name = name # Really want that name!
        x0 = Azure_nugget.network_client.virtual_network_gateways.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, name, gateway_params)
        x = x0.result()
    elif rtype == 'rtable':
        kwargs['location'] = Azure_format.enumloc(kwargs['location'])
        rtable_params = RouteTable(**kwargs)
        x0 = Azure_nugget.network_client.route_tables.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, name, rtable_params)
        x = x0.result()
    elif rtype == 'subnet':
        kwargs1 = {k: v for k, v in kwargs.items() if k not in ['vnet_name', 'vnet_id']}
        if 'vnet_name' in kwargs and 'vnet_id' in kwargs:
            raise Exception('Must specify a vnet_name, a vnet_id, but not both.')
        vnet_name_or_id = kwargs.get('vnet_name', kwargs.get('vnet_id', None))
        if not vnet_name_or_id:
            raise Exception('Must specify a vnet_name xor a vnet_id.')
        kwargs1['name'] = name # Redundant?
        subnet_params = Subnet(**kwargs1)
        x0 = Azure_nugget.network_client.subnets.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, vnet_name_or_id.split('/')[-1], name, subnet_params)
        x = x0.result()
    elif rtype == 'route':
        TODO
    elif rtype =='sgroup':
        kwargs['location'] = Azure_format.enumloc(kwargs['location'])
        sgroup_params = NetworkSecurityGroup(**kwargs)
        x0 = Azure_nugget.network_client.network_security_groups.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, name, sgroup_params)
        x = x0.result()
    elif rtype == 'kpair':
        TODO
    elif rtype =='machine':
        TODO
    elif rtype == 'address':
        TODO
    elif rtype == 'user':
        TODO
    elif rtype == 'peering':
        TODO
    else:
        raise Exception('Create ob type unrecognized: '+rtype0)

    f = lambda: add_tags(x, {'Name':name, '__Skythonic__':True})
    f_catch = lambda e: 'does not exist' in repr(e).lower()
    msg = 'created a resource of type '+rtype+' waiting for it to start existing.'
    plumber.loop_try(f, f_catch, msg, delay=4)

    if raw: # Generally discouraged to work with, except for keypairs.
        return x
    elif type(x) is not str:
        return Azure_format.obj2id(x)

def create_once(rtype, name, printouts, **kwargs):
    # Creates a resource unless the name is already there.
    # Returns the created or already-there resource.
    r0 = Azure_query.get_by_name(rtype, name)
    do_print = printouts is not None and printouts is not False
    if printouts is True:
        printouts = ''
    elif type(printouts) is str:
        printouts = printouts+' '
    if r0 is not None:
        if do_print:
            print(str(printouts)+'already exists:', rtype, name)
        if Azure_format.enumr(rtype) == 'machine':
            TODO
        return Azure_format.obj2id(r0)
    else:
        if do_print:
            print(str(printouts)+'creating:', rtype, name)
        out = create(rtype, name, **kwargs)
        if do_print:
            print('...done')
        return out

def delete(desc_or_id):
    # Deletes an object (returns True if sucessful, False if object wasn't existing).
    the_id = Azure_format.obj2id(desc_or_id)
    if the_id is None:
        raise Exception('None ID')

    if delete_user_input_check[0]:
        x = input('\033[95mType "delete" to confirm this AND ALL FUTURE deletions for this Python session:\033[0m').lower().strip()
        if x=='delete':
            delete_user_input_check[0] = False
        else:
            raise Exception('Once-per-session deletion confirmation denied by user.')

    del_tag = {'__deleted__':True}
    def _first_way(): # Multible ways to do something, which one is better?
        Azure_nugget.resource_client.resources.begin_create_or_update_by_id(the_id, api_version=Azure_nugget.api_version,  parameters=del_tag)
    def _second_way():
        x = Azure_nugget.resource_client.resources.get_by_id(the_id, api_version=Azure_nugget.api_version)
        if not x:
            raise Exception('None resource')
        tags1 = {**x.tags, **del_tag} if (hasattr(x,'tags') and x.tags) else del_tag
        x.tags = tags1
        #Azure_nugget.resource_client.resources.begin_create_or_update(the_id, x)
        Azure_nugget.resource_client.resources.begin_create_or_update_by_id(the_id, api_version=Azure_nugget.api_version,  parameters=x)
    _second_way()
    Azure_nugget.resource_client.resources.begin_delete_by_id(the_id, api_version=Azure_nugget.api_version)

    return True

def assoc(A, B, _swapped=False):
    # Association, attachment, etc. Order does not matter unless both directions have meaning.
    # Idempotent (like Clojures assoc).
    A = Azure_format.obj2id(A); B = Azure_format.obj2id(B)
    rA = Azure_format.enumr(A); rB = Azure_format.enumr(B)

    if (rA=='vpc' or rA=='vnet') and rB=='webgate':
        TODO
    elif (rA=='vpc' or rA=='vnet') and rB == 'sgroup':
        vnet = Azure_nugget.resource_client.resources.get_by_id(A, api_version=Azure_nugget.api_version)
        vnet.network_security_group = {'id': B}

        vnet_rgroup =  A.split('/')[A.split('/').index('resourceGroups')+1]
        Azure_nugget.network_client.virtual_networks.begin_create_or_update(vnet_rgroup, vnet.name, vnet)
    elif rA=='subnet' and rB=='rtable':
        subnet = Azure_nugget.resource_client.resources.get_by_id(A, api_version=Azure_nugget.api_version)
        subnet.route_table = {'id':B}
        Azure_nugget.resource_client.resources.begin_create_or_update_by_id(A, api_version=Azure_nugget.api_version, parameters=subnet)
    elif rA=='address' and rB=='machine':
        TODO
    elif (rA=='vpc' or rA=='vnet') and (rB=='vpc' or rB=='vnet'): # Peering can be thought of as an association.
        TODO
    elif _swapped:
        raise Exception(f"Don't know how to attach this pair of types {rA} to {rB}; this may require updating this function.")
    else:
        assoc(B, A, True)

def disassoc(A, B, _swapped=False):
    # Opposite of assoc and Idempotent.
    TODO
dissoc = disassoc # For those familiar with Clojure...

def modify_attribute(desc_or_id, k, v):
    # Is this simplier than AWS since the API isn't as dependent on different resource types?
    the_id = Azure_format.obj2id(desc_or_id)
    resource = Azure_nugget.resource_client.resources.get_by_id(the_id, api_version=Azure_nugget.api_version)
    setattr(resource, k, v)

def connect_to_internet(rtable_id, vnet_id):
    # TODO: This is a niche function, which should be refactored/abstracted.
    route0_params = Route(name="route_outbound", address_prefix="0.0.0.0/0",next_hop_type="Internet")
    route_table_name = rtable_id.split('/')[-1]
    ix = rtable_id.split('/').index('resourceGroups')
    rgroup_name = rtable_id.split('/')[ix+1]
    x0 = Azure_nugget.network_client.routes.begin_create_or_update(rgroup_name, route_table_name, route0_params.name, route0_params)

    #route1_params = Route(name="route_inbound",address_prefix="0.0.0.0/0",next_hop_type="VirtualNetworkGateway") # No need to specify inbound rules.
    #x1 = network_client.routes.begin_create_or_update(rgroup_name, route_table_name, route1_params.name, route1_params)

    vnet_name = vnet_id.split('/')[-1]
    vnet_rgroup = rtable_id.split('/')[rtable_id.split('/').index('resourceGroups')+1]

    vnet_params = Azure_nugget.network_client.virtual_networks.get(vnet_rgroup, vnet_name)
    vnet_params.route_table = {'id': rtable_id}
    vnet = Azure_nugget.network_client.virtual_networks.begin_create_or_update(vnet_rgroup, vnet_name, vnet_params).result()

def install_these():
    # What to install on a jumpbox?
    return [TODO]
