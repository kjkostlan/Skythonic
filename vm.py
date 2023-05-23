# Tools for keeping track of virtual machines, such as the login keys
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import paramiko, time, os
import file_io
import AWS.AWS_format as AWS_format
import eye_term, covert
import boto3
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def bprint(*txt):
    # Use our own color to make things more clear.
    txt = ' '.join([str(t) for t in txt])
    print('\033[94m'+txt+'\033[0m', end='')

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
    bprint('Warning: TODO: implement this auto-update Skythonic function.')

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
    return tubo

def _default_prompts():
    # Default line end prompts and the needed input (str or function of the pipe).

    def _super_advanced_linux_shell(tubo):
        # What button do you press to continue?
        import random
        for i in range(256): # We are getting frusterated...
            chs = ['\033[1A','\033[1B','\033[1C','\033[1D','o','O','y','Y','\n']
            ch = random.choice(chs)
            tubo.send(ch, suppress_input_prints=True, include_newline=False)
            tubo.update()
        return tubo.API('random_bashing_done')

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
            bprint(f'WARNING: timeout on {proc_name}')

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

def ssh_proc_args(instance_id):
    # Splat into into MessyPipe.
    username = 'ubuntu'; hostname = get_ip(instance_id) #username@hostname
    key_filename = covert.get_key(instance_id)[1]
    return{'username':username,'hostname':hostname, 'key_filename':key_filename}

def patient_ssh_pipe(instance_id, printouts=True, return_bytes=False, use_file_objs=False):
    # Ensures it is started and waites in a loop.
    instance_id = AWS_format.obj2id(instance_id)
    in_state = AWS_format.id2obj(instance_id)['State']['Name']
    if in_state == 'terminated':
        raise Exception(f'The instance {instance_id} has been terminated and can never ever be used again.')
    ec2c.start_instances(InstanceIds=[instance_id])

    pargs = ssh_proc_args(instance_id)

    def _err_catch(e):
        if 'Unable to connect to' in str(e) or 'timed out' in str(e) or 'encountered RSA key, expected OPENSSH key' in str(e) or 'Connection reset by peer' in str(e):
            return True
        if 'Error reading SSH protocol banner' in str(e):
            # This is a more serious error where we throw our hands up and just restart the machine.
            if printouts:
                bprint('The dreaded banner error. Restarting and hope for the best!')
            ec2c.reboot_instances(InstanceIds=[instance_id])
            return True
        return False # Unrecognized errors are thrown.

    out = eye_term.MessyPipe(proc_type='ssh', proc_args=pargs, printouts=printouts, return_bytes=return_bytes, use_file_objs=use_file_objs, f_loop_catch=_err_catch)
    out.machine_id = instance_id
    return out

def ez_ssh_cmds(instance_id, bash_cmds, f_polls=None, printouts=True):
    # This abstraction is quite leaky, so *only use when things are very simple and consistent*.
    # f_poll can be a list 1:1 with bash_cmds but this usage is better dealt with paired_ssh_cmds.
    #https://stackoverflow.com/questions/53635843/paramiko-ssh-failing-with-server-not-found-in-known-hosts-when-run-on-we
    #https://stackoverflow.com/questions/59252659/ssh-using-python-via-private-keys
    #https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _out, _err, _ = tubo.multi_API(bash_cmds, f_polls=f_polls)
    tubo.close()
    if printouts:
        bprint('\nWe closed the SSH\n')
    return _out, _err, tubo

def send_files(instance_id, file2contents, remote_root_folder, printouts=True):
    # None contents are deleted.
    # Both local or non-local paths allowed.
    # Automatically creates folders.
    instance_id = AWS_format.obj2id(instance_id)
    if printouts:
        bprint(f'Sending {len(file2contents)} files to {remote_root_folder} {instance_id}')
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
    bprint('WARNING: TODO fix this code to allow deletions and check if the files really were transfered.')
    return tubo

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
    if instance_id is None:
        raise Exception('None instance.')
    if type(instance_id) is list or type(instance_id) is tuple: # Many at once should be faster in parallel?
        instance_ids = [AWS_format.obj2id(iid) for iid in instance_id]
    else:
        instance_ids = [AWS_format.obj2id(instance_id)]
    ec2c.reboot_instances(InstanceIds=instance_ids)

########################Installation of packages################################

