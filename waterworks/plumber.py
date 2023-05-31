# Plumbers deal with pipes that *should be* working but *aren't* working.
import time
import waterworks.eye_term as eye_term

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

def _last_line(txt):
    return txt.replace('\r\n','\n').split('\n')[-1]

def get_prompt_response(txt, response_map):
    # "Do you want to continue (Y/n); input AWS user name; etc"
    lline = _last_line(txt.strip()) # First try the last line, then try everything since the last cmd ran.
    # (A few false positive inputs is unlikely to cause trouble).
    for otxt in [lline, txt]:
        for k in response_map.keys():
            if k in otxt:
                if callable(response_map[k]):
                    return response_map[k](otxt)
                return response_map[k]

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

def cmd_list_fixed_prompt(tubo, cmds, response_map, timeout=16):
    TODO #get_prompt_response(txt, response_map)
    x0 = tubo.blit()
    def _check_line(_tubo, txt):
        lline = _last_line(_tubo.blit(include_history=False))
        return txt in lline
    line_end_poll = lambda _tubo: looks_like_blanck_prompt(_last_line(_tubo.blit(include_history=False)))
    f_polls = {'_vanilla':line_end_poll}

    for k in response_map.keys():
        f_polls[k] = lambda _tubo, txt=k: _check_line(_tubo, txt)
    for cmd in cmds:
        _out, _err, poll_info = tubo.API(cmd, f_polls, timeout=timeout)
        while poll_info and poll_info != '_vanilla':
            txt = response_map[poll_info]
            if type(txt) is str:
                _,_, poll_info = tubo.API(txt, f_polls, timeout=timeout)
            else:
                txt(tubo); break
    x1 = tubo.blit(); x = x1[len(x0):]
    return tubo, x


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

def apt_error(txt):
    # Scan for errors in apt.
    # If no error is detected, returns None.
    msgs = {'Unable to acquire the dpkg frontend lock':'dpkg lock uh ho.',
            'sudo dpkg --configure -a" when needed':'Mystery --configure -a bug',
            'Unable to locate package':'Cant locate',
            'has no installation candidate':'The other cant locate',
            'Some packages could not be installed. This may mean that you have requested an impossible situation':'Oh no not the "impossible situation" error!'}
    for k in msgs.keys():
        if k in txt:
            return msgs[k]
    return None

def pip_error(txt):
    # Scan for errors in pip.
    # TODO: better handling of --break-system-packages option
    if "Command 'pip' not found" in x or 'pip: command not found' in txt:
        return 'pip not found'
    if 'No matching distribution found for' in txt:
        return 'package not found'
    if '--break-system-packages' in txt and 'This environment is externally managed' in txt:
        return 'externally managed env'
    return None

def ssh_error(e_txt):
    # Scan for errors in creating the ssh pipe (if making the pipe causes an Exception)
    msgs = {'Unable to connect to':'Unable to connect', 'timed out':'timeout',\
            'encountered RSA key, expected OPENSSH key':'RSA/OPENSSH keys',
            'Connection reset by peer':'connection reset',\
            'Error reading SSH protocol banner':'Oh no! the *banner* error!'}
    for k in msgs.keys():
        if k in e_txt:
            return msgs[k]
    return None

def apt_query(pkg):
    package_name = pkg.split(' ')[-1]
    return f'dpkg -s {package_name}'

def pip_query(pkg):
    #https://askubuntu.com/questions/588390/how-do-i-check-whether-a-module-is-installed-in-python-and-install-it-if-needed
    package_name = pkg.split(' ')[-1]
    return f'python3\nimport sys\nimport {package_name}\nx=456*789 if "{package_name}" in sys.modules else 123*456\nprint(x)\nquit()'

def apt_verify(pkg, txt):
    # Is the pkg installed properly (run after apt_query).
    if 'install ok installed' in txt or 'install ok unpacked' in txt:
        return True
    if 'is not installed' in txt:
        return False

def pip_verify(pkg, txt):
    # Is the pkg installed properly (run after apt_query).
    package_name = pkg.split(' ')[-1]
    if 'Successfully installed ' in txt or 'Requirement already satisfied' in txt:
        return True # Queries by re-running the installation cmd
    if str(456*789) in txt:
        return True # Our Python-based queries.
    if str(123*456) in txt or f"ModuleNotFoundError: No module named '{package_name}'" in txt:
        return False # Our Python-based queries.
    return None

def pipe_test():
    # A simple test for a bash (or ssh to bash) pipe bieng open.
    return ['echo foo{bar,baz}', 'foobar foobaz']

class Plumber():
    def __init__(self, packages, response_map, other_cmds, test_pairs, dt=2.0):
        self.last_restart_time = -1e100 # Wait for it to restart!
        #self.broken_record = 0 # Num times the last err appeared.
        #self.err_counts = {} # TODO: use.
        # test_pairs is a vector of [cmd, expected] pairs.
        if test_pairs is None or len(test_pairs)==0:
            test_pairs = []
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
        txt_or_none = get_prompt_response(tubo.blit(False), self.response_map)
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
            _quer = apt_query; _err = apt_error; _ver = apt_verify
            _cmd = 'sudo apt install '+ppair[0]
        elif ppair[0] == 'pip' or ppair[0] == 'pip3':
            _quer = pip_query; _err = pip_error; _ver = pip_verify
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
