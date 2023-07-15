# Handles permissions. Does not handle saving keys and other secrets (covert.py does that).

def admin_policy_id(): # For AWS this is the ARN = Amazon Resource Name
    TODO

def keys_user_has(user_name):
    TODO

def attach_user_policy_once(user_name, policy_id):
    TODO

def create_dangerkey_once(user_name):
    TODO

def authorize_ingress(sgroup_id, cidr, protocol, port0, port1):
    TODO