def _to_pipe(inst_or_pipe, printouts=True): # Idempotent.
    if type(inst_or_pipe) is eye_term.MessyPipe:
        if inst_or_pipe.closed:
            return inst_or_pipe.remake()
        return inst_or_pipe
    return patient_ssh_pipe(inst_or_pipe, printouts=printouts)

def _test_pair(tubo, t_cmds, expected, prompts=None, printouts=True, timeout=12):
    if prompts is None:
        prompts = _default_prompts()
    for i in range(2):
        if i==1:
            if printouts:
                bprint('Maybe a restart will help.')
            tubo.close(); restart_vm(tubo.machine_id)
            tubo = tubo.remake()
            raise Exception(f'Even after a restart, the package {package_name} does not work properly.')
        elif i==1:
            raise Exception('Cannot (a restart may or may not help; pass in an instance_id instead of a pipe to do so).')
        x0 = tubo.blit()
        tubo = _cmd_list_fixed_prompt(tubo, t_cmds, prompts, lambda cmd:timeout)
        x1 = tubo.blit(); x = x1[len(x0):]
        if len(list(filter(lambda r: r not in x, expected))) == 0:
            break # All test results are hit.
        if i==1:
            raise Exception(f'Even after a restart, this test failed.')
    return tubo

def update_apt(inst_or_pipe, printouts=True):
    # Updating apt with a restart seems to be the most robust option.
    #https://askubuntu.com/questions/521985/apt-get-update-says-e-sub-process-returned-an-error-code
    if inst_or_pipe is None:
        raise Exception('None instance/pipe')
    cmds = ['sudo rm -rf /tmp/*', 'sudo mkdir /tmp', 'sudo apt-get update', 'sudo apt-get upgrade', 'echo done']
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    x0 = tubo.blit()
    #if prompts is None: # No need to have this as an actual argument.
    prompts = _default_prompts()
    _cmd_list_fixed_prompt(tubo, cmds, prompts, lambda cmd:64.0)

    # Verification of installation:
    x1 = tubo.blit(); x = x1[len(x0):]
    if 'Reading state information... Done'.lower() not in x.lower():
        raise Exception('update_apt has failed for some reason.')

    if type(inst_or_pipe) is eye_term.MessyPipe:
        tubo.close()
        eye_term.log_pipes.append(tubo)
    return tubo

def ez_apt_package(inst_or_pipe, package_name, prompts=None, timeout=64, printouts=True):
    # Installation.
    # TODO: Use "sudo dpkg --configure -a" when needed.
    if prompts is None:
        prompts = _default_prompts()
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    def _core_fn(tubo):
        tubo = _to_pipe(tubo, printouts=printouts)
        x0 = tubo.blit()
        _cmd_list_fixed_prompt(tubo, [f'sudo apt install {package_name}', 'echo testing_install', f'dpkg -s {package_name}'], prompts, lambda cmd:timeout)
        x1 = tubo.blit(); x = x1[len(x0):]
        return x
    def _err_fn(x):
        if 'install ok installed' in x:
            return False
        elif 'Unable to locate package' in x:
            return True
        else:
            raise Exception(f'Unable to confirm installation of {package_name}')

    x = _core_fn(tubo)
    if not _err_fn(x):
        return tubo
    if printouts:
        bprint('Cant find, maybe we need an apt update?')
    tubo = update_apt(tubo, printouts)
    if not _err_fn(x):
        return tubo
    if printouts:
        bprint('Cant find, maybe we need an apt update?')
    tubo = update_apt(tubo, printouts)
    if not _err_fn(x):
        return tubo
    bprint('Maybe a restart after an apt-update will help.')
    tubo.close()
    restart_vm(tubo.machine_id)
    tubo = tubo.remake()
    if not _err_fn(x):
        return tubo
    if 'sudo dpkg --configure -a" when needed' in tubo.blit():
        raise Exception('TODO: figure out when to use sudo dpkg --configure -a which seems to be needed')
    raise Exception(f'The package {package_name} cannot be found, we cant restart without knowning the instance_id.')

