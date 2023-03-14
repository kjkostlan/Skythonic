import boto3, time
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
import AWS.AWS_query as AWS_query, AWS.AWS_core as AWS_core

def dep_check_delete(x, xdeps):
    # Deletes x with a dep check for instances (and anything else that "lingers").
    desc = AWS_core.id2obj(x)
    redo_deletes = True # False may save time but risks

    if '__deleted__' in str(desc):
        if not redo_deletes:
            return 0 # Already deleted, but still hanging out.
    else:
        print('Deleting this object:', x)
    id = AWS_core.obj2id(x)
    ec2c.create_tags(Tags=[{'Key': '__deleted__', 'Value': 'True'}],Resources=[id])
    def lingers(_id):
        return '__deleted__' in str(AWS_core.id2obj(_id))
    try:
        AWS_core.delete(x)
    except Exception as e:
        if 'DependencyViolation' in repr(e):
            who_lingers = list(filter(lingers, xdeps))
            if len(who_lingers)>0: # Stuff that may take a while to delete.
                while True:
                    print('Lingering dependencies on:', id, ':', who_lingers, 'Will retry in a loop untill the deletion works.')
                    try:
                        AWS_core.delete(x)
                        break
                    except Exception as e:
                        pass
                    time.sleep(4)
            else: #Oops the dependency list isn't complete enough.
                raise Exception('DependencyViolation error on:', id, 'despite no reported lingering dependencies.')
        else: #Other kinds of errors.
            raise e
    return int('__deleted__' not in str(desc))

def nuclear_clean(): # DELETE EVERYTHING DANGER!
    confirm = input('Warning: will delete EVERTYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default resources; input y to proceed')
    if confirm.strip().lower() !='y':
        print("Aborted by user.")
        return None
    resc = AWS_query.custom_resources()
    deps = AWS_query.what_needs_these(custom_only=False, include_empty=True)
    n_delete=0
    for k in ['addresses', 'machines', 'subnets', 'rtables','webgates','sgroups','vpcs','kpairs']: # Can the right order avoid needing deps?
        if k not in resc:
            continue
        for x in resc[k]:
            n_delete += dep_check_delete(x, deps[AWS_core.obj2id(x)])
    print('Deleted:', n_delete, 'resources.')
