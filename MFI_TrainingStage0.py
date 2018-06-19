# -*- coding: utf-8 -*-

# 2AC Visual task
# Training stage 0: A circular grating is presented and a free reward is given on the same side of the stimulus.
# When the mouse licks, a second reward becomes available and the stimulus goes off. 
# The grating lasts until the animal collects the reward on the correct side but independently of the first choice.
# Mice are expected to complete 1 block of 30 trials for each stimulus modality.

# Author: Maria Florencia Iacaruso
# contact: florencia.iacaruso@gmail.com

print 'Running Training stage 1 Visual Task'

#----------------------------------------------
# import libraries


import numpy as np   #matrix algebra
import numpy.random as rnd
import billiard
import matplotlib.pyplot as plt   #plotting library
import pygame   #library for sound presentation
import time #library for keeping track of time
import RPi.GPIO as GPIO  #library controlling the input output pins
import pickle
import csv
import socket
import requests as req
from psychopy import core, visual, event
from psychopy.monitors import Monitor
from psychopy import sound, core

tock = sound.Sound('8000', secs=0.4, sampleRate=96000)



max16bit = 32766

###-------------------------------------------
### Initialize function for sending data to server

pi_ID = str(1) # change depending on cage number
def send_data(load):
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    link = 'http://192.168.0.99:8000/getData/' + pi_ID + '/get_PiData/'

    session = req.Session()
    r1 = session.get(link,headers=headers)

    link1 = 'http://192.168.0.99:8000/getData/' + pi_ID + '/write_PiData/'


    payload = {'piData':load,'csrfmiddlewaretoken':r1.cookies['csrftoken']}
    #cookies = dict(session.cookies)
    session.post(link1,headers=headers,data=payload)
    return None


#--------------------------------------------------------
win = visual.Window( allowGUI=0,waitBlanking=1,fullscr=True)
win.refreshThreshold = 1/85 + 0.004
# INITIALISE SOME STIMULI

gaborL = visual.GratingStim(win, tex="sin", texRes=1024,
		size=[0.4,0.7],sf=[4,0],ori=0,name='gaborL', pos=[-0.4 , 0], contrast = 1, mask='circle')

gaborR = visual.GratingStim(win, tex="sin", texRes=1024,
		size=[0.4,0.7],sf=[4,0],ori=0,name='gaborR', pos=[0.4 , 0], contrast = 1, mask='circle')

FullRect = visual.Rect(win, width=5, height=5, name='FullRect', fillColor=[0, 0, 0])

# Set up input output on rasperry pi board

GPIO.setmode(GPIO.BOARD)  #sets the naming system for the pins

lickL = 37
lickR = 38


# set those pins as input
GPIO.setup(lickL,GPIO.IN)
GPIO.setup(lickR,GPIO.IN)

# add forced callbacks to those pins so that program response is instantaneous
GPIO.add_event_detect(lickL,GPIO.RISING,bouncetime=200)
GPIO.add_event_detect(lickR,GPIO.RISING,bouncetime=200)

### set pins to trigger solenoids
rewL = 40
rewR = 36
##
### set those pins as outputs
GPIO.setup(rewL,GPIO.OUT)
GPIO.setup(rewR,GPIO.OUT)


## Set LEDs for visual stimulation 
LEDPINL = 11
LEDPINR = 12
##
### set those pins as outputs
GPIO.setup(LEDPINL,GPIO.OUT)
GPIO.setup(LEDPINR,GPIO.OUT)


#-----------------------------------------
#Initialise reward delivery functions and processes (billiard is python 3 version of the multiprocessing library)

solOpenDur = 0.2 #(needs to be calibrated)

# Initialise reward delivery function
def deliverRew(channel):
    GPIO.output(channel,0)
    GPIO.output(channel,1)
    time.sleep(solOpenDur)
    GPIO.output(channel,0)

# Create processes that will deliver reward. When processes are run i.e. rewProcl.run()
# a separate python instance on one core runs the code in the assigned function so
# that the rest of the code doesn't block during the sleep comand
rewProcL = billiard.Process(target=deliverRew,args=(rewL,))
rewProcR = billiard.Process(target=deliverRew,args=(rewR,))


# Helper function called when reward is to be delivered.
# The mapping is 0 for right response, 1 left response

def rew_action(side,rewProcR,rewProcL):
    if side == 0:
        rewProcR.run()
        rewProcR = billiard.Process(target = deliverRew,args=(rewR,))

    if side == 1:
        rewProcL.run()
        rewProcL = billiard.Process(target = deliverRew,args=(rewL,))

    LR_target = rnd.randint(2)
    return LR_target

#-------------------------------------------
# Initialize variables
Training = True
maxRews = 20 ; nRews = 0

# Initialize lists for storage of reward and lick sides and times
lickList = []; rewList = [];  stimList = [];  stimList2 = [];
minILI = 0.01
test=1;
MaxExpDur = 60*45; # Time in seconds of experiment duration  

# Generate random delays to play next stimulus (uniformely distributed)
minDelay=200
maxDelay=300
randDelays = rnd.randint(minDelay, maxDelay,maxRews)
randDelays=0.001*randDelays # unit is seconds
##plt.hist(randDelays)
##fig=plt.gcf
##plt.show()


# Generate array of random order for presentation of Visual stim
sideIDs=np.zeros(maxRews)
sideIDs[0 : (maxRews/2)]=1
sideIDs[(maxRews/2) : maxRews]=2
rand_order=np.arange(maxRews)
rnd.shuffle(rand_order)
sideIDs=sideIDs[rand_order]

