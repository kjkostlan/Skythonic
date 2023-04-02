# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import paramiko
import file_io
import AWS.AWS_format as AWS_format
import eye_term, covert
import time
import eye_term
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def get_ip(x): # Address or machine.
    if type(x) is str and '.' in x: # Actually an ip address.
        return x
    if type(x) is str:
        x = AWS_format.id2obj(x)
    if 'PublicIp' in x:
        return x['PublicIp']
    if 'PublicIpAddress' in x:
        return x['PublicIpAddress']
    raise Exception('Cannot find the ip for:'+AWS_format.obj2id(x))

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    print('Warning: TODO: implement VM updates.')

###############################Command line#####################################

def ssh_cmd(instance_id, join_arguments=False):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal and is safe to yes if it is a VM you create in your account.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python
    instance_id = AWS_format.obj2id(instance_id)
    public_ip = get_ip(instance_id)
    out = ['ssh', '-i', covert.get_key(instance_id)[1], 'ubuntu@'+str(public_ip)]
    if join_arguments:
        out[2] = '"'+out[2]+'"'
        return ' '.join(out)
    else:
        return out

def ssh_pipe(instance_id, timeout=8, printouts=True):
    # Returns a MessyPipe which can be interacted with. Don't forget to close() it.
    username = 'ubuntu'; hostname = get_ip(instance_id) #username@hostname
    key_filename = covert.get_key(instance_id)[1]
    return eye_term.MessyPipe('ssh', {'username':username,'hostname':hostname, 'timeout':timeout, 'key_filename':key_filename}, printouts)

def patient_ssh_pipe(instance_id, printouts=True):
    # Ensures it is started and waites in a loop.
    ec2c.start_instances(InstanceIds=[instance_id])
    _err = lambda e: 'Unable to connect to' in str(e) or 'timed out' in str(e) or 'encountered RSA key, expected OPENSSH key' in str(e) or 'Connection reset by peer' in str(e) # Not sure why the error.
    return eye_term.loop_try(lambda:ssh_pipe(instance_id, timeout=8, printouts=printouts),
                             _err , f'ssh waiting for {instance_id} to be ready.', delay=4)

def ez_ssh_cmds(instance_id, bash_cmds, timeout=8, f_polls=None, printouts=True):
    # This abstraction is quite leaky, so *only use when things are very simple and consistent*.
    # f_poll can be a list 1:1 with bash_cmds but this usage is better dealt with paired_ssh_cmds.
    #https://stackoverflow.com/questions/53635843/paramiko-ssh-failing-with-server-not-found-in-known-hosts-when-run-on-we
    #https://stackoverflow.com/questions/59252659/ssh-using-python-via-private-keys
    #https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
    tubo = ssh_pipe(instance_id, timeout=timeout, printouts=printouts)
    _out, _err, _ = tubo.multi_API(bash_cmds, f_polls=f_polls)
    tubo.close()
    return _out, _err, tubo

#def paired_ssh_cmds(instance_id, cmd_pollfn_pairs, timeout=8, printouts=True):
    # Pair each ssh_cmd with the cooresponding expect function.
#    return ez_ssh_cmds(instance_id, [x[0] for x in cmd_pollfn_pairs], timeout=timeout, f_poll=[(x+[None])[1] for x in cmd_pollfn_pairs], printouts=printouts)

def send_files(instance_id, file2contents):
    # None contents are deleted.
    print(f'Specifying {len(file2contents)} files on a machine.')

    #https://linuxize.com/post/how-to-use-scp-command-to-securely-transfer-files/
    #scp file.txt username@to_host:/remote/directory/
    instance_id = AWS_format.obj2id(instance_id)
    public_ip = get_ip(instance_id)
    out = ['ssh', '-i', covert.get_key(instance_id)[1], 'ubuntu@'+str(public_ip)]
    # Step1: Open ssh client.
    TODO
    # Step2: Send?

##########################Installation tools####################################

def _super_advanced_linux_shell(tubo):
    # It breaks automation scripts. But why should it?
    import random
    for i in range(256): # We are getting frusterated...
        chs = ['\033[1A','\033[1B','\033[1C','\033[1D','o','O','y','Y','\n']
        ch = random.choice(chs)
        tubo.send(ch, suppress_input_prints=True, include_newline=False)
        tubo.update()
    return tubo.API('random_bashing_done')