def ez_pip_package(inst_or_pipe, package_name, break_sys_packages='polite', timeout=64, prompts=None, printouts=True):
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    x0 = tubo.blit()
    powstr = ' --break-system-packages' if break_sys_packages.lower()=='yes' else ''
    if prompts is None:
        prompts = _default_prompts()
    _cmd_list_fixed_prompt(tubo, [f'pip install {package_name}'+powstr], prompts, lambda cmd:timeout)
    x1 = tubo.blit(); x = x1[len(x0):]

    if printouts and break_sys_packages.lower() == 'yes':
        bprint('WARNING: using --break-system-packages option')
    if 'Successfully installed '+package_name in x or 'Requirement already satisfied' in x:
        pass
    elif "Command 'pip' not found" in x or 'pip: command not found' in x:
        tubo = ez_apt_package(tubo, 'python3-pip', timeout=timeout, printouts=printouts)
        tubo = ez_apt_package(tubo, 'python-is-python3', timeout=timeout, printouts=printouts)
    elif 'No matching distribution found for '+package_name in x:
        raise Exception(f'No matching pip for {package_name}')
    elif '--break-system-packages' in x and 'This environment is externally managed' in x and break_sys_packages.lower() != 'yes':
        if break_sys_packages == 'polite':
            ez_pip_package(inst_or_pipe, package_name, printouts=printouts, break_sys_packages='yes', timeout=timeout, prompts=prompts)
        elif not break_sys_packages or break_sys_packages.lower() == 'no' or break_sys_packages.lower() == 'deny' or break_sys_packages.lower() == 'forbidden':
            raise Exception('Externally managed env error and break_sys_packages arg set to "forbidden"')
    else:
        raise Exception(f'Cannot verify pip installation for: {package_name}')

    if type(inst_or_pipe) is not eye_term.MessyPipe:
        tubo.close()
    return tubo

def install_package(inst_or_pipe, package_name, package_manager, printouts=True):
    # Includes configuration for common packages; package_manager = 'apt' or 'pip'
    ### Per-package configurations:
    if inst_or_pipe is None:
        raise Exception('None instance/pipe')
    renames = {'ping':'iputils-ping','apache':'apache2', 'python':'python3-pip', 'python3':'python3-pip',
               'aws':'awscli', 'netcat':'netcat-openbsd'}

    xtra_cmds = {}
    xtra_cmds['apache2'] = ['sudo apt install libcgi-session-perl',
            'sudo systemctl enable apache2',
            'cd /etc/apache2/mods-enabled',
            'sudo ln -s ../mods-available/cgi.load cgi.load',
            'sudo ln -s ../mods-available/ssl.conf ssl.conf',
            'sudo ln -s ../mods-available/ssl.load ssl.load',
            'sudo ln -s ../mods-available/socache_shmcb.load socache_shmcb.load',
            'cd /etc/apache2/sites-enabled',
            'sudo ln -s ../sites-available/default-ssl.conf default-ssl.conf']
    xtra_cmds['python3-pip'] = ['sudo apt-get install python-is-python3']
    xtra_cmds['aws-cli'] = ['aws configure']

    xtra_code = {}
    xtra_code['aws-cli'] = lambda tubo: ez_pip_package(tubo, 'boto3', printouts=True, break_sys_packages='polite', timeout=64)

    timeouts = {'aws-cli':128, 'python3-pip':128}
    timeout = timeouts.get(package_name, 64)

    tests = {}
    tests['iputils-ping'] = [['ping -c 1 localhost'],['0% packet loss']]
    tests['apache2'] = [['sudo service apache2 start', 'curl -k http://localhost', 'sudo service apache2 stop'], ['<div class="section_header">', 'Apache2']]
    tests['python3-pip'] = [['python3', 'print(id)', 'quit()'],['<built-in function id>']]
    tests['aws-cli'] = [['aws ec2 describe-vpcs --output text',
                         'python3', 'import boto3', "boto3.client('ec2').describe_vpcs()", 'quit()']]

    extra_prompts = {}

    package_name = renames.get(package_name.lower(), package_name.lower()) # Lowercase, 0-9 -+ only.
    if package_name=='aws-cli': # This one requires using boto3 so is buried in this conditional.
        bprint('aws-cli is a HEAVY installation. Should take about 5 min.')
        region_name = boto3.session.Session().region_name
        publicAWS_key, privateAWS_key = covert.get_key(user_id)
        # The null prompts (empty string) may help to keep ssh alive:
        extra_prompts['aws-cli'] = {'Access Key ID':publicAWS_key, 'Secret Access Key':privateAWS_key,
                                    'region name':region_name, 'output format':'json',
                                    'Get:42':'', 'Unpacking awscli':'',
                                    'Setting up fontconfig':'', 'Extracting templates from packages':'',
                                    'Unpacking libaom3:amd64':''}

    ### Core installation:
    package_name = package_name.lower().replace('_','-')
    package_name = renames.get(package_name, package_name) # Lowercase, 0-9 -+ only.
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    prompts = {**_default_prompts(), **extra_prompts.get(package_name,{})}

    package_manager = package_manager.lower().replace('pip3','pip')
    if package_manager not in ['apt','pip']:
        raise Exception('Package manager must be "apt" or "pip".')
    if package_manager=='apt':
        tubo = ez_apt_package(tubo, package_name, printouts=printouts, timeout=timeout, prompts=prompts)
    elif package_manager=='pip':
        tubo = ez_pip_package(tubo, package_name, printouts=printouts, timeout=timeout, prompts=prompts)
    xtra = xtra_cmds.get(package_name,None)
    if xtra is not None:
        tubo = _cmd_list_fixed_prompt(tubo, xtra_cmds.get(package_name,None), _default_prompts(), lambda cmd:timeout)

    f = xtra_code.get(package_name, None)
    if f is not None:
        tubo = f(tubo)
    t = tests.get(package_name, None)
    if t is None:
        if printouts:
            bprint(f'Warning: no does-it-work test for {package_name}')
    else:
        t_cmds = t[0]; t_results = t[1]
        tubo = _test_pair(tubo, t_cmds, t_results, prompts=None, printouts=True)
    if type(inst_or_pipe) is not eye_term.MessyPipe:
        tubo.close()
    return tubo

