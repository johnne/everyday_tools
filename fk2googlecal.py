#!/usr/bin/env python

from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

import datetime

import sys

import string

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def parsePDF(filename):
    import re
    from pyPdf import PdfFileReader
    
    ## Define regular expressions to search for ranges of days, single days and extent of days
    r_ranges = re.compile("[MTOFLS].[nsre] (\d+\/\d{1,2}) \- [MTOFLS].[nsre] (\d+\/\d{1,2})")
    r_singles = re.compile("[MTOFLS].[nsre] (\d+\/\d{1,2})")
    r_extents = re.compile("([hel1\/\d]{3}) dag")

    pdf = PdfFileReader(open(filename, "rb"))
    pages = [page.extractText() for page in pdf.pages]
    text = "".join(pages)
    ranges = r_ranges.findall(text)
    singles = r_singles.findall(text)
    extents = r_extents.findall(text)

    ## Store extents for days
    range_days = []
    days = {}
    for item in ranges: range_days+=[item[0],item[1]]
    j = 0
    range_num = 0
    for i,item in enumerate(singles):
        if item in range_days:
            days[item] = extents[j]
            if range_num==0: range_num+=1
            else:
                j+=1
                range_num = 0
        else: 
            days[item] = extents[j]
            j+=1
    
    return ranges, days

def getevents(service, now):
    events = service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()

def readcalID(infile):
    if not infile:
        import os
        infile=os.environ["HOME"]+"/.fk2cal"
    hin = open(infile)
    calID = hin.readline().rstrip()
    return calID

def init(start,end, now, name, days, add=0, events={}):
    rename_extents = {"hel": "100%", "3/4": "75%", "1/2": "50%", "1/4": "25%", "1/8": "12.5%"}
    if not name: name = "Parent"
    year = now[0:4]
    month = now[5:7]
    thisyearmonths = [string.zfill(x,2) for x in range(int(month),13)]
    nextyearmonths = [string.zfill(x,2) for x in range(1,int(month))]
    startday,startmonth = start.split("/")
    endday,endmonth = end.split("/")    
    
    startday = string.zfill(int(startday),2)
    startmonth = string.zfill(int(startmonth),2)
    
    if startmonth in thisyearmonths: startyear = year
    else: startyear = str(int(year)+1)
    if endmonth in thisyearmonths: endyear = year
    else: endyear = str(int(year)+1)
    
    if add>0:
        enddate = datetime.date(int(endyear),int(endmonth),int(endday))
        enddate += datetime.timedelta(days=add)
        endyear = str(enddate.year)
        endmonth = string.zfill(enddate.month,2)
        endday = string.zfill(enddate.day,2)    
    
    extents = list(set([days[start],days[end]]))[0]
    try: extents = rename_extents[extents]
    except KeyError: pass
    
    event = {
        'summary': name+"@"+extents,
        'start': {
            'date': startyear+"-"+startmonth+"-"+startday,
        },
        'end': {
            'date': endyear+"-"+endmonth+"-"+endday,
        },
    }
    key = event['summary']+"|"+startyear+"-"+startmonth+"-"+startday+"|"+endyear+"-"+endmonth+"-"+endday
    events[key] = event
    return events

def initEvents(service, calID, now, days, ranges, name):
    inits = {}
    for r in ranges:
        start = r[0]
        end = r[1]
        inits[start] = ""
        inits[end] = ""
        events = init(start,end, now, name, days,add=1)

    for day in days:
        if day in inits:continue
        start = day
        end = day
        events = init(start, end, now, name, days, add=0, events=events)
    return events

def getEvents(calID, now, service):
    stored_events = {}
    eventsResult = service.events().list(calendarId=calID, timeMin=now, singleEvents=True).execute()
    ## Build unique keys from the events
    events = eventsResult.get('items', [])
    for event in events:
        start = event['start'].get('date')
        end = event['end'].get('date')
        summary = event['summary']
        key = summary+"|"+start+"|"+end
        stored_events[key] = event
    return stored_events

def matchEvents(events, stored_events):
    matched_events = {}
    for key in events:
        try: matched_events[key] = stored_events[key]
        except KeyError: continue
    return matched_events

def createEvents(events, keys, calID, service):
    for key in keys:
        event = service.events().insert(calendarId=calID, body=events[key]).execute()

def deleteEvents(events, calID, service):
    for event in events.values():
        eventID = event['id']
        service.events().delete(calendarId=calID, eventId=eventID).execute()

def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-p", "--pdf", type=str,
            help="PDF with planned parental leave exported from Forsakringskassan")
    parser.add_argument("-c", "--cal", type=str,
            help="Read Google Calendar ID of the calendar to use from file. Defaults to ~/.fk2cal")
    parser.add_argument("-n", "--name", type=str,
            help="Name to insert in events (optional)")
    parser.add_argument("-d", "--delete", action="store_true",
            help="Delete events parsed from PDF")
    parser.add_argument("--deletefuture", action="store_true",
            help="Delete all future events")
    
    args = parser.parse_args()

    if not args.pdf: sys.exit(parser.print_help())
    
    ## Parse PDF to get dates
    (ranges,days) = parsePDF(args.pdf)
    
    ## Read calendar ID
    calID = readcalID(args.cal)
    
    ## Get credentials and setup calendar service
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    ## Store current date and time
    now = datetime.datetime.now().isoformat() + "Z"
    
    ## Initialize events for dates
    events = initEvents(service, calID, now, days, ranges, args.name)
    
    ## Get the stored events
    stored_events = getEvents(calID, now, service)

    ## Match parsed and stored events
    matched_events = matchEvents(events, stored_events)

    ## Non matching keys
    non_match = list(set(events.keys()).difference(set(matched_events.keys())))

    ## If deleting
    if args.delete: 
        deleteEvents(matched_events, calID, service)
        sys.exit()
    if args.deletefuture:
        deleteEvents(stored_events, calID, service)
        sys.exit()

    ## Create events for non_matching
    if len(non_match)>0:
        createEvents(events, non_match, calID, service)

if __name__ == '__main__':
    main()
