#!/usr/bin/env python
"""DNS Record Updater for DreamHost https://github.com/toddrob99/dh-dns"""

API_URL = "https://api.dreamhost.com/" # You should not need to change this
API_KEY = "YOUR_API_KEY_GOES_HERE" # Generate at https://panel.dreamhost.com/?tree=home.api
DOMAINS = ["dyn.example.com","test.example.com"] # Domains to update, list of strings
COMMENT = "Last updated by dh-dns: {date}" # Comment to add to DNS record, {date} parameter available
UPDATE_INTERVAL = 60 # Minutes
LOG_LEVEL = "INFO" # Options: WARNING, INFO, DEBUG
PROWL_API_KEY = ""  # Leave blank ("") to disable, 
                    # or generate an API key at 
                    # https://www.prowlapp.com/api_settings.php

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
    logDir = cwd + "/logs"
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    logPath = logDir + '/dh-dns.log'
    logLevel = getattr(logging, LOG_LEVEL.upper(),30)
    logger = logging.getLogger('dh-dns')
    logger.setLevel(logLevel)
    handler = handlers.TimedRotatingFileHandler(logPath,when='midnight',interval=7,backupCount=3)
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

    global PROWL_API_KEY
    if PROWL_API_KEY != "":
        logger.info("Setting up Prowl notifications...")
        prowl = Prowl(PROWL_API_KEY)
        verifyKey = prowl.verify_key()
        if verifyKey.get('status') == 'success':
            logger.info("Prowl API key successfully verified. Notifications enabled!")
        else:
            PROWL_API_KEY = ""
            prowl = None
            logger.error("Unable to verify Prowl API key. Disabling Prowl notifications. Error code: %s %s, message: %s", verifyKey.get('code'), verifyKey.get('message'), verifyKey.get('errMsg'))
    else: prowl = None

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
                        if prowl: # Send Prowl notification
                            event = 'Monitored DNS Record Not Editable: ['+domain.name+']'
                            description = 'Please check your configuration. Domain '+domain.name+' is monitored but DreamHost says it is not editable.'
                            prowlResult = prowl.send_notification(event, description)
                            if prowlResult.get('status') == 'success':
                                logger.debug("Successfully sent notification to Prowl... Event: %s, Description: %s", event, description)
                            else:
                                logger.error("Failed to send notification to Prowl... Event: %s, Description: %s, Status code: %s %s, Error message: %s", event, description, prowlResult.get('code'), prowlResult.get('message'), prowlResult.get('errMsg'))

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
                            if prowl: # Send Prowl notification
                                event = 'Failed to Delete DNS Record: ['+domain.name+']'
                                description = 'Domain '+domain.name+' needs to be updated with new IP ['+newIp+'], but the deletion failed.\nError message: '+dhRemoveResponse.get('data')
                                prowlResult = prowl.send_notification(event, description)
                                if prowlResult.get('status') == 'success':
                                    logger.debug("Successfully sent notification to Prowl... Event: %s, Description: %s", event, description)
                                else:
                                    logger.error("Failed to send notification to Prowl... Event: %s, Description: %s, Status code: %s %s, Error message: %s", event, description, prowlResult.get('code'), prowlResult.get('message'), prowlResult.get('errMsg'))
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
                        domain.lastUpdate = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                        logger.info("Successfully added domain %s with IP [%s].",domain.name,newIp)
                        if prowl: # Send Prowl notification
                            event = 'DNS Record Updated: ['+domain.name+']'
                            description = 'Successfully updated domain '+domain.name+' with IP ['+newIp+'].'
                            prowlResult = prowl.send_notification(event, description)
                            if prowlResult.get('status') == 'success':
                                logger.debug("Successfully sent notification to Prowl... Event: %s, Description: %s", event, description)
                            else:
                                logger.error("Failed to send notification to Prowl... Event: %s, Description: %s, Status code: %s %s, Error message: %s", event, description, prowlResult.get('code'), prowlResult.get('message'), prowlResult.get('errMsg'))
                    else:
                        logger.error("Error adding domain %s: %s.",domain.name,dhAddResponse.get('data'))
                        if prowl: # Send Prowl notification
                            event = 'DNS Record Update Failed: ['+domain.name+']'
                            description = 'Failed to update domain '+domain.name+' with IP ['+newIp+']:\n'+dhAddResponse.get('data')
                            prowlResult = prowl.send_notification(event, description)
                            if prowlResult.get('status') == 'success':
                                logger.debug("Successfully sent notification to Prowl... Event: %s, Description: %s", event, description)
                            else:
                                logger.error("Failed to send notification to Prowl... Event: %s, Description: %s, Status code: %s %s, Error message: %s", event, description, prowlResult.get('code'), prowlResult.get('message'), prowlResult.get('errMsg'))

            currentIp = newIp
            logger.info("Done checking/updating domains. Sleeping for %i minutes.",UPDATE_INTERVAL)

        sleep(UPDATE_INTERVAL*60)

