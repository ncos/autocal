#!/usr/bin/env python



__program__ = 'gcalcli'
__version__ = 'v3.2'
__author__ = 'Eric Davis, Brian Hartvigsen'
__API_CLIENT_ID__ = '232867676714.apps.googleusercontent.com'
__API_CLIENT_SECRET__ = '3tZSxItw6_VnZMezQwC8lUqy'

# These are standard libraries and should never fail
import sys
import os
import re
import shlex
import time
import calendar
import locale
import textwrap
import signal
from datetime import datetime, timedelta, date
from unicodedata import east_asian_width

# Required 3rd party libraries
try:
    from dateutil.tz import tzlocal
    from dateutil.parser import parse
    import gflags
    import httplib2
    from apiclient.discovery import build
    from oauth2client.file import Storage
    from oauth2client.client import OAuth2WebServerFlow
    from oauth2client.tools import run
except ImportError as e:
    print "ERROR: Missing module - %s" % e.args[0]
    sys.exit(1)

# cPickle is a standard library, but in case someone did something really
# dumb, fall back to pickle.  If that's not their, your python is fucked
try:
    import cPickle as pickle
except ImportError:
    import pickle

# If they have parsedatetime, we'll use it for fuzzy datetime comparison.  If
# not, we just return a fake failure every time and use only dateutil.
try:
    from parsedatetime import parsedatetime
except:
    class parsedatetime:
        class Calendar:
            def parse(self, string):
                return ([], 0)

locale.setlocale(locale.LC_ALL, "")


def stringToUnicode(string):
    if string:
        return unicode(string, locale.getlocale()[1] or
                       locale.getpreferredencoding(False) or
                       "UTF-8")
    else:
        return u''


def stringFromUnicode(string):
    return string.encode(locale.getlocale()[1] or
                         locale.getpreferredencoding(False) or
                         "UTF-8", "replace")


def Version():
    sys.stdout.write(__program__+' '+__version__+' ('+__author__+')\n')
    sys.exit(1)


def Usage(expanded=False):
    sys.stdout.write(__doc__ % sys.argv[0])
    if expanded:
        print FLAGS.MainModuleHelp()
    sys.exit(1)


class CLR:

    useColor = True
    conky = False

    def __str__(self):
        return self.color if self.useColor else ""


class CLR_NRM(CLR):
    color = "\033[0m"


class CLR_BLK(CLR):
    color = "\033[0;30m"


class CLR_BRBLK(CLR):
    color = "\033[30;1m"


class CLR_RED(CLR):
    color = "\033[0;31m"


class CLR_BRRED(CLR):
    color = "\033[31;1m"


class CLR_GRN(CLR):
    color = "\033[0;32m"


class CLR_BRGRN(CLR):
    color = "\033[32;1m"


class CLR_YLW(CLR):
    color = "\033[0;33m"


class CLR_BRYLW(CLR):
    color = "\033[33;1m"


class CLR_BLU(CLR):
    color = "\033[0;34m"


class CLR_BRBLU(CLR):
    color = "\033[34;1m"


class CLR_MAG(CLR):
    color = "\033[0;35m"


class CLR_BRMAG(CLR):
    color = "\033[35;1m"


class CLR_CYN(CLR):
    color = "\033[0;36m"


class CLR_BRCYN(CLR):
    color = "\033[36;1m"


class CLR_WHT(CLR):
    color = "\033[0;37m"


class CLR_BRWHT(CLR):
    color = "\033[37;1m"


def SetConkyColors():
    # XXX these colors should be configurable
    CLR.conky = True
    CLR_NRM.color = ""
    CLR_BLK.color = "${color black}"
    CLR_BRBLK.color = "${color black}"
    CLR_RED.color = "${color red}"
    CLR_BRRED.color = "${color red}"
    CLR_GRN.color = "${color green}"
    CLR_BRGRN.color = "${color green}"
    CLR_YLW.color = "${color yellow}"
    CLR_BRYLW.color = "${color yellow}"
    CLR_BLU.color = "${color blue}"
    CLR_BRBLU.color = "${color blue}"
    CLR_MAG.color = "${color magenta}"
    CLR_BRMAG.color = "${color magenta}"
    CLR_CYN.color = "${color cyan}"
    CLR_BRCYN.color = "${color cyan}"
    CLR_WHT.color = "${color white}"
    CLR_BRWHT.color = "${color white}"


class ART:

    useArt = True
    fancy = ''
    plain = ''

    def __str__(self):
        return self.fancy if self.useArt else self.plain


class ART_HRZ(ART):
    fancy = '\033(0\x71\033(B'
    plain = '-'


class ART_VRT(ART):
    fancy = '\033(0\x78\033(B'
    plain = '|'


class ART_LRC(ART):
    fancy = '\033(0\x6A\033(B'
    plain = '+'


class ART_URC(ART):
    fancy = '\033(0\x6B\033(B'
    plain = '+'


class ART_ULC(ART):
    fancy = '\033(0\x6C\033(B'
    plain = '+'


class ART_LLC(ART):
    fancy = '\033(0\x6D\033(B'
    plain = '+'


class ART_CRS(ART):
    fancy = '\033(0\x6E\033(B'
    plain = '+'


class ART_LTE(ART):
    fancy = '\033(0\x74\033(B'
    plain = '+'


class ART_RTE(ART):
    fancy = '\033(0\x75\033(B'
    plain = '+'


class ART_BTE(ART):
    fancy = '\033(0\x76\033(B'
    plain = '+'


class ART_UTE(ART):
    fancy = '\033(0\x77\033(B'
    plain = '+'


def PrintErrMsg(msg):
    PrintMsg(CLR_BRRED(), msg)


def PrintMsg(color, msg):
    if isinstance(msg, unicode):
        msg = stringFromUnicode(msg)

    if CLR.useColor:
        sys.stdout.write(str(color))
        sys.stdout.write(msg)
        sys.stdout.write(str(CLR_NRM()))
    else:
        sys.stdout.write(msg)


def DebugPrint(msg):
    return
    PrintMsg(CLR_YLW(), msg)


def dprint(obj):
    try:
        from pprint import pprint
        pprint(obj)
    except ImportError:
        print obj


class DateTimeParser:
    def __init__(self):
        self.pdtCalendar = parsedatetime.Calendar()

    def fromString(self, eWhen):
        defaultDateTime = datetime.now(tzlocal()).replace(hour=0,
                                                          minute=0,
                                                          second=0,
                                                          microsecond=0)

        try:
            eTimeStart = parse(eWhen, default=defaultDateTime)
        except:
            struct, result = self.pdtCalendar.parse(eWhen)
            if not result:
                raise ValueError("Date and time is invalid")
            eTimeStart = datetime.fromtimestamp(time.mktime(struct), tzlocal())

        return eTimeStart


def DaysSinceEpoch(dt):
    # Because I hate magic numbers
    __DAYS_IN_SECONDS__ = 24 * 60 * 60
    return calendar.timegm(dt.timetuple()) / __DAYS_IN_SECONDS__


def GetTimeFromStr(eWhen, eDuration=0):
    dtp = DateTimeParser()

    try:
        eTimeStart = dtp.fromString(eWhen)
    except:
        PrintErrMsg('Date and time is invalid!\n')
        sys.exit(1)

    if FLAGS.allday:
        try:
            eTimeStop = eTimeStart + timedelta(days=float(eDuration))
        except:
            PrintErrMsg('Duration time (days) is invalid\n')
            sys.exit(1)

        sTimeStart = eTimeStart.date().isoformat()
        sTimeStop = eTimeStop.date().isoformat()

    else:
        try:
            eTimeStop = eTimeStart + timedelta(minutes=float(eDuration))
        except:
            PrintErrMsg('Duration time (minutes) is invalid\n')
            sys.exit(1)

        sTimeStart = eTimeStart.isoformat()
        sTimeStop = eTimeStop.isoformat()

    return sTimeStart, sTimeStop


def ParseReminder(rem):
    matchObj = re.match(r'^(\d+)([wdhm]?)(?:\s+(popup|email|sms))?$', rem)
    if not matchObj:
        PrintErrMsg('Invalid reminder: ' + rem + '\n')
        sys.exit(1)
    n = int(matchObj.group(1))
    t = matchObj.group(2)
    m = matchObj.group(3)
    if t == 'w':
        n = n * 7 * 24 * 60
    elif t == 'd':
        n = n * 24 * 60
    elif t == 'h':
        n = n * 60

    if not m:
        m = 'popup'

    return n, m