###############Installation of our packages and configs#########################

def update_Skythonic(inst_or_pipe, remote_root_folder='~/Skythonic', printouts=True):
    #Updates skythonic with what is stored locally (on the machine calling this fn).
    # Basically the same as install_custom_package(inst_or_pipe, skythonic) but with no testing.
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)

    file2contents = file_io.folder_load('.', allowed_extensions='.py')
    for k in list(file2contents.keys()):
        if file_io.dump_folder.split('/')[-1] in k:
            del file2contents[k]
    tubo = send_files(tubo.machine_id, file2contents, remote_root_folder, printouts=printouts)
    return tubo

def install_custom_package(inst_or_pipe, package_name, printouts=True):
    # Install packages which we make.
    # We choose the folders here.
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    package_name = package_name.lower().replace('_','-')
    file2contents = {}
    dest_folder = ''
    test_pair = None
    extra_prompts = {}
    cmd_list = None
    xtra_code = None
    timeout = 12

    ### Per package information:
    if package_name == 'skythonic': # Local copy.
        file2contents = file_io.folder_load('.', allowed_extensions='.py')
        for k in list(file2contents.keys()):
            if file_io.dump_folder.split('/')[-1] in k:
                del file2contents[k]
        dest_folder = '~/Skythonic'
        test_pair = [['cd Skythonic', 'python3 \nimport file_io\nprint(file_io)\n', 'quit()' ,'echo done'], ['module']]
        xtra_code = lambda tubo: ez_pip_package(tubo, 'paramiko', printouts=printouts, break_sys_packages='polite', timeout=64)
    elif package_name=='host-list':
        dest_folder = '/etc'
        cmd_list = [f'cd {dest_folder}', 'sudo wget https://developmentserver.com/BYOC/Resources/hosts.txt', 'sudo mv -f hosts.txt hosts', f"sudo sh -c 'echo jump > {dest_folder}/hostname'"]
    elif package_name=='app-server':
        cmds_list = ['cd /usr/local/bin',
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
    elif package_name=='web-server':
        cmds_list = ['cd /var/www/html', 'sudo wget https://developmentserver.com/BYOC/Resources/CiscoWorldLogo.jpg',
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
    else:
        raise Exception(f'Unrecognized custom package {package_name}')

    ### Core installation:
    if file2contents is not None:
        send_files(tubo.machine_id, file2contents, remote_root_folder=dest_folder, printouts=printouts)
    prompts = {**_default_prompts(), **extra_prompts}
    if cmd_list is not None:
        tubo = _cmd_list_fixed_prompt(tubo, cmd_list, prompts, lambda cmd:timeout)
    if xtra_code is not None:
        tubo = xtra_code(tubo)
    if test_pair is not None:
        tubo = _test_pair(tubo, test_pair[0], test_pair[1], prompts=None, printouts=True)

    return tubo
