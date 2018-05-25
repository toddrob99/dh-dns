#!/bin/sh
cd /path/to/dh-dns-master/
# Check if already running, if not then run
if  ps ax | grep -v grep | grep -q /path/to/dh-dns-master/dh-dns.py; then
    :            # do nothing if already running
else
	easy_install IPy
	nohup python -u /path/to/dh-dns-master/dh-dns.py &
fi
exit 0