class gcalcli:

    cache = {}
    allCals = []
    allEvents = []
    cals = []
    now = datetime.now(tzlocal())
    agendaLength = 5
    authHttp = None
    calService = None
    urlService = None
    command = 'notify-send -u critical -a gcalcli %s'
    dateParser = DateTimeParser()

    ACCESS_OWNER = 'owner'
    ACCESS_WRITER = 'writer'
    ACCESS_READER = 'reader'
    ACCESS_FREEBUSY = 'freeBusyReader'

    UNIWIDTH = {'W': 2, 'F': 2, 'N': 1, 'Na': 1, 'H': 1, 'A': 1}

    def __init__(self,
                 calNames=[],
                 calNameColors=[],
                 military=False,
                 detailCalendar=False,
                 detailLocation=False,
                 detailAttendees=False,
                 detailLength=False,
                 detailReminders=False,
                 detailDescr=False,
                 detailDescrWidth=80,
                 detailUrl=None,
                 ignoreStarted=False,
                 calWidth=10,
                 calMonday=False,
                 calOwnerColor=CLR_CYN(),
                 calWriterColor=CLR_GRN(),
                 calReaderColor=CLR_MAG(),
                 calFreeBusyColor=CLR_NRM(),
                 dateColor=CLR_YLW(),
                 nowMarkerColor=CLR_BRRED(),
                 borderColor=CLR_WHT(),
                 tsv=False,
                 refreshCache=False,
                 useCache=True,
                 configFolder=None,
                 client_id=__API_CLIENT_ID__,
                 client_secret=__API_CLIENT_SECRET__):

        self.military = military
        self.ignoreStarted = ignoreStarted
        self.calWidth = calWidth
        self.calMonday = calMonday
        self.tsv = tsv
        self.refreshCache = refreshCache
        self.useCache = useCache

        self.detailCalendar = detailCalendar
        self.detailLocation = detailLocation
        self.detailLength = detailLength
        self.detailReminders = detailReminders
        self.detailDescr = detailDescr
        self.detailDescrWidth = detailDescrWidth
        self.detailUrl = detailUrl
        self.detailAttendees = detailAttendees

        self.calOwnerColor = calOwnerColor
        self.calWriterColor = calWriterColor
        self.calReaderColor = calReaderColor
        self.calFreeBusyColor = calFreeBusyColor
        self.dateColor = dateColor
        self.nowMarkerColor = nowMarkerColor
        self.borderColor = borderColor

        self.configFolder = configFolder

        self.client_id = client_id
        self.client_secret = client_secret

        self._GetCached()


        if len(calNames):
            # Changing the order of this and the `cal in self.allCals` loop
            # is necessary for the matching to actually be sane (ie match
            # supplied name to cached vs matching cache against supplied names)
            for i in xrange(len(calNames)):
                matches = []
                for cal in self.allCals:
                    # For exact match, we should match only 1 entry and accept
                    # the first entry.  Should honor access role order since
                    # it happens after _GetCached()
                    if calNames[i] == cal['summary']:
                        # This makes sure that if we have any regex matches
                        # that we toss them out in favor of the specific match
                        matches = [cal]
                        cal['colorSpec'] = calNameColors[i]
                        break
                    # Otherwise, if the calendar matches as a regex, append
                    # it to the list of potential matches
                    elif re.search(calNames[i], cal['summary'], flags=re.I):
                        matches.append(cal)
                        cal['colorSpec'] = calNameColors[i]
                # Add relevant matches to the list of calendars we want to
                # operate against
                self.cals += matches
        else:
            self.cals = self.allCals

    @staticmethod
    def _LocalizeDateTime(dt):
        if not hasattr(dt, 'tzinfo'):
            return dt
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tzlocal())
        else:
            return dt.astimezone(tzlocal())

    def _GoogleAuth(self):
        if not self.authHttp:
            if self.configFolder:
                storage = Storage(os.path.expanduser("%s/oauth" %
                                                     self.configFolder))
            else:
                storage = Storage(os.path.expanduser('~/.gcalcli_oauth'))
            credentials = storage.get()

            if credentials is None or credentials.invalid:
                credentials = run(
                    OAuth2WebServerFlow(
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        scope=['https://www.googleapis.com/auth/calendar',
                               'https://www.googleapis.com/auth/urlshortener'],
                        user_agent=__program__+'/'+__version__),
                    storage)

            self.authHttp = credentials.authorize(httplib2.Http())

        return self.authHttp

    def _CalService(self):
        if not self.calService:
            self.calService = \
                build(serviceName='calendar',
                      version='v3',
                      http=self._GoogleAuth())

        return self.calService

    def _UrlService(self):
        if not self.urlService:
            self._GoogleAuth()
            self.urlService = \
                build(serviceName='urlshortener',
                      version='v1',
                      http=self._GoogleAuth())

        return self.urlService

    def _GetCached(self):
        if self.configFolder:
            cacheFile = os.path.expanduser("%s/cache" % self.configFolder)
        else:
            cacheFile = os.path.expanduser('~/.gcalcli_cache')

        if self.refreshCache:
            try:
                os.remove(cacheFile)
            except OSError:
                pass
                # fall through

        self.cache = {}
        self.allCals = []

        if self.useCache:
            # note that we need to use pickle for cache data since we stuff
            # various non-JSON data in the runtime storage structures
            try:
                with open(cacheFile, 'rb') as _cache_:
                    self.cache = pickle.load(_cache_)
                    self.allCals = self.cache['allCals']
                # XXX assuming data is valid, need some verification check here
                return
            except IOError:
                pass
                # fall through

        calList = self._CalService().calendarList().list().execute()

        while True:
            for cal in calList['items']:
                self.allCals.append(cal)
            pageToken = calList.get('nextPageToken')
            if pageToken:
                calList = self._CalService().calendarList().\
                    list(pageToken=pageToken).execute()
            else:
                break

        # gcalcli defined way to order calendars
        order = {self.ACCESS_OWNER: 1,
                 self.ACCESS_WRITER: 2,
                 self.ACCESS_READER: 3,
                 self.ACCESS_FREEBUSY: 4}

        self.allCals.sort(lambda x, y:
                          cmp(order[x['accessRole']],
                              order[y['accessRole']]))

        if self.useCache:
            self.cache['allCals'] = self.allCals
            with open(cacheFile, 'wb') as _cache_:
                pickle.dump(self.cache, _cache_)

    def _ShortenURL(self, url):
        if self.detailUrl != "short":
            return url
        # Note that when authenticated to a google account different shortUrls
        # can be returned for the same longUrl. See: http://goo.gl/Ya0A9
        shortUrl = self._UrlService().url().insert(body={'longUrl': url}).\
            execute()
        return shortUrl['id']

    def _CalendarColor(self, cal):

        if cal is None:
            return CLR_NRM()
        elif 'colorSpec' in cal and cal['colorSpec'] is not None:
            return cal['colorSpec']
        elif cal['accessRole'] == self.ACCESS_OWNER:
            return self.calOwnerColor
        elif cal['accessRole'] == self.ACCESS_WRITER:
            return self.calWriterColor
        elif cal['accessRole'] == self.ACCESS_READER:
            return self.calReaderColor
        elif cal['accessRole'] == self.ACCESS_FREEBUSY:
            return self.calFreeBusyColor
        else:
            return CLR_NRM()

    def _ValidTitle(self, event):
        if 'summary' in event and event['summary'].strip():
            return event['summary']
        else:
            return "(No title)"

    def _GetWeekEventStrings(self, cmd, curMonth,
                             startDateTime, endDateTime, eventList):

        weekEventStrings = ['', '', '', '', '', '', '']

        nowMarkerPrinted = False
        if self.now < startDateTime or self.now > endDateTime:
            # now isn't in this week
            nowMarkerPrinted = True

        for event in eventList:

            if cmd == 'calm' and curMonth != event['s'].strftime("%b"):
                continue

            dayNum = int(event['s'].strftime("%w"))
            if self.calMonday:
                dayNum -= 1
                if dayNum < 0:
                    dayNum = 6

            if event['s'] >= startDateTime and event['s'] < endDateTime:

                forceEventColorAsMarker = False

                if event['s'].hour == 0 and event['s'].minute == 0 and \
                        event['e'].hour == 0 and event['e'].minute == 0:
                    allDay = True
                else:
                    allDay = False

                if not nowMarkerPrinted:
                    if (DaysSinceEpoch(self.now) <
                            DaysSinceEpoch(event['s'])):
                        nowMarkerPrinted = True
                        weekEventStrings[dayNum-1] += \
                            ("\n" +
                             str(self.nowMarkerColor) +
                             (self.calWidth * '-'))
                    elif self.now <= event['s']:
                        # add a line marker before next event
                        nowMarkerPrinted = True
                        weekEventStrings[dayNum] += \
                            ("\n" +
                             str(self.nowMarkerColor) +
                             (self.calWidth * '-'))
                    # We don't want to recolor all day events, but ignoring
                    # them leads to issues where the "now" marker misprints
                    # into the wrong day.  This resolves the issue by skipping
                    # all day events for specific coloring but not for previous
                    # or next events
                    elif self.now >= event['s'] and \
                            self.now <= event['e'] and \
                            not allDay:
                        # line marker is during the event (recolor event)
                        nowMarkerPrinted = True
                        forceEventColorAsMarker = True

                if allDay:
                    tmpTimeStr = ''
                elif self.military:
                    tmpTimeStr = event['s'].strftime("%H:%M")
                else:
                    tmpTimeStr = \
                        event['s'].strftime("%I:%M").lstrip('0') + \
                        event['s'].strftime('%p').lower()

                if forceEventColorAsMarker:
                    eventColor = self.nowMarkerColor
                else:
                    eventColor = self._CalendarColor(event['gcalcli_cal'])

                # newline and empty string are the keys to turn off coloring
                weekEventStrings[dayNum] += \
                    "\n" + \
                    str(eventColor) + \
                    tmpTimeStr.strip() + \
                    " " + \
                    self._ValidTitle(event).strip()

        return weekEventStrings

    def _PrintLen(self, string):
        # We need to treat everything as unicode for this to actually give
        # us the info we want.  Date string were coming in as `str` type
        # so we convert them to unicode and then check their size. Fixes
        # the output issues we were seeing around non-US locale strings
        if not isinstance(string, unicode):
            string = stringToUnicode(string)
        printLen = 0
        for tmpChar in string:
            printLen += self.UNIWIDTH[east_asian_width(tmpChar)]
        return printLen

    # return print length before cut, cut index, and force cut flag
    def _NextCut(self, string, curPrintLen):
        idx = 0
        printLen = 0
        if not isinstance(string, unicode):
            string = stringToUnicode(string)
        for tmpChar in string:
            if (curPrintLen + printLen) >= self.calWidth:
                return (printLen, idx, True)
            if tmpChar in (' ', '\n'):
                return (printLen, idx, False)
            idx += 1
            printLen += self.UNIWIDTH[east_asian_width(tmpChar)]
        return (printLen, -1, False)

    def _GetCutIndex(self, eventString):

        printLen = self._PrintLen(eventString)

        if printLen <= self.calWidth:
            if '\n' in eventString:
                idx = eventString.find('\n')
                printLen = self._PrintLen(eventString[:idx])
            else:
                idx = len(eventString)

            DebugPrint("------ printLen=%d (end of string)\n" % idx)
            return (printLen, idx)

        cutWidth, cut, forceCut = self._NextCut(eventString, 0)
        DebugPrint("------ cutWidth=%d cut=%d \"%s\"\n" %
                   (cutWidth, cut, eventString))

        if forceCut:
            DebugPrint("--- forceCut cutWidth=%d cut=%d\n" % (cutWidth, cut))
            return (cutWidth, cut)

        DebugPrint("--- looping\n")

        while cutWidth < self.calWidth:

            DebugPrint("--- cutWidth=%d cut=%d \"%s\"\n" %
                       (cutWidth, cut, eventString[cut:]))

            while cut < self.calWidth and \
                    cut < printLen and \
                    eventString[cut] == ' ':
                DebugPrint("-> skipping space <-\n")
                cutWidth += 1
                cut += 1

            DebugPrint("--- cutWidth=%d cut=%d \"%s\"\n" %
                       (cutWidth, cut, eventString[cut:]))

            nextCutWidth, nextCut, forceCut = \
                self._NextCut(eventString[cut:], cutWidth)

            if forceCut:
                DebugPrint("--- forceCut cutWidth=%d cut=%d\n" % (cutWidth,
                                                                  cut))
                break

            cutWidth += nextCutWidth
            cut += nextCut

            if eventString[cut] == '\n':
                break

            DebugPrint("--- loop cutWidth=%d cut=%d\n" % (cutWidth, cut))

        return (cutWidth, cut)

    def _GraphEvents(self, cmd, startDateTime, count, eventList):

        # ignore started events (i.e. events that start previous day and end
        # start day)
        while (len(eventList) and eventList[0]['s'] < startDateTime):
            eventList = eventList[1:]

        dayWidthLine = (self.calWidth * str(ART_HRZ()))

        topWeekDivider = (str(self.borderColor) +
                          str(ART_ULC()) + dayWidthLine +
                          (6 * (str(ART_UTE()) + dayWidthLine)) +
                          str(ART_URC()) + str(CLR_NRM()))

        midWeekDivider = (str(self.borderColor) +
                          str(ART_LTE()) + dayWidthLine +
                          (6 * (str(ART_CRS()) + dayWidthLine)) +
                          str(ART_RTE()) + str(CLR_NRM()))

        botWeekDivider = (str(self.borderColor) +
                          str(ART_LLC()) + dayWidthLine +
                          (6 * (str(ART_BTE()) + dayWidthLine)) +
                          str(ART_LRC()) + str(CLR_NRM()))

        empty = self.calWidth * ' '

        # Get the localized day names... January 1, 2001 was a Monday
        dayNames = [date(2001, 1, i+1).strftime('%A') for i in range(7)]
        dayNames = dayNames[6:] + dayNames[:6]

        dayHeader = str(self.borderColor) + str(ART_VRT()) + str(CLR_NRM())
        for i in xrange(7):
            if self.calMonday:
                if i == 6:
                    dayName = dayNames[0]
                else:
                    dayName = dayNames[i+1]
            else:
                dayName = dayNames[i]
            dayName += ' ' * (self.calWidth - self._PrintLen(dayName))
            dayHeader += str(self.dateColor) + dayName + str(CLR_NRM())
            dayHeader += str(self.borderColor) + str(ART_VRT()) + \
                str(CLR_NRM())

        if cmd == 'calm':
            topMonthDivider = (str(self.borderColor) +
                               str(ART_ULC()) + dayWidthLine +
                               (6 * (str(ART_HRZ()) + dayWidthLine)) +
                               str(ART_URC()) + str(CLR_NRM()))
            PrintMsg(CLR_NRM(), "\n" + topMonthDivider + "\n")

            m = startDateTime.strftime('%B %Y')
            mw = (self.calWidth * 7) + 6
            m += ' ' * (mw - self._PrintLen(m))
            PrintMsg(CLR_NRM(),
                     str(self.borderColor) +
                     str(ART_VRT()) +
                     str(CLR_NRM()) +
                     str(self.dateColor) +
                     m +
                     str(CLR_NRM()) +
                     str(self.borderColor) +
                     str(ART_VRT()) +
                     str(CLR_NRM()) +
                     '\n')

            botMonthDivider = (str(self.borderColor) +
                               str(ART_LTE()) + dayWidthLine +
                               (6 * (str(ART_UTE()) + dayWidthLine)) +
                               str(ART_RTE()) + str(CLR_NRM()))
            PrintMsg(CLR_NRM(), botMonthDivider + "\n")

        else:  # calw
            PrintMsg(CLR_NRM(), "\n" + topWeekDivider + "\n")

        PrintMsg(CLR_NRM(), dayHeader + "\n")
        PrintMsg(CLR_NRM(), midWeekDivider + "\n")

        curMonth = startDateTime.strftime("%b")

        # get date range objects for the first week
        if cmd == 'calm':
            dayNum = int(startDateTime.strftime("%w"))
            if self.calMonday:
                dayNum -= 1
                if dayNum < 0:
                    dayNum = 6
            startDateTime = (startDateTime - timedelta(days=dayNum))
        startWeekDateTime = startDateTime
        endWeekDateTime = (startWeekDateTime + timedelta(days=7))

        for i in xrange(count):

            # create/print date line
            line = str(self.borderColor) + str(ART_VRT()) + str(CLR_NRM())
            for j in xrange(7):
                if cmd == 'calw':
                    d = (startWeekDateTime +
                         timedelta(days=j)).strftime("%d %b")
                else:  # (cmd == 'calm'):
                    d = (startWeekDateTime +
                         timedelta(days=j)).strftime("%d")
                    if curMonth != (startWeekDateTime +
                                    timedelta(days=j)).strftime("%b"):
                        d = ''
                tmpDateColor = self.dateColor

                if self.now.strftime("%d%b%Y") == \
                   (startWeekDateTime + timedelta(days=j)).strftime("%d%b%Y"):
                    tmpDateColor = self.nowMarkerColor
                    d += " **"

                d += ' ' * (self.calWidth - self._PrintLen(d))
                line += str(tmpDateColor) + \
                    d + \
                    str(CLR_NRM()) + \
                    str(self.borderColor) + \
                    str(ART_VRT()) + \
                    str(CLR_NRM())
            PrintMsg(CLR_NRM(), line + "\n")

            weekColorStrings = ['', '', '', '', '', '', '']
            weekEventStrings = self._GetWeekEventStrings(cmd, curMonth,
                                                         startWeekDateTime,
                                                         endWeekDateTime,
                                                         eventList)

            # get date range objects for the next week
            startWeekDateTime = endWeekDateTime
            endWeekDateTime = (endWeekDateTime + timedelta(days=7))

            while 1:

                done = True
                line = str(self.borderColor) + str(ART_VRT()) + str(CLR_NRM())

                for j in xrange(7):

                    if weekEventStrings[j] == '':
                        weekColorStrings[j] = ''
                        line += (empty +
                                 str(self.borderColor) +
                                 str(ART_VRT()) +
                                 str(CLR_NRM()))
                        continue

                    # get/skip over a color sequence
                    if ((not CLR.conky and weekEventStrings[j][0] == '\033') or
                            (CLR.conky and weekEventStrings[j][0] == '$')):
                        weekColorStrings[j] = ''
                        while ((not CLR.conky and
                                weekEventStrings[j][0] != 'm') or
                                (CLR.conky and weekEventStrings[j][0] != '}')):
                            weekColorStrings[j] += weekEventStrings[j][0]
                            weekEventStrings[j] = weekEventStrings[j][1:]
                        weekColorStrings[j] += weekEventStrings[j][0]
                        weekEventStrings[j] = weekEventStrings[j][1:]

                    if weekEventStrings[j][0] == '\n':
                        weekColorStrings[j] = ''
                        weekEventStrings[j] = weekEventStrings[j][1:]
                        line += (empty +
                                 str(self.borderColor) +
                                 str(ART_VRT()) +
                                 str(CLR_NRM()))
                        done = False
                        continue

                    weekEventStrings[j] = weekEventStrings[j].lstrip()

                    printLen, cut = self._GetCutIndex(weekEventStrings[j])
                    padding = ' ' * (self.calWidth - printLen)

                    line += (weekColorStrings[j] +
                             weekEventStrings[j][:cut] +
                             padding +
                             str(CLR_NRM()))
                    weekEventStrings[j] = weekEventStrings[j][cut:]

                    done = False
                    line += (str(self.borderColor) +
                             str(ART_VRT()) +
                             str(CLR_NRM()))

                if done:
                    break

                PrintMsg(CLR_NRM(), line + "\n")

            if i < range(count)[len(range(count))-1]:
                PrintMsg(CLR_NRM(), midWeekDivider + "\n")
            else:
                PrintMsg(CLR_NRM(), botWeekDivider + "\n")

    def _tsv(self, startDateTime, eventList):
        for event in eventList:
            output = "%s\t%s\t%s\t%s" % (event['s'].strftime('%Y-%m-%d'),
                                         event['s'].strftime('%H:%M'),
                                         event['e'].strftime('%Y-%m-%d'),
                                         event['e'].strftime('%H:%M'))

            if self.detailUrl:
                output += "\t%s" % (self._ShortenURL(event['htmlLink'])
                                    if 'htmlLink' in event else '')
                output += "\t%s" % (self._ShortenURL(event['hangoutLink'])
                                    if 'hangoutLink' in event else '')

            output += "\t%s" % self._ValidTitle(event).strip()

            if self.detailLocation:
                output += "\t%s" % (event['location'].strip()
                                    if 'location' in event else '')

            if self.detailDescr:
                output += "\t%s" % (event['description'].strip()
                                    if 'description' in event else '')

            if self.detailCalendar:
                output += "\t%s" % event['gcalcli_cal']['summary'].strip()

            output = "%s\n" % output.replace('\n', '''\\n''')
            sys.stdout.write(stringFromUnicode(output))

    def _PrintEvent(self, event, prefix):

        def _formatDescr(descr, indent, box):
            wrapper = textwrap.TextWrapper()
            if box:
                wrapper.initial_indent = (indent + '  ')
                wrapper.subsequent_indent = (indent + '  ')
                wrapper.width = (self.detailDescrWidth - 2)
            else:
                wrapper.initial_indent = indent
                wrapper.subsequent_indent = indent
                wrapper.width = self.detailDescrWidth
            new_descr = ""
            for line in descr.split("\n"):
                if box:
                    tmpLine = wrapper.fill(line)
                    for singleLine in tmpLine.split("\n"):
                        singleLine = singleLine.ljust(self.detailDescrWidth,
                                                      ' ')
                        new_descr += singleLine[:len(indent)] + \
                            str(ART_VRT()) + \
                            singleLine[(len(indent)+1):
                                       (self.detailDescrWidth-1)] + \
                            str(ART_VRT()) + '\n'
                else:
                    new_descr += wrapper.fill(line) + "\n"
            return new_descr.rstrip()

        indent = 10 * ' '
        detailsIndent = 19 * ' '

        if self.military:
            timeFormat = '%-5s'
            tmpTimeStr = event['s'].strftime("%H:%M")
        else:
            timeFormat = '%-7s'
            tmpTimeStr = \
                event['s'].strftime("%I:%M").lstrip('0').rjust(5) + \
                event['s'].strftime('%p').lower()

        if not prefix:
            prefix = indent

        PrintMsg(self.dateColor, prefix)
        if event['s'].hour == 0 and event['s'].minute == 0 and \
           event['e'].hour == 0 and event['e'].minute == 0:
            fmt = '  ' + timeFormat + '  %s\n'
            PrintMsg(self._CalendarColor(event['gcalcli_cal']), fmt %
                     ('', self._ValidTitle(event).strip()))
        else:
            fmt = '  ' + timeFormat + '  %s\n'
            PrintMsg(self._CalendarColor(event['gcalcli_cal']), fmt %
                     (tmpTimeStr, self._ValidTitle(event).strip()))

        if self.detailCalendar:
            xstr = "%s  Calendar: %s\n" % (
                detailsIndent,
                event['gcalcli_cal']['summary']
            )
            PrintMsg(CLR_NRM(), xstr)

        if self.detailUrl and 'htmlLink' in event:
            hLink = self._ShortenURL(event['htmlLink'])
            xstr = "%s  Link: %s\n" % (detailsIndent, hLink)
            PrintMsg(CLR_NRM(), xstr)

        if self.detailUrl and 'hangoutLink' in event:
            hLink = self._ShortenURL(event['hangoutLink'])
            xstr = "%s  Hangout Link: %s\n" % (detailsIndent, hLink)
            PrintMsg(CLR_NRM(), xstr)

        if self.detailLocation and \
           'location' in event and \
           event['location'].strip():
            xstr = "%s  Location: %s\n" % (
                detailsIndent,
                event['location'].strip()
            )
            PrintMsg(CLR_NRM(), xstr)

        if self.detailAttendees and 'attendees' in event:
            xstr = "%s  Attendees:\n" % (detailsIndent)
            PrintMsg(CLR_NRM(), xstr)

            if 'self' not in event['organizer']:
                xstr = "%s    %s: <%s>\n" % (
                    detailsIndent,
                    event['organizer'].get('displayName', 'Not Provided')
                                      .strip(),
                    event['organizer']['email'].strip()
                )
                PrintMsg(CLR_NRM(), xstr)

            for attendee in event['attendees']:
                if 'self' not in attendee:
                    xstr = "%s    %s: <%s>\n" % (
                        detailsIndent,
                        attendee.get('displayName', 'Not Provided').strip(),
                        attendee['email'].strip()
                    )
                    PrintMsg(CLR_NRM(), xstr)

        if self.detailLength:
            diffDateTime = (event['e'] - event['s'])
            xstr = "%s  Length: %s\n" % (detailsIndent, diffDateTime)
            PrintMsg(CLR_NRM(), xstr)

        if self.detailReminders and 'reminders' in event:
            if event['reminders']['useDefault'] is True:
                xstr = "%s  Reminder: (default)\n" % (detailsIndent)
                PrintMsg(CLR_NRM(), xstr)
            elif 'overrides' in event['reminders']:
                for rem in event['reminders']['overrides']:
                    xstr = "%s  Reminder: %s %d minutes\n" % \
                           (detailsIndent, rem['method'], rem['minutes'])
                    PrintMsg(CLR_NRM(), xstr)

        if self.detailDescr and \
           'description' in event and \
           event['description'].strip():
            descrIndent = detailsIndent + '  '
            box = True  # leave old non-box code for option later
            if box:
                topMarker = (descrIndent +
                             str(ART_ULC()) +
                             (str(ART_HRZ()) *
                              ((self.detailDescrWidth - len(descrIndent)) -
                               2)) +
                             str(ART_URC()))
                botMarker = (descrIndent +
                             str(ART_LLC()) +
                             (str(ART_HRZ()) *
                              ((self.detailDescrWidth - len(descrIndent)) -
                               2)) +
                             str(ART_LRC()))
                xstr = "%s  Description:\n%s\n%s\n%s\n" % (
                    detailsIndent,
                    topMarker,
                    _formatDescr(event['description'].strip(),
                                 descrIndent, box),
                    botMarker
                )
            else:
                marker = descrIndent + '-' * \
                    (self.detailDescrWidth - len(descrIndent))
                xstr = "%s  Description:\n%s\n%s\n%s\n" % (
                    detailsIndent,
                    marker,
                    _formatDescr(event['description'].strip(),
                                 descrIndent, box),
                    marker
                )
            PrintMsg(CLR_NRM(), xstr)

    def _DeleteEvent(self, event):

        if self.iamaExpert:
            self._CalService().events().\
                delete(calendarId=event['gcalcli_cal']['id'],
                       eventId=event['id']).execute()
            PrintMsg(CLR_RED(), "Deleted!\n")
            return

        PrintMsg(CLR_MAG(), "Delete? [N]o [y]es [q]uit: ")
        val = raw_input()

        if not val or val.lower() == 'n':
            return

        elif val.lower() == 'y':
            self._CalService().events().\
                delete(calendarId=event['gcalcli_cal']['id'],
                       eventId=event['id']).execute()
            PrintMsg(CLR_RED(), "Deleted!\n")

        elif val.lower() == 'q':
            sys.stdout.write('\n')
            sys.exit(0)

        else:
            PrintErrMsg('Error: invalid input\n')
            sys.stdout.write('\n')
            sys.exit(1)

    def _EditEvent(self, event):

        while True:

            PrintMsg(CLR_MAG(), "Edit?\n" +
                                "[N]o [s]ave [q]uit " +
                                "[t]itle [l]ocation " +
                                "[w]hen len[g]th " +
                                "[r]eminder [d]escr: ")
            val = raw_input()

            if not val or val.lower() == 'n':
                return

            elif val.lower() == 's':
                # copy only editable event details for patching
                modEvent = {}
                keys = ['summary', 'location', 'start', 'end',
                        'reminders', 'description']
                for k in keys:
                    if k in event:
                        modEvent[k] = event[k]

                self._CalService().events().\
                    patch(calendarId=event['gcalcli_cal']['id'],
                          eventId=event['id'],
                          body=modEvent).execute()
                PrintMsg(CLR_RED(), "Saved!\n")
                return

            elif not val or val.lower() == 'q':
                sys.stdout.write('\n')
                sys.exit(0)

            elif val.lower() == 't':
                PrintMsg(CLR_MAG(), "Title: ")
                val = raw_input()
                if val.strip():
                    event['summary'] = \
                        stringToUnicode(val.strip())

            elif val.lower() == 'l':
                PrintMsg(CLR_MAG(), "Location: ")
                val = raw_input()
                if val.strip():
                    event['location'] = \
                        stringToUnicode(val.strip())

            elif val.lower() == 'w':
                PrintMsg(CLR_MAG(), "When: ")
                val = raw_input()
                if val.strip():
                    td = (event['e'] - event['s'])
                    length = ((td.days * 1440) + (td.seconds / 60))
                    newStart, newEnd = GetTimeFromStr(val.strip(), length)
                    event['s'] = parse(newStart)
                    event['e'] = parse(newEnd)

                    if FLAGS.allday:
                        event['start'] = {'date': newStart,
                                          'dateTime': None,
                                          'timeZone': None}
                        event['end'] = {'date': newEnd,
                                        'dateTime': None,
                                        'timeZone': None}

                    else:
                        event['start'] = {'date': None,
                                          'dateTime': newStart,
                                          'timeZone': event['gcalcli_cal']['timeZone']}
                        event['end'] = {'date': None,
                                        'dateTime': newEnd,
                                        'timeZone': event['gcalcli_cal']['timeZone']}

            elif val.lower() == 'g':
                PrintMsg(CLR_MAG(), "Length (mins): ")
                val = raw_input()
                if val.strip():
                    newStart, newEnd = \
                        GetTimeFromStr(event['start']['dateTime'], val.strip())
                    event['s'] = parse(newStart)
                    event['e'] = parse(newEnd)

                    if FLAGS.allday:
                        event['start'] = {'date': newStart,
                                          'dateTime': None,
                                          'timeZone': None}
                        event['end'] = {'date': newEnd,
                                        'dateTime': None,
                                        'timeZone': None}

                    else:
                        event['start'] = {'date': None,
                                          'dateTime': newStart,
                                          'timeZone': event['gcalcli_cal']['timeZone']}
                        event['end'] = {'date': None,
                                        'dateTime': newEnd,
                                        'timeZone': event['gcalcli_cal']['timeZone']}

            elif val.lower() == 'r':
                rem = []
                while 1:
                    PrintMsg(CLR_MAG(),
                             "Enter a valid reminder or '.' to end: ")
                    r = raw_input()
                    if r == '.':
                        break
                    rem.append(r)

                if rem or not FLAGS.default_reminders:
                    event['reminders'] = {'useDefault': False,
                                          'overrides': []}
                    for r in rem:
                        n, m = ParseReminder(r)
                        event['reminders']['overrides'].append({'minutes': n,
                                                                'method': m})
                else:
                    event['reminders'] = {'useDefault': True,
                                          'overrides': []}

            elif val.lower() == 'd':
                PrintMsg(CLR_MAG(), "Description: ")
                val = raw_input()
                if val.strip():
                    event['description'] = \
                        stringToUnicode(val.strip())

            else:
                PrintErrMsg('Error: invalid input\n')
                sys.stdout.write('\n')
                sys.exit(1)

            self._PrintEvent(event, event['s'].strftime('\n%Y-%m-%d'))

    def _IterateEvents(self, startDateTime, eventList,
                       yearDate=False, work=None):

        if len(eventList) == 0:
            PrintMsg(CLR_YLW(), "\nNo Events Found...\n")
            return

        # 10 chars for day and length must match 'indent' in _PrintEvent
        dayFormat = '\n%Y-%m-%d' if yearDate else '\n%a %b %d'
        day = ''

        for event in eventList:

            if self.ignoreStarted and (event['s'] < self.now):
                continue

            tmpDayStr = event['s'].strftime(dayFormat)
            prefix = None
            if yearDate or tmpDayStr != day:
                day = prefix = tmpDayStr

            self._PrintEvent(event, prefix)

            if work:
                work(event)

    def _GetAllEvents(self, cal, events, end):

        eventList = []

        while 1:
            if 'items' not in events:
                break

            for event in events['items']:

                event['gcalcli_cal'] = cal

                if 'status' in event and event['status'] == 'cancelled':
                    continue

                if 'dateTime' in event['start']:
                    event['s'] = parse(event['start']['dateTime'])
                else:
                    # all date events
                    event['s'] = parse(event['start']['date'])

                event['s'] = self._LocalizeDateTime(event['s'])

                if 'dateTime' in event['end']:
                    event['e'] = parse(event['end']['dateTime'])
                else:
                    # all date events
                    event['e'] = parse(event['end']['date'])

                event['e'] = self._LocalizeDateTime(event['e'])

                # For all-day events, Google seems to assume that the event
                # time is based in the UTC instead of the local timezone.  Here
                # we filter out those events start beyond a specified end time.
                if end and (event['s'] >= end):
                    continue

                # http://en.wikipedia.org/wiki/Year_2038_problem
                # Catch the year 2038 problem here as the python dateutil
                # module can choke throwing a ValueError exception. If either
                # the start or end time for an event has a year '>= 2038' dump
                # it.
                if event['s'].year >= 2038 or event['e'].year >= 2038:
                    continue

                eventList.append(event)

            pageToken = events.get('nextPageToken')
            if pageToken:
                events = self._CalService().events().\
                    list(calendarId=cal['id'],
                         pageToken=pageToken).execute()
            else:
                break

        return eventList

    def _SearchForCalEvents(self, start, end, searchText):

        eventList = []

        for cal in self.cals:
            events = self._CalService().events().\
                list(calendarId=cal['id'],
                     timeMin=start.isoformat() if start else None,
                     timeMax=end.isoformat() if end else None,
                     q=searchText if searchText else None,
                     singleEvents=True).execute()
            eventList.extend(self._GetAllEvents(cal, events, end))

        eventList.sort(lambda x, y: cmp(x['s'], y['s']))

        return eventList

    def ListAllCalendars(self):

        accessLen = 0

        for cal in self.allCals:
            length = len(cal['accessRole'])
            if length > accessLen:
                accessLen = length

        if accessLen < len('Access'):
            accessLen = len('Access')

        format = ' %0' + str(accessLen) + 's  %s\n'

        PrintMsg(CLR_BRYLW(), format % ('Access', 'Title'))
        PrintMsg(CLR_BRYLW(), format % ('------', '-----'))

        for cal in self.allCals:
            PrintMsg(self._CalendarColor(cal),
                     format % (cal['accessRole'], cal['summary']))

    def TextQuery(self, searchText=''):

        # the empty string would get *ALL* events...
        if searchText == '':
            return

        # This is really just an optimization to the gcalendar api
        # why ask for a bunch of events we are going to filter out
        # anyway?
        # TODO: Look at moving this into the _SearchForCalEvents
        #       Don't forget to clean up AgendaQuery too!

        start = self.now if self.ignoreStarted else None
        eventList = self._SearchForCalEvents(start, None, searchText)

        self._IterateEvents(self.now, eventList, yearDate=True)

    def AgendaQuery(self, startText='', endText=''):

        if startText == '':
            # convert now to midnight this morning and use for default
            start = self.now.replace(hour=0,
                                     minute=0,
                                     second=0,
                                     microsecond=0)
        else:
            try:
                start = self.dateParser.fromString(startText)
            except:
                PrintErrMsg('Error: failed to parse start time\n')
                return

        # Again optimizing calls to the api.  If we've been told to
        # ignore started events, then it doesn't make ANY sense to
        # search for things that may be in the past
        if self.ignoreStarted and start < self.now:
            start = self.now

        if endText == '':
            end = (start + timedelta(days=self.agendaLength))
        else:
            try:
                end = self.dateParser.fromString(endText)
            except:
                PrintErrMsg('Error: failed to parse end time\n')
                return

        eventList = self._SearchForCalEvents(start, end, None)

        if self.tsv:
            self._tsv(start, eventList)
        else:
            self._IterateEvents(start, eventList, yearDate=False)

    def CalQuery(self, cmd, startText='', count=1):

        if startText == '':
            # convert now to midnight this morning and use for default
            start = self.now.replace(hour=0,
                                     minute=0,
                                     second=0,
                                     microsecond=0)
        else:
            try:
                start = self.dateParser.fromString(startText)
                start = start.replace(hour=0, minute=0, second=0,
                                      microsecond=0)
            except:
                PrintErrMsg('Error: failed to parse start time\n')
                return

        # convert start date to the beginning of the week or month
        if cmd == 'calw':
            dayNum = int(start.strftime("%w"))
            if self.calMonday:
                dayNum -= 1
                if dayNum < 0:
                    dayNum = 6
            start = (start - timedelta(days=dayNum))
            end = (start + timedelta(days=(count * 7)))
        else:  # cmd == 'calm':
            start = (start - timedelta(days=(start.day - 1)))
            endMonth = (start.month + 1)
            endYear = start.year
            if endMonth == 13:
                endMonth = 1
                endYear += 1
            end = start.replace(month=endMonth, year=endYear)
            daysInMonth = (end - start).days
            offsetDays = int(start.strftime('%w'))
            if self.calMonday:
                offsetDays -= 1
                if offsetDays < 0:
                    offsetDays = 6
            totalDays = (daysInMonth + offsetDays)
            count = (totalDays / 7)
            if totalDays % 7:
                count += 1

        eventList = self._SearchForCalEvents(start, end, None)

        self._GraphEvents(cmd, start, count, eventList)

    def QuickAddEvent(self, eventText, reminder=None):

        if eventText == '':
            return

        if len(self.cals) != 1:
            PrintErrMsg("Must specify a single calendar\n")
            return

        newEvent = self._CalService().events().\
            quickAdd(calendarId=self.cals[0]['id'],
                     text=eventText).execute()

        if reminder or not FLAGS.default_reminders:
            rem = {}
            rem['reminders'] = {'useDefault': False,
                                'overrides': []}
            for r in reminder:
                n, m = ParseReminder(r)
                rem['reminders']['overrides'].append({'minutes': n,
                                                      'method': m})

            newEvent = self._CalService().events().\
                patch(calendarId=self.cals[0]['id'],
                      eventId=newEvent['id'],
                      body=rem).execute()

        if self.detailUrl:
            hLink = self._ShortenURL(newEvent['htmlLink'])
            PrintMsg(CLR_GRN(), 'New event added: %s\n' % hLink)

    def AddEvent(self, eTitle, eWhere, eStart, eEnd, eDescr, reminder):

        if len(self.cals) != 1:
            PrintErrMsg("Must specify a single calendar\n")
            return

        event = {}
        event['summary'] = stringToUnicode(eTitle)

        if FLAGS.allday:
            event['start'] = {'date': eStart}
            event['end'] = {'date': eEnd}

        else:
            event['start'] = {'dateTime': eStart,
                              'timeZone': self.cals[0]['timeZone']}
            event['end'] = {'dateTime': eEnd,
                            'timeZone': self.cals[0]['timeZone']}

        if eWhere:
            event['location'] = stringToUnicode(eWhere)
        if eDescr:
            event['description'] = stringToUnicode(eDescr)

        if reminder or not FLAGS.default_reminders:
            event['reminders'] = {'useDefault': False,
                                  'overrides': []}
            for r in reminder:
                n, m = ParseReminder(r)
                event['reminders']['overrides'].append({'minutes': n,
                                                        'method': m})

        newEvent = self._CalService().events().\
            insert(calendarId=self.cals[0]['id'],
                   body=event).execute()

        if self.detailUrl:
            hLink = self._ShortenURL(newEvent['htmlLink'])
            PrintMsg(CLR_GRN(), 'New event added: %s\n' % hLink)

    def DeleteEvents(self, searchText='', expert=False):

        # the empty string would get *ALL* events...
        if searchText == '':
            return

        eventList = self._SearchForCalEvents(None, None, searchText)

        self.iamaExpert = expert
        self._IterateEvents(self.now, eventList,
                            yearDate=True, work=self._DeleteEvent)

    def EditEvents(self, searchText=''):

        # the empty string would get *ALL* events...
        if searchText == '':
            return

        eventList = self._SearchForCalEvents(None, None, searchText)

        self._IterateEvents(self.now, eventList,
                            yearDate=True, work=self._EditEvent)

    def Remind(self, minutes=10, command=None):

        if command is None:
            command = self.command

        # perform a date query for now + minutes + slip
        start = self.now
        end = (start + timedelta(minutes=(minutes + 5)))

        eventList = self._SearchForCalEvents(start, end, None)

        message = ''

        for event in eventList:

            # skip this event if it already started
            # XXX maybe add a 2+ minute grace period here...
            if event['s'] < self.now:
                continue

            if self.military:
                tmpTimeStr = event['s'].strftime('%H:%M')
            else:
                tmpTimeStr = \
                    event['s'].strftime('%I:%M').lstrip('0') + \
                    event['s'].strftime('%p').lower()

            message += '%s  %s\n' % \
                       (tmpTimeStr, self._ValidTitle(event).strip())

        if message == '':
            return

        cmd = shlex.split(command)

        for i, a in zip(xrange(len(cmd)), cmd):
            if a == '%s':
                cmd[i] = message

        pid = os.fork()
        if not pid:
            os.execvp(cmd[0], cmd)

    def ImportICS(self, verbose=False, dump=False, reminder=None,
                  icsFile=None):

        def CreateEventFromVOBJ(ve):

            event = {}

            if verbose:
                print "+----------------+"
                print "| Calendar Event |"
                print "+----------------+"

            if hasattr(ve, 'summary'):
                DebugPrint("SUMMARY: %s\n" % ve.summary.value)
                if verbose:
                    print "Event........%s" % ve.summary.value
                event['summary'] = ve.summary.value

            if hasattr(ve, 'location'):
                DebugPrint("LOCATION: %s\n" % ve.location.value)
                if verbose:
                    print "Location.....%s" % ve.location.value
                event['location'] = ve.location.value

            if not hasattr(ve, 'dtstart') or not hasattr(ve, 'dtend'):
                PrintErrMsg("Error: event does not have a dtstart and "
                            "dtend!\n")
                return None

            if ve.dtstart.value:
                DebugPrint("DTSTART: %s\n" % ve.dtstart.value.isoformat())
            if ve.dtend.value:
                DebugPrint("DTEND: %s\n" % ve.dtend.value.isoformat())
            if verbose:
                if ve.dtstart.value:
                    print "Start........%s" % \
                        ve.dtstart.value.isoformat()
                if ve.dtend.value:
                    print "End..........%s" % \
                        ve.dtend.value.isoformat()
                if ve.dtstart.value:
                    print "Local Start..%s" % \
                        self._LocalizeDateTime(ve.dtstart.value)
                if ve.dtend.value:
                    print "Local End....%s" % \
                        self._LocalizeDateTime(ve.dtend.value)

            if hasattr(ve, 'rrule'):

                DebugPrint("RRULE: %s\n" % ve.rrule.value)
                if verbose:
                    print "Recurrence...%s" % ve.rrule.value

                event['recurrence'] = ["RRULE:" + ve.rrule.value]

            if hasattr(ve, 'dtstart') and ve.dtstart.value:
                # XXX
                # Timezone madness! Note that we're using the timezone for the
                # calendar being added to. This is OK if the event is in the
                # same timezone. This needs to be changed to use the timezone
                # from the DTSTART and DTEND values. Problem is, for example,
                # the TZID might be "Pacific Standard Time" and Google expects
                # a timezone string like "America/Los_Angeles". Need to find
                # a way in python to convert to the more specific timezone
                # string.
                # XXX
                # print ve.dtstart.params['X-VOBJ-ORIGINAL-TZID'][0]
                # print self.cals[0]['timeZone']
                # print dir(ve.dtstart.value.tzinfo)
                # print vars(ve.dtstart.value.tzinfo)

                start = ve.dtstart.value.isoformat()
                if isinstance(ve.dtstart.value, datetime):
                    event['start'] = {'dateTime': start,
                                      'timeZone': self.cals[0]['timeZone']}
                else:
                    event['start'] = {'date': start}

                if reminder or not FLAGS.default_reminders:
                    event['reminders'] = {'useDefault': False,
                                          'overrides': []}
                    for r in reminder:
                        n, m = ParseReminder(r)
                        event['reminders']['overrides'].append({'minutes': n,
                                                                'method': m})

                # Can only have an end if we have a start, but not the other
                # way around apparently...  If there is no end, use the start
                if hasattr(ve, 'dtend') and ve.dtend.value:
                    end = ve.dtend.value.isoformat()
                    if isinstance(ve.dtend.value, datetime):
                        event['end'] = {'dateTime': end,
                                        'timeZone': self.cals[0]['timeZone']}
                    else:
                        event['end'] = {'date': end}

                else:
                    event['end'] = event['start']

            if hasattr(ve, 'description') and ve.description.value.strip():
                descr = ve.description.value.strip()
                DebugPrint("DESCRIPTION: %s\n" % descr)
                if verbose:
                    print "Description:\n%s" % descr
                event['description'] = descr

            if hasattr(ve, 'organizer'):
                DebugPrint("ORGANIZER: %s\n" % ve.organizer.value)

                if ve.organizer.value.startswith("MAILTO:"):
                    email = ve.organizer.value[7:]
                else:
                    email = ve.organizer.value
                if verbose:
                    print "organizer:\n %s" % email
                event['organizer'] = {'displayName': ve.organizer.name,
                                      'email': email}

            if hasattr(ve, 'attendee_list'):
                DebugPrint("ATTENDEE_LIST : %s\n" % ve.attendee_list)
                if verbose:
                    print "attendees:"
                event['attendees'] = []
                for attendee in ve.attendee_list:
                    if attendee.value.upper().startswith("MAILTO:"):
                        email = attendee.value[7:]
                    else:
                        email = attendee.value
                    if verbose:
                        print " %s" % email

                    event['attendees'].append({'displayName': attendee.name,
                                               'email': email})

            return event

        try:
            import vobject
        except:
            PrintErrMsg('Python vobject module not installed!\n')
            sys.exit(1)

        if dump:
            verbose = True

        if not dump and len(self.cals) != 1:
            PrintErrMsg("Must specify a single calendar\n")
            return

        f = sys.stdin

        if icsFile:
            try:
                f = file(icsFile)
            except Exception, e:
                PrintErrMsg("Error: " + str(e) + "!\n")
                sys.exit(1)

        while True:

            try:
                v = vobject.readComponents(f).next()
            except StopIteration:
                break

            for ve in v.vevent_list:

                event = CreateEventFromVOBJ(ve)

                if not event:
                    continue

                if dump:
                    continue

                if not verbose:
                    newEvent = self._CalService().events().\
                        insert(calendarId=self.cals[0]['id'],
                               body=event).execute()
                    hLink = self._ShortenURL(newEvent['htmlLink'])
                    PrintMsg(CLR_GRN(), 'New event added: %s\n' % hLink)
                    continue

                PrintMsg(CLR_MAG(), "\n[S]kip [i]mport [q]uit: ")
                val = raw_input()
                if not val or val.lower() == 's':
                    continue
                if val.lower() == 'i':
                    newEvent = self._CalService().events().\
                        insert(calendarId=self.cals[0]['id'],
                               body=event).execute()
                    hLink = self._ShortenURL(newEvent['htmlLink'])
                    PrintMsg(CLR_GRN(), 'New event added: %s\n' % hLink)
                elif val.lower() == 'q':
                    sys.exit(0)
                else:
                    PrintErrMsg('Error: invalid input\n')
                    sys.exit(1)


