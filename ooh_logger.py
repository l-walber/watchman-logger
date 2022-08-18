# Out of Hours/Autolog script
# Written by L Walber, IT Services, University of Aberdeen
# l.walber@abdn.ac.uk
# some time, 2015

'''This script pulls down the XML file sent from our out of hours support,
splits it into individual calls and emails them on to our Autolog system.'''

# imports
import logging
import sys
import os
import poplib
import smtplib
import html
import datetime
import string
import logging.handlers
from email import parser
import email.utils
from email.mime.text import MIMEText
from oohconfig import CONFIG, TEMPLATE

# Try to import the fast C version, or regular py version if that fails
try:
    import xml.etree.cElementTree as X
except ImportError:
    import xml.etree.ElementTree as X


def main():
    # declare globals for reuse in functions - otherwise the scope will be limited to just main()
    global log
    global TODAY
    global FILEPATH
    global STATUS

    # constants/variables
    dateformat = "%d%m%y"
    TODAY = datetime.date.today().strftime(dateformat)
    FILEPATH = os.path.dirname(os.path.realpath(__file__))
    xmlDir = FILEPATH + '\\xml\\'
    STATFILE = FILEPATH + '\\stats.csv'
    LOGFILE = FILEPATH + '\\auto.log'

    STATUS = {1: 'Pending', 2: 'Unassigned', 3: 'Unaccepted', 4: 'On Hold',
              5: 'Off Hold', 6: 'Resolved', 7: 'Deferred', 8: 'Incoming',
              9: 'Escalated(O)', 10: 'Escalated(G)', 11: 'Escalated(A)',
              16: 'Closed', 17: 'Cancelled', 18: 'Closed Chargeable'}

    # fixes or library changes
    poplib._MAXLINE = 20480  # fix for "line too long" error in getMail

    # set up the logger
    LOGFORMAT = '%(asctime)s - %(funcName)s - %(levelname)s - %(message)s'
    # formats the logging string. This one will look like:
    # 31/03/2016 13:22:36,044 - main - DEBUG - This is an example message.

    log = logging.getLogger('main')
    handler = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=CONFIG['logsize'], backupCount=CONFIG['logbackups'],)

    if CONFIG['debug']:
        log.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)

    formatter = logging.Formatter(LOGFORMAT)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    log.info('Starting up.')

    if check_for_XML(xmlDir, TODAY):
        log.warning('Successfully ran earlier. Terminating script.')
        sys.exit()

    xmlFile = getAttachments(xmlDir)

    if xmlFile is None:
        log.warning('No XML retrieved. Terminating script.')
        sys.exit()

    root = getXML(xmlDir, xmlFile)

    calls = parseCalls(root)

    with open(STATFILE, 'a') as f:
        f.write('%s, %s\n' % (datetime.date.today(), len(calls)))

    if len(calls) == 0:
        log.warning('No calls for today. Terminating.')
        sys.exit()

    sendMail(calls)

    log.info('%s calls logged today. Process complete.' % len(calls))

# functions


def getMail():
    '''Retrieve emails from account specified in config file.'''

    log.info('Retrieving mail.')
    pop_conn = poplib.POP3_SSL(CONFIG['popserver'])
    pop_conn.user(CONFIG['username'])
    pop_conn.pass_(CONFIG['password'])
    # retrieve messages from server with a list comprehension
    # will need to change this because piecing together every single message
    # only to discard all but one is not ideal
    messages = [pop_conn.retr(i) for i in range(1, len(pop_conn.list()[1]) + 1)]
    # Stick the message pieces together with newlines
    messages = ["\n".join(mssg[1]) for mssg in messages]
    # parse message into an email object
    messages = [parser.Parser().parsestr(mssg) for mssg in messages]

    pop_conn.quit()  # disconnect from the server cleanly

    log.debug('Retrieved %s emails.' % len(messages))

    return messages


def getAttachments(xmlDir):
    '''Extract XML file from the emails retrieved.'''

    attachment = None
    messages = getMail()
    for msg in messages:
        for part in msg.walk():
            if part.get_filename() is not None:
                # check if the file extension is xml. tried to use MIMEtypes
                # but OOH doesn't use these properly
                partname = part.get_filename()
                if partname.endswith():
                    xmlname = partname.split('.')[0]
                    attachmentDate = xmlname[-6:]
                    log.debug('Today:%s, file:%s' % (TODAY, attachmentDate))
                    if TODAY == attachmentDate:  # if it matches, download
                        data = part.get_payload(decode=True)
                        with open(xmlDir + partname, 'wb') as f:
                            f.write(data)
                        attachment = partname
    if attachment is not None:
        log.info('Retrieved file %s.' % attachment)
    else:
        log.warning('File not found - try again later.')

    return attachment


