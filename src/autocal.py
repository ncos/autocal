#!/usr/bin/env python

from datetime import *
from gcalcli import *

db_file_meat = '../db/meat.md'
db_file_fish = '../db/fish.md'

cal_cid = '996124500222-lrv2poibi8ll15cg25s1bs8eu7atjfk2.apps.googleusercontent.com'
cal_seq = 'zmQliJX0STI81we6csuy5wzb'



def setCal(cal_name):
    matches = []
    for cal in gcal.allCals:
        if cal_name == cal['summary']:
            gcal.cals = [cal]
            return
    print ("ERROR! there is no such calendar as '" + cal_name + "'!")
    print ("Available:")
    gcal.ListAllCalendars()
    exit(1)

def removeByDescription(desc, start=None, end=None):
    ev_list = gcal._SearchForCalEvents(start, end, None)
    gcal.iamaExpert = True
    for ev in ev_list: 
        if desc in ev['description']:
            #print ev['summary']
            #gcal.iamaExpert = False
            gcal._DeleteEvent(ev)

# Food db related functions
class Food:
    def __init__(self):
        self.name = "(unknown food)"
        self.description = ""
        self.calories = 0.0
        self.price = 0.0
        self.avaluable_courses = []
        self.timesaweek = -1
        self.sTime, self.eTime = GetTimeFromStr('31/12/1984 00:00', 5)


class OneDayShedule:
    def __init__(self):
        self.foods = []
        self.snack = []
    
    def setTIME(self, eTimeStart):
        '''
        should be called after all setFood insts have been called
        call like ods.setTIME(datetime(2002, 12, 4, 8, 0))
        '''
        eDistance = 180
        eDuration = 30
        self.sTimes = [(eTimeStart + timedelta(minutes=float(i*eDistance))).isoformat()
                                                       for i in xrange(len(self.foods))]
        self.eTimes = [(eTimeStart + timedelta(minutes=float(i*eDistance+eDuration))).isoformat()
                                                       for i in xrange(len(self.foods))]                                                    
        for (i, food_list) in enumerate(self.foods):
            for food in food_list:
                food.sTime = self.sTimes[i]
                food.eTime = self.eTimes[i]
        
    def setFoodI(self, i, food_tuple):
        '''
        i is a number from 1 to ... - the number of food
        food_tuple - set of foods to take
        '''
        if (i < 1): 
            raise ValueError("'i' can be in range 1..inf! (i="+str(i)+")") 
        while len(self.foods) < i:
            self.foods.append([Food()]) # Extending with dummy placeholders
        self.foods[i - 1] = food_tuple
    
    def __repr__(self):
        pass

    def send(self):
        # Google calendar specific functions

        gcal = gcalcli(client_id=cal_cid, client_secret=cal_seq, refreshCache=True)       
        setCal('red')
        n, m = ParseReminder('5m popup')
        for (i, food_list) in enumerate(self.foods):
            text = ""
            for food in food_list:
                text += food.name + '\n'


def getListOfFood(file_name):
    f_lines = []
    with open(file_name, 'r') as f:
        f_lines = f.readlines()
    

gcal = gcalcli(client_id=cal_cid, client_secret=cal_seq, refreshCache=True)       
def main():

    setCal('red');
    n, m = ParseReminder('30m popup')
    eStart, eEnd = GetTimeFromStr('4/19/2017 10:00', 60)
    gcal.ListAllCalendars()
    gcal.AddEvent("My test event", "NONE", eStart, eEnd, "_autogenerated_", [str(n) + ' ' + m])  
    #removeByDescription("_autogenerated_")
    print datetime.now(tzlocal())
    print eStart

    #ods = OneDayShedule()
    #ods.setTIME(datetime(2002, 12, 4, 8, 0))

    #print getListOfFood(db_file_meat)

    #print ods.times


if __name__ == '__main__':
    main()
