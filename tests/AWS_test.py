#Tests of AWS bsic querying and resource creation/deletion.
import time, sys
import AWS.AWS_query as AWS_query
import AWS.AWS_setup as AWS_setup
import AWS.AWS_format as AWS_format
import AWS.AWS_clean as AWS_clean
import AWS.AWS_core as AWS_core
import vm, covert
from waterworks import plumber, fittings
import boto3
ec2c = boto3.client('ec2')

def oprint(*args):
    print('\033[93m'+' '.join([str(a) for a in args])+'\033[0m')

class test_results:
    def __init__(self, name=None):
        self.results = []
        self.details = []
        self.names = []
        self.name = name
    def failures(self):
        out = []
        for i in range(len(self.results)):
            if not self.results[i]:
                out.append(self.details[i])
        return out
    def all_passed(self):
        return len(self.failures())==0
    def add_test(self, result, details, name=None):
        self.results.append(result)
        self.details.append(details)
        self.names.append(name)

    def __str__(self):
        fs = self.failures()
        n = len(self.results)
        if len(fs)==0:
            return f'{self.name}: all {n} tests passed!'
        else:
            return f'{self.name}: {len(fs)}/{n} tests failed.'
    def __repr__(self):
        return '<test_results '+str(self)+'>'
    def report(self, verbose=True):
        if self.all_passed():
            return 'No failures to report.'
        lines = []
        for i in range(len(self.results)):
            if not self.results[i]:
                lines.append('FAILED TEST: '+self.names[i]+(': '+str(self.details[i]).replace('\r\n','\n') if verbose else ''))
        return '\n'.join(lines)

def _jump_ssh_cmd_test(results, the_cmd, look_for, vm_id, test_name, printouts=True):
    tubo = vm.patient_ssh_pipe(vm_id, printouts=False)

    #tubo.send('echo AWS_test')
    #import time
    #time.sleep(1.0)
    #print('BLitty:', tubo.blit())
    #TODO

    out, err, _ = tubo.API('echo AWS_test')
    tubo.empty(True)
    tubo.send(the_cmd)
    time.sleep(0.25) # Useful if we don't really need laconic_wait.
    vm.laconic_wait(tubo, 'testing', timeout_seconds=24)
    pipe_dump = tubo.blit()
    tubo.close()
    passed = look_for in pipe_dump
    results.add_test(passed, pipe_dump, test_name)
    if not passed:
        print('Testing cmd on jumpbox failed: '+test_name+' looked for but did not find: '+look_for)

def test_obj2id(printouts=True):
    out = True
    all = AWS_query.get_resources()
    n = 0
    for k in all.keys():
        for x in all[k]:
            the_id =AWS_format.obj2id(x)
            x1 = AWS_format.id2obj(the_id)
            the_id2 = AWS_format.obj2id(x1)
            if printouts:
                if type(x) is not dict:
                    print('Original qurey not a dict:\n', x)
                if type(x1) is not dict and type(x) is dict:
                    print('New query not a dict:\n', x)
                if type(the_id) is not str:
                    print('Converting this to an id failed:\n',x)
                if the_id != the_id2:
                    print('Id round trip not equal:',the_id, the_id2)
                if x != x1:
                    print('Difference in round-trip dict-to-dict; may be a subtle difference not our fault but needs to be OKed by this fn if so.')
            out = out and type(the_id) is str and type(x) is dict and type(x1) is dict and the_id2==the_id and x==x1
            n = n+1
    if n<8:
        raise Exception('Not enough resource to give a good test of this fn.')
    return out

