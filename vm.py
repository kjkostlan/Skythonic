# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import paramiko, time, os
import file_io
import AWS.AWS_format as AWS_format
import eye_term, covert
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
    raise Exception('Cannot find the ip for: '+AWS_format.obj2id(x))

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    print('Warning: TODO: implement VM updates.')

try: # Precompute.
    _imgs
except:
    _imgs = [None]
def ubuntu_aim_image():
    # Attemts to return the latest "stable" minimal AIM Ubuntu image.
    if _imgs[0] is None:
        filters = [{'Name':'name','Values':['*ubuntu*']}, {'Name': 'state', 'Values': ['available']}]
        filters.append({'Name':'architecture','Values':['x86_64']})
        imgs0 = ec2c.describe_images(Filters=filters, Owners=['amazon'])['Images']
        filter_fn = lambda d:d.get('Public',False) and d.get('ImageType',None)=='machine' and 'pro' not in d.get('Name',None) and 'minimal' in d.get('Name',None)
        imgs = list(filter(filter_fn, imgs0))
        _imgs[0] = {'Ubuntu':imgs}
    imgs = _imgs[0]['Ubuntu']

    if len(imgs)==0:
        raise Exception('No matching images to this body of filters.')
    imgs_sort = list(sorted(imgs,key=lambda d:d.get('CreationDate', '')))
    return imgs_sort[-1]['ImageId']

###############################Command line#####################################

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

def _default_prompts():
    # Default line end prompts and the needed input (str or function of the pipe).
    return {'Pending kernel upgrade':'\n\n\n','continue? [Y/n]':'Y',
            'continue connecting (yes/no)?':'Y',
            'Which services should be restarted?':_super_advanced_linux_shell} # Newfangled menu.

def laconic_wait(tubo, proc_name, timeout_seconds=24):
    # For cmds that don't return much. TODO: get working on windows.
    timeout_seconds = int(timeout_seconds)
    for i in range(timeout_seconds): # TODO: set the timeout based on the number/size of files.
        tubo.send('echo foo{bar,baz}')
        time.sleep(1); tubo.update()
        if 'foobar foobaz' in tubo.blit(True):
            break
        if i==timeout_seconds-1 and printouts:
            print(f'WARNING: timeout on {proc_name}')

def ssh_bash(instance_id, join_arguments=True):
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
    instance_id = AWS_format.obj2id(instance_id)
    in_state = AWS_format.id2obj(instance_id)['State']['Name']
    if in_state == 'terminated':
        raise Exception(f'The instance {instance_id} has been terminated and can never ever be used again.')
    ec2c.start_instances(InstanceIds=[instance_id])
    _err = lambda e: 'Unable to connect to' in str(e) or 'timed out' in str(e) or 'encountered RSA key, expected OPENSSH key' in str(e) or 'Connection reset by peer' in str(e) # Not sure why the error.
    try:
        return ssh_pipe(instance_id, timeout=8, printouts=True)
    except Exception as e:
        print('Starting wait cycle because SSH not available this moment, error:', str(e))
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
    if printouts:
        print('\nWe closed the SSH\n')
    return _out, _err, tubo