def GetColor(value):
    colors = {'default': CLR_NRM(),
              'black': CLR_BLK(),
              'brightblack': CLR_BRBLK(),
              'red': CLR_RED(),
              'brightred': CLR_BRRED(),
              'green': CLR_GRN(),
              'brightgreen': CLR_BRGRN(),
              'yellow': CLR_YLW(),
              'brightyellow': CLR_BRYLW(),
              'blue': CLR_BLU(),
              'brightblue': CLR_BRBLU(),
              'magenta': CLR_MAG(),
              'brightmagenta': CLR_BRMAG(),
              'cyan': CLR_CYN(),
              'brightcyan': CLR_BRCYN(),
              'white': CLR_WHT(),
              'brightwhite': CLR_BRWHT(),
              None: CLR_NRM()}

    if value in colors:
        return colors[value]
    else:
        return None


def GetCalColors(calNames):
    calColors = {}
    for calName in calNames:
        calNameParts = calName.split("#")
        calNameSimple = calNameParts[0]
        calColor = calColors.get(calNameSimple)
        if len(calNameParts) > 0:
            calColorRaw = calNameParts[-1]
            calColorNew = GetColor(calColorRaw)
            if calColorNew is not None:
                calColor = calColorNew
        calColors[calNameSimple] = calColor
    return calColors


