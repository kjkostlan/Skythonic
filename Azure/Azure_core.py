# Lower level Azure functions.
from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet

def add_tags(desc_or_id, d, ignore_none_desc=False):
    TODO

def create(rtype0, name, **kwargs):
    # Returns the ID, which is commonly introduced into other objects.
    raw = False # needed for keypairs.
    if kwargs.get('raw_object', False): # Generally discouraged to work with.
        raw = True
    if 'raw_object' in kwargs:
        del kwargs['raw_object']
    rtype = Azure_format.enumr(rtype0)
    if rtype == 'vpc' or rtype == 'vnet':
        TODO
    elif rtype == 'webgate':
        TODO
    elif rtype == 'rtable':
        TODO
    elif rtype == 'subnet':
        TODO
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
    elif type(x) is dict:
        return Azure_format.obj2id(x)
    else:
        return TODO

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
        out = create(rtype, name, **kwargs)
        if do_print:
            print(str(printouts)+'creating:', rtype, name)
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
    # TODO: fill out this function more.
    the_id = Azure_format.obj2id(desc_or_id)
    ty = Azure_format.enumr(the_id)
    if ty == 'vpc':
        TODO
    else:
        TODO # More cases please!

def create_route(rtable_id, dest_cidr, gateway_id):
    # TODO: This is a niche function, which should be refactors/abstracted.
    TODO

def install_these():
    # What to install on a jumpbox?
    return [TODO]
