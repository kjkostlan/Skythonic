import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
import AWS.AWS_query as AWS_query, AWS.AWS_core as AWS_core, AWS.AWS_format as AWS_format
import covert, eye_term

def has_been_deleted(id):
    # To clean up stuff that lingers.
    try:
        desc = AWS_format.id2obj(id, False)
    except Exception as e:
        if 'list index out of range' in repr(e): # Already deleted.
            return True # When it ceases to exist this error can be raised.
        else:
            raise e
    if desc is None:
        return False
    tags = AWS_format.tag_dict(desc)
    return tags.get('__deleted__', False)

def dep_check_delete(id_or_obj, xdeps):
    # Deletes x with a dep check for instances (and anything else that "lingers").
    # Retruns True if it deleted an object for the first time and that exists.
    desc = AWS_format.id2obj(id_or_obj); id = AWS_format.obj2id(id_or_obj)
    redo_deletes = True # False may save time but risks skipping over stuff.
    print_redo_deletes = True

    if has_been_deleted(id):
        if not redo_deletes:
            return 0 # Already deleted, but still hanging out.
        if print_redo_deletes:
            print('Deleting this object (again):', id)
    else:
        print('Deleting this object:', id)
    try:
        AWS_core.add_tags(id_or_obj, {'__deleted__':True})
    except Exception as e:
        if 'does not exist' in repr(e):
            print(f'Tried to delete {id} but object doesnt exist; no need to delete.')
            return 0
        else:
            raise e

    lingers = lambda: list(filter(has_been_deleted, xdeps))
    f_try = lambda: AWS_core.delete(id)
    def f_catch(e):
        if 'DependencyViolation' in repr(e):
            lrs = set(lingers()); xdeps1 = set(xdeps)
            if len(xdeps1-lrs)>0:
                raise Exception('DependencyViolation error on:', id, ' these deps werent deleted:', str(xdeps1-lrs))
            if len(xdeps1)==0:
                raise Exception('DependencyViolation error on:', id, ' even though no deps seem to be remaining.')
            return True
        return False
    msg = lambda: 'Lingering dependencies on '+ id+': '+str(lingers())+' Will retry in a loop untill the deletion works.'
    eye_term.loop_try(f_try, f_catch, msg, delay=4)

    return int('__deleted__' not in str(desc))

def _nuclear_clean(only_skythonic_stuff=True): # DELETE EVERYTHING DANGER!
    resc = AWS_query.custom_resources()
    deps = AWS_query.what_needs_these(custom_only=False, include_empty=True)
    n_delete=0
    for k in ['users', 'peerings','addresses', 'machines', 'subnets', 'rtables','webgates','sgroups','vpcs','kpairs']: # Can the right order avoid needing deps?
        if k not in resc:
            continue
        for x in resc[k]:
            xid = AWS_format.obj2id(x)
            if only_skythonic_stuff and not AWS_format.tag_dict(x).get('__Skythonic__', False):
                continue # Only delete items created by Skythonic.
            # Can't remove instance from subnet?
            #if k=='subnets' and xid.startswith('subnet-'): # Try to dissoc addresses from VMS to speed up deletion. (more to come later)
            #    for dep_id in deps[xid]:
            #        if dep_id.startswith('i-'):
            #            print('Dissoc to speed up deletion:', xid, dep_id)
            #            TODO
            n_delete += dep_check_delete(x, deps[xid])
    print('Deleted (for the first time):', n_delete, 'resources.')

def nuclear_clean():
    confirm = input('Warning: will delete EVERYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default resources; input y to proceed')
    if confirm.strip().lower() !='y':
        print("Cancelled by user.")
        return None
    covert.remove_pickle()
    _nuclear_clean(False)

def skythonic_wipe():
    confirm = input('Warning: will delete EVERY resource created by Skythonic; using the __Skythonic__ tag, (not just the lab); input y to proceed')
    if confirm.strip().lower() !='y':
        print("Cancelled by user.")
        return None
    covert.remove_pickle()
    _nuclear_clean(True)