def send_files(instance_id, file2contents, remote_root_folder, printouts=True):
    # None contents are deleted.
    # Both local or non-local paths allowed.
    # Automatically creates folders.
    if printouts:
        print(f'Sending {len(file2contents)} files to {remote_root_folder} {instance_id}')
    instance_id = AWS_format.obj2id(instance_id)
    ez_ssh_cmds(instance_id,[f'mkdir -p {eye_term.quoteless(remote_root_folder)}'], printouts=printouts)

    #https://linuxize.com/post/how-to-use-scp-command-to-securely-transfer-files/
    #scp file.txt username@to_host:/remote/directory/
    public_ip = get_ip(instance_id)

    tmp_dump = os.path.realpath(file_io.dump_folder+'/_vm_tmp_dump')
    file_io.empty_folder(tmp_dump, ignore_permiss_error=False, keeplist=None)

    # Enclosing folders that need to be made:
    folders = set()
    for k in file2contents.keys():
        pieces = k.replace('\\','/').split('/')
        for j in range(len(pieces)-1):
            folders.add('/'.join(pieces[0:j]))
    folders = list(folders); folders.sort(key=lambda x:len(x.split('/')))

    # Make, from shortest to longest:
    for k in file2contents.keys():
        file_io.fsave(tmp_dump+'/'+k, file2contents[k])

    pem_fname = covert.get_key(instance_id)[1]
    #https://serverfault.com/questions/330503/scp-without-known-hosts-check
    tmp_dump1 = tmp_dump+'/*'
    scp_cmd = f'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r -i {eye_term.quoteless(pem_fname)} {eye_term.quoteless(tmp_dump1)} ubuntu@{public_ip}:{eye_term.quoteless(remote_root_folder)}'

    tubo = eye_term.MessyPipe('shell', None, printouts=printouts)
    tubo.send(scp_cmd)

    # Getting the output from the scp command is ... tricky. Use echos instead:
    laconic_wait(tubo, 'scp upload '+instance_id, timeout_seconds=24)

    file_io.power_delete(tmp_dump)
    print('WARNING: TODO fix this code to allow deletions and check if the files really were transfered.')
    return tubo, []

def download_remote_file(instance_id, remote_path, local_dest_folder=None, printouts=True, bin_mode=False):
    # Downalods to a local path or simply returns the file contents.
    save_here = os.path.realpath(file_io.dump_folder+'/_vm_tmp_dump/') if local_dest_folder is None else local_dest_folder
    file_io.power_delete(save_here)
    file_io.make_folder(save_here)

    public_ip = get_ip(instance_id); pem_fname = covert.get_key(instance_id)[1]
    tubo = eye_term.MessyPipe('shell', None, printouts=printouts)
    #https://unix.stackexchange.com/questions/188285/how-to-copy-a-file-from-a-remote-server-to-a-local-machine
    scp_cmd = f'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r -i {eye_term.quoteless(pem_fname)} ubuntu@{public_ip}:{eye_term.quoteless(remote_path)} {eye_term.quoteless(save_here)}'

    tubo.send(scp_cmd)
    laconic_wait(tubo, 'scp download '+instance_id, timeout_seconds=24)
    out = file_io.fload(save_here+remote_path.replace('\\','/').split('/')[-1], bin_mode=bin_mode)

    if local_dest_folder is None:
        file_io.power_delete(save_here)

    return out, tubo

def restart_vm(instance_id):
    if type(instance_id) is list or type(instance_id) is tuple: # Many at once should be faster in parallel?
        instance_ids = [AWS_format.obj2id(iid) for iid in instance_id]
    else:
        instance_ids = [AWS_format.obj2id(instance_id)]
    ec2c.reboot_instances(InstanceIds=instance_ids)

########################Installation of packages################################

class Ireport: # Installation report.
    def __init__(self, pipes, errors):
        self.pipes = pipes
        self.errors = errors
    def append(self, append_this):
        self.pipes = self.pipes+append_this.pipes
        self.errors = self.errors+append_this.errors
    def error_free(self):
        return len(self.errors)==0

def _super_advanced_linux_shell(tubo):
    # It breaks automation scripts. But why should it?
    import random
    for i in range(256): # We are getting frusterated...
        chs = ['\033[1A','\033[1B','\033[1C','\033[1D','o','O','y','Y','\n']
        ch = random.choice(chs)
        tubo.send(ch, suppress_input_prints=True, include_newline=False)
        tubo.update()
    return tubo.API('random_bashing_done')

