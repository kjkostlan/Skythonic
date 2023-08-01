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

def empower_vm(instance_id, redo_login=False):
    # Give a vm access to the Azure account.
    import time
    from waterworks import plumber, eye_term # Plumbers are debuggy.
    import vm
    from . import Azure_format
    instance_id = Azure_format.obj2id(instance_id)

    tubo = vm.patient_ssh_pipe(instance_id, printouts=True, binary_mode=False)
    tubo.send('echo using_az_login')
    while not eye_term.standard_is_done(tubo.blit(include_history=False)): # Initial startup cmd, not sure if necessary.
        time.sleep(0.25)

    need_to_log_in = True
    if not redo_login:
        tubo.send('az account show -o jsonc')
        while not eye_term.standard_is_done(tubo.blit(include_history=False)):
            time.sleep(0.25)
        txt = tubo.blit()
        need_to_log_in = "Please run 'az login' to setup account." in txt
        if not need_to_log_in:
            if 'environmentName' in txt and 'tenantId' in txt:
                pass
            else:
                raise Exception('Cannot confirm or deny if this vm is "az login"ed or not.')

    if need_to_log_in:
        tubo.send('az login --use-device-code\n')
        print('MANUAL step: paste this URL and code into your browser and then log into Azure if need be.')
        while not eye_term.standard_is_done(tubo.blit(include_history=False)):
            time.sleep(0.25)
    else:
        print('SKIPPING log in step, already logged in. Use redo_login=True to force a redo')

    # Testing:
    core_cmds = ['cd ~/Skythonic', 'python3', 'import subprocess', 'from azure.mgmt.network.models import SecurityRule']
    core_cmds.extend(['print(SecurityRule)'])
    core_cmds.extend(['''_subs_id = subprocess.check_output("az account show --query 'id' -o tsv", shell=True).decode('utf-8').strip()'''])
    core_cmds.extend(['print("The subs_id:", _subs_id)'])
    core_cmds.extend(["print(745*2430 if '-' in _subs_id else None)"])

    response_map = {**plumber.default_prompts(), **{}}
    tests = [['python\nx=2*6\nprint(x)\nquit()', '12']]

    tasks = {'commands':core_cmds}
    p = plumber.Plumber(tubo, tasks, response_map, dt=2.0)
    tubo = p.run()

    if str(745*2430) not in p.blit_all():
        raise Exception('Cannot verify the Python Azure test.')

    return True
