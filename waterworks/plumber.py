# Plumbers deal with pipes that *should be* working but *aren't* working.
import time
import waterworks.eye_term as eye_term
import waterworks.plumber_tools as ptools

def default_prompts():
    # Default line end prompts and the needed input (str or function of the pipe).
    def _super_advanced_linux_shell(): # Newfangled menu where.
        # What button do you press to continue?
        import random
        out = []
        for i in range(256): # We are getting frusterated...
            chs = ['\033[1A','\033[1B','\033[1C','\033[1D','o','O','y','Y','\n']
            out.append(random.choice(chs))
        return ''.join(out)

    return {'Pending kernel upgrade':'\n\n\n','continue? [Y/n]':'Y',
            'continue connecting (yes/no)?':'Y',
            'Which services should be restarted?':_super_advanced_linux_shell()}

#def _restart_parent(tubo):
#    # More robust against TODO
#    tubo.close()
#    t0 = time.time()
#    restart_vm(tubo.machine_id)
#    time.sleep(1.5)
#    tubo = tubo.remake()
#    t1 = time.time()
#    if t1-t0 < 8:
#        raise Exception(f'The restart happened too fast ({t1-t0} s), maybe it was short-circuted?')
#    return tubo

def loop_try(f, f_catch, msg, delay=4):
    # Waiting for something? Keep looping untill it succedes!
    # Useful for some shell/concurrency operations.
    if not callable(f):
        raise Exception(f'{f} which is type {type(f)} is not a callable')
    while True:
        try:
            return f()
        except Exception as e:
            if f_catch(e):
                if callable(msg):
                    msg = msg()
                if len(msg)>0:
                    print('Loop try ('+'\033[90m'+str(e)+'\033[0m'+') '+msg)
            else:
                raise e
        time.sleep(delay)

def with_timeout(tubo, f, timeout=6, message=None):
    # Uses f (f(pipe)=>bool) as an expect with a timeout.
    # Alternative to calling pipe.API with a timeout.
    x = {}
    if message is None:
        message = str(f)
    if f(tubo) or tubo.sure_of_EOF():
        x['reason'] = 'Detected '+str(message)
        return True
    if tubo.drought_len()>timeout:
        raise Exception('Timeout')
    return False

class Plumber():
    def __init__(self, packages, response_map, other_cmds, test_pairs, dt=2.0):
        self.last_restart_time = -1e100 # Wait for it to restart!
        #self.broken_record = 0 # Num times the last err appeared.
        #self.err_counts = {} # TODO: use.
        # test_pairs is a vector of [cmd, expected] pairs.
        if test_pairs is None or len(test_pairs)==0:
            test_pairs = []
        if test_pairs == 'default':
            test_pairs = [['echo foo{bar,baz}', 'foobar foobaz']]
        self.dt = dt
        self.response_map = response_map

        self.remaining_packages = list(packages)
        self.remaining_misc_cmds = other_cmds
        self.remaining_tests = test_pairs

        self.completed_packages = []
        self.completed_misc_cmds = []
        self.completed_tests = []

        self.mode = 'green' # Finite state machine.

    def get_resp_map_response(self, tubo):
        txt_or_none = ptools.get_prompt_response(tubo.blit(False), self.response_map)
        return txt_or_none

    def short_wait(self, tubo):
        # Waits up to self.dt for the tubo, hoping that the tubo catches up.
        # Returns True for if the command finished or if a response was caused.
        sub_dt = 1.0/2048.0
        t0 = time.time(); t1 = t0+self.dt
        while time.time()<t1:
            if eye_term.standard_is_done(tubo.blit(include_history=False)) or self.get_resp_map_response(tubo):
                return True
            sub_dt = sub_dt*1.414
            ts = min(sub_dt, t1-time.time())
            if ts>0:
                time.sleep(ts)
            else:
                break
        return False

    def step_packages(self, tubo):
        # Returns True once installation and testing is completed.
        pkg = self.remaining_packages[0].strip(); ppair = pkg.split(' ')
        if ppair[0] == 'apt':
            _quer = ptools.apt_query; _err = ptools.apt_error; _ver = ptools.apt_verify
            _cmd = 'sudo apt install '+ppair[0]
        elif ppair[0] == 'pip' or ppair[0] == 'pip3':
            _quer = ptools.pip_query; _err = ptools.pip_error; _ver = ptools.pip_verify
            _cmd = 'pip3 install '+ppair[0]
        else:
            raise Exception(f'Package must be of the format "apt foo" or "pip bar" (not "{pkg}"); no other managers are currently supported.')

        if not self.short_wait(tubo): # TODO: timeout if wait too long/dry pipes.
            return False

        if self.mode == 'green':
            tubo.send(_cmd)
            self.mode = 'blue'
            return False
        elif self.mode == 'blue':
            if _err(tubo.blit(False)):
                self.mode = 'green' # Try again.
            else:
                x = self.get_resp_map_response(tubo)
                if x:
                    tubo.send(x)
                else:
                    self.mode = 'yellow'
            return False
        elif self.mode == 'yellow': # Testing A
            if _err(tubo.blit(False)):
                self.mode = 'green' # Try again.
            else:
                tubo.send(_quer(pkg))
            return False
        elif self.mode == 'orange': # Testing B
            if _err(tubo.blit(False)):
                self.mode = 'green' # Try again.
            elif _ver(pkg, tubo.blit(False)):
                self.mode = 'green' # Reset.
                return True # Package has been verified.
            else:
                self.mode = 'green' # Try again.
            return False
        else:
            self.mode = 'green'
            return False

    def step_cmds(self, tubo):
        # Extra cmds.
        if not self.short_wait(tubo): # TODO: timeout if wait too long/dry pipes.
            return False
        x = self.get_resp_map_response(tubo)
        if x:
            tubo.send(x)
            return False
        if self.mode == 'yellow':
            self.mode = 'green'
            return True
        else:
            the_cmd = self.remaining_misc_cmds[0]
            tubo.send(the_cmd)
            self.mode = 'yellow'

    def step_tests(self, tubo):
        if not self.short_wait(tubo): # TODO: timeout if wait too long/dry pipes.
            return False
        x = self.get_resp_map_response(tubo)
        if x:
            tubo.send(x)
            return False
        the_cmd, look_for_this = self.remaining_tests[0]
        if self.mode == 'green':
            tubo.send(the_cmd)
            self.mode = 'yellow'
        elif self.mode == 'yellow':
            self.mode = 'green'
            if look_for_this in tubo.blit(False):
                return True
            else:
                return False

    def step(self, tubo):
        # One step (one sent cmd or restart action) in the attempt to run the cmds, verify packages, etc.
        if len(self.remaining_packages)>0:
            # Attempt to install a package.
            if self.step_packages(tubo):
                self.completed_packages.append(self.remaining_packages[0])
                self.remaining_packages = self.remaining_packages[1:]
        elif len(self.remaining_misc_cmds)>0:
            # Commands that are ran after installation.
            if self.step_cmds(tubo):
                self.completed_misc_cmds.append(self.remaining_misc_cmds[0])
                self.remaining_misc_cmds = self.remaining_misc_cmds[1:]
        elif len(self.remaining_tests)>0:
            if self.step_tests(tubo):
                self.completed_tests.append(self.remaining_tests[0])
                self.remaining_tests = self.remaining_tests[1:]
        else:
            return tubo, True
        return tubo, False

    def run(self, tubo):
        while True:
            tubo, finished = self.step(tubo)
            if finished:
                break
        return tubo
