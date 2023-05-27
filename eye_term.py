# TODO: Make a mini project (and remove all aws code).
# Shell is centered around a human seeing things, and it feeds streams.
# The human often has to respond mid stream with "y" to continue, for example, or timeout if things are taking too long.
# Programming languages, on the other hand, are sequential at thier core (often with tools to multitask).
# *Of course* the 2023+ solution is AI, but this one should be fairly simple.
#https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
#https://hackersandslackers.com/automate-ssh-scp-python-paramiko/
import time, re, os, sys, threading, select

try:
    log_pipes # All logs go here.
except:
    log_pipes = []
    rm_ctrl_chars_default = False

def bprint(*txt):
    # Use our own color to differentiate from the data dump that is the ssh/bash stream.
    txt = ' '.join([str(t) for t in txt])
    print('\033[94m'+txt+'\033[0m', end='')

def termstr(cmds, _out, _err):
    # Prints it in a format that is easier to read.
    pieces = []
    for i in range(len(_out)):
        c = cmds[i] if type(cmds[i]) is str else cmds[i][0]
        pieces.append('→'+c+'←')
        pieces.append(_out[i])
        if _err is not None:
            pieces.append(_err[i])
    txt = '\n'.join(pieces)
    txt = txt.replace('\r\n','\n')
    txt = txt.replace('\n\n','\n')
    return txt

def quoteless(the_path):
    # Quotes prevent the nice convienent ~ and * syntax of directories.
    # So escaping spaces helps.
    return the_path.replace('\\','/').replace(' ',' \\')

def remove_control_chars(txt, label=True, rm_bash_escapes=False):
    # They have a powerful compression effect that can prevent newlines from ever bieng printed again.
    for cix in list(range(32))+[127]:
        if cix not in [9, 10]: # [9, 10] = [\t, \n]
            if label:
                txt = txt.replace(chr(cix),'֍'+hex(cix)+'֍')
            else:
                txt = txt.replace(chr(cix),'')
    if rm_bash_escapes:
        txt = txt.replace('[', '֍') # Removes bash control chars.
    return txt

def utf8_one_char(read_bytes_fn):
    # One unicode char may be multible bytes, but if so the first n-1 bytes are not valid single byte chars.
    # See: https://en.wikipedia.org/wiki/UTF-8.
    # TODO: consider: class io.TextIOWrapper(buffer, encoding=None, errors=None, newline=None, line_buffering=False, write_through=False)
    bytes = read_bytes_fn(1)
    while True:
        try:
            return bytes.decode('UTF-8')
        except UnicodeDecodeError as e:
            if 'unexpected end of data' not in str(e):
                raise e
            bytes = bytes+read_bytes_fn(1)

class ThreadSafeList(): # TODO: deprecated.
    # Fill in a read loop on another thread and then use pop_all()
    # https://superfastpython.com/thread-safe-list/
    def __init__(self):
        self._list = list()
        self._lock = threading.Lock()
    def append(self, value):
        with self._lock:
            self._list.append(value)
    def pop(self):
        with self._lock:
            return self._list.pop()
    def get(self, index):
        with self._lock:
            return self._list[index]
    def length(self):
        with self._lock:
            return len(self._list)
    def pop_all(self):
        with self._lock:
            out = self._list.copy()
            self._list = []
            return out

def pipe_loop(tubo): # For ever watching... untill the thread gets closed.
    dt0 = 0.001
    dt1 = 2.0
    dt = dt0
    while not tubo.closed:
        try:
            n = tubo.update()
            if n==0:
                dt = dt0
            else:
                dt = min(dt*2, dt1)
            time.sleep(dt)
        except Exception as e:
            tubo.loop_err = e

