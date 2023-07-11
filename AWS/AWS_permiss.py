# Handles permissions. Does not handle saving keys and other secrets (covert does that).
import boto3
iam = boto3.client('iam')
ec2c = boto3.client('ec2')

def admin_policy_id(): # For AWS this is the ARN = Amazon Resource Name
    return 'arn:aws:iam::aws:policy/AdministratorAccess'

def keys_user_has(user_name):
    return iam.list_access_keys(UserName=user_name)['AccessKeyMetadata'] #Note: the user access keys are disjoint from the global access keys.

def attach_user_policy_once(user_name, policy_id):
    try: # Made idempotent.
        iam.attach_user_policy(UserName=user_name, PolicyArn=policy_id)
    except Exception as e:
        if 'already exists' not in str(e):
            raise e

def create_dangerkey_once(user_name):
    # These keys are very powerful. Which in security means they are *dangerous*
    kys = keys_user_has(user_name)
    if len(kys)==0: # No keys attached to this user.
        key_dict = iam.create_access_key(UserName=user_name)
        k0 = key_dict['AccessKey']['AccessKeyId']
        k1 = key_dict['AccessKey']['SecretAccessKey']
        return [k0, k1]

def authorize_ingress(sgroup_id, cidr, protocol, port0, port1):
    try:
        ec2c.authorize_security_group_ingress(GroupId=sgroup_id, CidrIp=cidr, IpProtocol=protocol, FromPort=port0, ToPort=port1)
    except Exception as e:
        if 'already exists' not in repr(e):
            raise e
