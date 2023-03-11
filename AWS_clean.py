import boto3, time
import AWS_query, AWS_core

def nuclear_clean():
    # DELETE EVERYTHING DANGER!
    confirm = input('Warning: will delete EVERTYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default resources; input y to proceed')
    if confirm.strip().lower() !='y':
        print("Aborted by user.")
        return None
    resc = AWS_query.get_resources()
    n_delete=0
    for k in ['addresses', 'machines', 'subnets', 'rtables','webgates','sgroups','vpcs','kpairs']: # order matters.
        if k not in resc:
            continue
        for x in resc[k]:
            # Defaults that the account comes with (don't delete these):
            if k == 'rtables' and 'Associations' in x and len(x['Associations'])>0 and x['Associations'][0]['Main']:
                continue
            if k == 'vpcs' and x['IsDefault']:
                continue
            if k == 'sgroups' and x['GroupName']=='default':
                continue # Every VPC makes a default security group.
            print('Deleting this object:', x)
            AWS_core.delete(x)
            n_delete = n_delete+1
    print('Deleted:', n_delete, 'resources.')
