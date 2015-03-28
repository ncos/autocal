#!/usr/bin/env python

from gcalcli import *

gcal = gcalcli(client_id='996124500222-lrv2poibi8ll15cg25s1bs8eu7atjfk2.apps.googleusercontent.com',
               client_secret='zmQliJX0STI81we6csuy5wzb')

def set_cal(cal_name):
    matches = []
    for cal in gcal.allCals:
        if cal_name == cal['summary']:
            gcal.cals = [cal]
            return True
    print ("ERROR! there is no such calendar as '" + cal_name + "'!")
    print ("Available:")
    gcal.ListAllCalendars()
    return False
            
def main():
    
    set_cal('tserver.calendar@gmail.com');
    n, m = ParseReminder('30m popup')
    eStart, eEnd = GetTimeFromStr('3/28/2015 10:00', 60)
    
    gcal.ListAllCalendars()
    gcal.AddEvent("My test event", "NONE", eStart, eEnd, "---", [str(n) + ' ' + m]) 
    

if __name__ == '__main__':
    main()
