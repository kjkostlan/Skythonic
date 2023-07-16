def has_been_deleted(id):
    TODO

def dep_check_delete(id_or_obj, xdeps=None):
    TODO

def _nuclear_clean(only_skythonic_stuff=True, restrict_to_these=None, remove_lingers=False): # DELETE EVERYTHING DANGER!
    TODO

def nuclear_clean(remove_lingers=False):
    confirm = input('\033[95mWarning: will delete EVERYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default resources; input y to proceed:\033[0m')
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