def update_Apt(instance_id, printouts=True, full_restart_here=True): # Restarting may reduce the error rate.
    # Update the apt, which can help.
    #https://askubuntu.com/questions/521985/apt-get-update-says-e-sub-process-returned-an-error-code
    cmds = ['sudo rm -rf /tmp/*', 'sudo mkdir /tmp', 'sudo apt-get update', 'sudo apt-get upgrade', 'echo foo', 'echo bar', 'echo baz']#, 'sudo dpkg --configure -a']#, anti_massive_interaction]
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:64.0)
    tubo.close()
    if full_restart_here:
        if printouts:
            print(f'Rebooting {instance_id} as part of the "apt update" process')
        ec2c.reboot_instances(InstanceIds=[instance_id])

    return Ireport([tubo],[]), lambda: print('TODO: test update_Apt') # TODO: error reporting here instead of empty list.

def install_Ping(instance_id, printouts=True):
    # Ping is not installed with the minimal linux.
    #https://www.atlantic.net/vps-hosting/how-to-install-and-use-the-ping-command-in-linux/
    cmds = ['sudo apt-get install iputils-ping', 'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    if 'not found' in str(tubo.history_contents):
        errs.append('Ping produces a not found eror.')

    def _test(printouts=True):
        tubo = patient_ssh_pipe(instance_id, printouts=printouts)
        _cmd_list_fixed_prompt(tubo, ['ping', 'echo done'], _default_prompts(), lambda cmd:32.0)
        tubo.close()

    return Ireport([tubo], errs), _test

def install_mysqlClient(instance_id, printouts=True):
    cmds = ['sudo apt install mysql-client',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    def _test(printouts=True):
        print('TODO: Test mwsqlClient install')

    return Ireport([tubo], errs), _test

def install_netTools(instance_id, printouts=True):
    cmds = ['sudo apt install net-tools',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    if 'not found' in str(tubo.history_contents):
        errs.append('Ping produces a not found eror.')

    def _test(printouts=True):
        print('TODO: Test netTools install')

    return Ireport([tubo], errs), _test

def install_netcat(instance_id, printouts=True):
    cmds = ['sudo apt install netcat',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    if 'not found' in str(tubo.history_contents):
        errs.append('Ping produces a not found eror.')

    def _test(printouts=True):
        print('TODO: Test netcat install')

    return Ireport([tubo], errs), _test

def install_vim(instance_id, printouts=True):
    cmds = ['sudo apt install vim',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    if 'not found' in str(tubo.history_contents):
        errs.append('Ping produces a not found eror.')

    def _test(printouts=True):
        print('TODO: Test vim install')

    return Ireport([tubo], errs), _test

def install_apache(instance_id, printouts=True):
    cmds = ['sudo apt install apache2 libcgi-session-perl',
            'sudo systemctl enable apache2',
            'cd /etc/apache2/mods-enabled',
            'sudo ln -s ../mods-available/cgi.load cgi.load',
            'sudo ln -s ../mods-available/ssl.conf ssl.conf',
            'sudo ln -s ../mods-available/ssl.load ssl.load',
            'sudo ln -s ../mods-available/socache_shmcb.load socache_shmcb.load',
            'cd /etc/apache2/sites-enabled',
            'sudo ln -s ../sites-available/default-ssl.conf default-ssl.conf',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []

    def _test(printouts=True):
        print('TODO: Test apache install')

    return Ireport([tubo], errs), _test

def install_tcpdump(instance_id, printouts=True):
    cmds = ['sudo apt install tcpdump',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    if 'not found' in str(tubo.history_contents):
        errs.append('Ping produces a not found eror.')

    def _test(printouts=True):
        print('TODO: Test tcpdump install')

    return Ireport([tubo], errs), _test

def install_iputilsPing(instance_id, printouts=True):
    cmds = ['sudo apt install iputils-ping',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:32.0)
    tubo.close()

    errs = []
    if 'not found' in str(tubo.history_contents):
        errs.append('Ping produces a not found eror.')

    def _test(printouts=True):
        print('TODO: Test iputils-ping install')

    return Ireport([tubo], errs), _test

def install_python3(instance_id, printouts=True):
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, ['sudo apt-get install python3-pip', 'sudo apt-get install python-is-python3'],\
                           _default_prompts(), lambda cmd:64 if 'install' in cmd else 12.0)
    def _test():
        test_cmd_fns = [['echo bash_test'],
                        ['python3'], ['print(id)','<built-in function id>'],
                        ['quit()']]
        tubo = patient_ssh_pipe(instance_id, printouts=True)
        errs = []
        for pair in test_cmd_fns:
            _out, _err, _ = tubo.API(pair[0], f_polls=None, dt_min=0.01, dt_max=1)
            if len(pair)>1:
                if pair[1] not in _out:
                    warn_txt = f'WARNING: Command {pair[0]} expected to have {pair[1]} in its output which wasnt found. Either a change to the API or an installation error.'
                    print(warn_txt) if printouts else ''
                    errs.append(warn_txt)
        tubo.close()
        return errs
    return Ireport([tubo], []), _test

def install_AWS(instance_id, user_name, region_name, printouts=True):
    # Installs and tests AWS+boto3 on a machine, raising Exceptions if the process fails.
    # user_name is NOT the vm's user_name.
    instance_id = AWS_format.obj2id(instance_id)
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

    tubo = patient_ssh_pipe(instance_id, printouts=printouts)

    null_prompts = {'Get:42':'', 'Unpacking awscli':'',
                    'Setting up fontconfig':'', 'Extracting templates from packages':'',
                    'Unpacking libaom3:amd64':''}
    aws_prompts = {'Access Key ID':publicAWS_key, 'Secret Access Key':privateAWS_key,
                   'region name':region_name, 'output format':'json'}
    line_end_prompts = {**_default_prompts(), **null_prompts, **aws_prompts}

    _cmd_list_fixed_prompt(tubo, ['sudo apt-get install awscli'], _default_prompts(), lambda cmd:64 if 'install' in cmd else 12.0)
    if "sudo dpkg --configure -a" in str(tubo.history_contents): # Error condition and one-time fix.
        _cmd_list_fixed_prompt(tubo, ['sudo dpkg --configure -a', 'sudo apt-get install awscli'], _default_prompts(), lambda cmd:64 if 'install' in cmd else 12.0)

    tubo = _reset(tubo, full_restart=False)

    _cmd_list_fixed_prompt(tubo, ['aws configure'], line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)

    # Discussion on vs 'pip3 install boto3' vs 'python3 -m pip install boto3':
        #https://stackoverflow.com/questions/59997065/pip-python-normal-site-packages-is-not-writeable
    pip_cmds = ['python3 -m pip install boto3', 'pip install --upgrade awscli', 'pip install --upgrade botocore'] # Upgrades may avoid errors.
    _cmd_list_fixed_prompt(tubo, pip_cmds, line_end_prompts, lambda cmd:64 if 'install' in cmd else 12.0)
    tubo = _reset(tubo, full_restart=False)
    tubo.close(); pipes.append(tubo)
    def _test(printouts=True):
        test_cmd_fns = [['echo bash_test'],
                        ['aws ec2 describe-vpcs --output text', 'CIDRBLOCKASSOCIATIONSET'], ['echo python_boto3_test'],
                        ['python3'], ['import boto3'], ["boto3.client('ec2').describe_vpcs()", "'Vpcs': [{'CidrBlock'"],
                        ['quit()']]
        tubo = patient_ssh_pipe(instance_id, printouts=True)
        errs = []
        for pair in test_cmd_fns:
            _out, _err, _ = tubo.API(pair[0], f_polls=None, dt_min=0.01, dt_max=1)
            if len(pair)>1:
                if pair[1] not in _out:
                    warn_txt = f'WARNING: Command {pair[0]} expected to have {pair[1]} in its output which wasnt found. Either a change to the API or an installation error.'
                    print(warn_txt) if printouts else ''
                    errs.append(warn_txt)
        tubo.close()
        return errs

    errs = _test(printouts=printouts)
    if printouts:
        t1 = time.time(); print('Elapsed time on installation (s):',t1-t0)
        print('Check the above test to ensure it works.')
    return Ireport(pipes, errs), _test

###############Installation of our packages and configs#########################

def install_Skythonic(instance_id, remote_root_folder='~/Skythonic', printouts=True):
    # Installs the *local* copy of Skythonic to the instance_id.
    file2contents = file_io.folder_load('.', allowed_extensions='.py')
    for k in list(file2contents.keys()):
        if file_io.dump_folder.split('/')[-1] in k:
            del file2contents[k]
    tubo, errs = send_files(instance_id, file2contents, remote_root_folder, printouts=printouts)

    def _test():
        tubo = patient_ssh_pipe(instance_id, printouts=True)
        _cmd_list_fixed_prompt(tubo, ['cd Skythonic', 'python3 \nimport file_io\nprint(file_io)\n', 'quit()' ,'echo done'], _default_prompts(), lambda cmd:32.0)
        tubo.close()

    return Ireport([tubo], errs), _test

def install_hostList(instance_id, printouts=True):
    cmds = ['cd /etc', 'sudo wget https://developmentserver.com/BYOC/Resources/hosts.txt', 'sudo mv -f hosts.txt hosts', "sudo sh -c 'echo jump > /etc/hostname'"]
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:8.0)
    def _test(printouts=True):
        print('TODO: test this.')
    return Ireport([tubo], []), _test

def install_appServerCmds(instance_id, printouts=True):
    cmds = ['cd /usr/local/bin',
            'sudo wget https://developmentserver.com/BYOC/Resources/addserver.txt',
            'sudo wget https://developmentserver.com/BYOC/Resources/addserver.pl.txt',
            'sudo wget https://developmentserver.com/BYOC/Resources/rmserver.txt',
            'sudo wget https://developmentserver.com/BYOC/Resources/rmserver.pl.txt',
            'sudo mv addserver.txt addserver',
            'sudo mv addserver.pl.txt addserver.pl',
            'sudo mv rmserver.txt rmserver',
            'sudo mv rmserver.pl.txt rmserver.pl',
            'sudo chmod a+x *',
            "sudo sh -c 'echo app1 > /etc/hostname'"]
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:8.0)
    def _test(printouts=True):
        print('TODO: test install_appServerCmds.')
    return Ireport([tubo], []), _test

def install_webServerCmds(instance_id, printouts=True):
    cmds = ['cd /var/www/html', 'sudo wget https://developmentserver.com/BYOC/Resources/CiscoWorldLogo.jpg',
            'sudo wget https://developmentserver.com/BYOC/Resources/index.html.txt',
            'sudo mv index.html.tx index.html',
            'cd /usr/lib/cgi-bin',
            'sudo wget https://developmentserver.com/BYOC/Resources/index.cgi.txt',
            'sudo wget https://developmentserver.com/BYOC/Resources/qr1.cgi.txt',
            'sudo mv index.cgi.txt index.cgi',
            'sudo mv qr1.cgi.txt qr1.cgi',
            'sudo chmod a+x *',
            'sudo a2enmod cgid',
            "sudo sh -c 'echo web1 >/etc/hostname'",
            'sudo systemctl restart apache2',
            'systemctl status apache2.service --no-pager',
            'sudo apachectl configtest',
            'journalctl -xeu apache2.service --no-pager',
            'echo done']
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _cmd_list_fixed_prompt(tubo, cmds, _default_prompts(), lambda cmd:8.0)
    def _test(printouts=True):
        print('TODO: test install_webServerCmds.')
    return Ireport([tubo], []), _test