class MessyPipe:
    # The low-level basic messy pipe object with a way to get [output, error] as a string.
    def _init_core(self, proc_type, proc_args=None, printouts=True, return_bytes=False):
        self.proc_type = proc_type
        self.proc_args = proc_args
        self.send_f = None # Send strings OR bytes.
        self.stdout_f = None # Returns an empty bytes if there is nothing to get.
        self.stderr_f = None
        self._streams = None # Mainly used for debugging.
        self.color = 'linux'
        self.remove_control_chars = rm_ctrl_chars_default # **Only on printing** Messier but should prevent terminal upsets.
        self.printouts = printouts # True when debugging.
        self.return_bytes = return_bytes
        self._close = None
        self.closed = False
        self.machine_id = None # Optional user data.
        self.restart_fn = None # Optional fn allowing any server to be restarted.
        self.lock = threading.Lock()
        self.loop_thread = threading.Thread(target=pipe_loop, args=[self])
        self.packets = [['<init>', b'' if self.return_bytes else '', b'' if self.return_bytes else '', time.time(), time.time()]] # Each command: [cmd, out, err, time0, time1]
        self.loop_err = None

        _to_str = lambda x: x if type(x) is str else x.decode()
        _to_bytes = lambda x: x if type(x) is bytes else x.encode()

        def _mk_close_fn(f):
            def _tmp(self):
                log_pipes.append(self)
                self.closed = True
                f()
            return _tmp

        if proc_type == 'shell':
            #https://stackoverflow.com/questions/375427/a-non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
            #https://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            import subprocess
            terminal = 'cmd' if os.name=='nt' else 'bash' # Windows vs non-windows.
            posix_mode = 'posix' in sys.builtin_module_names
            if not proc_args:
                procX = terminal
            elif type(proc_args) is str:
                procX = proc_args
            elif type(proc_args) is list or type(proc_args) is tuple:
                procX = ' '.join(proc_args)
            elif type(proc_args) is dict:
                procX = ' '.join([k+' '+proc_args[k] for k in proc_args.keys()])
            else:
                raise Exception('For the shell, the type of proc args must be str, list, or dict.')
            def _read_loop(the_pipe, safe_list):
                while True:
                    safe_list.append(ord(the_pipe.read(1)) if self.return_bytes else utf8_one_char(the_pipe.read))
                #for line in iter(out.readline, b''): # Could readline be better or is it prone to getting stuck?
                #    safe_list.append(line)
                #out.close()
            p = subprocess.Popen(procX, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=posix_mode) #bufsize=1, shell=True

            def _stdouterr_f(is_err):
                p_std = [p.stderr if is_err else p.stdout]
                ready_to_read, _, _ = select.select([p_std], [], [], 0)
                all_data = ''
                if p_std in ready_to_read:
                    all_data = p_std.read()
                if type(all_data) is bytes and not self.return_bytes:
                    all_data = all_data.decode('UTF-8')
                if type(all_data) is not bytes and self.return_bytes:
                    all_data = all_data.encode()
                return all_data

            self.stdout_f = lambda: _stdouterr_f(False)
            self.stderr_f = lambda: _stdouterr_f(True)

        elif proc_type == 'ssh':
            #https://unix.stackexchange.com/questions/70895/output-of-command-not-in-stderr-nor-stdout?rq=1
            #https://stackoverflow.com/questions/55762006/what-is-the-difference-between-exec-command-and-send-with-invoke-shell-on-para
            # https://stackoverflow.com/questions/40451767/paramiko-recv-ready-returns-false-values
            #https://gist.github.com/kdheepak/c18f030494fea16ffd92d95c93a6d40d
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Being permissive is quite a bit easier...
            #print('Connecting paramiko SSH with these arguments:', proc_args)
            #if not proc_args:
            #    proc_args['banner_timeout'] = 32 # Does this help?
            client.connect(**proc_args) #password=passphrase) #proc_args['hostname'],
            use_keepalive=True
            if use_keepalive: #https://stackoverflow.com/questions/5402919/prevent-sftp-ssh-session-timeout-with-paramiko
                transport = client.get_transport()
                transport.set_keepalive(30)
            channel = client.invoke_shell()
            self._streams = channel

            def _send(x, include_newline=True):
                x = _to_str(x)+('\n' if include_newline else '')
                channel.send(x)
            self.send_f = _send
            def _get_elements(ready_fn, read_fn):
                out = []
                while ready_fn():
                    out.append(ord(read_fn(1)) if self.return_bytes else utf8_one_char(read_fn))
                return ''.join(out).encode() if self.return_bytes else ''.join(out)
            self.stdout_f = lambda: _get_elements(channel.recv_ready, channel.recv)
            self.stderr_f = lambda: _get_elements(channel.recv_stderr_ready, channel.recv_stderr)

            #chan = client.get_transport().open_session() #TODO: what does this do and is it needed?
            self._close = _mk_close_fn(client.close)
        else: # TODO: more kinds of pipes.
            raise Exception('proc_type must be "shell" or "ssh"')

        if self.stdout_f is None or self.stderr_f is None:
            raise Exception('stdout_f and/or stderr_f not set.')

        def _remake(self):
            out = MessyPipe(self.proc_type, self.proc_args, self.printouts, self.return_bytes)
            out.machine_id = self.machine_id
            out.remove_control_chars = self.remove_control_chars
            return out
        self._remake = _remake

        self.update()
        self.loop_thread.daemon = True; self.loop_thread.start() # This must only happen when the setup is complete.
        while True:
            try:
                self.API('echo pipe_begin', timeout=2.0) # This may prevent sending commands too early.
                break
            except Exception as e:
                if 'API timeout' not in str(e):
                    raise e
            print(f'Waiting for {proc_pipe} pipe to be ready for a simple bash cmd.')

    def __init__(self, proc_type, proc_args=None, printouts=True, return_bytes=False):
        self._init_core(proc_type, proc_args=proc_args, printouts=printouts, return_bytes=return_bytes)

    def blit(self, include_history=True):
        # Mash the output and error together.
        with self.lock:
            self.assert_no_loop_err()
            if include_history:
                return ''.join([pk[1]+pk[2] for pk in self.packets])
            else:
                return self.packets[-1][1]+self.packets[-1][2]

    def update(self): # Returns the len of the data.
        with self.lock:
            _out = None; _err = None
            def _boring_txt(txt):
                txt = txt.replace('\r\n','\n')
                if self.remove_control_chars:
                    txt = remove_control_chars(txt, True)
                return txt
            _out = self.stdout_f()
            _err = self.stderr_f()
            if self.printouts:
                if len(_out)>0:
                    print(_boring_txt(_out), end='') # Newlines should be contained within the feed so there is no need to print them directly.
                if len(_err)>0:
                    print(_boring_txt(_err), end='')
            if len(_out)+len(_err)>0:
                self.packets[-1][1] = self.packets[-1][1]+_out
                self.packets[-1][2] = self.packets[-1][2]+_err
                self.packets[-1][4] = time.time()
            return len(_out)+len(_err)

    def drought_len(self):
        # How long since neither stdout nor stderr spoke to us.
        return time.time() - self.packets[-1][4]

    def send(self, txt, include_newline=True, suppress_input_prints=False):
        # The non-blocking operation.
        #https://stackoverflow.com/questions/6203653/how-do-you-execute-multiple-commands-in-a-single-session-in-paramiko-python
        if self.closed:
            raise Exception('The pipe has been closed and cannot accept commands; use pipe.remake() to get a new, open pipe.')
        if self.printouts and not suppress_input_prints:
            if self.color=='linux':
                #https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
                print('\x1b[0;33;40m'+'→'+'\x1b[6;30;42m' +txt+'\x1b[0;33;40m'+'←'+'\x1b[0m')
            else:
                print('→'+txt+'←')
        self.packets.append([txt, b'' if self.return_bytes else '', b'' if self.return_bytes else '', time.time(), time.time()])
        self.send_f(txt, include_newline=include_newline)

    def API(self, txt, f_polls=None, timeout=8.0):
        # Behaves like an API, returning out, err, and information about which polling fn suceeded.
        # Optional timeout if all polling fns fail.
        self.send(txt)
        if f_polls is None:
            f_polls = {'default':standard_is_done}
        elif callable(f_polls):
            f_polls = {'user':f_polls}
        elif type(f_polls) is list or type(f_polls) is tuple:
            f_polls = dict(zip(range(len(f_polls)), f_polls))

        which_poll=None
        while which_poll is None:
            for k in f_polls.keys():
                if f_polls[k](self):
                    which_poll=k # Break out of the loop
                    break
            time.sleep(0.1)
            td = self.drought_len()
            if self.printouts:
                if td>min(6, 0.75*timeout):
                    if self.color=='linux':
                        # Colors: https://misc.flogisoft.com/bash/tip_colors_and_formatting
                        print('\x1b[0;33;40m'+f'{td} seconds has elapsed with dry pipes.'+'\x1b[0m')
                    else:
                        print(f'{td} seconds has elapsed with dry pipes.')
            if timeout is not None and td>timeout:
                raise Exception(f'API timeout on cmd {txt}; ')

        self.assert_no_loop_err()

        return self.packets[-1][1], self.packets[-1][2], which_poll

    def assert_no_loop_err(self):
        if self.loop_err:
            print('Polling loop exception:')
            raise self.loop_err

    def multi_API(self, cmds, f_polls=None, timeout=8):
        # For simplier series of commands.
        # Returns output, errors. f_poll can be a list of fns 1:1 with cmds.
        outputs = []; errs = []; polls_info = []
        self.empty()
        for i in range(len(cmds)):
            out, err, poll_info = self.API(cmds[i], f_polls=f_polls, timeout=timeout)
            outputs.append(out)
            errs.append(err)
            polls_info.append(poll_info)
        return outputs, errs, polls_info

    def close(self):
        self._close(self)
        self.closed = True

    def sure_of_EOF(self):
        # Only if we are sure! Not all that useful since it isn't often triggered.
            #https://stackoverflow.com/questions/35266753/paramiko-python-module-hangs-at-stdout-read
        #    ended_list = [False, False] # TODO: fix this.
        #    return len(list(filter(lambda x: x, ended_list)))==len(ended_list)
        return False # TODO: maybe once in a while there are pipes that are provably closable.

    def remake(self):
        # If closed, opens a new pipe to the same settings and returns it.
        # Recommended to put into a loop which may i.e. restart vms or otherwise debug things.
        if not self.closed:
            self.close()
        return self._remake(self)

