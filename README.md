![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

# recursive-gobuster
A wrapper around [gobuster](https://github.com/OJ/gobuster) that automatically scans newly discovered directories.

## Why though?

@OJ designed gobuster to not be recursive.  In fact, it's [#3](https://github.com/OJ/gobuster#oh-dear-god-why) in the list of reasons describing why he wrote gobuster in the first place.  He's a much smarter man than I and I'm sure his reasoning for not including the capability is sound, but I wanted the ability to kick off a scan with my favorite scanner and walk away.  

I started off looking for something ready-made. I found and really liked [Ryan Wendel's](http://www.ryanwendel.com/2017/08/06/recursive-gobuster-script/) shell script to accomplish recursive gobuster scanning.  However, there were a few minor behavioral things I wanted to tweak.  I also wanted to speed up execution a bit.  His original script is what prompted me to write this one.  

## Dependencies 

- [pyinotify](https://github.com/seb-m/pyinotify)
- python >= 3.6

## Install

`recursive-gobuster` is distributed with a pre-packaged executable zip file.  This way, those who want to use this tool can do so without needing to manage their own virtualenv. 

```
git clone https://github.com/epi052/recursive-gobuster.git

./recursive-gobuster/recursive-gobuster.pyz 
usage: recursive-gobuster.pyz [-h] [-t THREADS] [-x EXTENSIONS] [-w WORDLIST]
                              [-d]
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

- There is no limit placed on the number of concurrent scans and no option to do rate limiting. Each one is its own separate process, however this behavior may not be desirable, depending on your target and host machine.
- The tool is pretty opinionated about options fed to gobuster.  Removing the `-e`, or `-n` will likely break functionality of the tool.  The other options are either configurable via command line options, or can be manipulated in the source code without any adverse side-effects

| hard-coded options | meaning |
|----|--------------------------------------------------|
| -q | Don't print the banner and other noise           |
| -n | Don't print status codes                         |
| -e | Expanded mode, print full URLs                   |
| -k | Skip SSL certificate verification                |

Knowing all that, it's still just a python script and can easily be manipulated to your own preferences.  I've included `build.sh` so you can make changes and easily generate a new packaged version.  

## Examples 

### Standard run with defaults 
The default wordlist is `seclists/Discovery/Web-Content/common.txt`.  The default number of threads is `20`.  There are no extensions by default.

```
time /opt/recursive_gobuster.pyz http://10.10.10.112
http://10.10.10.112/.hta/
http://10.10.10.112/.htpasswd/
http://10.10.10.112/.htaccess/
2019/01/17 05:49:34 [-] Wildcard response found: http://10.10.10.112/.htpasswd/a1612d11-2fda-486f-a039-d5aef1556386 => 403
2019/01/17 05:49:34 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:34 [-] Wildcard response found: http://10.10.10.112/.hta/b2b5e936-7574-41c8-bb60-022c81b0b325 => 403
2019/01/17 05:49:34 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:34 [-] Wildcard response found: http://10.10.10.112/.htaccess/5ae6f6d2-7269-48e4-af73-b6d604f6d3b2 => 403
2019/01/17 05:49:34 [!] To force processing of Wildcard responses, specify the '-fw' switch.
http://10.10.10.112/Images/
http://10.10.10.112/Images/.htaccess/
http://10.10.10.112/Images/.htpasswd/
http://10.10.10.112/Images/.hta/
2019/01/17 05:49:35 [-] Wildcard response found: http://10.10.10.112/Images/.htpasswd/12ec114e-3818-499e-bcb2-9b4139e6eb71 => 403
2019/01/17 05:49:35 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:35 [-] Wildcard response found: http://10.10.10.112/Images/.htaccess/003ce118-407c-483f-9edd-cb7cad646685 => 403
2019/01/17 05:49:35 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:35 [-] Wildcard response found: http://10.10.10.112/Images/.hta/f0f57fb2-93f5-4c5c-9cc9-84c09090e8ad => 403
2019/01/17 05:49:35 [!] To force processing of Wildcard responses, specify the '-fw' switch.
http://10.10.10.112/assets/
http://10.10.10.112/assets/.htaccess/
http://10.10.10.112/assets/.hta/
http://10.10.10.112/assets/.htpasswd/
2019/01/17 05:49:36 [-] Wildcard response found: http://10.10.10.112/assets/.htaccess/6fe86826-d623-4119-a1e4-b54edac070b3 => 403
2019/01/17 05:49:36 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:36 [-] Wildcard response found: http://10.10.10.112/assets/.hta/6259ad75-3d6a-4881-9a19-cad99623b204 => 403
2019/01/17 05:49:36 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:36 [-] Wildcard response found: http://10.10.10.112/assets/.htpasswd/5d2a8a43-9fe7-4f37-8fee-1498ae9048da => 403
2019/01/17 05:49:36 [!] To force processing of Wildcard responses, specify the '-fw' switch.
http://10.10.10.112/assets/css/
http://10.10.10.112/images/
http://10.10.10.112/assets/css/.htpasswd/
http://10.10.10.112/assets/css/.htaccess/
http://10.10.10.112/assets/css/.hta/
2019/01/17 05:49:41 [-] Wildcard response found: http://10.10.10.112/assets/css/.htpasswd/dc99e161-2379-4f98-930d-90248641fe73 => 403
2019/01/17 05:49:41 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:41 [-] Wildcard response found: http://10.10.10.112/assets/css/.htaccess/dd6b320c-a54b-4e29-9821-dd7b78b68c82 => 403
2019/01/17 05:49:41 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:41 [-] Wildcard response found: http://10.10.10.112/assets/css/.hta/917be959-5ac9-4201-b44f-c89dc1c9bcb5 => 403
2019/01/17 05:49:41 [!] To force processing of Wildcard responses, specify the '-fw' switch.
http://10.10.10.112/images/.htaccess/
http://10.10.10.112/images/.htpasswd/
http://10.10.10.112/images/.hta/
2019/01/17 05:49:41 [-] Wildcard response found: http://10.10.10.112/images/.hta/dfb25bd1-26c3-4fcd-9e0e-605fa3354505 => 403
2019/01/17 05:49:41 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:41 [-] Wildcard response found: http://10.10.10.112/images/.htpasswd/5ccb242b-0c03-4df1-9132-20fe8cc4b01b => 403
2019/01/17 05:49:41 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:41 [-] Wildcard response found: http://10.10.10.112/images/.htaccess/f64e7160-f6b6-4c89-a76f-1a34b3f879a5 => 403
2019/01/17 05:49:41 [!] To force processing of Wildcard responses, specify the '-fw' switch.
http://10.10.10.112/assets/fonts/
http://10.10.10.112/assets/fonts/.htaccess/
http://10.10.10.112/assets/fonts/.hta/
http://10.10.10.112/assets/fonts/.htpasswd/
2019/01/17 05:49:43 [-] Wildcard response found: http://10.10.10.112/assets/fonts/.htaccess/c29f202e-6bc1-47b0-bcaf-b450dbec87fc => 403
2019/01/17 05:49:43 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:43 [-] Wildcard response found: http://10.10.10.112/assets/fonts/.hta/d0df1e60-81bc-4516-bcae-ea03999acbdb => 403
2019/01/17 05:49:43 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:43 [-] Wildcard response found: http://10.10.10.112/assets/fonts/.htpasswd/03f5de0a-396b-4dc7-9d08-7b46202e3641 => 403
2019/01/17 05:49:43 [!] To force processing of Wildcard responses, specify the '-fw' switch.
http://10.10.10.112/assets/js/
http://10.10.10.112/assets/js/.hta/
http://10.10.10.112/assets/js/.htaccess/
http://10.10.10.112/assets/js/.htpasswd/
2019/01/17 05:49:44 [-] Wildcard response found: http://10.10.10.112/assets/js/.htpasswd/5c192b5e-8ef2-4a98-a850-64ff3308f82e => 403
2019/01/17 05:49:44 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:44 [-] Wildcard response found: http://10.10.10.112/assets/js/.hta/bf5b535a-ced5-4d4e-9de4-8f748473615c => 403
2019/01/17 05:49:44 [!] To force processing of Wildcard responses, specify the '-fw' switch.
2019/01/17 05:49:44 [-] Wildcard response found: http://10.10.10.112/assets/js/.htaccess/f1483aeb-8572-4186-8221-19bddcf57ef7 => 403
2019/01/17 05:49:44 [!] To force processing of Wildcard responses, specify the '-fw' switch.
All scans complete. Cleaning up.

real	0m37.033s
user	0m0.162s
sys	0m0.112s

# ls -l recursive*
-rw-r--r--  1 root root    962 Jan 11 20:42 recursive_gobuster_http:__10.10.10.112.log

```

### Scan with STDERR sent to /dev/null
This option is included to suppress all the **Wildcard response** messages sent to STDERR.

```
/opt/recursive_gobuster.pyz -d http://10.10.10.112
http://10.10.10.112/.hta/
http://10.10.10.112/.htpasswd/
http://10.10.10.112/.htaccess/
http://10.10.10.112/Images/
http://10.10.10.112/Images/.htaccess/
http://10.10.10.112/Images/.htpasswd/
http://10.10.10.112/Images/.hta/
http://10.10.10.112/assets/
http://10.10.10.112/assets/.htaccess/
http://10.10.10.112/assets/.htpasswd/
http://10.10.10.112/assets/.hta/
http://10.10.10.112/assets/css/
http://10.10.10.112/images/
http://10.10.10.112/assets/css/.htaccess/
http://10.10.10.112/assets/css/.hta/
http://10.10.10.112/assets/css/.htpasswd/
http://10.10.10.112/images/.htaccess/
http://10.10.10.112/images/.htpasswd/
http://10.10.10.112/images/.hta/
http://10.10.10.112/assets/fonts/
http://10.10.10.112/assets/fonts/.hta/
http://10.10.10.112/assets/fonts/.htaccess/
http://10.10.10.112/assets/fonts/.htpasswd/
http://10.10.10.112/assets/js/
http://10.10.10.112/assets/js/.htaccess/
http://10.10.10.112/assets/js/.hta/
http://10.10.10.112/assets/js/.htpasswd/
All scans complete. Cleaning up.

real	0m37.141s
user	0m0.182s
sys	0m0.073s
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
