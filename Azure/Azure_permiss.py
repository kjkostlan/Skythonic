# Handles permissions. Does not handle saving keys and other secrets (covert.py does that).
from azure.mgmt.network.models import SecurityRule, SecurityRuleProtocol
from . import Azure_nugget

def admin_policy_id(): # For AWS this is the ARN = Amazon Resource Name
    TODO

def keys_user_has(user_name):
    TODO

def attach_user_policy_once(user_name, policy_id):
    TODO

def create_dangerkey_once(user_name):
    TODO

def authorize_ingress(sgroup_id, cidr, protocol, port0, port1):
    if cidr != '0.0.0.0/0':
        raise Exception('TODO: filtered addresses.')
    proto = getattr(SecurityRuleProtocol, protocol)
    ssh_rule_params = SecurityRule(
        protocol=proto,
        source_port_range="*",
        destination_port_range=str(port0)+'-'+str(port1),
        source_address_prefix=cidr,
        destination_address_prefix="*",  # Allow traffic to any destination
        access="Allow",
        priority=100,
        direction="Inbound",
        name="Allow_"+protocol)

    sgroup_name = sgroup_id.split('/')[-1]
    Azure_nugget.network_client.security_rules.begin_create_or_update(
        Azure_nugget.skythonic_rgroup_name,
        sgroup_name,
        "Allow_"+protocol,
        ssh_rule_params)

def empower_vm(instance_id):
    # Give a vm access to the Azure account.
    # Azure_permiss.empower_vm(Azure_query.get_resources('instances', ids=True)[0])
    import vm
    from . import Azure_format
    instance_id = Azure_format.obj2id(instance_id)
    core_cmds = ['cd ~/Skythonic', 'python', 'from azure.mgmt.network.models import SecurityRule']
    tubo = vm.patient_ssh_pipe(instance_id, printouts=True, binary_mode=False)
    response_map = {**plumber.default_prompts(), **{}}
    tests = [['python\nx=2*6\nprint(x)', '12']]

    p = plumber.Plumber(tubo, [], response_map, core_cmds, tests, dt=2.0)
    tubo = p.run()
    TODO