def _cmd_list_fixed_prompt(tubo, cmds, response_map, timeout_f):
    def check_line(_tubo, txt):
        lline = eye_term.last_line(_tubo)
        if len(txt)<6: # Heuristic.
            return lline.strip().endswith(txt)
        else:
            return txt in lline
    line_end_poll = lambda _tubo: check_line(_tubo, '$') or check_line(_tubo, '>')
    f_polls = {'_vanilla':line_end_poll}

    for k in response_map.keys():
        f_polls[k] = lambda _tubo, txt=k: check_line(_tubo, txt)
    for cmd in cmds:
        _out, _err, poll_info = tubo.API(cmd, f_polls, timeout=timeout_f(cmd))
        if 'awscli not found' in str(_err): # TODO: handle this error.
            raise Exception('AWS CLI not found error can randomally appear. Try running the setup script again.')
        while poll_info and poll_info != '_vanilla':
            txt = response_map[poll_info]
            if type(txt) is str:
                _,_, poll_info = tubo.API(txt, f_polls, timeout=timeout_f(cmd))
            else:
                txt(tubo); break

def install_aws(instance_id, user_name, region_name, printouts=True):
    # Installs and tests AWS on a machine, raising Exceptions if the process fails.
    # user_name is NOT the vm's user_name.
    # (installs python3, boto3, curl).
    user_id = covert.user_dangerkey(user_name)
    publicAWS_key, privateAWS_key = covert.get_key(user_id)
    pipes = []

    def _reset(tubo, full_restart):
        tubo.close(); pipes.append(tubo)
        if full_restart:
            print('Rebooting machine: '+instance_id)
            ec2c.reboot_instances(InstanceIds=[instance_id])
        tubo1 = patient_ssh_pipe(instance_id, printouts=printouts)
        return tubo1

    print('Beginning installation. Should take about 5 min')
    t0 = time.time()

    tubo = patient_ssh_pipe(instance_id, printouts=printouts);

    line_end_prompts = {'Pending kernel upgrade':'\n\n\n','continue? [Y/n]':'Y',
                        'Which services should be restarted?':_super_advanced_linux_shell, # Try to work through this newfangled menu.
                        'Access Key ID':publicAWS_key, 'Secret Access Key':privateAWS_key,
                        'region name':region_name, 'output format':'json',
                        # Null prompts may protect us from connection reset:
                        'Get:42':'',
                        'Unpacking awscli':'',
                        'Setting up fontconfig':'',
                        'Extracting templates from packages':''}
    line_endings = {'$','>'}
    #anti_massive_interaction ='sudo NEEDRESTART_MODE=a apt-get dist-upgrade --yes' #https://askubuntu.com/questions/1367139/apt-get-upgrade-auto-restart-services
    #https://askubuntu.com/questions/521985/apt-get-update-says-e-sub-process-returned-an-error-code
    cmds = ['sudo rm -rf /tmp/*', 'sudo mkdir /tmp', 'sudo apt-get update', 'sudo apt-get upgrade', 'echo foo', 'echo bar', 'echo baz']#, 'sudo dpkg --configure -a']#, anti_massive_interaction]
    _cmd_list_fixed_prompt(tubo, cmds, line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)
    full_restart_here = True #Inconsistent where errors sometimes happen.
    tubo = _reset(tubo, full_restart=full_restart_here)

    _cmd_list_fixed_prompt(tubo, ['sudo apt-get install awscli'], line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)
    if "sudo dpkg --configure -a" in str(tubo.history_contents):
        _cmd_list_fixed_prompt(tubo, ['sudo dpkg --configure -a', 'sudo apt-get install awscli'], line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)

    tubo = _reset(tubo, full_restart=False)

    _cmd_list_fixed_prompt(tubo, ['sudo apt-get install python3-pip'], line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)
    tubo = _reset(tubo, full_restart=False)

    _cmd_list_fixed_prompt(tubo, ['aws configure'], line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)

    pip_cmd = 'pip3 install boto3'
    pip_cmd = 'python3 -m pip install boto3' # Is this any better? https://stackoverflow.com/questions/59997065/pip-python-normal-site-packages-is-not-writeable
    _cmd_list_fixed_prompt(tubo, [pip_cmd], line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)
    tubo = _reset(tubo, full_restart=False)

    test_cmd_fns = [['echo bash_test'],
                    ['aws ec2 describe-vpcs --output text', 'CIDRBLOCKASSOCIATIONSET'], ['echo python_boto3_test'],
                    ['python3'], ['import boto3'], ["boto3.client('ec2').describe_vpcs()", "'Vpcs': [{'CidrBlock'"],
                    ['quit()']]

    for pair in test_cmd_fns:
        _out, _err, _ = tubo.API(pair[0], f_polls=None, dt_min=0.01, dt_max=1)
        if len(pair)>1:
            if pair[1] not in _out:
                raise Exception(f'Command {pair[0]} expected to have {pair[1]} in its output which wasnt found. Either a change to the API or an installation error.')
    tubo.close(); pipes.append(tubo)
    if printouts:
        t1 = time.time(); print('Elapsed time on installation (s):',t1-t0)
        print('Check the above test to ensure it works.')
    return pipes
