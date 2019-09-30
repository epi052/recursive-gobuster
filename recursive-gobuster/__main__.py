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
        self.user = kwargs.get("user")
        self.proxy = kwargs.get("proxy")
        self.tmpdir = kwargs.get("tmpdir")
        self.devnull = kwargs.get("devnull")
        self.threads = kwargs.get("threads")
        self.version = kwargs.get("version")
        self.password = kwargs.get("password")
        self.wordlist = kwargs.get("wordlist")
        self.extensions = kwargs.get("extensions")
        self.target = self.original_target = kwargs.get("target")

    def _normalize_targetname(self, tgt: str) -> str:
        """ Returns a string representing a target URL that is compatible with linux filesystem naming conventions.

        Forward slashes (/) are not allowed in linux file names.  This function simply replaces them with an underscore.

        Args:
            tgt: target url i.e. http://10.10.10.112/images/

        Returns:
            normalized target url i.e. http:__10.10.10.112_images_
        """
        return tgt.replace("/", "_")

    def run_gobuster(self, target: str) -> None:
        """ Runs gobuster in a non-blocking subprocess.

        The function is pretty opinionated about options fed to gobuster.  Removing the -e, or -n will likely break
        functionality of the script.  The other options are either configurable via command line options, or can be
        manipulated without any adverse side-effects.

        Hard-coded options/args
            -q
                Don't print the banner and other noise
            -n
                Don't print status codes
            -e
                Expanded mode, print full URLs
            -k
                Skip SSL certificate verification

        Args:
            target: target url i.e. http://10.10.10.112/images/
        """
        normalized_target = self._normalize_targetname(target)

        command = ["gobuster"]

        if self.version == 3:
            command.append("dir")

        command.extend(
            [
                "-q",
                "-n",
                "-e",
                "-k",
                "-t",
                self.threads,
                "-u",
                target,
                "-w",
                self.wordlist,
                "-o",
                f"{self.tmpdir}/{normalized_target}",
            ]
        )

        if self.extensions:
            command.append("-x")
            command.append(self.extensions)

        if self.user:
            # gobuster silently ignores the case where -P is set but -U is not; we'll follow suit.
            command.append("-U")
            command.append(self.user)
            if self.password is not None:
                # password set to anything (including empty string)
                command.append("-P")
                command.append(self.password)

        if self.proxy:
            command.append("-p")
            command.append(self.proxy)

        suppress = subprocess.DEVNULL if self.devnull else None
        print(" ".join(command))
        try:
            subprocess.Popen(command, stderr=suppress)
        except FileNotFoundError as e:
            print(e)
            raise SystemExit

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

                """
                In response to https://github.com/epi052/recursive-gobuster/issues/2

                In the scans below, 00.php/ should not kick off another scan.  The loop below aims to address the problem.

                gobuster -q -n -e -k -t 20 -u https://bluejeans.com/00/ -w /wordlists/seclists/Discovery/Web-Content/common.txt -o /tmp/rcrsv-gbstryv_fcneq/https:__bluejeans.com_00_ -x php
                gobuster -q -n -e -k -t 20 -u https://bluejeans.com/00.php/ -w /wordlists/seclists/Discovery/Web-Content/common.txt -o /tmp/rcrsv-gbstryv_fcneq/https:__bluejeans.com_00.php_ -x php
                """
                for extension in self.extensions.split(","):
                    if line.endswith(f".{extension}"):
                        break
                else:
                    # found a path -> https://somedomain/images, add a forward slash to scan in case of dir-ness
                    tgt = f"{line}/"

                    normalized_target = self._normalize_targetname(tgt)

                    if (
                        normalized_target in active_scans or normalized_target in completed_scans
                    ):  # skip active/complete
                        continue

                    # found a directory that is not being actively scanned and has not already been scanned
                    self.run_gobuster(target=tgt)

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

            with open(
                f"recursive-gobuster_{self._normalize_targetname(self.original_target)}.log", "w"
            ) as f:
                f.write("".join(results))

            shutil.rmtree(self.tmpdir)

        raise SystemExit(0)


def get_gobuster_version() -> int:
    """ Return an int representing gobuster's version.

    There is no --version or similar for gobuster, so this function checks output of running gobuster without
    any options/arguments.  Depending on the usage statement, we determine whether or not gobuster is version
    3+ or not.

    Returns:
        int representing gobuster version; internal representation only.  Not in sync with gobuster releases
    """
    proc = subprocess.run(["gobuster"], stdout=subprocess.PIPE)

    # version 3+ with dns dir etc...
    return 3 if b"Usage:" in proc.stdout.splitlines()[0] else 2


def main(args_ns: argparse.Namespace) -> None:
    tmpdir = tempfile.mkdtemp(prefix="rcrsv-gbstr")  # directory for gobuster scan results

    # watch manager stores the watches and provides operations on watches
    wm = pyinotify.WatchManager()

    version = get_gobuster_version()

    handler = EventHandler(
        target=args_ns.target,
        tmpdir=tmpdir,
        wordlist=args_ns.wordlist,
        threads=args_ns.threads,
        extensions=args_ns.extensions,
        devnull=args.devnull,
        user=args_ns.user,
        password=args_ns.password,
        proxy=args_ns.proxy,
        version=version,
    )

    notifier = pyinotify.Notifier(wm, handler)

    # watch for file appends (found dir/file) and files closing (scan complete)
    mask = pyinotify.IN_MODIFY | pyinotify.IN_CLOSE_WRITE

    wm.add_watch(tmpdir, mask)

    handler.run_gobuster(args_ns.target)  # kick off first scan against initial target

    signal.signal(signal.SIGINT, handler.cleanup)  # register signal handler to handle SIGINT

    notifier.loop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-t", "--threads", default="20", help="# of threads for each spawned gobuster (default: 20)"
    )
    parser.add_argument(
        "-x", "--extensions", help="extensions passed to the -x option for spawned gobuster", default="",
    )
    parser.add_argument(
        "-w",
        "--wordlist",
        default="/usr/share/seclists/Discovery/Web-Content/common.txt",
        help="wordlist for each spawned gobuster (default: /usr/share/seclists/Discovery/Web-Content/common.txt)",
    )
    parser.add_argument(
        "-d", "--devnull", action="store_true", default=False, help="send stderr to devnull"
    )
    parser.add_argument("-U", "--user", help="Username for Basic Auth (dir mode only)")
    parser.add_argument("-P", "--password", help="Password for Basic Auth (dir mode only)")
    parser.add_argument(
        "-p", "--proxy", help="Proxy to use for requests [http(s)://host:port] (dir mode only)"
    )
    parser.add_argument("target", help="target to scan")

    args = parser.parse_args()

    main(args)