rand_oris=np.zeros(maxRews)
rand_oris[range(0 ,maxRews,2) ]=0
rand_oris[range(1 ,maxRews,2)]=45
rand_oris=rand_oris[rand_order]
print rand_oris


# Initialize relevant timers
timer = time.time()-10;  lickT=time.time();prevL = time.time(); sendT=time.time()

# Define start time
start = time.time()

# Deliver an initial free reward on each side
_ = rew_action(0,rewProcR,rewProcL) # 1 left, 0 right
rewList.append([time.time()-start,'R'])
time.sleep(3)
_ = rew_action(1,rewProcR,rewProcL)
rewList.append([time.time()-start,'L'])
time.sleep(3)

def data_sender(lickList,rewList,stimList,sendT):

    lickStr = 'LickList:' + '-'.join([str(np.round(entry[0],decimals=4))+entry[1] for entry in lickList])
    rewStr = 'rewList:' + '-'.join([str(np.round(entry[0],decimals=4))+entry[1] for entry in rewList])
    stimStr = 'stimList:'  + '-'.join([str(np.round(entry[0],decimals=4))+entry[1] for entry in stimList])

    sendStr = ','.join([rewStr,stimStr,lickStr])
            
    sendProc = billiard.Process(target=send_data,args=(sendStr,))
    sendProc.start()
    print 'sending'
    send_data(sendStr)
    sendT = time.time()
    stimList = []; lickList = []; rewList = [];
    return lickList, rewList,stimList, sendT



print 'Starting loop'
##print nRews
while Training:
        if test==0:
            if (time.time()-sendT>5):
                lickList, rewList, stimList, sendT = data_sender(lickList,rewList,stimList,sendT)





# Check to make sure that only 1 lick is detected if the mouse makes contact.
# Corrects for switch bounces from the relay in the lick


    # Play the grating

        if sideIDs[nRews]== 1:
            
            gaborL.ori=rand_oris[nRews];
            gaborL.draw()

            if event.getKeys(keyList=['escape', 'q']):
                Training=False

            win.flip()


            if nRews == len(stimList2):
                stimList.append([time.time()-start,'GraL',rand_oris[nRews]])
                stimList2.append([time.time()-start,'GraL',rand_oris[nRews]])

                # Free reward
                _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                rewList.append([time.time()-start,'L'])
                tock.play()
# HERE ADD THE DETECTION OF LICKS IN THE 2 SPOUTS AND THE REWARD IF LICK IN THE CORRECT SPOUT
# Lick detection and is appropiate reward delivery

            if(GPIO.event_detected(lickL)):
                if GPIO.input(lickL):
##                    print 'L'
                    if (time.time()-prevL)>minILI:
                        lickT = time.time()
                        lickList.append([lickT-start,'L'])
                        prevL = time.time()
                        _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                        rewList.append([time.time()-start,'L'])
                        FullRect.draw()
                        win.flip()
                        time.sleep(randDelays[nRews])
                        nRews = nRews+1;
##                        print nRews
                        
                    else:
                        prevL = time.time()
                        
            if(GPIO.event_detected(lickR)):
                if GPIO.input(lickR):
##                    print 'R'
                    if (time.time()-prevL)>minILI:
                        lickT = time.time()
                        lickList.append([lickT-start,'R'])
                        prevL = time.time()
                    else:
                        prevL = time.time()
       
        else:

            gaborR.ori=rand_oris[nRews];
            gaborR.draw()
            if event.getKeys(keyList=['escape', 'q']):
                win.close()
                core.quit()
            win.flip()
            
            if nRews == len(stimList2):
                stimList.append([time.time()-start,'GraR',rand_oris[nRews]])
                stimList2.append([time.time()-start,'GraR',rand_oris[nRews]])
                # Free reward
                _ = rew_action(0,rewProcR,rewProcL) # 1 left, 0 right
                rewList.append([time.time()-start,'R'])
                tock.play()
# HERE ADD THE DETECTION OF LICKS IN THE 2 SPOUTS AND THE REWARD IF LICK IN THE CORRECT SPOUT
# Lick detection and is appropiate reward delivery

            if(GPIO.event_detected(lickR)):
                if GPIO.input(lickR):
##                    print 'R'
                    if (time.time()-prevL)>minILI:
                        lickT = time.time()
                        lickList.append([lickT-start,'R'])
                        prevL = time.time()
                        _ = rew_action(0,rewProcR,rewProcL)
                        rewList.append([time.time()-start,'R'])
                        FullRect.draw()
                        win.flip()
                        time.sleep(randDelays[nRews])
                        nRews = nRews+1;
##                        print nRews
                    else:
                        prevL = time.time()
                    
            if(GPIO.event_detected(lickL)):
                if GPIO.input(lickL):
##                        print 'L'
                    if (time.time()-prevL)>minILI:
                        lickT = time.time()
                        lickList.append([lickT-start,'L'])
                        prevL = time.time()
                    else:
                        prevL = time.time()


        if (nRews>(maxRews-1)) or time.time() - start > MaxExpDur:
            Training=False
            
        if event.getKeys(keyList=['escape', 'q']):
            Training=False
                            
if test==0:
    lickList, rewList, stimList, sendT = data_sender(lickList,rewList,stimList,sendT)

print 'stimList2'
print stimList2
print 'rewList'
print rewList
print 'lickList'
print lickList
print ['Total time = ' , time.time()-start]
print ['Total licks = ' , len(lickList)]
print ['Total trials = ' , len(stimList2)]

#

     


