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
    def __init__(self, tubo, packages, response_map, other_cmds, test_pairs, fn_override=None, dt=2.0):
        # test_pairs is a vector of [cmd, expected] pairs.
        self.last_restart_time = -1e100 # Wait for it to restart!
        #self.broken_record = 0 # Num times the last err appeared.
        #self.err_counts = {} # TODO: use.
        if test_pairs is None or len(test_pairs)==0:
            test_pairs = []
        if test_pairs == 'default':
            test_pairs = [['echo foo{bar,baz}', 'foobar foobaz']]
        self.dt = dt # Time-step when we need to wait, if the cmd returns faster we will respond faster.
        self.response_map = response_map
        self.fn_override = fn_override
        self.cmd_history = []
        self.tubo = tubo

        self.remaining_packages = list(packages)
        self.remaining_misc_cmds = other_cmds
        self.remaining_tests = test_pairs

        self.completed_packages = []
        self.completed_misc_cmds = []
        self.completed_tests = []

        self.mode = 'green' # Finite state machine.

    def send_cmd(self, _cmd):
        # Preferable than tubo.send since we store cmd_history.
        self.tubo.send(_cmd)
        self.cmd_history.append(_cmd)

    def blit_based_response(self):
        # Responses based on the blit alone, including error handling.
        # None means that there is no need to give a specific response.
        pkg = 'Nonepkg'
        if len(self.remaining_packages)>0:
            pkg = self.remaining_packages[0]
        txt = self.tubo.blit(False)
        w = ptools.ssh_error(txt, self.cmd_history)
        if w is not None:
            return w
        x = ptools.apt_error(txt, pkg, self.cmd_history)
        if x is not None:
            return x
        y = ptools.pip_error(txt, pkg, self.cmd_history)
        if y is not None:
            return y
        z = ptools.get_prompt_response(txt, self.response_map) # Do this last in case there is a false positive that actually is an error.
        if z is not None:
            return z
        return None

    def short_wait(self):
        # Waits up to self.dt for the tubo, hoping that the tubo catches up.
        # Returns True for if the command finished or if a response was caused.
        sub_dt = 1.0/2048.0
        t0 = time.time(); t1 = t0+self.dt
        while time.time()<t1:
            if eye_term.standard_is_done(self.tubo.blit(include_history=False)) or self.blit_based_response():
                return True
            sub_dt = sub_dt*1.414
            ts = min(sub_dt, t1-time.time())
            if ts>0:
                time.sleep(ts)
            else:
                break
        return False

    def step_packages(self):
        # Returns True once installation and testing is completed.
        pkg = self.remaining_packages[0].strip(); ppair = pkg.split(' ')
        if ppair[0] == 'apt':
            _quer = ptools.apt_query; _err = ptools.apt_error; _ver = ptools.apt_verify
            _cmd = 'sudo apt install '+ppair[1]
        elif ppair[0] == 'pip' or ppair[0] == 'pip3':
            _quer = ptools.pip_query; _err = ptools.pip_error; _ver = ptools.pip_verify
            _cmd = 'pip3 install '+ppair[1]
        else:
            raise Exception(f'Package must be of the format "apt foo" or "pip bar" (not "{pkg}"); no other managers are currently supported.')

        if self.mode == 'green':
            self.send_cmd(_cmd)
            self.mode = 'blue'
        elif self.mode == 'blue':
            self.send_cmd(_quer(pkg))
            self.mode = 'orange'
        elif self.mode == 'orange': # Testing B
            self.mode = 'green' # Keep looping the send cmd, send query, verify result loop.
            if _ver(pkg, self.tubo.blit(False)):
                return True
        else:
            self.mode = 'green'
        return False

    def step_tests(self):
        the_cmd, look_for_this = self.remaining_tests[0]
        if self.mode == 'green':
            self.tubo.send(the_cmd)
            self.mode = 'magenta'
        elif self.mode == 'magenta':
            self.mode = 'green' # Another reset loop if we fail.
            txt = self.tubo.blit(False)
            if callable(look_for_this) and look_for_this(txt): # Function or string.
                return True
            elif look_for_this in txt:
                return True
        else:
            self.mode = 'green'
        return False

    def step(self):
        if not self.short_wait():
            return False
        if self.fn_override is not None: # For those occasional situations where complete control of everything is needed.
            if self.fn_override(self):
                return False
        send_this = self.blit_based_response() # These can introject randomally (if i.e. the SSH pipe goes down and need a reboot).
        if callable(send_this): # Sometimes the response is a function of the plumber, not a simple txt prompt.
            send_this(self)
        elif send_this is not None:
            self.send_cmd(send_this)
        elif len(self.remaining_packages)>0:
            if self.step_packages():
                self.completed_packages.append(self.remaining_packages[0])
                self.remaining_packages = self.remaining_packages[1:]
        elif len(self.remaining_misc_cmds)>0:
            # Commands that are ran after installation.
            self.send_cmd(self.self.remaining_misc_cmds[0])
            self.completed_misc_cmds.append(self.remaining_misc_cmds[0])
            self.remaining_misc_cmds = self.remaining_misc_cmds[1:]
        elif len(self.remaining_tests)>0:
            # Extra tests, beyond the specific verifications.
            if self.step_tests():
                self.completed_tests.append(self.remaining_tests[0])
                self.remaining_tests = self.remaining_tests[1:]
        else:
            return True
        return False

    def run(self):
        while not self.step():
            pass
        return self.tubo
