# 2AC Auditory and visual task training stage 0
# Trail starts with a sound/LED and a free reward on the side associated with the stimulus.
# The stimulus is presented until the correct port is licked and then there is a reward and the sound goes off
# Visual and auditory blocls are interleaved. 60 trails in the first session 
# Author: Maria Florencia Iacaruso
# contact: florencia.iacaruso@gmail.com

print 'Running Training stage 0 Sound and visual in blocks of 30'

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

max16bit = 32766

###-------------------------------------------
### Initialize function for sending data to server

##pi_IP = [(s.connect(('8.8.8.8',80)), s.getsocketname()[0],s.close()) for s in [socket.socket(socket.AF_INET,socket.SOCK_DGRAM)]][0][1]
##pi_ID = str(int(pi_IP[-3:])-100)
pi_ID = str(1) # change depending on cage number
##

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
# Define function to generate the sound waves

def gensin(frequency=8000, duration=0.1, sampRate=96000,edgeWin=0.05):

    """ Frequency in Hz, duration in seconds and sampleRate
        in Hz"""

    cycles = np.linspace(0,duration*2*np.pi,num=duration*sampRate)
    wave = np.sin(cycles*frequency,dtype='float32')

    ####smooth your sinwave
    numSmoothSamps = np.round(edgeWin*sampRate)
    #onset smoothing
    wave[0:numSmoothSamps] = wave[0:numSmoothSamps] * np.cos(np.pi*np.linspace(0.5,1,num=numSmoothSamps))**2
    wave[-numSmoothSamps:] = wave[-numSmoothSamps:] * np.cos(np.pi*np.linspace(0,0.5,num=numSmoothSamps))**2
    wave = np.round(wave*max16bit)

    return wave.astype('int16')
SOUNDDUR = 1
sound1 = gensin(frequency=8000, duration=30)
sound2 = gensin(frequency=15000, duration=30)

# Set-up the audio mixer

sR = 96000

pygame.mixer.pre_init(frequency=sR, size=-16, channels=1, buffer=4096)
pygame.init()
pygame.mixer.init(frequency=sR, size=-16, channels=1, buffer=4096)

# convert sound1 to a sound array
sndArray1 = pygame.sndarray.make_sound(sound1)
sndArray2 = pygame.sndarray.make_sound(sound2)
#--------------------------------------------------------
# Set up input output on rasperry pi board

GPIO.setmode(GPIO.BOARD)  #sets the naming system for the pins

lickL = 36
lickR = 38


# set those pins as input
GPIO.setup(lickL,GPIO.IN)
GPIO.setup(lickR,GPIO.IN)

# add forced callbacks to those pins so that program response is instantaneous
GPIO.add_event_detect(lickL,GPIO.RISING)
GPIO.add_event_detect(lickR,GPIO.RISING)

### set pins to trigger solenoids
rewL = 37
rewR = 33
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

solOpenDur = 0.15 #(needs to be calibrated)

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
maxRews = 4 ; # Maximum number of rewards per block  
maxRews2=1; # This is the number of blocks. 1 block means 1 block of visual stimuli and 1 block of auditory stimuli 
maxRews3=maxRews*maxRews2*2;

# Experiment structure 
ExpDur = 45*60 #max total duration in seconds

# Initialize lists for storage of reward and lick sides and times
nRews = 0
lickList = []; rewList = []; stimList = []; stimList2 = [];
minILI = 0.05
nPun=0 # Counts the number of consecutive punishments

# Generate random delays to play sound (uniformely distributed)
minDelay=6000
maxDelay=10000

randDelays = rnd.randint(minDelay, maxDelay,maxRews3)
randDelays=0.001*randDelays # unit is seconds
##plt.hist(randDelays)
##fig=plt.gcf
##plt.show()

# Generate a loop to create many randomly permuted blocks of sound or LEDs and concatenate them
StimIDs3=np.zeros(0)
for iterNr in range(maxRews2):
    # Generate array of random order for presentation of sounds
    SoundIDs=np.zeros(maxRews)
    SoundIDs[0 : (maxRews/2)]=1
    SoundIDs[(maxRews/2) : maxRews]=2
    rnd.shuffle(SoundIDs)

    # Generate array of random order for presentation of Visual stim
    LEDsIDs=np.zeros(maxRews)
    LEDsIDs[0 : (maxRews/2)]=3
    LEDsIDs[(maxRews/2) : maxRews]=4
    rnd.shuffle(LEDsIDs)
    
    StimIDs2=np.concatenate((SoundIDs, LEDsIDs),axis=0)
    StimIDs3=np.concatenate((StimIDs3, StimIDs2),axis=0)
print StimIDs3


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


#_____________________________________________________________________________

def data_sender(lickList,rewList,stimList,sendT):

    lickStr = 'LickList:' + '-'.join([str(np.round(entry[0],decimals=4))+entry[1] for entry in lickList])
    rewStr = 'rewList:' + '-'.join([str(np.round(entry[0],decimals=4))+entry[1] for entry in rewList])
    stimStr = 'stimList:'  + '-'.join([str(np.round(entry[0],decimals=4))+entry[1] for entry in stimList])

    sendStr = ','.join([rewStr,stimStr,lickStr])
            
    sendProc = billiard.Process(target=send_data,args=(sendStr,))
    sendProc.start()
    print 'sending'
    #send_data(sendStr)
    sendT = time.time()
    stimList = []; lickList = []; rewList = [];
    return lickList, rewList,stimList, sendT