class Prowl:
    def __init__(self, apiKey=None):
        self.apiKey = apiKey
        self.appName = "DreamHost DNS Updater (dh-dns)"

    def verify_key(self, apiKey=None):
       if apiKey == None: apiKey=self.apiKey
       return self.api_call('verify',{},apiKey)

    def send_notification(self, event, description, apiKey=None, priority=0, url=None, appName=None):
        if appName == None: appName=self.appName
        if apiKey == None: apiKey=self.apiKey

        data = {'event':event, 'description':description, 'priority':priority, 'application':appName, 'apikey':apiKey}
        if url: data.update({'url':url})
        return self.api_call('add',data,apiKey)

    def api_call(self, action, data, apiKey=None):
        if apiKey == None: apiKey=self.apiKey

        import urllib2, urllib
        url = 'https://api.prowlapp.com/publicapi/'+action
        if action=='verify': url += "?apikey="+apiKey

        encodedData = urllib.urlencode(data)
        logger.debug("Making API call to Prowl (%s) with data: %s",url, encodedData)
        try:
            req = urllib2.Request(url=url,data=encodedData)
            response = urllib2.urlopen(req).read()
        except urllib2.HTTPError as e:
            response = {'status':'error', 'code':str(e.code), 'message':e.reason}
        except urllib2.URLError as e:
            response = {'status':'error', 'code':str(e.code), 'message':e.reason}
        except Exception as e:
            response = {'status':'error', 'code':'-1', 'message':'Unknown error', 'errMsg':e}

        return self.parse_response(response)

    def parse_response(self, response):
        import xml.etree.ElementTree as ET

        errorMessages = {   
                            '-1' : 'Unknown error',
                            '200': 'Success',
                            '400': 'Bad request, the parameters you provided did not validate.',
                            '401': 'Not authorized, the API key given is not valid, and does not correspond to a user.',
                            '406': 'Not acceptable, your IP address has exceeded the API limit.',
                            '409': 'Not approved, the user has yet to approve your retrieve request.',
                            '500': 'Internal server error, something failed to execute properly on the Prowl side.'
                        }

        if isinstance(response,dict):
            if not response.get('errMsg',None): response.update({'errMsg':errorMessages[response.get('code')]})
            return response

        root = ET.fromstring(response)
        child = root[0]
        parsedResponse = {}
        parsedResponse.update({'status':child.tag, 'message':child.text, 'errMsg':errorMessages[child.get('code')]})
        for key,val in child.attrib.items():
            parsedResponse.update({key:val})

        return parsedResponse

if __name__ == '__main__':
    logger = Logger()
    logger.info("Logging started with log level %s. Log file: %s.",LOG_LEVEL,"dh-dns.log")

    domains = []
    for x in DOMAINS:
        domains.append(Domain(x))

    monitor(domains)
