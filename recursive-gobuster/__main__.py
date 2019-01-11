"""
Title: recursive-gobuster
Date: 20190110
Author: epi <epibar052@gmail.com>
  https://epi052.gitlab.io/notes-to-self/
Tested on:
    linux/x86_64 4.15.0-43-generic
    Python 3.6.6
    pyinotify 0.9.6
"""
import time
import signal
import shutil
import argparse
import tempfile
import subprocess

from pathlib import Path

import pyinotify

active_scans = list()
completed_scans = list()


class EventHandler(pyinotify.ProcessEvent):
    """
    Handles notifications and takes actions through specific processing methods.
    For an EVENT_TYPE, a process_EVENT_TYPE function will execute.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tmpdir = kwargs.get('tmpdir')
        self.threads = kwargs.get('threads')
        self.wordlist = kwargs.get('wordlist')
        self.extensions = kwargs.get('extensions')
        self.target = self.original_target = kwargs.get('target')

    def _normalize_targetname(self, tgt: str) -> str:
        """ Returns a string representing a target URL that is compatible with linux filesystem naming conventions.

        Forward slashes (/) are not allowed in linux file names.  This function simply replaces them with an underscore.

        Args:
            tgt: target url i.e. http://10.10.10.112/images/

        Returns:
            normalized target url i.e. http:__10.10.10.112_images_
        """
        return tgt.replace('/', '_')

    def run_gobuster(self, target: str) -> None:
        """ Runs gobuster in a non-blocking subprocess.

        The function is pretty opinionated about options fed to gobuster.  Removing the -f, -e, or -n will likely break
        functionality of the script.  The other options are either configurable via command line options, or can be
        manipulated without any adverse side-effects.

        Hard-coded options/args
            -f
                Append a forward-slash to each directory request
            -q
                Don't print the banner and other noise
            -n
                Don't print status codes
            -r
                Follow redirects
            -e
                Expanded mode, print full URLs
            -k
                Skip SSL certificate verification
            -a string
                Set the User-Agent string

        Args:
            target: target url i.e. http://10.10.10.112/images/
        """
        normalized_target = self._normalize_targetname(target)

        command = [
            'gobuster',
            '-f', '-q', '-n', '-r', '-e', '-k', '-t', self.threads,  # fqnrekt, lol
            '-u', target,
            '-w', self.wordlist,
            '-a', 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            '-o', f"{self.tmpdir}/{normalized_target}"
        ]

        if self.extensions:
            command.append('-x')
            command.append(self.extensions)

        """
        my personal preference is to suppress all the wildcard error messages as seen below. 

        [-] Wildcard response found: http://10.10.10.112/.hta/eb7c8242-0d3b-4e7a-9336-f6d6327b87a3 => 403
        [!] To force processing of Wildcard responses, specify the '-fw' switch.

        If you want to see these, or think that you're missing something from stderr, remove stderr=subprocess.DEVULL 
        from the Popen constructor.
        """
        subprocess.Popen(command, stderr=subprocess.DEVNULL)

        active_scans.append(normalized_target)

    def process_IN_MODIFY(self, event: pyinotify.Event) -> None:
        """ Handles event produced when a file is modified.

        This function is designed to trigger when any of the watched gobuster output files are appended to.  The
        output files are appened to each time a new file/folder is identified by gobuster.  This function will
        pull out the new entry and start a new gobuster scan against it, if appropriate.

        Args:
            event: pyinotify.Event
        """
        with open(event.pathname) as f:
            for line in f:
                line = line.strip()

                if not line.endswith('/'):  # skip non-directories
                    continue

                # found a directory -> https://somedomain/images/
                normalized_target = self._normalize_targetname(line)

                if normalized_target in active_scans or normalized_target in completed_scans:  # skip active/complete
                    continue

                # found a directory that is not being actively scanned and has not already been scanned
                self.run_gobuster(target=line)

    def process_IN_CLOSE_WRITE(self, event: pyinotify.Event) -> None:
        """ Handles event produced when a file that was open for writing is closed.

        This function is designed to trigger when any of the watched gobuster output files are closed.  This is
        indicative of scan completion.

        Args:
            event: pyinotify.Event
        """
        normalized_target = self._normalize_targetname(event.name)

        # scan related to the target is complete; remove it from active and place it in complete
        active_scans.remove(normalized_target)
        completed_scans.append(normalized_target)

        if not active_scans:
            # likely, no more scans are running
            time.sleep(3)  # attempt to avoid race condition
            if not active_scans:
                # check one last time
                print(f"All scans complete. Cleaning up.")
                self.cleanup(None, None)

    def cleanup(self, sig, frame) -> None:
        """ Simple function to write results seen so far and remove the temp directory.

        Can be called from either all scans completing, or receiving a SIGINT.  When triggered from catching a SIGINT,
        the function is called with two arguments: the signal number and the current stack frame.  When we call it
        ourselves, we don't care about those, so we can just call this manually with sig=None,frame=None

        Args:
            sig:  signal number or None
            frame:  current stack frame or None
        """
        results = list()
        pathtmpdir = Path(self.tmpdir)

        if pathtmpdir.exists():  # ensure we got at least some results
            for file in pathtmpdir.iterdir():
                with file.open() as f:
                    results += f.readlines()

            results.sort()

            with open(f"recursive-gobuster_{self._normalize_targetname(self.original_target)}.log", 'w') as f:
                f.write(''.join(results))

            shutil.rmtree(self.tmpdir)

        raise SystemExit(0)


def main(args_ns: argparse.Namespace) -> None:
    tmpdir = tempfile.mkdtemp(prefix='rcrsv-gbstr')  # directory for gobuster scan results

    # watch manager stores the watches and provides operations on watches
    wm = pyinotify.WatchManager()

    handler = EventHandler(
        target=args_ns.target,
        tmpdir=tmpdir,
        wordlist=args_ns.wordlist,
        threads=args_ns.threads,
        extensions=args_ns.extensions
    )

    notifier = pyinotify.Notifier(wm, handler)

    # watch for file appends (found dir/file) and files closing (scan complete)
    mask = pyinotify.IN_MODIFY | pyinotify.IN_CLOSE_WRITE

    wm.add_watch(tmpdir, mask)

    handler.run_gobuster(args_ns.target)  # kick off first scan against initial target

    signal.signal(signal.SIGINT, handler.cleanup)  # register signal handler to handle SIGINT

    notifier.loop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', '--threads', default='20', help='# of threads for each spawned gobuster (default: 20)')
    parser.add_argument('-x', '--extensions', help='extensions passed to the -x option for spawned gobuster')
    parser.add_argument('-w', '--wordlist', default='/usr/share/seclists/Discovery/Web-Content/common.txt',
                        help='wordlist for each spawned gobuster (default: /usr/share/seclists/Discovery/Web-Content/common.txt)')
    parser.add_argument('target', help='target to scan')

    args = parser.parse_args()

    main(args)