FLAGS = gflags.FLAGS
# allow mixing of commands and options
FLAGS.UseGnuGetOpt()

gflags.DEFINE_bool("help", None, "Show this help")
gflags.DEFINE_bool("helpshort", None, "Show command help only")
gflags.DEFINE_bool("version", False, "Show the version and exit")

gflags.DEFINE_string("client_id", __API_CLIENT_ID__, "API client_id")
gflags.DEFINE_string("client_secret", __API_CLIENT_SECRET__,
                     "API client_secret")

gflags.DEFINE_string("configFolder", None,
                     "Optional directory to load/store all configuration "
                     "information")
gflags.DEFINE_bool("includeRc", False,
                   "Whether to include ~/.gcalclirc when using configFolder")
gflags.DEFINE_multistring("calendar", [], "Which calendars to use")
gflags.DEFINE_multistring("defaultCalendar", [],
                          "Optional default calendar to use if no --calendar "
                          "options are given")
gflags.DEFINE_bool("military", False, "Use 24 hour display")

# Single --detail that allows you to specify what parts you want
gflags.DEFINE_multistring("details", [], "Which parts to display, can be: "
                          "'all', 'calendar', 'location', 'length', "
                          "'reminders', 'description', 'longurl', 'shorturl', "
                          "'url', 'attendees'")