##############Expect-like tools that try to correct for errors##################

#def _restart_parent(tubo):
#    TODO
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

def _non_empty_lines(txt):
    txt = txt.replace('\r\n','\n').strip()
    return list(filter(lambda x: len(x)>0, txt.split('\n')))

def last_line(tubo):
    # Last non-empty line (empty if no such line exists).
    txt = tubo.blit(include_history=False)
    lines = _non_empty_lines(txt)
    if len(lines)==0:
        return ''
    return lines[-1]

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

def looks_like_blanck_prompt(line):
    # When most cmds finish they return to foo/bar/baz$, or xyz>, etc.
    # This determines whether the line is one of these.
    line = line.strip()
    for ending in ['$', '>', '#']:
        if line.endswith(ending):
            return True
    return False

def default_prompts():
    # Default line end prompts and the needed input (str or function of the pipe).
    def _super_advanced_linux_shell(tubo):
        # What button do you press to continue?
        import random
        for i in range(256): # We are getting frusterated...
            chs = ['\033[1A','\033[1B','\033[1C','\033[1D','o','O','y','Y','\n']
            ch = random.choice(chs)
            tubo.send(ch, suppress_input_prints=True, include_newline=False)
        return tubo.API('random_bashing_done')

    return {'Pending kernel upgrade':'\n\n\n','continue? [Y/n]':'Y',
            'continue connecting (yes/no)?':'Y',
            'Which services should be restarted?':_super_advanced_linux_shell} # Newfangled menu.

