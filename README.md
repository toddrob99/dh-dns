# dh-dns
DreamHost DNS Updater

This project is intended to simulate dynamic DNS for DreamHost customers. It will monitor the specified domains on your DreamHost account and keep them updated when your IP public changes.

The current version support IPv4 only.

### Configuration

* Generate an API key here: https://panel.dreamhost.com/?tree=home.api
	* I suggest giving access only to the DNS functions (all 3 are required)
	* Paste the API key at the top of dh-dns.py (`API_KEY = "YOUR_API_KEY_GOES_HERE"`)
* Update the `DOMAINS` list at the top of dh-dns.py with the domains you want to monitor (`DOMAINS = ["dyn.example.com","test.example.com"]`)
* Update the `COMMENT` if you wish. This will be added to the DNS records if not blank (`COMMENT = "Last updated by dh-dns: {date}"`)
* Update `UPDATE_INTERVAL` if you wish to update more or less frequently. Default is 60 minutes (`UPDATE_INTERVAL = 60`)
* Update `LOG_LEVEL` if you wish to log more or less info. Available options are `WARNING`, `INFO`, `DEBUG` and each will give more info than the last (`LOG_LEVEL = "INFO"`)

### Running

* Install Python (written for Python 3.5+ as of v1.4, might not work properly with earlier versions)
* Install dependent modules:
	* `pip install pyprowl`
	* `pip install IPy`
	* `pip install requests`
* I run this on my Synology NAS as a scheduled task (at system start), using `dh-dns.sh` as the startup script

### Issues/Questions/Suggestions

* Feel free to post an issue on GitHub
* If you have questions or suggestions, message me on reddit (/u/toddrob), or email me (todd at toddrob.com)

### Changelog

#### v1.4
* Updated to run on Python 3.5+
* Added support for `flake8` linting and `black` formatting
* Removed `simplejson` and `urllib2` dependencies, replaced with `requests`
* Removed `Prowl` class in favor of `pyprowl` module
* Updated to use `api.ipify.org` to get current public IP

#### v1.2
* Added support for Prowl notifications
* Moved dh-dns.log to logs directory, set weekly log file rotation with retention of 3 previous files (via `Logger` class)
* Add `IPy` and `simplejson` dependency installs to `dh-dns.sh` startup script

#### v1.1
* Check individual domains even if last known IP matches newly-detected IP. That way if an update failed last time around, it will try again.
* Improved logging
* Added dh-dns.sh to run as a daemon on Linux (I use it on Synology)
* Updated README