print 'Starting loop'
print nRews
while Training:
    # control sector to send data to webserver
    # if 5 seconds have elapsed since the last data_sending
                if (time.time()-sendT>5):
                    lickList, rewList, stimList, sendT = data_sender(lickList,rewList,stimList,sendT)
   
        
   # Check to make sure that only 1 lick is detected if the mouse makes contact.
        # Corrects for switch bounces from the relay in the lick

 
            # Play the sound, needs to change to present 1 of the 2 sounds



                if StimIDs3[nRews]== 1:
                    sndArray1.play()
                    if nRews == len(stimList2):
                        stimList.append([time.time()-start,'Sound8KHz'])
                        stimList2.append([time.time()-start,'Sound8KHz'])
                        prevL = time.time()

                        _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                        rewList.append([time.time()-start,'L'])
                        
                    if(GPIO.event_detected(lickL)):
                        if GPIO.input(lickL):
                            print 'L'
                            if (time.time()-prevL)>minILI:
                                lickT = time.time()
                                lickList.append([lickT-start,'L'])
                                _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                                rewList.append([time.time()-start,'L'])
                                
                                pygame.mixer.stop()
                                time.sleep(randDelays[nRews])
                                nRews = nRews+1;
                                prevL = time.time()
                                
                               
                            else:
                                prevL = time.time()
                                
                    if(GPIO.event_detected(lickR)):
                        if GPIO.input(lickR):
                            if (time.time()-prevL)>minILI:
                                lickT = time.time()
                                lickList.append([lickT-start,'R'])
                                prevL = time.time()
                                
                            else:
                                prevL = time.time()
                else:
                    if StimIDs3[nRews]== 2:
                        sndArray2.play()
                        if nRews == len(stimList2):
                            stimList.append([time.time()-start,'Sound15KHz'])
                            stimList2.append([time.time()-start,'Sound15KHz'])
                            prevL = time.time()
                            _ = rew_action(0,rewProcR,rewProcL) # 1 left, 0 right
                            rewList.append([time.time()-start,'R'])

                        if(GPIO.event_detected(lickR)):
                            if GPIO.input(lickR):
                                print 'R'
                                if (time.time()-prevL)>minILI:
                                    lickT = time.time()
                                    lickList.append([lickT-start,'R'])
                                    _ = rew_action(0,rewProcR,rewProcL)
                                    rewList.append([time.time()-start,'R'])
                                    pygame.mixer.stop()
                                    time.sleep(randDelays[nRews])
                                    nRews = nRews+1;
                                    prevL = time.time()
                                    
                                else:
                                    prevL = time.time()
                                
                        if(GPIO.event_detected(lickL)):
                            if GPIO.input(lickL):
                                if (time.time()-prevL)>minILI:
                                    lickT = time.time()
                                    lickList.append([lickT-start,'L'])
                                    prevL = time.time()
                                else:
                                    prevL = time.time()

                    else:
                        if StimIDs3[nRews]== 3:
                            GPIO.output(LEDPINL,1)
                            if nRews == len(stimList2):
                                stimList.append([time.time()-start,'LEDL'])
                                stimList2.append([time.time()-start,'LEDL'])
                                prevL = time.time()

                                _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                                rewList.append([time.time()-start,'L'])

                              
                            if(GPIO.event_detected(lickL)):
                                if GPIO.input(lickL):
                                    print 'L'
                                    if (time.time()-prevL)>minILI:
                                        lickT = time.time()
                                        lickList.append([lickT-start,'L'])
                                        _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                                        rewList.append([time.time()-start,'L'])
                                        GPIO.output(LEDPINL,0)
                                        time.sleep(randDelays[nRews])
                                        nRews = nRews+1;
                                        prevL = time.time()
                                        
                                    else:
                                        prevL = time.time()
                                    
                            if(GPIO.event_detected(lickR)):
                                if GPIO.input(lickR):
                                    if (time.time()-prevL)>minILI:
                                        lickT = time.time()
                                        lickList.append([lickT-start,'R'])
                                        prevL = time.time()
                                    else:
                                        prevL = time.time()

                        else:
                            if StimIDs3[nRews]== 4:
                                GPIO.output(LEDPINR,1)
                                if nRews == len(stimList2):
                                    stimList.append([time.time()-start,'LEDR'])
                                    stimList2.append([time.time()-start,'LEDR'])
                                    prevL = time.time()
                                    
                                    _ = rew_action(0,rewProcR,rewProcL) # 1 left, 0 right
                                    rewList.append([time.time()-start,'R'])
                                    
                                if(GPIO.event_detected(lickR)):
                                    if GPIO.input(lickR):
                                        print 'R'
                                        if (time.time()-prevL)>minILI:
                                            lickT = time.time()
                                            lickList.append([lickT-start,'R'])
                                            _ = rew_action(0,rewProcR,rewProcL)
                                            rewList.append([time.time()-start,'R'])
                                            GPIO.output(LEDPINR,0)
                                            time.sleep(randDelays[nRews])
                                            nRews = nRews+1;
                                            prevL = time.time()
                                            
                                        else:
                                            prevL = time.time()
                                            
                                if(GPIO.event_detected(lickL)):
                                    if GPIO.input(lickL):
                                        if (time.time()-prevL)>minILI:
                                            lickT = time.time()
                                            lickList.append([lickT-start,'L'])
                                            prevL = time.time()
                                        else:
                                            prevL = time.time()

                if (nRews>(maxRews3-1)) or time.time() - start > ExpDur:
                    Training=False
                    print stimList2
                    print rewList
                    print lickList
                    print ['Total time = ' , time.time()-start]
                    print ['Total licks = ' , len(lickList)]
                    print ['Total trials = ' ,nRews]
                    lickList, rewList, stimList, sendT = data_sender(lickList,rewList,stimList,sendT)
