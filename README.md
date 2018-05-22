# dh-dns
DreamHost DNS Updater

This project is intended to simulate dynamic DNS for DreamHost customers. It will monitor the specified domains on your DreamHost account and keep them updated when your IP public changes.

The current version support IPv4 only.

### Configuration

* Generate an API key here: https://panel.dreamhost.com/?tree=home.api
	* I suggest giving access only to the DNS functions (all 3 are required)
	* Paste the API key at the top of dh-dns.py (API_KEY = "YOUR_API_KEY_GOES_HERE")
* Update the DOMAINS list at the top of dh-dns.py with the domains you want to monitor (DOMAINS = ["dyn.example.com","test.example.com"])
* Update the COMMENT if you wish. This will be added to the DNS records if not blank (COMMENT = "Last updated by dh-dns: {date}")
* Update UPDATE_INTERVAL if you wish to update more or less frequently. Default is 60 minutes (UPDATE_INTERVAL = 60)
* Update LOG_LEVEL if you wish to log more or less info. Available options are WARNING, INFO, DEBUG and each will give more info than the last (LOG_LEVEL = "INFO")

### Running

* Install Python (written in 2.7, might not work properly in Python 3)
* Install dependent modules:
	* pip install simplejson
	* pip install IPy
* I run this on my Synology NAS as a scheduled task (at system start), using dh-dns.sh as the startup script

### Issues/Questions/Suggestions

* Feel free to post an issue on GitHub
* If you have questions or suggestions, message me on reddit (/u/toddrob), or email me (todd at toddrob.com)
