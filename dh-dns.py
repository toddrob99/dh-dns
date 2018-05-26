#!/usr/bin/env python
"""DNS Record Updater for DreamHost https://github.com/toddrob99/dh-dns"""

API_URL = "https://api.dreamhost.com/" # You should not need to change this
API_KEY = "YOUR_API_KEY_GOES_HERE" # Generate at https://panel.dreamhost.com/?tree=home.api
DOMAINS = ["dyn.example.com","test.example.com"] # Domains to update, list of strings
COMMENT = "Last updated by dh-dns: {date}" # Comment to add to DNS record, {date} parameter available
UPDATE_INTERVAL = 60 # Minutes
LOG_LEVEL = "INFO" # Options: WARNING, INFO, DEBUG

""" DO NOT CHANGE ANYTHING BELOW THIS LINE """

from uuid import uuid4
import urllib
import urllib2
import simplejson as json
from datetime import datetime
from time import sleep
from IPy import IP

class Domain:
    def __init__(self,domain):
        self.name = domain
        self.lastUpdate = None
        logger.info("Domain added: %s",self.name)

class DreamHost:
    cmds = {
            'list': 'dns-list_records',
            'remove': 'dns-remove_record',
            'add': 'dns-add_record'
    }

    def __init__(self,apiUrl,apiKey):
        self.url = apiUrl + "?key=" + API_KEY + "&format=json"
        self.apiKey = apiKey
        self.allDomains = {}

    def api_call(self,cmd):
        url = self.url + "&unique_id="+str(uuid4())[:64]+"&cmd="+cmd
        logger.debug("Making DreamHost API call: %s",url)
        try:
            apiResponse = json.load(urllib2.urlopen(url))
            logger.debug("API Response: %s",apiResponse)
            return apiResponse
        except urllib2.HTTPError, e:
            logger.error("DreamHost API responded with error: %s",e)
            return {'result':'error','data':str(e)}
        except urllib2.URLError:
            logger.error("Connection to DreamHost API failed.")
            return {'result':'error','data':str(e)}
        except Exception, e:
            logger.error("Unknown error encountered while making API call: %s",e)
            return {'result':'error','data':str(e)}

class Logger:
    import logging
    from logging import handlers
    import os
    cwd = os.path.dirname(os.path.realpath(__file__))
    logLevel = getattr(logging, LOG_LEVEL.upper(),30)
    #logging.basicConfig(filename=cwd+"/dh-dns.log", format='%(asctime)s : %(levelname)s : %(message)s', 
    #                    datefmt='%Y-%m-%d %I:%M:%S %p', level=logLevel)
    logger = logging.getLogger('dh-dns')
    logger.setLevel(logLevel)
    handler = handlers.TimedRotatingFileHandler(cwd+'/dh-dns.log',when='midnight',interval=7,backupCount=3)
    formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #aliases to shorten calls (logger.logger.info -> logger.info)
    info = logger.info
    warn = logger.warn
    error = logger.error
    debug = logger.debug

def monitor(domains):
    """ domains is a list of Domain class objects """
    dh = DreamHost(API_URL,API_KEY)
    currentIp = ""

    while True: # Enter update loop
        # Pull current domain info from DH
        dhDomainResponse = dh.api_call(dh.cmds['list']) # List all domains from DH account
        if dhDomainResponse.get('result') == 'success':
            for data in [data for data in dhDomainResponse.get('data') if data.get('type')=='A']:
                dh.allDomains.update({data.get('record'): {'value': data.get('value'), 
                                      'editable': data.get('editable'), 
                                      'comment': data.get('comment')
                                    }})
            logger.debug("All A records from DreamHost: %s",format(dh.allDomains))
        else:
            logger.error("Error reported by DreamHost API: %s.",dhDomainResponse.get('data'))

        newIp = ""
        validIp = False

        # Get current IP
        try:
            newIp = urllib2.urlopen("https://toddrob.com/ip.php?bot=1").read().strip()
            ipType = IP(newIp).iptype()
            if ipType != 'PUBLIC':
                logger.warn("%s IP address detected: [%s]. PUBLIC IP required, ignoring.",ipType,newIp)
            else:
                logger.debug("%s IP address detected: [%s].",ipType,newIp)
                validIp = True
        except urllib2.HTTPError, e:
            logger.error("IP lookup responded with error: %s.",e)
        except urllib2.URLError:
            logger.error("Connection to IP lookup failed.")
        except ValueError, e:
            logger.error("Invalid IP address detected: %s.",e)
        except Exception, e:
            logger.error("Unknown error encountered while looking up current IP: %s.",e)

        if not validIp:
            try:
                IP(currentIp) # Failed to look up current IP, so check if last known IP is valid
            except ValueError, e:
                logger.error("Last known IP is invalid: %s. Skipping domain check and sleeping for %i minutes.",e,UPDATE_INTERVAL)
            else:
                newIp = currentIp
                validIp = True
                logger.info("Checking domains against last known IP: [%s].",newIp)

        if validIp:
            for domain in domains:
                addFlag = False
                if dh.allDomains.get(domain.name):
                    # Monitored domain already exists
                    if dh.allDomains.get(domain.name).get('editable') == "0":
                        logger.warn("Domain %s is not editable, skipping.",domain.name)
                    elif dh.allDomains.get(domain.name).get('value') == newIp:
                        logger.info("No update needed for %s.",domain.name)
                    else:
                        # Update needed - remove record and set flag to add it
                        logger.info("New IP detected for %s: [%s]. Deleting existing record.",domain.name,newIp)
                        dhRemoveResponse = dh.api_call(dh.cmds['remove'] + "&type=A&record=" + domain.name + \
                                                       "&value=" + dh.allDomains.get(domain.name).get('value'))
                        if dhRemoveResponse.get('result') == 'success':
                            logger.info("Successfully deleted domain %s.",domain.name)
                            addFlag = True
                        else:
                            logger.error("Error deleting domain %s: %s.",domain.name,dhRemoveResponse.get('data'))
                else:
                    # Monitored domain does not exist
                    logger.info("Domain %s does not exist.",domain.name)
                    addFlag = True

                if addFlag:
                    if len(COMMENT)>0:
                        comment = "&comment=" + urllib.quote_plus(COMMENT.replace("{date}",
                                                                  datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
                    else:
                        comment = ""
                    dhAddResponse = dh.api_call(dh.cmds['add'] + "&record=" + domain.name + "&type=A&value=" + newIp + comment)
                    if dhAddResponse.get('result') == 'success':
                        logger.info("Successfully added domain %s with IP [%s].",domain.name,newIp)
                        domain.lastUpdate = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                    else:
                        logger.error("Error adding domain %s: %s.",domain.name,dhAddResponse.get('data'))

            currentIp = newIp
            logger.info("Done checking/updating domains. Sleeping for %i minutes.",UPDATE_INTERVAL)

        sleep(UPDATE_INTERVAL*60)

if __name__ == '__main__':
    logger = Logger()
    logger.info("Logging started with log level %s. Log file: %s.",LOG_LEVEL,"dh-dns.log")

    domains = []
    for x in DOMAINS:
        domains.append(Domain(x))

    monitor(domains)
