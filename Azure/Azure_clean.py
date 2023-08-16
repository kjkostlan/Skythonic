import re, time
import covert
from . import Azure_query, Azure_nugget, Azure_core

def _dep_id_tweak(_id):
    # Occasionally need to tweak this id:
    _id1 = _id
    pieces = _id.split('/')
    if pieces[-2]=='ipConfigurations':
        if pieces[-1]==pieces[-3]:
            _id1 = '/'.join(pieces[0:-2])
    if _id1 != _id:
        print('Tweaking a dep id:', _id, '=>', _id1)
    return _id1

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

    return [_dep_id_tweak(_id).strip() for _id in ids]

def _delete_attempt_get_deps(the_id):
    print('Attempting to delete:', the_id)
    try:
        Azure_core.delete(the_id, raise_not_founds=False)
        return []
    except Exception as e:
        dep_ids = _is_in_use_by(e)
        if not dep_ids:
            raise e
        return dep_ids

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
        bad_deps = _delete_attempt_get_deps(the_id)
        if len(bad_deps) == 0: # Successful.
            delete_in_order = delete_in_order[1:]
            deleted_resc.add(the_id)
            n_delete = n_delete+1
            print('Deleted sucessfully')
        else: # A strange error-check.
            unquery_deps = []
            es = []
            for dep_id in bad_deps:
                try:
                    Azure_nugget.try_versions(Azure_nugget.resource_client.resources.get_by_id, dep_id)
                except Exception as e:
                    es.append(e)
                    unquery_deps.append(dep_id)
            if len(es)>0:
                bad_deps1 = _delete_attempt_get_deps(the_id)
                for i in range(len(unquery_deps)):
                    if unquery_deps[i] in set(bad_deps1):
                        print(es[i])
                        raise Exception(f'{unquery_deps[i]} is a dependency of {the_id} that must first be deleted. But it cannot even been queried (see above printout)')
        for dep_id in bad_deps: # How often is there more than one?
            if Azure_query.lingers(dep_id) or dep_id in deleted_resc: # deleted_resc is also a "linger" check.
                print('Waiting for deletion to finish for:', dep_id)
                time.sleep(2)
            else:
                print('Adding dep to delete-in-order array:', dep_id)
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