def test_assoc_query(printouts=True):
    # Associations must be symmetric.
    out = True

    # Associations = attachments = connections.
    if printouts:
        print('This test is expensive O(n^2) for large amounts of resources.')
    safe_err_msgs = ['thier own kind', 'directly associated with']
    all = AWS_query.get_resources()
    if printouts:
        print('Total resource counts:', [f'{k}={len(all[k])}' for k in all.keys()])

    AWS_types = ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address','peering','user', 'IAMpolicy']
    has_resources = {}
    resc_count = 0; link_count = 0
    link_map = {} # {id:[resources]}
    err_map = {} #{type_type:error}, only one error at a time. Makes sure reciprocal.
    for ty in AWS_types:
        if printouts:
            print('Working on connections to:', ty)
        for ky in all.keys():
            for x in all[ky]:
                has_resources[ky] = True
                the_id = AWS_format.obj2id(x)
                try:
                    links = AWS_query.assocs(x, ty)
                    if the_id not in link_map:
                        link_map[the_id] = []
                    link_map[the_id].extend(links); link_count = link_count+len(links)
                except Exception as e:
                    bad_err = True
                    for msg in safe_err_msgs:
                        if msg in str(e):
                            _tmp = the_id+ AWS_format.enumr(the_id)+'_'+ty# DEBUG
                            err_map[AWS_format.enumr(the_id)+'_'+ty] = msg
                            bad_err = False
                    if bad_err:
                        raise e
            resc_count += 1
    if printouts:
        print('Done with heavy AWS API usage.')

    if resc_count<10:
        raise Exception('So few resources that this test cannot be trusted.')
    if link_count<12:
        raise Exception('Too few links between resources.')
    if printouts:
        print('Total number of connections:', link_count)
    # Test reciprocity:
    reverse_link_map = {} #Also {id:[resources]}
    for orig_id in link_map.keys():
        for dest_id in link_map[orig_id]:
            if dest_id not in reverse_link_map:
                reverse_link_map[dest_id] = []
            reverse_link_map[dest_id].append(orig_id)

    forward_only = []; reverse_only = []; total_oneways = 0

    kys = set(list(link_map.keys())+list(reverse_link_map.keys()))
    for ky in kys:
        l0 = set(link_map.get(ky,[])); l1 = set(reverse_link_map.get(ky,[]))
        for hanging in l0-l1:
            forward_only.append(hanging)
        for hanging in l1-l0:
            reverse_only.append(hanging)
        if printouts:
            if len(l0-l1)>0:
                total_oneways = total_oneways+len(l0-l1)
                print('One way forward-only connection:', ky, 'to', l0-l1)
            #if len(l1-l0)>0: # Redundent.
            #    print('One way reverse-only connection:', ky, 'from', l1-l0)
    out = out and len(forward_only)+len(reverse_only)==0
    bad_kys = []
    for k in err_map.keys(): # Errors must also have reciprocity
        pieces = k.split('_')
        if has_resources.get(pieces[0], False) and has_resources.get(pieces[1],False): # Only two-way errors.
            k1 = pieces[1]+'_'+pieces[0]
            if err_map[k] != err_map.get(k1,None):
                out = False
                bad_kys.append(k)
                if printouts:
                    print(f'Forward and reverse errs not the same for {k}; {err_map[k]} vs {err_map.get(k1,None)}')

    return out

def test_ssh_jumpbox(printouts=True):
    # Tests: A: is everything installed?
    #        B: Are the scp files actually copied over?
    # (printouts will not print everything, only test failures)
    out = test_results('weaker_jumpbox_tests')
    vm_desc = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if vm_desc is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')

    #tubo = vm.patient_ssh_pipe(vm_desc, printouts=True)
    #tubo.send('cd ~/Skythonic/\npython3\nx=1+2\nprint(x)\nquit()')
    #out, err, _ = tubo.API('echo AWS_test')
    #tubo.empty(True)
    #out, err, _ = tubo.API('cd ~/Skythonic/')
    #tubo.send('python3\nx=1+2\nprint(x)\nquit()')
    #tubo.send('python3')
    #time.sleep(1.0); tubo.update()
    #tubo.send('x = 1+2')
    #time.sleep(1.0); tubo.update()
    #tubo.send('print(x)')
    #time.sleep(1.0); tubo.update()
    #tubo.send('quit()')
    #time.sleep(1.0); tubo.update()
    #tubo.close()
    #return False

    _jump_ssh_cmd_test(out, 'ping', 'ping: usage error: Destination address required', vm_desc, 'Test_ping', printouts)
    _jump_ssh_cmd_test(out, 'aws ec2 describe-subnets', 'BYOC_jumpbox_subnet', vm_desc, 'Test_AWS_descsubnets', printouts)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic\n ls -a', 'eye_term.py', vm_desc, 'test files skythonic', printouts)

    # Delete and re-install Skythonic:
    _jump_ssh_cmd_test(out, 'rm -rf ~/Skythonic \n echo deleted', 'deleted', vm_desc, 'delete and re-download Skythonic', printouts)
    #print('<<Re-Installing Skythonic>>')
    vm.install_Skythonic(vm_desc, '~/Skythonic', printouts=False)
    #print('<<DONE Re-Installing Skythonic>>')
    covert.danger_copy_keys_to_vm(vm_desc, '~/Skythonic', printouts=False)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/softwareDump\n ls -a', 'BYOC_keypair.pem', vm_desc, 'test softwareDump', printouts)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/\npython3\nx=1944+2018\nprint(x)\nquit()', str(1944+2018), vm_desc, 'test py shell', printouts)

    return out

