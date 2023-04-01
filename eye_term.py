# (This could be a mini project)
# Shell is centered around a human seeing things, and it feeds streams.
# The human often has to respond mid stream with "y" to continue, for example, or timeout if things are taking too long.
# Programming languages, on the other hand, are sequential at thier core (often with tools to multitask).
# *Of course* the 2023+ solution is AI, but this one should be fairly simple.
#https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
#https://hackersandslackers.com/automate-ssh-scp-python-paramiko/
import time, re

def loop_try(f, f_catch, msg, delay=4):
    # Waiting for something? Keep looping untill it succedes!
    # Useful for some shell/concurrency operations.
    while True:
        try:
            return f()
        except Exception as e:
            if f_catch(e):
                if callable(msg):
                    print(msg())
                else:
                    print(msg)
            else:
                raise e
        time.sleep(delay)

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

class ThreadSafeList():
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

class MessyPipe:
    # The low-level basic messy pipe object with a way to get [output, error] as a string.
    def __init__(self, proc_type, proc_args, printouts, return_bytes=False, use_file_objs=False):
        self.proc_type = proc_type
        self.send_f = None # Send strings OR bytes.
        self.stdout_f = None # Returns an empty bytes if there is nothing to get.
        self.stderr_f = None
        self._streams = None # Mainly used for debugging.
        self.color = 'linux'
        self.remove_control_chars = True # **Only on printing** Messier but should prevent terminal upsets.
        self.printouts = printouts # True when debugging.
        self.t0 = time.time() # Time since last clear.
        self.t1 = time.time() # Time of last sucessful read.
        self.poll_log = [] # Polling fns can put debug-useful info here.
        self.contents = ['',''] # Output and error.
        self.history_contents = ['',''] # Includes history.
        self.cmd_history = []
        self.combined_contents = '' # Better approximation to the printout combining out and err.

        _to_str = lambda x: x if type(x) is str else x.decode()
        _to_bytes = lambda x: x if type(x) is bytes else x.encode()

        if proc_type == 'shell':
            #https://stackoverflow.com/questions/375427/a-non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
            #https://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            import subprocess
            def _read_loop(the_pipe, safe_list):
                while True:
                    safe_list.append(ord(the_pipe.read(1)) if return_bytes else utf8_one_char(the_pipe.read))
                #for line in iter(out.readline, b''): # Could readline be better or is it prone to getting stuck?
                #    safe_list.append(line)
                #out.close()
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
            p = subprocess.Popen(procX, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=posix_mode) #bufsize=1, shell=True

            def _send(x, include_newline=True):
                x = _to_bytes(_to_str(x)+'\n' if include_newline else x)
                p.stdin.write(x); p.stdin.flush() # Flushing seems to be needed.
            self.send_f = _send
            stdout_store = ThreadSafeList()
            stderr_store = ThreadSafeList()
            t = threading.Thread(target=read_loop, args=(p.stdout, stdout_store))
            t.daemon = True # thread dies with the program
            t.start()
            t = threading.Thread(target=read_loop, args=(p.stderr, stderr_store))
            t.daemon = True # thread dies with the program
            t.start()
            self.stdout_f = _read_loop(the_pipe, stdout_store)
            self.stderr_f = _read_loop(the_pipe, stderr_store)
            self.close = p.kill
        elif proc_type == 'ssh':
            #https://unix.stackexchange.com/questions/70895/output-of-command-not-in-stderr-nor-stdout?rq=1
            #https://stackoverflow.com/questions/55762006/what-is-the-difference-between-exec-command-and-send-with-invoke-shell-on-para
            # https://stackoverflow.com/questions/40451767/paramiko-recv-ready-returns-false-values
            #https://gist.github.com/kdheepak/c18f030494fea16ffd92d95c93a6d40d
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Being permissive is quite a bit easier...
            client.connect(**proc_args) #password=passphrase) #proc_args['hostname'],
            channel = client.invoke_shell()
            self._streams = channel
            if use_file_objs:
                TODO # This needs to be fixed or use_file_objs as a deprecated features.
                channel.settimeout(0.125)
                self._streams = [channel.makefile_stdin('wb'), channel.makefile('rb'), channel.makefile_stderr('rb')]#, channel.makefile('rb')]
                [self.send_f, self.stdout_f, stlf.stderr_f] = [s.read for s in self._streams]
            else:
                def _send(x, include_newline=True):
                    x = _to_str(x)+('\n' if include_newline else '')
                    channel.send(x)
                self.send_f = _send
                def _get_bytes(ready_fn, read_fn):
                    out = []
                    while channel.recv_ready():
                        out.append(ord(read_fn(1)) if return_bytes else utf8_one_char(read_fn))
                    return ''.join(out).encode() if return_bytes else ''.join(out)
                self.stdout_f = lambda: _get_bytes(channel.recv_ready, channel.recv)
                self.stderr_f = lambda: _get_bytes(channel.recv_stderr_ready, channel.recv_stderr)

            #chan = client.get_transport().open_session() #TODO: what does this do and is it needed?
            self.close = client.close
        else: # TODO: more kinds of pipes.
            raise Exception('proc_type must be "shell" or "ssh"')

    def update(self):
        _out = None; _err = None
        def _boring_txt(txt):
            if self.remove_control_chars:
                txt = txt.replace('\r\n','\n')
                for cix in list(range(32))+[127]:
                    if cix not in [9, 10]:
                        txt = txt.replace(chr(cix),'֍'+hex(cix)+'֍')
                return txt
            return txt
        _out = self.stdout_f()
        _err = self.stderr_f()
        if self.printouts:
            if len(_out)>0:
                print(_boring_txt(_out), end='') # Newlines should be contained within the feed so there is no need to print them directly.
            if len(_err)>0:
                print(_boring_txt(_err), end='')
        self.combined_contents = self.combined_contents+_out+_err
        new_stuff = [_out, _err]
        for i in range(len(new_stuff)):
            if len(new_stuff[i])>0:
                self.t1 = time.time() # T1 is updated whenever we recieve anything.
                self.contents[i] = self.contents[i]+new_stuff[i]

    def empty(self, remove_history=False):
        self.t0 = time.time()
        self.history_contents = [self.history_contents[i]+self.contents[i] for i in range(len(self.contents))]
        self.contents = ['' for _ in self.contents]
        self.combined_contents = ''
        if remove_history:
            self.history_contents = []; self.cmd_history = []; self.poll_log = []

    def drought_len(self):
        return time.time() - self.t1

    def send(self, txt, include_newline=True):
        # The non-blocking operation.
        #https://stackoverflow.com/questions/6203653/how-do-you-execute-multiple-commands-in-a-single-session-in-paramiko-python
        self.cmd_history.append(txt)
        if self.printouts:
            if self.color=='linux':
                #https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
                print('\x1b[0;33;40m'+'→'+'\x1b[6;30;42m' +txt+'\x1b[0;33;40m'+'←'+'\x1b[0m')
            else:
                print('→'+txt+'←')
        self.send_f(txt, include_newline=include_newline)

    def API(self, txt, f_poll=None, dt_min=0.0001, dt_max=1):
        # Sents the command, then calls f_poll(self) repeatedly with gradually increasing dt.
        # When f_poll returns True it will return the result and clear self.
        # A default f_poll if it is None
        self.send(txt)
        dt = dt_min
        npoll0 = len(self.poll_log)
        if f_poll is None:
            f_poll = standard_is_done
        while not f_poll(self):
            time.sleep(dt)
            dt = min(dt*1.414, dt_max)
            if self.printouts:
                td = self.drought_len()
                if td>6:
                    if self.color=='linux':
                        print('\x1b[0;33;40m'+f'{td} seconds has elapsed with no input.'+'\x1b[0m')
                    else:
                        print(f'{td} seconds has elapsed with no input.')
            self.update()
        if len(self.poll_log)==npoll0:
            raise Exception('Debug mode, remove this raise in production:', f_poll)
            self.poll_log.append({'f_poll forgot to append pipe.poll_log when it returned true':True})
        self.poll_log[-1]['last_cmd'] = self.cmd_history[-1]
        self.poll_log[-1]['combined_contents'] = self.combined_contents
        out = self.contents.copy()
        self.empty()
        return out

    def multi_API(self, cmds, f_poll=None, dt_min=0.0001, dt_max=1):
        # For simplier series of commands.
        # Returns output, errors. f_poll can be a list of fns 1:1 with cmds.
        outputs = []; errs = []
        self.empty()
        for i in range(len(cmds)):
            f_poll1 = f_poll[i] if (type(f_poll) is list or type(f_poll) is tuple) else f_poll
            out, err = self.API(cmds[i], f_poll=f_poll1, dt_min=dt_min, dt_max=dt_max)
            outputs.append(out)
            errs.append(err)
        return outputs, errs

    def sure_of_EOF(self):
        # Only if we are sure! Not all that useful since it isn't often triggered.
            #https://stackoverflow.com/questions/35266753/paramiko-python-module-hangs-at-stdout-read
        #    ended_list = [False, False] # TODO: fix this.
        #    return len(list(filter(lambda x: x, ended_list)))==len(ended_list)
        return False # TODO: mayve once in a while there are pipes that are provably closable.

