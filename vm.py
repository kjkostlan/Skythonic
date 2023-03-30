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

    #https://unix.stackexchange.com/questions/70895/output-of-command-not-in-stderr-nor-stdout?rq=1
    #https://stackoverflow.com/questions/55762006/what-is-the-difference-between-exec-command-and-send-with-invoke-shell-on-para
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Being permissive is quite a bit easier...
    client.connect(hostname, username=username, key_filename=covert.get_key(instance_id)[1], timeout=timeout)#password=passphrase)

    return eye_term.MessyPipe(client, printouts)

def ez_ssh_cmds(instance_id, bash_cmds, timeout=8, f_poll=None, printouts=True):
    # This abstraction is quite leaky, so *only use when things are very simple and consistent*.
    # f_poll can be a list 1:1 with bash_cmds but this usage is better dealt with paired_ssh_cmds.
    #https://stackoverflow.com/questions/53635843/paramiko-ssh-failing-with-server-not-found-in-known-hosts-when-run-on-we
    #https://stackoverflow.com/questions/59252659/ssh-using-python-via-private-keys
    #https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
    tubo = ssh_pipe(instance_id, timeout=timeout, printouts=printouts)
    _out, _err = tubo.multi_API(bash_cmds, f_poll=f_poll)
    tubo.close()
    return _out, _err, tubo

#def paired_ssh_cmds(instance_id, cmd_pollfn_pairs, timeout=8, printouts=True):
    # Pair each ssh_cmd with the cooresponding expect function.
#    return ez_ssh_cmds(instance_id, [x[0] for x in cmd_pollfn_pairs], timeout=timeout, f_poll=[(x+[None])[1] for x in cmd_pollfn_pairs], printouts=printouts)

def send_files(instance_id, file2contents):
    # None contents are deleted.
    print('Sending files to a machine.')
    # Step1: Open ssh client.
    TODO
    # Step2: Send.

##########################Installation tools####################################

def install_aws(instance_id, user_name, region_name, printouts=True):
    # Installs and tests AWS on a machine, raising Exceptions if the process fails.
    # user_name is NOT the vm's user_name.
    eye_term.loop_try(lambda:ez_ssh_cmds(instance_id, [], timeout=4), lambda e: 'Unable to connect to' in str(e) or 'timed out' in str(e), f'Retrying {instance_id} in a loop (in case the vm is starting up).', delay=4)

    user_id = covert.user_dangerkey(user_name)
    publicAWS_key, privateAWS_key = covert.get_key(user_id)

    tubo = ssh_pipe(instance_id, timeout=8, printouts=printouts); pipes = [tubo]

    _expt = eye_term.basic_expect_fn
    cmd_fn_pairs = [['echo begin', None], ['sudo apt-get update', None],
                    ['sudo apt-get install awscli', lambda pipey: eye_term.standard_is_done(pipey, timeout=128)],
                    ['Y', None], # _expt('~$', timeout=128)
                    ['aws configure', _expt('Access Key ID')],
                    [publicAWS_key, _expt('Secret Access Key')],
                    [privateAWS_key, _expt('region name')],
                    [region_name, _expt('output format')],
                    ['json', None],
                    ['sudo apt-get install python3-pip', lambda pipey: eye_term.standard_is_done(pipey, timeout=128)],
                    ['Y', None], ['pip3 install boto3', None]]

    if printouts:
        print('Beginning installation. Should take about 60 seconds')
    for pair in cmd_fn_pairs:
        tubo.API(pair[0], f_poll=pair[1], dt_min=0.01, dt_max=1)

    reboot = False
    if reboot:
        tubo.close()
        ec2c.reboot_instances(InstanceIds=[inst_id])
        AWS_core.loop_try(lambda:ez_ssh_cmds(inst_id, [], timeout=4), lambda e: 'Unable to connect to' in str(e) or 'timed out' in str(e), f'Waiting for {inst_id} to finish reboot.', delay=4)
        tubo = ssh_pipe(instance_id, timeout=8, printouts=printouts)
        pipes.append(tubo)

    test_cmd_fns = [['echo bash_test', None],
                    ['aws ec2 describe-vpcs --output text', None, 'CIDRBLOCKASSOCIATIONSET'], ['echo python_boto3_test', None],
                    ['python3', None], ['import boto3', None], ["boto3.client('ec2').describe_vpcs()", None, "'Vpcs': [{'CidrBlock'"],
                    ['quit()', None]]

    for pair in test_cmd_fns:
        _out, _err = tubo.API(pair[0], f_poll=pair[1], dt_min=0.01, dt_max=1)
        if len(pair)>2:
            if pair[2] not in _out:
                raise Exception(f'Command {pair[0]} expected to have {pair[2]} in its output which wasnt found. Either a change to the API or an installation error.')
    tubo.close()
    if printouts:
        print('Check the above installation to ensure it works.')
    return pipes
