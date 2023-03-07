import boto3
import AWS_query, AWS_core

def nuclear_clean():
    # DELETE EVERYTHING DANGER!
    confirm = input('Warning: will delete EVERTYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default VPC; input y to proceed')
    if confirm.strip().lower() !='y':
        print("Aborted by user.")
        return None
    resc = AWS_query.get_resources()
    for k in resc.keys():
        for x in resc[k]:
            if k != 'vpcs' or not x['IsDefault']: # Don't delete the default VPC since it comes with a fresh account.
                AWS_core.delete(x)
