import boto3
import AWS_query

def nuclear_clean():
    # DELETE EVERYTHING DANGER!
    confirm = input('Warning: will delete EVERTYTHING in the WHOLE ACCOUNT (not just the lab) leaving just the default VPC; input y to proceed')
    if confirm.strip().lower() !='y':
        print("Aborted by user.")
        return None
    resc = AWS_query.get_resources()
    TODO
    # Don't delete default VPC since it comes with a fresh account.
