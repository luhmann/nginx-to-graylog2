#!/usr/bin/env python
import sys
import re
import graypy
import logging
import argparse
import datetime
import time
from urlparse import urlparse, parse_qs
from user_agents import parse


parser = argparse.ArgumentParser(description='Load an access load file, parse it assuming a certain format and push it to a configured graylog server')
parser.add_argument('--file', dest='input', default=None, help='Please provide the location of the file that is supposed to be parsed')
args = parser.parse_args()


handler = graypy.GELFHandler('localhost', 12201, debugging_fields=False, localname="myvideo.de")
js_error_indicator = 'error.gif'
date_format = '%Y-%m-%d %H:%M:%S'

standard_logger = logging.getLogger('myvideo_access_events')
standard_logger.setLevel(logging.DEBUG)
standard_logger.addHandler(handler)

js_logger = logging.getLogger('myvideo_js_messages')
js_logger.setLevel(logging.ERROR)
js_logger.addHandler(handler)

regexp = '^(?P<varnish>\S+) \S+ \S+ \[(?P<timestamp>\S+ \S+)\] "(?P<http_method>\S*) (?P<route>\S*)[^"]*" (?P<http_response>\d+) \S* "(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)"'


file = open(args.input, 'r')
# this is getting out of hand ... we might need some functions here
for line in file:
    try:
        params = {}
        matches = re.search(regexp, line)
        if matches:
            matches = matches.groupdict()
            
            structTime = time.strptime(matches['timestamp'], '%d/%b/%Y:%H:%M:%S +0100')
            matches['event_timestamp'] = datetime.datetime(*structTime[:6]).strftime(date_format)
            matches['@timestamp'] = int(datetime.datetime(*structTime[:6]).strftime('%s'))
            matches['http_response'] = int(matches['http_response'])

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

            params.update(matches)
            route = params['route']

            if js_error_indicator in route:
                js_errors = urlparse(route)
                parsed_errors = parse_qs(js_errors.query)
                params['url'] = parsed_errors['url'][0]
                params['js_error_message'] = parsed_errors['message'][0]
                params['line'] = int(parsed_errors['line'][0])

                if 'file' in parsed_errors:
                    params['file'] = parsed_errors['file'][0]

                if 'timestamp' in parsed_errors:
                    params['js_error_timestamp'] = datetime.datetime.fromtimestamp(int(parsed_errors['timestamp'][0])/1000).strftime(date_format)
                    
                adapter = logging.LoggerAdapter(logging.getLogger('myvideo_js_messages'), params)
                adapter.error(params['js_error_message'])
            else:
                adapter = logging.LoggerAdapter(logging.getLogger('myvideo_access_events'), params)
                adapter.debug(line)
        else:
            #if no matches print out line for debugging purposes
            print line
        
    except Exception as ex:
       print ex
       print line
       continue
