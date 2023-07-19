# Lower level Azure functions.
from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet, VirtualNetworkGateway
from . import Azure_query, Azure_format, Azure_nugget
import waterworks.plumber as plumber

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
        x = Azure_nugget.network_client.virtual_networks.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, name, vnet_params).result()
    elif rtype == 'webgate': # Strangely, the tutorials still use *virtual* gateways to connect to the *real* internet. There is no InternetGateway model.
        kwargs1 = {**kwargs, 'name':name}
        gateway_params = VirtualNetworkGateway(**kwargs1)
        gateway_params.name = name # Really want that name!
        print('User gate params:', kwargs1)
        x = Azure_nugget.network_client.virtual_network_gateways.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, name, gateway_params).result()
    elif rtype == 'rtable':
        TODO
    elif rtype == 'subnet':
        kwargs1 = {k: v for k, v in kwargs.items() if k not in ['vnet_name', 'vnet_id']}
        if 'vnet_name' in kwargs and 'vnet_id' in kwargs:
            raise Exception('Must specify a vnet_name, a vnet_id, but not both.')
        vnet_name_or_id = kwargs.get('vnet_name', kwargs.get('vnet_id', None))
        if not vnet_name_or_id:
            raise Exception('Must specify a vnet_name xor a vnet_id.')
        kwargs1['name'] = name # Redundant?
        subnet_params = Subnet(**kwargs1)
        x = Azure_nugget.network_client.subnets.begin_create_or_update(Azure_nugget.skythonic_rgroup_name, vnet_name_or_id.split('/')[-1], name, subnet_params).result()
    elif rtype == 'route':
        TODO
    elif rtype =='sgroup':
        TODO
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

    rtype = Azure_format.to_dict(the_id)

    if rtype == 'webgate':
        TODO
    elif rtype == 'vpc' or rtype=='vnet':
        TODO
    elif rtype == 'subnet':
        TODO
    elif rtype == 'kpair':
        TODO
    elif rtype == 'sgroup':
        TODO
    elif rtype == 'rtable':
        TODO
    elif rtype == 'machine':
        stop_first = True
        if stop_first:
            TODO
        TODO
    elif rtype == 'address': # These are addresses
        TODO
    elif rtype=='peering':
        TODO
    elif rtype=='user':
        TODO
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
    A = Azure_format.obj2id(A); B = Azure_format.obj2id(B)
    rA = Azure_format.enumr(A); rB = Azure_format.enumr(B)

    if rA=='vpc' and rB=='webgate':
        TODO
    elif rA=='subnet' and rB=='rtable':
        TODO
    elif rA=='address' and rB=='machine':
        TODO
    elif (rA=='vpc' or rA=='vnet') and (rB=='vpc' or rB=='vnet'): # Peering can be thought of as an association.
        TODO
    elif _swapped:
        raise Exception(f"Don't know how to attach {A} to {B}; this may require updating this function.")
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

def create_route(rtable_id, dest_cidr, gateway_id):
    # TODO: This is a niche function, which should be refactors/abstracted.
    TODO

def install_these():
    # What to install on a jumpbox?
    return [TODO]