def getXML(xmlDir, xmlFile):
    '''Open XML file and return root object.'''

    log.debug('Getting root for xmlfile %s' % xmlFile)
    with open(xmlDir + xmlFile, 'r') as g:
        tree = X.parse(g)
    root = tree.getroot()
    return root


def parseCalls(xml):
    '''Work through XML file and return a list of call/dictionary objects.'''
    log.debug('Parsing XML file.')
    calls = []
    UNK = {'XY001': 'Unknown Student', 'XY002': 'Unknown Staff',
           'XY003': 'Unknown Unknown'}  # cleaner way of getting a name + username for unknowns

    for n, s in enumerate(sorted(STATUS)):
        log.debug('Checking status code %s.' % s)
        for i, call in enumerate(xml.findall("./statuses/status_group/[@id='%s']/tickets/" % s)):
            callref = call.find('callref').text
            user = call.find('cust_id').text
            if user in UNK:
                log.debug('User marked as "%s", changing to %s.' % (user, UNK[user]))
                user = UNK[user]
            t = int(call.find('logdatex').text)  # logtime is provided as ctime
            logtime = datetime.datetime.fromtimestamp(t)  # this changes it to something readable
            logtime = logtime.strftime('%d.%m.%y : %H:%M:%S')
            problem = call.find('prob_info').text + ':\n\n'

            updates = call.findall('./updates/')
            for update in updates:
                updatetext = update.findall('./updatetxt')
                for u in updatetext:
                    up = u.text
                    problem += '\n' + up

            problem = html.unescape(problem)

            res = STATUS[s]

            callDict = {'ref': callref, 'res': res, 'user': user,
                        'time': logtime, 'problem': problem}

            calls.append(callDict)
            n += 1

        if n > 0:
            log.info('Found %s calls in status %s: %s.' % (n, s, STATUS[s]))
        else:
            log.debug('Found no calls in status %s: %s.' % (s, STATUS[s]))

    log.info('Parsed %s calls.' % len(calls))

    return calls


def callMSG(call):
    '''Converts call form into an email object.'''
    text = string.Template(TEMPLATE).substitute(call)
    msg = MIMEText(text)
    msg.set_unixfrom('Watchman')
    msg['To'] = email.utils.formataddr(('Servicedesk', CONFIG['recp']))
    msg['From'] = email.utils.formataddr(('Watchman', CONFIG['user']))
    msg['Subject'] = 'Watchman call %s' % call['time']

    return msg


def sendMail(calls):
    '''Send calls as individual call emails.'''

    msgs = []

    log.debug('Converting calls to emails.')

    target = CONFIG['debugemail'] if CONFIG['debug'] else CONFIG['recp']
    log.info('Preparing %s calls, sending to %s.' % (len(calls), target))

    for i, call in enumerate(calls):
        log.debug('Converting call %s of %s - user: %s' % (i + 1, len(calls), call['user']))
        msgs.append(callMSG(call))

    server = smtplib.SMTP(CONFIG['smtpname'], int(CONFIG['smtpport']))

    try:
        if CONFIG['debug']:
            server.set_debuglevel(True)
        else:
            server.set_debuglevel(False)

        server.ehlo()

        # encrypt if available - we might require this, never tested without
        if server.has_extn('STARTTLS'):
            server.starttls()
            server.ehlo()  # now that we're encrypted, say hey to the server

        log.info('Connecting to mail server.')

        server.login(CONFIG['username'], CONFIG['password'])  # log in using xrs@ rather than name@

        for i, msg in enumerate(msgs):
            log.debug('Sending message %s of %s.' % (i + 1, len(msgs)))
            server.sendmail(CONFIG['user'], [target], msg.as_string())  # target pulled from section above - chooses either debugemail or recp

    finally:
        log.info('Disconnecting from the server.')
        server.quit()  # be nice, close connection cleanly


def check_for_XML(xmlDir, date):
    '''Checks working/archive directory for today's XML, returns True if found. If found, the file has been downloaded already.'''

    log.info('Checking for today\'s XML file.')
    log.info('Today = %s.' % TODAY)

    f = xmlDir + 'NoohAberdeen%s.xml' % date

    if os.path.exists(f):
        log.warning('File found.')
        return True
    log.info('File not found.')
    return False


if __name__ == '__main__':
    main()
