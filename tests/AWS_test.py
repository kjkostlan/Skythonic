import time
import AWS.AWS_query as AWS_query
import AWS.AWS_setup as AWS_setup
import AWS.AWS_format as AWS_format
import AWS.AWS_clean as AWS_clean
import AWS.AWS_core as AWS_core
import vm, covert

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

def _jump_ssh_cmd_test(results, the_cmd, look_for, vm_id, test_name):
    print('Testing cmd on jumpbox: '+test_name)
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

def test_obj2id():
    out = True
    all = AWS_query.get_resources()
    n = 0
    for k in all.keys():
        for x in all[k]:
            the_id =AWS_format.obj2id(x)
            x1 = AWS_format.id2obj(the_id)
            out = out and type(the_id) is str and type(x) is dict and type(x1) is dict
            n = n+1
    if n<8:
        raise Exception('Not enough resource to give a good test of this fn.')
    return out

def test_assoc_query():
    # Associations = attachments = connections.
    print('This test is expensive O(n^2) for large amounts of resources.')
    safe_err_msgs = ['thier own kind', 'directly associated with']
    all = AWS_query.get_resources()
    types = ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address','peering','user']
    resc_count = 0; link_count = 0
    link_map = {} # {type: {id:[resources]}}
    err_map = {} #{type_type:error}, only one error at a time. Makes sure reciprocal.
    for ty in types:
        link_map[ty] = {}
        for ky in all.keys():
            for x in all[ky]:
                id = AWS_format.obj2id(x)
            try:
                links = AWS_query.assocs(x, ty)
                link_map[ty][id] = links; link_count = link_count+len(links)
            except Exception as e:
                bad_err = True
                for msg in safe_err_msgs:
                    if msg in str(e):
                        err_map[AWS_format.enumr(id)+'_'+ty] = msg
                        bad_err = False
                if bad_err:
                    raise e
            resc_count += 1

    if resc_count<10:
        raise Exception('So few resources that this test cannot be trusted.')
    if link_count<12:
        raise Exception('Too few links between resources.')

    # Test reciprocity:
    reverse_link_map = {} #Also {type: {id:[resources]}}
    for ty in types:
        reverse_link_map[ty] = {}
        for id in link_map[ty].keys():
            for dest_id in link_map[ty][id]:
                if dest_id not in reverse_link_map[ty]:
                    reverse_link_map[ty][dest_id] = []
                reverse_link_map[ty][dest_id].append(id)

    out = True

    forward_only = {} #{type: [id]}
    reverse_only = {}
    for ty in types:
        forward_only[ty] = []
        reverse_only[ty] = []
        kys = set(list(link_map[ty].keys())+list(reverse_link_map[ty].keys()))
        for ky in kys:
            l0 = set(link_map[ty].get(ky,[])); l1 = set(reverse_link_map[ty].get(ky,[]))
            for hanging in l0-l1:
                forward_only[ty].append(hanging)
            for hanging in l1-l0:
                reverse_only[ty].append(hanging)
        out = out and len(forward_only[ty])+len(reverse_only[ty])==0

    bad_kys = []
    for k in err_map.keys(): # Errors must also have reciprocity
        pieces = k.split('_')
        k1 = pieces[1]+'_'+pieces[0]
        if err_map[k] != err_map.get(k1,None):
            out = False
            bad_kys.append(k)

    return out

def test_ssh_jumpbox():
    # Tests: A: is everything installed?
    #        B: Are the scp files actually copied over?
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

    _jump_ssh_cmd_test(out, 'ping', 'ping: usage error: Destination address required', vm_desc, 'Test_ping')
    _jump_ssh_cmd_test(out, 'aws ec2 describe-subnets', 'BYOC_jumpbox_subnet', vm_desc, 'Test_AWS_descsubnets')

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic\n ls -a', 'eye_term.py', vm_desc, 'test files skythonic')

    # Delete and re-install Skythonic:
    _jump_ssh_cmd_test(out, 'rm -rf ~/Skythonic \n echo deleted', 'deleted', vm_desc, 'delete and re-download Skythonic')
    #print('<<Re-Installing Skythonic>>')
    vm.install_Skythonic(vm_desc, '~/Skythonic', printouts=False)
    #print('<<DONE Re-Installing Skythonic>>')
    covert.danger_copy_keys_to_vm(vm_desc, '~/Skythonic', printouts=False)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/softwareDump\n ls -a', 'BYOC_keypair.pem', vm_desc, 'test softwareDump')

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/\npython3\nx=1944+2018\nprint(x)\nquit()', str(1944+2018), vm_desc, 'test py shell')

    return out

def test_new_machine_and_jumpbox():
    #Tests: A: Make a machine in the jumpbox and ssh to it.
    #       B: Make a machine OUTSIDE the jumpbox and ssh to it from the jumpbox.
    jump_desc = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if jump_desc is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')

    out = test_results('stronger_jumpbox_tests')
    vm.install_Skythonic(jump_desc, '~/Skythonic', printouts=False)

    # First just test non-jumpbox vm:
    vm_name = 'testing_vm'
    subnet_id = AWS_format.obj2id(AWS_query.get_by_name('subnet','BYOC'+'_'+'jumpbox'+'_subnet'))
    if subnet_id is None:
        raise Exception('Cannot find subnet')
    securitygroup_id = AWS_format.obj2id(AWS_query.get_by_name('sgroup','BYOC'+'_'+'jumpbox'+'_sGroup'))
    if securitygroup_id is None:
        raise Exception('Cannot find sgroup')
    private_ip = '10.100.250.111' # Must be in the subnet cidr.
    key_name = 'testing_vm_key_name'
    inst_id = AWS_query.get_by_name('machine', vm_name)
    if AWS_query.lingers(inst_id):
        print(f'Instance {inst_id} was deleted but is lingering and so a new instance with the same name will be created.')
        inst_id = None
    if inst_id is None:
        inst_id = AWS_format.obj2id(AWS_setup.simple_vm(vm_name, private_ip, subnet_id, securitygroup_id, key_name))
        addr = AWS_core.create_once('address', 'testing_address', True, Domain='vpc')
        AWS_setup.wait_and_attach_address(inst_id, addr)
    else:
        print('inst Tags:', AWS_format.tag_dict(inst_id))
        addr = AWS_query.get_by_name('address', 'testing_address')
    try:
        tubo = vm.patient_ssh_pipe(inst_id, printouts=False)
    except Exception as e:
        if 'has been terminated' in str(e):
            AWS_core.delete(inst_id)
            raise Exception('Zombie machine has been deleted. Try running this again')
        else:
            raise e

    AWS_core.delete(inst_id)
    AWS_clean.dep_check_delete(addr, xdeps=None)
    #AWS_core.delete(addr)

    #Test A: Make a machine in the jumpbox and ssh to it.
