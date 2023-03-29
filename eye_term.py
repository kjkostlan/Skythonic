# (This could be a mini project)
# Shell is centered around a human seeing things, and it feeds streams.
# The human often has to respond mid stream with "y" to continue, for example, or timeout if things are taking too long.
# Programming languages, on the other hand, are sequential at thier core (often with tools to multitask).
# *Of course* the 2023+ solution is AI, but this one should be fairly simple.
#https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
#https://hackersandslackers.com/automate-ssh-scp-python-paramiko/
import time, re

class MessyPipe:
    # The low-level basic messy pipe object with a way to get [output, error] as a string.
    def __init__(self, client, printouts, use_file_objs=False):
        self.client = client
        self.ctype = str(type(client))
        self.channel = None
        self.filelike_streams = None
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
        if 'paramiko.client.SSHClient' in self.ctype:
            self.channel = client.invoke_shell()
            if use_file_objs:
                self.channel.settimeout(0.125)
                self.filelike_streams = [self.channel.makefile_stdin('wb'), self.channel.makefile('rb'), self.channel.makefile_stderr('rb')]#, self.channel.makefile('rb')]

            chan = client.get_transport().open_session()

            self.close = lambda: client.close()
        else: #TODO: more types of pipes (local processes, etc)
            raise Exception("Unknown client type:"+str(type(client)))
        # https://stackoverflow.com/questions/40451767/paramiko-recv-ready-returns-false-values
        #https://gist.github.com/kdheepak/c18f030494fea16ffd92d95c93a6d40d

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

        if 'paramiko.client.SSHClient' in self.ctype:
            if self.filelike_streams is not None:
                def _read(file_like_obj):
                    grow = []
                    while True:
                        try:
                            grow.append(file_like_obj.read(1).decode())
                        except Exception as e:
                            if 'timeout()' not in repr(e):
                                raise e
                            break
                    return ''.join(grow)
                _out = _read(self.filelike_streams[1])
                _err = _read(self.filelike_streams[2])
            else:
                #https://www.accadius.com/reading-the-ssh-output/
                #https://docs.paramiko.org/en/stable/api/channel.html
                #Maybe read multible bytes at once? https://stackoverflow.com/questions/44736204/how-to-find-out-how-many-bytes-in-socket-before-recv-in-python
                out = []
                while self.channel.recv_ready():
                    out.append(self.channel.recv(1).decode('UTF-8'))
                _out = ''.join(out)
                err = []
                while self.channel.recv_stderr_ready():
                    err.append(self.channel.recv_stderr(1).decode('UTF-8'))
                _err = ''.join(err)
                if self.printouts:
                    if len(_out)>0:
                        print(_boring_txt(_out), end='') # Newlines should be contained within the feed so there is no need to print them directly.
                    if len(_err)>0:
                        print(_boring_txt(_err), end='')
                self.combined_contents = self.combined_contents+_out+_err
        else:
            raise Exception('This code currently does not understand: '+self.ctype)
        new_stuff = [_out, _err]
        for i in range(len(new_stuff)):
            if len(new_stuff[i])>0:
                self.t1 = time.time() # T1 is updated whenever the pipe sends stuff.
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

    def send(self, txt):
        # The non-blocking operation.
        #https://stackoverflow.com/questions/6203653/how-do-you-execute-multiple-commands-in-a-single-session-in-paramiko-python
        self.cmd_history.append(txt)
        if self.printouts:
            if self.color=='linux':
                #https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
                print('\x1b[0;33;40m'+'→'+'\x1b[6;30;42m' +txt+'\x1b[0;33;40m'+'←'+'\x1b[0m')
            else:
                print('→'+txt+'←')
        if 'paramiko.client.SSHClient' in self.ctype:
            if self.filelike_streams is not None:
                self.filelike_streams[0].write(txt+'\n')
            else:
                self.channel.send(txt+'\n')
        else:
            raise Exception('This code currently does not understand: '+self.ctype)

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
        # Note: this fn doesn't seem to be reliable.
        if 'paramiko.client.SSHClient' in self.ctype:
            #https://stackoverflow.com/questions/35266753/paramiko-python-module-hangs-at-stdout-read
            ended_list = [False, False] # TODO: fix this.
            return len(list(filter(lambda x: x, ended_list)))==len(ended_list)

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
