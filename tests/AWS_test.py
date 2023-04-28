import AWS.AWS_query as AWS_query
import vm

def _cmd_test(the_cmd, look_for, vm_id):
    tubo = vm.patient_ssh_pipe(vm_id, printouts=True)
    tubo.send(the_cmd)
    vm.laconic_wait(tubo, 'testing', timeout_seconds=24)
    x = tubo.blit()
    print('X is:', x)

def test_ssh_jumpbox():
    # Tests: A: is everything installed?
    #        B: Are the scp files actually copied over?
    vm_desc = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if vm_desc is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')

    _cmd_test('ping', 'foo', vm_desc)
    _cmd_test('aws TODO', look_for, vm_desc)
    _cmd_test(cmd, look_for, vm_desc)

    print(vm_desc)
    return False

def test_new_machine_and_jumpbox():
    #Tests: A: Make a machine in the jumpbox and ssh to it.
    #       B: Make a machine OUTSIDE the jumpbox and ssh to it from the jumpbox.

    TODO