# old style flags for backwards compatibility
gflags.DEFINE_bool("detail_all", False, "Display all details")
gflags.DEFINE_bool("detail_calendar", False, "Display calendar name")
gflags.DEFINE_bool("detail_location", False, "Display event location")
gflags.DEFINE_bool("detail_attendees", False, "Display event attendees")
gflags.DEFINE_bool("detail_length", False, "Display length of event")
gflags.DEFINE_bool("detail_reminders", False, "Display reminders")
gflags.DEFINE_bool("detail_description", False, "Display description")
gflags.DEFINE_integer("detail_description_width", 80, "Set description width")
gflags.DEFINE_enum("detail_url", None, ["long", "short"], "Set URL output")

gflags.DEFINE_bool("tsv", False, "Use Tab Separated Value output")
gflags.DEFINE_bool("started", True, "Show events that have started")
gflags.DEFINE_integer("width", 10, "Set output width", short_name="w")
gflags.DEFINE_bool("monday", False, "Start the week on Monday")
gflags.DEFINE_bool("color", True, "Enable/Disable all color output")
gflags.DEFINE_bool("lineart", True, "Enable/Disable line art")
gflags.DEFINE_bool("conky", False, "Use Conky color codes")

gflags.DEFINE_string("color_owner", "cyan", "Color for owned calendars")
gflags.DEFINE_string("color_writer", "green", "Color for writable calendars")
gflags.DEFINE_string("color_reader", "magenta",
                     "Color for read-only calendars")
