import covert
from . import Azure_query, Azure_nugget, Azure_core

def has_been_deleted(id):
    TODO

def dep_check_delete(id_or_obj, xdeps=None):
    TODO

def _nuclear_clean(only_skythonic_stuff=True, restrict_to_these=None, remove_lingers=False): # DELETE EVERYTHING DANGER!
    big_stuff = Azure_query.get_resources(ids=True, include_lingers=remove_lingers)
    if restrict_to_these:
        TODO # How to handle this?
    n_delete = 0
    for k in ['peerings','addresses', 'machines', 'disks', 'nics', 'subnets', 'rtables','webgates','sgroups','vnets','kpairs']: # How much does order matter?
        for the_id in big_stuff[k]:
            if only_skythonic_stuff and '/'+Azure_nugget.skythonic_rgroup_name+'/' not in the_id:
                continue
            print('About to delete:', the_id)
            Azure_core.delete(the_id)
            n_delete = n_delete+1
    print('Deleted:', n_delete, 'resources.')

def nuclear_clean(remove_lingers=False):
    confirm = input('\033[95mWarning: will delete EVERYTHING in the WHOLE ACCOUNT (not just the labs or Skythonic resource group) leaving just the default resources; input y to proceed:\033[0m')
    if confirm.strip().lower() !='y':
        print("Cancelled by user.")
        return None
    covert.remove_pickle()
    _nuclear_clean(False, None, remove_lingers)

def skythonic_wipe(remove_lingers=False):
    confirm = input('\033[95mWarning: will delete EVERY resource created by Skythonic; using the __Skythonic__ tag, (not just the lab); input y to proceed:\033[0m')
    if confirm.strip().lower() !='y':
        print("Cancelled by user.")
        return None
    covert.remove_pickle()
    _nuclear_clean(True, None, remove_lingers)

def power_delete(id_list, remove_lingers=False):
    TODO