def standard_is_done(p):
    # A default works-most-of-the-time pipe dryness detector.
    # Will undergo a lot of tweaks that try to extract the spatial information.
    txt = p.blit(include_history=False)
    if p.proc_type=='shell': #Sometimes they use empty lines!?
        lines = txt.replace('\r\n','\n').split('\n')
        if len(txt)>0 and len(lines[-1].strip()) == 0:
            return True

    lines = _non_empty_lines(txt)
    return len(lines)>0 and looks_like_blanck_prompt(lines[-1])

def cmd_list_fixed_prompt(tubo, cmds, response_map, timeout=16):
    x0 = tubo.blit()
    def _check_line(_tubo, txt):
        lline = last_line(_tubo)
        return txt in lline
    line_end_poll = lambda _tubo: looks_like_blanck_prompt(last_line(tubo))
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

def pipelayer_ssh(make_pipe_fn):
    # Tries to get an SSH pipe working properly.
    while True:
        try:
            tubo = make_pipe_fn()
            return tubo
        except Exception as e:
            se = str(e)
            msgs = {'Unable to connect to':'Unable to connect', 'timed out':'timeout',\
                    'encountered RSA key, expected OPENSSH key':'RSA/OPENSSH keys',
                    'Connection reset by peer':'connection reset',\
                    'Error reading SSH protocol banner':'Oh no! the *banner* error!'}
            hit = False
            for k in msgs.keys():
                if k in se:
                    if printouts:
                        print('\033[90m SSH waiting to clear error: '+str(msgs[k])+'\033[0m')
                    hit = True
            if not hit: # Not a standard error.
                raise e
        time.sleep(1.0)
    tubo = plumber_basic(tubo)
    return tubo

