#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import os
import sys
from unittest.mock import Mock

print(sys.path)

print('startcap start',flush=True)

print('STAT:START',flush=True)
print(sys.argv,flush=True)

print('STAT:PC:0',flush=True)
#sys.path.append('/home/wot/Desktop/project/parad3/script/test/')
hw_dev_ctrl = Mock()


ON = 1
OFF = 0
TRUE = 1
FALSE = 0

#Defining Name for valves
PCS_V1 = 0
PCS_V2 = 1
PCS_V3 = 2
PCS_V4 = 3
PCS_V5 = "IO14"
PCS_V6 = 5
PCS_V7 = 6
PCS_V8 = 7
PCS_V9 = 8
PCS_V10 = 9
PCS_V11 = 10
PCS_V12 = 12
PCS_V13 = 13
PCS_V14 = 14

FORWARD = 0
REVERSE = 1

SIG_CH1 = 0
SIG_CH2 = 1
SIG_CH3 = 2
SIG_CH4 = 3

INFUSE = 0
WITHDRAW = 1

	
HW_CTRL = hw_dev_ctrl()

HW_CTRL.Connect_hw()

HW_CTRL.SyringePump_Off(1)


#HW_CTRL.Mem_Write_Byte(2,66)
time.sleep(1)
xx= 46
print(chr(xx))
#HW_CTRL.Init_SPP()
#HW_CTRL.BPP_Init_Dev()
HW_CTRL.Sig_Gen_Off(SIG_CH4)

print("System Initialized")

print ("Valve V12 Off")
HW_CTRL.Valve_ctrl("PCS_V12", OFF)
time.sleep(0.5)

print ("Valve V13 Off")
HW_CTRL.Valve_ctrl("PCS_V13", OFF)
time.sleep(0.5)

print ("Valve V14 Off")
HW_CTRL.Valve_ctrl("PCS_V14", OFF)
time.sleep(0.5)


#print("Sig Gen Ch-4 freq: 1857000, Amp : 250 ",flush=True)
#HW_CTRL.Sig_Gen(SIG_CH4, 1857000, 250)
#print("laser on")
#HW_CTRL.SetLD_Current(47.3)

try:

	lag1 = len(sys.argv)
	print(lag1)
	tok1 = 'CPZT='
	print(len(tok1))
	arg1 = sys.argv[1]
	print("arg1=")
	print(arg1)
	pos1 = arg1.find(tok1)
	print((pos1))
	if pos1 == -1:
		exit(0)
	val1 = arg1[pos1+len(tok1):]
	print(val1)
	vals1 = val1.split(",")
	print(vals1)
	power = float(vals1[0])*10
	print('power=' , power)
	freq = float(vals1[1])*1000000
	print('freq =' ,freq)



	HW_CTRL.Sig_Gen(SIG_CH4,freq,int(power))
	print("Signal Generator working",flush=True)
		#ostr1 = 'Signal set to' + freq +  'MHz' + power + 'V'
	#print(sig_val)



	#lag2 = len(sys.argv)
		# tok2 = 'LASER='
	#print(len(tok2))
		# arg2 = sys.argv[2]
	#print(arg2)
	#pos2 = arg2.find(tok2)
	#print('pos2=')
	#print(pos2)
		# if pos2 == -1:
	#    exit(0)
		# val2 = arg2[pos2+len(tok2):]
		# power2 = float(val2)
		# ostr2 = 'Set laser to ' + val2 + 'mA'
		# print(ostr2)
	#from machinectl import laser_ctrl
	#lc = laser_ctrl.laser_ctrl()
	#if(power2 <0) or (power2 >100):
	#    print("Laser: set a error value!")
	#    exit(0)
		#` lc.SetLD_Current(power2)


	lag1 = len(sys.argv)
	print(lag1)
	tok3 = 'SPV='
	print(len(tok3))
	arg3 = sys.argv[3]
	print("arg3 =")
	print(arg3)
	pos3 = arg3.find(tok3)
	print(pos3)
	if pos3 == -1:
		exit(0)
	val3 = arg3[pos3+len(tok3):]
	print(val3)
	vals3 = val3.split(",")
	print(vals3)
	speed = float(vals3[0])
	print('speed=' , speed)
	vol = float(vals3[1])
	print('vol =',vol)
	t = vol*60000/speed
	print(t)


	HW_CTRL.SyringePump_Ctrl(1,WITHDRAW,speed,vol)
	print(" Syringe Pump working", flush=True)

	#HW_CTRL.SyringePump_Ctrl(2,WITHDRAW,100,10)
	#HW_CTRL.SyringePump_Ctrl(2,WITHDRAW,5000,10)
		#HW_CTRL.SyringePump_Ctrl(2,WITHDRAW,1000,5)

except Exception as e:
	print(e)
print("exit")
#except KeyboardInterrupt:
	#time.sleep(1)
	#HW_CTRL.SyringePump_Off(2)
	#HW_CTRL.SPP_Stop()
	#time.sleep(0.1)
	#HW_CTRL.BPP_stop()
	#time.sleep(0.1)
	#HW_CTRL.Sig_Gen_Off(SIG_CH1)
	#HW_CTRL.Sig_Gen_Off(SIG_CH2)
	#HW_CTRL.Sig_Gen_Off(SIG_CH3)
	#HW_CTRL.Sig_Gen_Off(SIG_CH4)
	#HW_CTRL.Disconnect_hw()

	#print("System Halt")
print('', flush=True)

t = int(t)
for i in range(t):
	pt = int((i/t)*100)
	print('STAT:PC:' + str(pt),flush=True)
	time.sleep(1)
print('STAT:PC:100',flush=True)

print('STAT:END',flush=True)

#exit(0)
