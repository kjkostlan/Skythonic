import boto3, time
import AWS.AWS_query as AWS_query, AWS.AWS_core as AWS_core

def needs_this(x):
    # This can't be deleted because other objects rely on this.
    # (The AWS GUI automates clean up better but still isn't perfect).
    print('X is:', x)
    TODO

def this_needs(x):
    TODO

def nuclear_clean(): # DELETE EVERYTHING DANGER!
    confirm = input('Warning: will delete EVERTYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default resources; input y to proceed')
    if confirm.strip().lower() !='y':
        print("Aborted by user.")
        return None
    resc = AWS_query.custom_resources()
    n_delete=0
    for k in ['addresses', 'machines', 'subnets', 'rtables','webgates','sgroups','vpcs','kpairs']: # order matters.
        if k not in resc:
            continue
        for x in resc[k]:
            print('Deleting this object:', x)
            AWS_core.delete(x)
            n_delete = n_delete+1
    print('Deleted:', n_delete, 'resources.')