def plumber_basic(tubo, timeout_seconds=24, err_msg = '???'):
    # For cmds that don't return much. TODO: get working on windows.
    timeout_seconds = int(timeout_seconds)
    for i in range(timeout_seconds):
        tubo.send('echo foo{bar,baz}')
        time.sleep(1)
        if 'foobar foobaz' in tubo.blit(True):
            break
        if tubo.printouts:
            print('\033[90m'+'Waiting for pipe to blit back.'+'\033[0m')
        if i==timeout_seconds-1:
            raise Exception(f'Timeout waiting on {err_msg}')

def plumber_apt(tubo, apt_cmd, xtra_prompt_responses, timeout=64):
    # Tries to get an apt prompt working.
    # tubo.API(self, txt, f_polls=None, timeout=8.0)

    def _verify_apt_package(tubo, package_name, timeout=timeout):
        # Have we installed a package?
        tubo, x = cmd_list_fixed_prompt(tubo, [f'dpkg -s {package_name}'], eye_term.default_prompts(), timeout=timeout)
        verify = 'install ok installed' in x or 'install ok unpacked' in x
        falsify = 'is not installed' in x
        return tubo, True if verify else (False if falsify else None)

    response_map = {**default_prompts(), **xtra_prompt_responses}
    while True:
        tubo, txt = cmd_list_fixed_prompt(tubo, [apt_cmd], response_map, timeout=timeout)

        msgs = {'Unable to acquire the dpkg frontend lock':'dpkg lock uh ho.',
                'sudo dpkg --configure -a" when needed':'Mystery --configure -a bug',
                'Unable to locate package':'Cant locate',
                'has no installation candidate':'The other cant locate',
                'Some packages could not be installed. This may mean that you have requested an impossible situation':'Oh no not the "impossible situation" error!'}
        hit_err = False
        for k in msgs.keys():
            if k in txt:
                if tubo.printouts:
                    print('\033[90m Apt cmd error: '+msgs[k]+', retrying\033[0m')
                hit_err = True
        if not hit_err:
            tubo, tresult = _verify_apt_package(tubo, package_name, timeout=timeout)
            if tresult is False:
                raise Exception('Mysterious apt error')
            elif tresult is None:
                raise Exception("Cannot verify installation of package.")
            else:
                break #Success!
        time.sleep(2.0)

    return tubo

def plumber_pip(tubo, pip_cmd, xtra_prompt_responses, break_sys_packages='polite', timeout=64):
    # Tries to get an apt prompt working.
    x0 = tubo.blit()
    if prompts is None:
        prompts = eye_term.default_prompts()
    tubo, x = cmd_list_fixed_prompt(tubo, [pip_cmd], prompts, timeout=timeout)

    if tubo.printouts and break_sys_packages.lower() == 'yes':
        bprint('WARNING: using --break-system-packages option')
    if 'Successfully installed '+package_name in x or 'Requirement already satisfied' in x:
        pass
    elif "Command 'pip' not found" in x or 'pip: command not found' in x:
        tubo = plumber_apt(tubo, 'sudo apt get python3-pip', timeout=64)
        tubo = plumber_apt(tubo, 'sudo apt get python-is-python3', timeout=64)
    elif 'No matching distribution found for '+package_name in x:
        raise Exception(f'No matching pip for {package_name}')
    elif '--break-system-packages' in x and 'This environment is externally managed' in x and break_sys_packages.lower() != 'yes':
        if break_sys_packages == 'polite':
            plumber_pip(tubo, pip_cmd+' --break-system-packages', xtra_prompt_responses, break_sys_packages='yes', timeout=timeout)
        elif not break_sys_packages or break_sys_packages.lower() == 'no' or break_sys_packages.lower() == 'deny' or break_sys_packages.lower() == 'forbidden':
            raise Exception('Externally managed env error and break_sys_packages arg set to "forbidden"')
    else:
        raise Exception(f'Cannot verify pip installation for: {package_name}')

    if type(inst_or_pipe) is not eye_term.MessyPipe:
        tubo.close()
    return tubo
