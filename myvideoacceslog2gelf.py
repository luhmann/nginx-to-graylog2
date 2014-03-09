#!/usr/bin/env python
#
import sys
import re
import graypy
import logging
import argparse
import datetime
import time
import os.path
from urlparse import urlparse, parse_qs
from user_agents import parse

"""
Get the arguments from the command line
Invoke with python myvideoaccesslog2gelf.py --file <filename>

:param file     The name and path of the input file, will look for matching files with standard log-rotation pattern in the same filepath
"""
parser = argparse.ArgumentParser(description='Load an access load file, parse it assuming a certain format and push it to a configured graylog server')
parser.add_argument('--file', dest='input', default=None, help='Please provide the location of the file that is supposed to be parsed')
args = parser.parse_args()

# Settings
handler = graypy.GELFHandler('localhost', 12201, debugging_fields=False, localname="myvideo.de")
js_error_indicator = 'error.gif'
date_format = '%Y-%m-%d %H:%M:%S'
healthcheckString = '/_internal/healthcheck'

# Regex for the access-log format
regexp = '^(?P<varnish>\S+) \S+ \S+ \[(?P<timestamp>\S+ \S+)\] "(?P<http_method>\S*) (?P<route>\S*)[^"]*" (?P<http_response>\d+) \S* "(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)"'

# Setup a standard logger for all non js-error-logging events
# Log-Level Debug
standard_logger = logging.getLogger('myvideo_access_events')
standard_logger.setLevel(logging.DEBUG)
standard_logger.addHandler(handler)

# Setup another logger for the targeted js-error messages
# Log Level Error
js_logger = logging.getLogger('myvideo_js_messages')
js_logger.setLevel(logging.ERROR)
js_logger.addHandler(handler)

"""
The actual file-parser

:param filename       The current filepath that we try to parse
"""
def parseFile(filename):
  file = open(filename, 'r')

  #Setup a loop index to keep track of how many files have been imported
  loopIndex = 0
  for line in file:
    try:
        # the dictionary holding the fields that will be pushed to elastic search
        params = {}
        matches = re.search(regexp, line)

        if matches:
            matches = matches.groupdict()

            #skip all healtcheck requests
            if healthcheckString in matches['message']
              continue

            # parse timestamp of log entry and try to set it as the actual timestamp
            structTime = time.strptime(matches['timestamp'], '%d/%b/%Y:%H:%M:%S +0100')
            matches['event_timestamp'] = datetime.datetime(*structTime[:6]).strftime(date_format)
            matches['@timestamp'] = int(datetime.datetime(*structTime[:6]).strftime('%s'))

            # make sure this is an integer so we can run some statistics in elastic search on it
            matches['http_response'] = int(matches['http_response'])

            # parse user-agent string to get some extended inforamtion
            user_agent = matches['user_agent']
            user_agent = parse(user_agent)
            params['browser'] = (user_agent.browser.family + ' ' + user_agent.browser.version_string).encode('utf-8')
            params['device'] = user_agent.device.family.encode('utf-8')
            params['os'] = (user_agent.os.family + user_agent.os.version_string).encode('utf-8')
            params['is_mobile'] = user_agent.is_mobile
            params['is_tablet'] = user_agent.is_tablet
            params['is_touch_capable'] = user_agent.is_touch_capable
            params['is_pc'] = user_agent.is_pc
            params['is_bot'] = user_agent.is_bot

            params['deviceAndOs'] = (params['device'] + ' ' + params['os']).encode('utf-8')

            params.update(matches)

            # check if this is an js error report
            route = params['route']
            if js_error_indicator in route:
                # if yes parse the route and extract the information we are looking for
                js_errors = urlparse(route)
                parsed_errors = parse_qs(js_errors.query)
                params['url'] = parsed_errors['url'][0]
                params['js_error_message'] = parsed_errors['message'][0]
                params['line'] = int(parsed_errors['line'][0])

                if 'file' in parsed_errors:
                    params['file'] = parsed_errors['file'][0]

                if 'timestamp' in parsed_errors:
                    params['js_error_timestamp'] = datetime.datetime.fromtimestamp(int(parsed_errors['timestamp'][0])/1000).strftime(date_format)

                # log the error
                adapter = logging.LoggerAdapter(logging.getLogger('myvideo_js_messages'), params)
                adapter.error(params['js_error_message'])
            else:
                # otherwise just log the message
                adapter = logging.LoggerAdapter(logging.getLogger('myvideo_access_events'), params)
                adapter.debug(line)
        else:
            #if no matches print out line for debugging purposes
            print line

        # provide some feedback
        if loopIndex%10000 == 0:
          print filename + ': Parsed ' + str(loopIndex) + ' Events'

        loopIndex += 1
    except Exception as ex:
       print ex
       print line
       loopIndex += 1
       continue

fileLoopCounter = 0
fileExists = True

# Iterate all the files that match the pattern, otherwise stop
while fileExists:
  extension = '.' + str(fileLoopCounter) if fileLoopCounter > 0 else ''
  filename = args.input + extension

  if os.path.isfile(filename):
    print '------------------------------- PARSING NEW FILE ' + filename + '-------------------------------------------'
    parseFile(filename)
  else:
    fileExists = False
    break

  fileLoopCounter += 1
