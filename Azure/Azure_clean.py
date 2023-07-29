import re, time
import covert
from . import Azure_query, Azure_nugget, Azure_core

def _is_in_use_by(e):
    # Attempts to parse a dependency error, giving us the resources that must be deleted before us since it uses us.
    # Returns None if it fails.
    synophrases = ['is used by existing resource', 'is in use by', 'still allocated to resource']
    txt = str(e)
    for synp in synophrases:
        txt = txt.replace(synp, synophrases[0])
    pieces = txt.split(synophrases[0])
    if len(pieces)<2:
        return None
    ids = re.findall(r'\S+\/\S+\/\S+\/\S+[^\.^ ]', pieces[1])
    if len(ids)==0:
        return None
    out = []
    for _id in ids:
        _id = _id.strip()
        #if '/Microsoft.Network/networkInterfaces/' in _id: # The ID does not point directly to the nic. # Or can we just work directly with this?
        #    pieces = _id.split('/')
        #    name = pieces[pieces.index('networkInterfaces')+1]
        #    _id1 = Azure_query.get_by_name('nic', name, include_lingers=True)
        #    if not _id1:
        #        raise Exception('Cannot get the nic id from this id:', _id)
        #    _id = _id1
    return [_id.strip() for _id in ids]

def _nuclear_clean(only_skythonic_stuff=True, restrict_to_these=None, remove_lingers=False): # DELETE EVERYTHING DANGER!
    big_grab = Azure_query.get_resources(ids=True, include_lingers=remove_lingers)
    if restrict_to_these:
        TODO # How to handle this?
    n_delete = 0
    delete_in_order = []
    for k in ['peerings', 'machines', 'nics', 'addresses', 'disks', 'subnets', 'rtables','webgates','sgroups','vnets','kpairs']:
        for the_id in big_grab[k]:
            if only_skythonic_stuff and '/'+Azure_nugget.skythonic_rgroup_name+'/' not in the_id:
                continue
            delete_in_order.append(the_id)

    # O(n^2) in theory as we chip through delete_in_order. But in practice it would take a very large n to matter.
    deleted_resc = set()
    n_delete = 0
    while len(delete_in_order)>0:
        the_id = delete_in_order[0]
        print('Attempt to delete:', the_id)
        try:
            Azure_core.delete(the_id, raise_not_founds=False)
            delete_in_order = delete_in_order[1:]
            deleted_resc.add(the_id)
            n_delete = n_delete+1
        except Exception as e:
            dep_ids = _is_in_use_by(e)
            if not dep_ids:
                raise e
            for dep_id in dep_ids: # How often is there more than one?
                if Azure_query.lingers(dep_id) or dep_id in deleted_resc: # deleted_resc is also a "linger" check.
                    print('Waiting for deletion to finish for:', dep_id)
                    time.sleep(2)
                else:
                    print('Adding dep to delete:', dep_id)
                    delete_in_order = [dep_id]+delete_in_order
    print('Deleted:', n_delete, 'resources.')

def nuclear_clean(remove_lingers=False):
    confirm = input('\033[95mWarning: will delete EVERYTHING in the WHOLE ACCOUNT (not just the labs or Skythonic resource group) leaving just the default resources; input y to proceed:\033[0m')
    if confirm.strip().lower() !='y':
        print("Cancelled by user.")
        return None
    covert.remove_pickle()
    _nuclear_clean(False, None, remove_lingers)

def skythonic_wipe(remove_lingers=False):
    confirm = input('\033[95mWarning: will delete EVERY resource created by Skythonic (and dependent resources); using the __Skythonic__ tag, (not just the lab); input y to proceed:\033[0m')
    if confirm.strip().lower() !='y':
        print("Cancelled by user.")
        return None
    covert.remove_pickle()
    _nuclear_clean(True, None, remove_lingers)

def power_delete(id_list, remove_lingers=False):
    TODO