def _new_machine(jump_subnet_id, jump_sgroup_id, machine_name, kpair_name, address_name, private_ip, printouts):
    #if printouts and AWS_query.lingers(AWS_query.get_by_name('machine', machine_name, True)):
    #    print(f'Instance {inst_id} was deleted but is lingering and so a new instance with the same name will be created.')

    #addr0 = AWS_query.get_by_name('address', address_name)
    #if addr0 is not None:
    #    oprint('Address already created, but will still make vm and attach it.')
    vm_ids = [AWS_format.obj2id(vm_obj) for vm_obj in AWS_query.get_resources('machine')]
    oprint('AWS_test__new_machine: All current machines:', vm_ids, 'We want to make a machine with this name:', machine_name)
    for vid in vm_ids:
        tags = AWS_format.tag_dict(vid)
        print('AWS_test__new_machine: Vid:', vid, tags)
        if 'Name' in tags and tags['Name'] == machine_name:
            raise Exception(f'The machine already exists: {machine_name}')


    #inter_we_specify = kwargs['NetworkInterfaces'][0]
    #subnet_id = inter_we_specify['SubnetId']
    #address_we_want = inter_we_specify['PrivateIpAddress']
    #subnet_interfaces = ec2c.describe_network_interfaces(Filters=[{'Name': 'subnet-id','Values': [subnet_id]}])['NetworkInterfaces']
    #for subn_i in subnet_interfaces:
    #    if subn_i['PrivateIpAddress'] == address_we_want and 'Attachment' in subn_i:
    #        iid = subn_i['Attachment']['InstanceId']
    #        print('Tags of instance which is conflict:', AWS_format.tag_dict(iid))


    inst_id = AWS_format.obj2id(AWS_setup.simple_vm(machine_name, private_ip, jump_subnet_id, jump_sgroup_id, kpair_name))
    addr = AWS_core.create_once('address', address_name, printouts, Domain='vpc')

    AWS_setup.wait_and_attach_address(inst_id, addr)
    return inst_id

def _del_machine(machine_name, kpair_name, address_name):
    goners = [AWS_query.get_by_name('machine', machine_name), AWS_query.get_by_name('kpair', address_name),\
              AWS_query.get_by_name('address', address_name)]
    goners = list(filter(lambda x: x is not None, goners))
    AWS_clean.power_delete(goners)