def non_empty_lines(txt):
    txt = txt.replace('\r\n','\n').strip()
    return list(filter(lambda x: len(x)>0, txt.split('\n')))

def looks_like_prompt(line):
    # When most cmds finish they return to foo/bar/baz$, or xyz>, etc.
    # This determines whether the line is one of these.
    line = line.strip()
    for ending in ['$', '>', '#', 'continue? [Y/n]']:
        if line.endswith(ending):
            return True
    return False

def basic_wait(p, timeout=4):
    # A simple waiting function. TODO: bundle into a larger heuristic.
    return p.sure_of_EOF() or p.drought_len()>timeout

def basic_expect_fn(the_pattern, is_re=False, timeout=12):
    # A standard expect fn based on text. Only looks for stuff in the last command.
    def _expt(p):
        txt = ''.join(p.contents) # Mash the out and err together.
        t = p.drought_len()
        if t>timeout:
            print(f'Warning: expect timeout {timeout} after:', p.cmd_history[-1], 'expecting:', the_pattern)
            p.poll_log.append({'reason':f'Timeout {timeout}s waiting for {the_pattern}.'})
            return True
        if re.search(the_pattern, txt) is not None if is_re else the_pattern in txt:
            p.poll_log.append({'reason':f'Found {the_pattern}'})
            return True
        return False
    return _expt

def standard_is_done(p, timeout=8):
    # A default works-most-of-the-time pipe dryness detector.
    # Will undergo a lot of tweaks that try to extract the spatial information.
    #all_lines = many_lines(p)
    lines = non_empty_lines(p.combined_contents)
    t = p.drought_len()
    if t>timeout:
        print('Warning: default poll fn timeout on:', p.cmd_history[-1])
        p.poll_log.append({'reason':f'Timeout {timeout}s on the default fn.'})
        return True
    elif len(lines)>0 and looks_like_prompt(lines[-1]):
        p.poll_log.append({'reason':'The last line looks like a command prompt which is ready for the cmd fn.'})
        return True
    return False

def termstr(cmds, _out, _err):
    # Prints it in a format that is easier to read.
    # For realtime printouts the printouts option should be used instead.
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