gflags.DEFINE_string("color_freebusy", "default",
                     "Color for free/busy calendars")
gflags.DEFINE_string("color_date", "yellow", "Color for the date")
gflags.DEFINE_string("color_now_marker", "brightred",
                     "Color for the now marker")
gflags.DEFINE_string("color_border", "white", "Color of line borders")

gflags.DEFINE_string("locale", None, "System locale")

gflags.DEFINE_multistring("reminder", [],
                          "Reminders in the form 'TIME METH' or 'TIME'.  TIME "
                          "is a number which may be followed by an optional "
                          "'w', 'd', 'h', or 'm' (meaning weeks, days, hours, "
                          "minutes) and default to minutes.  METH is a string "
                          "'popup', 'email', or 'sms' and defaults to popup.")
gflags.DEFINE_string("title", None, "Event title")
gflags.DEFINE_string("where", None, "Event location")
gflags.DEFINE_string("when", None, "Event time")
gflags.DEFINE_integer("duration", None,
                      "Event duration in minutes or days if --allday is given.")
gflags.DEFINE_string("description", None, "Event description")
gflags.DEFINE_bool("allday", False,
                   "If --allday is given, the event will be an all-day event "
                   "(possibly multi-day if --duration is greater than 1). The "
                   "time part of the --when will be ignored.")
