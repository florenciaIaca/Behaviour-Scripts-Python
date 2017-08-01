# 2AC Auditory task
# Trail starts with a sound that is presented until the correct port is licked and then there is a reward and the sound goes off
# Author: Maria Florencia Iacaruso
# contact: florencia.iacaruso@gmail.com

print 'Running Training stage 1 Sound'

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
##import request as req

max16bit = 32766

###-------------------------------------------
### Initialize function for sending data to server
##
### Figure out appropiate IP address based on server
##pi_IP = [(s.connect(('8.8.8.8',80)), s.getsocketname()[0],s.close()) for s in [socket.socket(socket.AF_INET,socket.SOCK_DGRAM)]][0][1]
##pi_ID = str(int(pi_IP[-3:])-100)
##
##def send_data(load):
##    
##    headers = {'User-Agent': 'Mozilla/5.0'}
##    link = 'http://192.168.0.99:8000/getData/' + pi_ID + '/get_PiData/'
##
##    session = req.Session()
##    r1 = session.get(link,headers=headers)
##
##    link1 = 'http://192.168.0.99:8000/getData/' + pi_ID + '/write_PiData/'
##
##
##    payload = {'piData':load,'csrfmiddlewaretoken':r1.cookies['csrftoken']}
##    #cookies = dict(session.cookies)
##    session.post(link1,headers=headers,data=payload)
##    return None
##

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

lickL = 37
lickR = 38


# set those pins as input
GPIO.setup(lickL,GPIO.IN)
GPIO.setup(lickR,GPIO.IN)

# add forced callbacks to those pins so that program response is instantaneous
GPIO.add_event_detect(lickL,GPIO.RISING)
GPIO.add_event_detect(lickR,GPIO.RISING)

### set pins to trigger solenoids
rewL = 40
rewR = 36
##
### set those pins as outputs
GPIO.setup(rewL,GPIO.OUT)
GPIO.setup(rewR,GPIO.OUT)

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
maxRews = 4 ; nRews = 0
intervalDur = 10

# Initialize lists for storage of reward and lick sides and times
lickList = []; rewList = []
minILI = 0.01

# Generate random delays to play sound (uniformely distributed)
minDelay=200
maxDelay=300

randDelays = rnd.randint(minDelay, maxDelay,maxRews)
randDelays=0.001*randDelays # unit is seconds
##plt.hist(randDelays)
##fig=plt.gcf
##plt.show()

# Generate array of random order for presentation of sounds
SoundIDs=np.zeros(maxRews)
SoundIDs[0 : (maxRews/2)]=1
SoundIDs[(maxRews/2) : maxRews]=2
rnd.shuffle(SoundIDs)
print SoundIDs

# Initialize relevant timers
timer = time.time()-10;  lickT=time.time();prevL = time.time(); sendT=time.time()

# Define start time
start = time.time()
print 'Starting loop'
print nRews
while Training:
    # control sector to send data to webserver
    # if 5 seconds have elapsed since the last data_sending
##    if (time.time()-sendT>5):
##
##        lickStr = 'LickList:'  + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in licklist])
##        rewStr = 'rewList:'  + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in rewList])
##        sendStr = ','.join(rewStr,lickStr)
##
##        sendProc = billiard.Process(target=send_data,args=(sendStr,))
##        sendProc.start()
##        print 'sending'
##        sendT = time.time()
##        lickList = []; rewList = [];

   
        
   # Check to make sure that only 1 lick is detected if the mouse makes contact.
        # Corrects for switch bounces from the relay in the lick

 
            # Play the sound, needs to change to present 1 of the 2 sounds

                if SoundIDs[nRews]== 1:
                    sndArray1.play()
##                    print 'Sound = 8KHz, (R)'
                    
# HERE ADD THE DETECTION OF LICKS IN THE 2 SPOUTS AND THE REWARD IF LICK IN THE CORRECT SPOUT
# Lick detection and is appropiate reward delivery


                  

                    if(GPIO.event_detected(lickL)):
                        print 'L'
                        if (time.time()-prevL)>minILI:
                            lickT = time.time()
                            lickList.append([lickT-start,'L'])
                            prevL = time.time()
                            _ = rew_action(1,rewProcR,rewProcL) # 1 left, 0 right
                            rewList.append([time.time()-start,'L'])
                            pygame.mixer.stop()
                            nRews = nRews+1;
                            time.sleep(5)
                            print nRews
                            
                        else:
                            prevL = time.time()
                            
                    if(GPIO.event_detected(lickR)):
##                        print 'R'
                        if (time.time()-prevL)>minILI:
                            lickT = time.time()
                            lickList.append([lickT-start,'R'])
                            prevL = time.time()
                        else:
                            prevL = time.time()

                         
                
                else:
                    sndArray2.play()
##                    print 'Sound = 15KHz, (L)'
# HERE ADD THE DETECTION OF LICKS IN THE 2 SPOUTS AND THE REWARD IF LICK IN THE CORRECT SPOUT
# Lick detection and is appropiate reward delivery


                    

                    if(GPIO.event_detected(lickR)):
                        print 'R'
                        if (time.time()-prevL)>minILI:
                            lickT = time.time()
                            lickList.append([lickT-start,'R'])
                            prevL = time.time()
                            _ = rew_action(0,rewProcR,rewProcL)
                            rewList.append([time.time()-start,'R'])
                            pygame.mixer.stop()
                            nRews = nRews+1;
                            time.sleep(5)
                            print nRews
                        else:
                            prevL = time.time()
                            
                    if(GPIO.event_detected(lickL)):
##                        print 'L'
                        if (time.time()-prevL)>minILI:
                            lickT = time.time()
                            lickList.append([lickT-start,'L'])
                            prevL = time.time()
                        else:
                            prevL = time.time()


                if (nRews>(maxRews-1)):
                    Training=False


#
