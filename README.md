# recursive-gobuster
A wrapper around [gobuster](https://github.com/OJ/gobuster) that automatically scans newly discovered directories.

## Why though?

@OJ designed gobuster to not be recursive.  In fact, it's [#3](https://github.com/OJ/gobuster#oh-dear-god-why) in the list of reasons describing why he wrote gobuster in the first place.  He's a much smarter man than I and I'm sure his reasoning for not including the capability is sound, but I wanted the ability to kick off a scan with my favorite scanner and walk away.  

I started off looking for something ready-made. I found and really liked [Ryan Wendel's](http://www.ryanwendel.com/2017/08/06/recursive-gobuster-script/) shell script to accomplish recursive gobuster scanning.  However, there were a few minor behavioral things I wanted to tweak.  I also wanted to speed up execution a bit.  His original script is what prompted me to write this one.  

## Dependencies 

- [pyinotify](https://github.com/seb-m/pyinotify)

## Install

`recursive-gobuster` is distributed with a pre-packaged executable zip file.  This way, those who want to use this tool can do so without needing to manage their own virtualenv. 

```
git clone https://github.com/epi052/recursive-gobuster.git

./recursive-gobuster/recursive-gobuster.pyz 
usage: recursive-gobuster.pyz [-h] [-t THREADS] [-x EXTENSIONS] [-w WORDLIST]
                              target
```

Optionally, set it somewhere in your PATH

`sudo ln -s $(pwd)/recursive-gobuster/recursive-gobuster.pyz /usr/local/bin`

## Build 
There is a `build.sh` script included that performs the following actions:

- installs [pyinotify](https://github.com/seb-m/pyinotify) into the `recursive-gobuster` directory
- removes pip metadata
- creates an executable zip using python's [zipapp](https://docs.python.org/3/library/zipapp.html) library
- ensures the executable zip has the executable bit set

Since there is a prebuilt package included in the repo, the build script is primarily included in case you want to modify the functionality of the script and afterwards would like to rebuild the executable zip. That workflow would look something like this:

1. modify `recursive-gobuster/__main__.py` to your liking 
2. delete or backup current `recursive-gobuster.pyz`
3. run `build.sh`

## Tool Behavior

`recursive-gobuster` isn't recursive in the sense of how it works, only in that it will continue scanning directories until there are no more identified.  These are the high-level steps it takes to scan:

1. Creates a temporary directory and sets an `inotify` watch on the same directory.
2. Begins a `gobuster` scan against the specified _target url_.
3. Defines the scan's output file to be located within the watched directory.
4. Watches the initial (and all subsequent) scan output file for two filesystem events [IN_MODIFY](https://github.com/seb-m/pyinotify/wiki/Events-types) and [IN_DELETE](https://github.com/seb-m/pyinotify/wiki/Events-types).  Each time a file is **modified**, any new sub-directory identified is used as the _target url_ for a new scan.  The new scans begin as soon as a new sub-directory is seen (i.e. asynchronously).  When a file is **closed**, it signifies the end of that particular scan.
5. Cleans up the temporary directory when all scans are complete.
6. Creates a sorted log file of all results in the current working directory.

## Considerations
I wrote this tool for me, to be integrated into my workflow with my preferences in mind.  As such, there are some things to be aware of that you may or may not care for.

- STDERR is mapped to `/dev/null`.  I do this to suppress the wildcard error messages from gobuster, it's a personal preference and I've commented the code where it can be reenabled if that's your thing.
- There is no limit placed on the number of concurrent scans and no option to do rate limiting. Each one is its own separate process, however this behavior may not be desirable, depending on your target and host machine.
- The tool is pretty opinionated about options fed to gobuster.  Removing the `-f`, `-e`, or `-n` will likely break functionality of the tool.  The other options are either configurable via command line options, or can be manipulated in the source code without any adverse side-effects

| hard-coded options | meaning |
|----|--------------------------------------------------|
| -f | Append a forward-slash to each directory request |
| -q | Don't print the banner and other noise           |
| -n | Don't print status codes                         |
| -r | Follow redirects                                 |
| -e | Expanded mode, print full URLs                   |
| -k | Skip SSL certificate verification                |
| -a | Set the User-Agent string                        |

Knowing all that, it's still just a python script and can easily be manipulated to your own preferences.  I've included `build.sh` so you can make changes and easily generate a new packaged version.  

## Examples 

### Standard run with defaults 
The default wordlist is `seclists/Discovery/Web-Content/common.txt`.  The default number of threads is `20`.  There are no extensions by default.

```
time /opt/recursive_gobuster.pyz http://10.10.10.112
http://10.10.10.112/.htaccess/
http://10.10.10.112/.htpasswd/
http://10.10.10.112/.hta/
http://10.10.10.112/Images/
http://10.10.10.112/Images/.htaccess/
http://10.10.10.112/Images/.hta/
http://10.10.10.112/Images/.htpasswd/
http://10.10.10.112/assets/
http://10.10.10.112/assets/.htpasswd/
http://10.10.10.112/assets/.hta/
http://10.10.10.112/assets/.htaccess/
http://10.10.10.112/assets/css/
http://10.10.10.112/assets/css/.hta/
http://10.10.10.112/assets/css/.htaccess/
http://10.10.10.112/assets/css/.htpasswd/
http://10.10.10.112/images/
http://10.10.10.112/images/.hta/
http://10.10.10.112/images/.htaccess/
http://10.10.10.112/images/.htpasswd/
http://10.10.10.112/assets/fonts/
http://10.10.10.112/assets/fonts/.hta/
http://10.10.10.112/assets/fonts/.htaccess/
http://10.10.10.112/assets/fonts/.htpasswd/
http://10.10.10.112/assets/js/
http://10.10.10.112/assets/js/.htpasswd/
http://10.10.10.112/assets/js/.hta/
http://10.10.10.112/assets/js/.htaccess/
All scans complete. Cleaning up.

real	0m37.033s
user	0m0.162s
sys	0m0.112s

# ls -l recursive*
-rw-r--r--  1 root root    962 Jan 11 20:42 recursive_gobuster_http:__10.10.10.112.log

```

### Scan with extensions
```
/opt/recursive_gobuster.pyz -x php,html http://10.10.10.112
http://10.10.10.112/.htaccess/
-------- 8< --------
```

### Scan with different wordlist

```
/opt/recursive_gobuster.pyz -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt http://10.10.10.112
http://10.10.10.112/.htaccess/
-------- 8< --------
```