gflags.DEFINE_bool("prompt", True,
                   "Prompt for missing data when adding events")
gflags.DEFINE_bool("default_reminders", True,
                   "If no --reminder is given, use the defaults.  If this is "
                   "false, do not create any reminders.")

gflags.DEFINE_bool("iamaexpert", False, "Probably not")
gflags.DEFINE_bool("refresh", False, "Delete and refresh cached data")
gflags.DEFINE_bool("cache", True, "Execute command without using cache")

gflags.DEFINE_bool("verbose", False, "Be verbose on imports",
                   short_name="v")
gflags.DEFINE_bool("dump", False, "Print events and don't import",
                   short_name="d")

gflags.RegisterValidator("details",
                         lambda value: all(x in ["all", "calendar",
                                                 "location", "length",
                                                 "reminders", "description",
                                                 "longurl", "shorturl", "url",
                                                 "attendees"]
                                           for x in value))
gflags.RegisterValidator("reminder",
                         lambda value: all(ParseReminder(x) for x in value))
gflags.RegisterValidator("color_owner",
                         lambda value: GetColor(value) is not None)
gflags.RegisterValidator("color_writer",
                         lambda value: GetColor(value) is not None)
gflags.RegisterValidator("color_reader",
                         lambda value: GetColor(value) is not None)
gflags.RegisterValidator("color_freebusy",
                         lambda value: GetColor(value) is not None)
gflags.RegisterValidator("color_date",
                         lambda value: GetColor(value) is not None)
gflags.RegisterValidator("color_now_marker",
                         lambda value: GetColor(value) is not None)
gflags.RegisterValidator("color_border",
                         lambda value: GetColor(value) is not None)

gflags.ADOPT_module_key_flags(gflags)


