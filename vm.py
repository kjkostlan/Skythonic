# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import paramiko
import file_io
import AWS.AWS_format as AWS_format
import eye_term, covert

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

    # Step1: Open ssh client.
    TODO
    # Step2: Send.

##########################Installation tools####################################

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
            _,_, poll_info = tubo.API(response_map[poll_info], f_polls, timeout=timeout_f(cmd))

def install_aws(instance_id, user_name, region_name, printouts=True):
    # Installs and tests AWS on a machine, raising Exceptions if the process fails.
    # user_name is NOT the vm's user_name.
    eye_term.loop_try(lambda:ez_ssh_cmds(instance_id, [], timeout=4), lambda e: 'Unable to connect to' in str(e) or 'timed out' in str(e), f'Retrying ssh to {instance_id} in a loop (in case the vm is starting up).', delay=4)

    user_id = covert.user_dangerkey(user_name)
    publicAWS_key, privateAWS_key = covert.get_key(user_id)

    tubo = ssh_pipe(instance_id, timeout=8, printouts=printouts); pipes = [tubo]

    print('Beginning installation. Should take about 60 seconds')
    line_end_prompts = {'Which services should be restarted?':'-a','continue? [Y/n]':'Y',
                        'Access Key ID':publicAWS_key, 'Secret Access Key':privateAWS_key,
                        'region name':region_name, 'output format':'json'}
    line_endings = {'$','>'}
    cmds = ['echo begin', 'sudo apt-get update', 'sudo apt-get install awscli', 'aws configure',
            'sudo apt-get install ssh',
            'sudo apt-get install python3-pip', 'pip3 install boto3', 'echo done']
    _cmd_list_fixed_prompt(tubo, cmds, line_end_prompts, lambda cmd:128 if cmd else 6.0)

    reboot = False
    if reboot:
        tubo.close()
        ec2c.reboot_instances(InstanceIds=[inst_id])
        AWS_core.loop_try(lambda:ez_ssh_cmds(inst_id, [], timeout=4), lambda e: 'Unable to connect to' in str(e) or 'timed out' in str(e), f'Waiting for {inst_id} to finish reboot.', delay=4)
        tubo = ssh_pipe(instance_id, timeout=8, printouts=printouts)
        pipes.append(tubo)

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
        print('Check the above installation to ensure it works.')
    return pipes