def test_new_machine_from_jumpbox(printouts=True):
    #Tests: A: Make a machine in the jumpbox and ssh to it.
    #       B: Make a machine OUTSIDE the jumpbox and ssh to it from the jumpbox.
    jump_desc = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if jump_desc is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')

    jump_subnet_id = AWS_query.assocs(jump_desc,'subnet')[0]
    jump_sgroup_id = AWS_query.assocs(jump_desc,'sgroup')[0]
    jump_cidr = AWS_format.id2obj(jump_subnet_id)['CidrBlock']

    out = True

    AWS_test = sys.modules['tests.AWS_test'] #Import ourselves!
    def _qu(x):
        return "'"+x+"'"
    def _vm_code(x):
        # exec this locally or ran via ssh on another machine:
        new_code = f'AWS_test._new_machine({_qu(jump_subnet_id)}, {_qu(jump_sgroup_id)}, {_qu(x["vm_name"])}, {_qu(x["kpair_name"])}, {_qu(x["address_name"])}, {_qu(x["private_ip"])}, {printouts})'
        del_code = f'AWS_test._del_machine({_qu(x["vm_name"])}, {_qu(x["kpair_name"])}, {_qu(x["address_name"])})'
        return new_code, del_code

    def clean_xtras(x):
        y = AWS_query.get_by_name('kpair', x['kpair_name'], include_lingers=False)
        if y is not None:
            AWS_core.delete(y)

    delete_skythonic_folder_jbox = True
    if delete_skythonic_folder_jbox:
        oprint('About to delete Skythonic folder on jbox')
        tubo = vm.patient_ssh_pipe(jump_desc, printouts=printouts)
        p = plumber.Plumber(tubo, packages=[], response_map={}, other_cmds=['sudo rm -rf ~/Skythonic'], test_pairs=[], fn_override=None, dt=2.0)
        p.run()
        covert.danger_copy_keys_to_vm(jump_desc, skythonic_root_folder='~/Skythonic', printouts=True, preserve_dest=False)
        oprint('Done deleting Skythonic jbox folder and copying our keys back over there.')

    out = test_results('stronger_jumpbox_tests')
    oprint('Updating Skythonic on jumpbox...')
    vm.update_Skythonic(jump_desc, '~/Skythonic', printouts=printouts)
    oprint('...done update Skythonic')

    x0 = {'kpair_name':'testing_vm_key_name', 'vm_name':'testing_vm_AWS_test', 'address_name':'testing_address', 'private_ip':'10.200.250.111'}

    for x in [x0]:
        clean_xtras(x)

    for x in [x0]:
        if not fittings.in_cidr(x['private_ip'], jump_cidr):
            raise Exception(f'Private ip = {private_ip} not in Cidr = {jump_cidr}')

    def _start_py_code(msg):
        return ['echo '+msg, 'cd ~/Skythonic', 'python3']

    def _import_code():
        return ['import AWS.AWS_core as AWS_core', 'import AWS.AWS_vm as AWS_vm', 'import vm', 'import AWS.AWS_query as AWS_query', 'import tests.AWS_test as AWS_test', 'import waterworks.plumber as plumber']

    #Test A: SSH to jumpbox; make a machine in the jumpbox; ssh to it from jumpbox.
    oprint('Deleting test machine if it was created')
    exec(_vm_code(x0)[1])
    vm_desc = AWS_query.get_by_name('machine', x0['vm_name'])
    if vm_desc is not None:
        raise Exception('The test machine failed to end up deleted.')

    _tmp = ec2c.describe_key_pairs(Filters=[{'Name': 'key-name', 'Values': [x0['kpair_name']]}])['KeyPairs']
    if len(_tmp)>0:
        raise Exception('The key pair did not get deleted.')

    debug_extra_create_delete_cycle = False
    if debug_extra_create_delete_cycle:
        oprint('DEBUG extra create + delete; remove once testing of this testing code is done.')
        exec(_vm_code(x0)[0]) # DEBUG.
        exec(_vm_code(x0)[1]) # DEBUG.
        print('DEBUG done.')

    cmds = [l for l in _start_py_code('test vm ssh jmake')+_import_code()]
    cmds.append('print("MILESTONE HERE: About to make the machine *from* the jumpbox")')
    cmds.append(_vm_code(x0)[0])
    cmds.append(f"test_desc = AWS_query.get_by_name('machine', {_qu(x0['vm_name'])})")
    cmds.append('print("ABOUT TO GO DEEPER")')
    cmds.append('tubo = vm.patient_ssh_pipe(test_desc, printouts=False)')
    cmds.append('jump2new_vm = ["tmp=$(curl http://169.254.169.254/latest/meta-data/instance-id)", "echo $tmp"]')
    cmds.append('p = plumber.Plumber(tubo, packages=[], response_map={}, other_cmds=jump2new_vm, test_pairs=[], fn_override=None, dt=2.0)')
    cmds.append('p.run()')
    cmds.append('print(p.blit_all())')

    tubo = vm.patient_ssh_pipe(jump_desc, printouts=printouts)
    p = plumber.Plumber(tubo, packages=[], response_map={}, other_cmds=cmds, test_pairs=[], fn_override=None, dt=2.0)
    p.run()

    dump = p.blit_all()
    vm_desc = AWS_query.get_by_name('machine', x0['vm_name'])
    if vm_desc is None:
        raise Exception('The jumpbox failed to produce the vm.')
    vm_id = AWS_format.obj2id(vm_desc)
    out = out and vm_id in dump
    oprint(f'Checking if the jumpbox making another machine worked {vm_id}; {vm_id in dump}')

    for x in [x0]:
        clean_xtras(x)

    return False

    test_id_gold = AWS_format.obj2id(AWS_query.get_by_name('machine', x0['vm_name']))
    out = out and test_id_gold in str(test_id_blabla)

    #test_id_blabla = [tubo.API(f'tubo.API({_qu(l)})') for l in _start_py_code('test vm deeper lev')+_import_code()+['print(AWS_vm.our_vm_id())']][-1]
    #print('test id bla bla bla:', test_id_blabla)
    # Note: we do not test jumpbox to cloud shell file xfer b/c ssh to cloud shell is a bit esoteric.

    exec(_vm_code(x0)[1])
    oprint('test_id_blabla:', test_id_blabla)
    return False

    #Test 0: Query the ID of our machine in cloud shell (should be none) vs jumpbox:
    cloud_shell_id = AWS_vm.our_vm_id()
    jump_id = AWS_format.obj2id(jump_desc)
    tubo = vm.patient_ssh_pipe(jump_desc, printouts=printouts)
    [tubo.API(l) for l in _start_py_code('test vm ssh ID0')+_import_code()]
    jump_id_blabla = tubo.API('print(AWS_vm.our_vm_id())')
    tubo.API('quit()')
    out = out and cloud_shell_id is None and jump_id in str(jump_id_blabla)
    oprint('ID CHECK:', out)
    return False

    #for i in range(8):
    #    time.sleep(1.0)

    exec(_vm_code[x0][1])

    return False

    _del_machine(x0)
    TODO
    inst_id = _new_machine(x0)
    tubo = vm.patient_ssh_pipe(inst_id, printouts=False)
    x = tubo.API('echo foo', f_polls=None, timeout=8.0, dt_min=0.001, dt_max=2.0)
    oprint(tubo.blit())
    _del_machine(x0)

    #Test B: Make a machine OUTSIDE the jumpbox and ssh to it from the jumpbox.
    # (this will require copying keys).
    #TODO

    return False