def BowChickaWowWow():
    try:
        argv = sys.argv
        if os.path.exists(os.path.expanduser('~/.gcalclirc')):
            # We want .gcalclirc to be sourced before any other --flagfile
            # params since we may be told to use a specific config folder, we
            # need to store generated argv in temp variable
            tmpArgv = [argv[0], "--flagfile=~/.gcalclirc"] + argv[1:]
        else:
            tmpArgv = argv
        args = FLAGS(tmpArgv)
    except gflags.FlagsError, e:
        PrintErrMsg(str(e))
        Usage(True)
        sys.exit(1)

    if FLAGS.configFolder:
        if not os.path.exists(os.path.expanduser(FLAGS.configFolder)):
            os.makedirs(os.path.expanduser(FLAGS.configFolder))
        if os.path.exists(os.path.expanduser("%s/gcalclirc" %
                                             FLAGS.configFolder)):
            if not FLAGS.includeRc:
                tmpArgv = argv + ["--flagfile=%s/gcalclirc" %
                                  FLAGS.configFolder, ]
            else:
                tmpArgv += ["--flagfile=%s/gcalclirc" % FLAGS.configFolder, ]

        FLAGS.Reset()
        args = FLAGS(tmpArgv)

    argv = tmpArgv

    if FLAGS.version:
        Version()

    if FLAGS.help:
        Usage(True)
        sys.exit()

    if FLAGS.helpshort:
        Usage()
        sys.exit()

    if not FLAGS.color:
        CLR.useColor = False

    if not FLAGS.lineart:
        ART.useArt = False

    if FLAGS.conky:
        SetConkyColors()

    if FLAGS.locale:
        try:
            locale.setlocale(locale.LC_ALL, FLAGS.locale)
        except Exception, e:
            PrintErrMsg("Error: " + str(e) + "!\n"
                        "Check supported locales of your system.\n")
            sys.exit(1)

    # pop executable off the stack
    args = args[1:]
    if len(args) == 0:
        PrintErrMsg('Error: no command\n')
        sys.exit(1)

    # No sense instaniating gcalcli for nothing
    if not args[0] in ['list', 'search', 'agenda', 'calw', 'calm', 'quick',
                       'add', 'delete', 'edit', 'remind', 'import', 'help']:
        PrintErrMsg('Error: %s is an invalid command' % args[0])
        sys.exit(1)

    # all other commands require gcalcli be brought up
    if args[0] == 'help':
        Usage()
        sys.exit(0)

    if len(FLAGS.calendar) == 0:
        FLAGS.calendar = FLAGS.defaultCalendar

    calNames = []
    calNameColors = []
    calColors = GetCalColors(FLAGS.calendar)
    calNamesFiltered = []
    for calName in FLAGS.calendar:
        calNameSimple = calName.split("#")[0]
        calNamesFiltered.append(stringToUnicode(calNameSimple))
        calNameColors.append(calColors[calNameSimple])
    calNames = calNamesFiltered

    if 'all' in FLAGS.details or FLAGS.detail_all:
        if not FLAGS['detail_calendar'].present:
            FLAGS['detail_calendar'].value = True
        if not FLAGS['detail_location'].present:
            FLAGS['detail_location'].value = True
        if not FLAGS['detail_length'].present:
            FLAGS['detail_length'].value = True
        if not FLAGS['detail_reminders'].present:
            FLAGS['detail_reminders'].value = True
        if not FLAGS['detail_description'].present:
            FLAGS['detail_description'].value = True
        if not FLAGS['detail_url'].present:
            FLAGS['detail_url'].value = "long"
        if not FLAGS['detail_attendees'].present:
            FLAGS['detail_attendees'].value = True
    else:
        if 'calendar' in FLAGS.details:
            FLAGS['detail_calendar'].value = True
        if 'location' in FLAGS.details:
            FLAGS['detail_location'].value = True
        if 'attendees' in FLAGS.details:
            FLAGS['detail_attendees'].value = True
        if 'length' in FLAGS.details:
            FLAGS['detail_length'].value = True
        if 'reminders' in FLAGS.details:
            FLAGS['detail_reminders'].value = True
        if 'description' in FLAGS.details:
            FLAGS['detail_description'].value = True
        if 'longurl' in FLAGS.details or 'url' in FLAGS.details:
            FLAGS['detail_url'].value = 'long'
        elif 'shorturl' in FLAGS.details:
            FLAGS['detail_url'].value = 'short'
        if 'attendees' in FLAGS.details:
            FLAGS['detail_attendees'].value = True

    gcal = gcalcli(calNames=calNames,
                   calNameColors=calNameColors,
                   military=FLAGS.military,
                   detailCalendar=FLAGS.detail_calendar,
                   detailLocation=FLAGS.detail_location,
                   detailAttendees=FLAGS.detail_attendees,
                   detailLength=FLAGS.detail_length,
                   detailReminders=FLAGS.detail_reminders,
                   detailDescr=FLAGS.detail_description,
                   detailDescrWidth=FLAGS.detail_description_width,
                   detailUrl=FLAGS.detail_url,
                   ignoreStarted=not FLAGS.started,
                   calWidth=FLAGS.width,
                   calMonday=FLAGS.monday,
                   calOwnerColor=GetColor(FLAGS.color_owner),
                   calWriterColor=GetColor(FLAGS.color_writer),
                   calReaderColor=GetColor(FLAGS.color_reader),
                   calFreeBusyColor=GetColor(FLAGS.color_freebusy),
                   dateColor=GetColor(FLAGS.color_date),
                   nowMarkerColor=GetColor(FLAGS.color_now_marker),
                   borderColor=GetColor(FLAGS.color_border),
                   tsv=FLAGS.tsv,
                   refreshCache=FLAGS.refresh,
                   useCache=FLAGS.cache,
                   configFolder=FLAGS.configFolder,
                   client_id=FLAGS.client_id,
                   client_secret=FLAGS.client_secret
                   )

    if args[0] == 'list':
        gcal.ListAllCalendars()

    elif args[0] == 'search':
        if len(args) != 2:
            PrintErrMsg('Error: invalid search string\n')
            sys.exit(1)

        # allow unicode strings for input
        gcal.TextQuery(stringToUnicode(args[1]))

        sys.stdout.write('\n')

    elif args[0] == 'agenda':
        if len(args) == 3:  # start and end
            gcal.AgendaQuery(startText=args[1], endText=args[2])
        elif len(args) == 2:  # start
            gcal.AgendaQuery(startText=args[1])
        elif len(args) == 1:  # defaults
            gcal.AgendaQuery()
        else:
            PrintErrMsg('Error: invalid agenda arguments\n')
            sys.exit(1)

        if not FLAGS.tsv:
            sys.stdout.write('\n')

    elif args[0] == 'calw':
        if not FLAGS.width:
            PrintErrMsg('Error: invalid width, don\'t be an idiot!\n')
            sys.exit(1)

        if len(args) >= 2:
            try:
                # Test to make sure args[1] is a number
                int(args[1])
            except:
                PrintErrMsg('Error: invalid calw arguments\n')
                sys.exit(1)

        if len(args) == 3:  # weeks and start
            gcal.CalQuery(args[0], count=int(args[1]), startText=args[2])
        elif len(args) == 2:  # weeks
            gcal.CalQuery(args[0], count=int(args[1]))
        elif len(args) == 1:  # defaults
            gcal.CalQuery(args[0])
        else:
            PrintErrMsg('Error: invalid calw arguments\n')
            sys.exit(1)

        sys.stdout.write('\n')

    elif args[0] == 'calm':
        if not FLAGS.width:
            PrintErrMsg('Error: invalid width, don\'t be an idiot!\n')
            sys.exit(1)

        if len(args) == 2:  # start
            gcal.CalQuery(args[0], startText=args[1])
        elif len(args) == 1:  # defaults
            gcal.CalQuery(args[0])
        else:
            PrintErrMsg('Error: invalid calm arguments\n')
            sys.exit(1)

        sys.stdout.write('\n')

    elif args[0] == 'quick':
        if len(args) != 2:
            PrintErrMsg('Error: invalid event text\n')
            sys.exit(1)

        # allow unicode strings for input
        gcal.QuickAddEvent(stringToUnicode(args[1]),
                           reminder=FLAGS.reminder)

    elif (args[0] == 'add'):
        if FLAGS.prompt:
            if FLAGS.title is None:
                PrintMsg(CLR_MAG(), "Title: ")
                FLAGS.title = raw_input()
            if FLAGS.where is None:
                PrintMsg(CLR_MAG(), "Location: ")
                FLAGS.where = raw_input()
            if FLAGS.when is None:
                PrintMsg(CLR_MAG(), "When: ")
                FLAGS.when = raw_input()
            if FLAGS.duration is None:
                if FLAGS.allday:
                    PrintMsg(CLR_MAG(), "Duration (days): ")
                else:
                    PrintMsg(CLR_MAG(), "Duration (mins): ")
                FLAGS.duration = raw_input()
            if FLAGS.description is None:
                PrintMsg(CLR_MAG(), "Description: ")
                FLAGS.description = raw_input()
            if not FLAGS.reminder:
                while 1:
                    PrintMsg(CLR_MAG(),
                             "Enter a valid reminder or '.' to end: ")
                    r = raw_input()
                    if r == '.':
                        break
                    n, m = ParseReminder(str(r))
                    FLAGS.reminder.append(str(n) + ' ' + m)

        # calculate "when" time:
        eStart, eEnd = GetTimeFromStr(FLAGS.when, FLAGS.duration)

        gcal.AddEvent(FLAGS.title, FLAGS.where, eStart, eEnd,
                      FLAGS.description, FLAGS.reminder)

    elif args[0] == 'delete':
        if len(args) != 2:
            PrintErrMsg('Error: invalid search string\n')
            sys.exit(1)

        # allow unicode strings for input
        gcal.DeleteEvents(stringToUnicode(args[1]),
                          FLAGS.iamaexpert)

        sys.stdout.write('\n')

    elif args[0] == 'edit':
        if len(args) != 2:
            PrintErrMsg('Error: invalid search string\n')
            sys.exit(1)

        # allow unicode strings for input
        gcal.EditEvents(stringToUnicode(args[1]))

        sys.stdout.write('\n')

    elif args[0] == 'remind':
        if len(args) == 3:  # minutes and command
            gcal.Remind(int(args[1]), args[2])
        elif len(args) == 2:  # minutes
            gcal.Remind(int(args[1]))
        elif len(args) == 1:  # defaults
            gcal.Remind()
        else:
            PrintErrMsg('Error: invalid remind arguments\n')
            sys.exit(1)

    elif args[0] == 'import':
        if len(args) == 1:  # stdin
            gcal.ImportICS(FLAGS.verbose, FLAGS.dump, FLAGS.reminder)
        elif len(args) == 2:  # ics file
            gcal.ImportICS(FLAGS.verbose, FLAGS.dump, FLAGS.reminder, args[1])
        else:
            PrintErrMsg('Error: invalid import arguments\n')
            sys.exit(1)


def SIGINT_handler(signum, frame):
    PrintErrMsg('Signal caught, bye!\n')
    sys.exit(1)

signal.signal(signal.SIGINT, SIGINT_handler)

if __name__ == '__main__':
    BowChickaWowWow()
