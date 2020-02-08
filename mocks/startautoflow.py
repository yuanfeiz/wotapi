#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import os
import random
import sys
from unittest.mock import Mock, MagicMock

CLEAN_PREFILTER_SURFACTANT = Mock()
CLEAN_CONFILTER_SURFACTANT = Mock()
PUSHOUT = Mock()
SAMPLING_10_breaking = Mock()



HW_CTRL = Mock()
HW_CTRL.Mem_Read_Byte.return_value = 65
PFCWS = CLEAN_PREFILTER_SURFACTANT()
CFCWS = CLEAN_CONFILTER_SURFACTANT()
#SAMPLE = SAMPLING()
SAMPLE_10_DIVISION = SAMPLING_10_breaking()
PUSH = PUSHOUT()
#START_CAP = Start_cap()

HW_CTRL.Connect_hw()
HW_CTRL.SyringePump_Off(1)
#HW_CTRL.Mem_Write_Byte(2,66)
time.sleep(1)
xx= HW_CTRL.Mem_Read_Byte(2) 	
print("Data Read from EEPROM",chr(xx))	
#print(chr(xx))	
HW_CTRL.Init_SPP()
HW_CTRL.BPP_Init_Dev()

print("System Initialized")


#script/startautoflow.py FPZT=50.0,110.0,150,110 LASER=46.8 SPV=100.0,2.0 FPZT=50.0,110.0,150,110

print('STAT:START')
#run code to control the bump, laser, syringe pump, signal generator and etc.
time.sleep(1)

#for i in range(100):
#    time.sleep(1)
#    print('STAT:CT', i, flush=True)
#
#for i in range(100):
#    time.sleep(1)
#    print('STAT:PD', i, flush=True)
#
#for i in range(100):
#    time.sleep(1)	
#    print('STAT:IC', i, flush=True)
#

loop = "TRUE"
ctstate = 0
pstate = -1
i_ct=i_pd=i_ic=0




while(loop == "TRUE"):
	time.sleep(1)
	i_ct += random.random()
	i_pd += random.random()
	i_ic += random.random()
	print('STAT:CT', i_ct, flush=True)	
	print('STAT:PD', i_pd, flush=True)
	print('STAT:IC', i_ic, flush=True)

	
	if(pstate != ctstate):	
				
		if (ctstate == 1):			
			time.sleep(2)

		elif (ctstate == 2):		
			time.sleep(3)

		elif (ctstate == 3):			
			time.sleep(2)

		elif (ctstate == 4):		
			time.sleep(2)

		elif (ctstate == 5):		
			time.sleep(1)

		elif (ctstate == 6):			
			time.sleep(2)

		elif (ctstate == 7):			
			time.sleep(1)

		elif (ctstate == 8):			
			time.sleep(2)

		elif (ctstate == 9):			
			time.sleep(1)

		elif (ctstate == 10):			
			time.sleep(1)

		elif (ctstate == 11):			
			time.sleep(1)	

		elif (ctstate == 12):			
			time.sleep(1)

		else: 
			time.sleep(0.1)
		
		
		# Previous state
		pstate = ctstate

		# Do process for current state
		if(ctstate == 0):
			i_ct = 5
			ctstate = 1
		elif (ctstate == 1):
			time.sleep(0.1)
			print('prefilter cleaning')
			
			PFCWS.Init()
			time.sleep(0.1)
			PFCWS.run_process()
			
			
			#os.system('python script/prefilterclean.py')
			i_ct = 25
			ctstate = 2
		elif (ctstate == 2):
			time.sleep(0.1)	

			print('confilter cleaning')
			CFCWS.Init()
			time.sleep(0.1)
			CFCWS.run_process()
		
			#os.system('python script/confilterclean.py')
			i_ct = 50
			ctstate = 3
		elif (ctstate == 3):
			time.sleep(0.1)
			print('concentration')
			time.sleep(0.1)
			SAMPLE_10_DIVISION.Init()
			time.sleep(0.1)
			SAMPLE_10_DIVISION.run_process()
			
			#os.system('python script/concentration.py')
			i_ct = 100
			ctstate = 4

		#elif (ctstate == 4):	
			#time.sleep(3)		
			#os.system('python script/pushout.py')

			#ctstate = 5
		#elif (ctstate == 4):			
			#i_ct = 100
			#ctstate = 6
		elif (ctstate == 4):		
			i_pd = 5
			ctstate = 5
		elif (ctstate == 5):			
			i_pd = 20
			ctstate = 6
		elif (ctstate == 6):			
			i_pd = 40
			ctstate = 7
		elif (ctstate == 7):			
			i_pd = 60
			ctstate = 8
		elif (ctstate == 8):			
			i_pd = 80
			ctstate = 9
		elif (ctstate == 9):			
			i_pd = 95
			ctstate = 10
		elif (ctstate == 10):			
			i_pd = 100
			ctstate = 11
		else:
			loop = "FALSE"
		
		'''
  
		print("Testing program")
	
	
		# Previous state
		pstate = ctstate

		# Do process for current state
		if(ctstate == 0):
			i_ct = 5
			ctstate = 1
		elif (ctstate == 1):
			time.sleep(0.1)
			print('prefilter cleaning')
			
			#PFCWS.Init()
			time.sleep(5)
			#PFCWS.run_process()
			
			
			#os.system('python script/prefilterclean.py')
			i_ct = 25
			ctstate = 2
		elif (ctstate == 2):
			time.sleep(0.1)	

			print('confilter cleaning')
			#CFCWS.Init()
			time.sleep(5)
			#CFCWS.run_process()
		
			#os.system('python script/confilterclean.py')
			i_ct = 50
			ctstate = 3
		elif (ctstate == 3):
			time.sleep(0.1)
			print('concentration')
			time.sleep(0.1)
			#SAMPLE_10_DIVISION.Init()
			time.sleep(0.1)
			#SAMPLE_10_DIVISION.run_process()
			
			#os.system('python script/concentration.py')
			i_ct = 100
			ctstate = 4

		#elif (ctstate == 4):	
			#time.sleep(3)		
			#os.system('python script/pushout.py')

			#ctstate = 5
		#elif (ctstate == 4):			
			#i_ct = 100
			#ctstate = 6
		elif (ctstate == 4):		
			i_pd = 5
			ctstate = 5
		elif (ctstate == 5):			
			i_pd = 20
			ctstate = 6
		elif (ctstate == 6):			
			i_pd = 40
			ctstate = 7
		elif (ctstate == 7):			
			i_pd = 60
			ctstate = 8
		elif (ctstate == 8):			
			i_pd = 80
			ctstate = 9
		elif (ctstate == 9):			
			i_pd = 95
			ctstate = 10
		elif (ctstate == 10):			
			i_pd = 100
			ctstate = 11
		else:
			loop = "FALSE"
		


		'''


print('STAT:END')
