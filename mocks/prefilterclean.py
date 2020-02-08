#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import os
import sys
from unittest.mock import Mock

print('STAT:START')
time.sleep(1)
try:

	# from machinectl.hardware_ctrl import hw_dev_ctrl
	# from machinectl.clean_con_surfactant import  CLEAN_CONFILTER_SURFACTANT
	HW_CTRL = Mock()
	CFCWS = Mock()
	HW_CTRL.Connect_hw()
	#HW_CTRL.SyringePump_Off(1)	
	#HW_CTRL.Init_SPP()
	HW_CTRL.BPP_Init_Dev()
	print("System Initialized")
	
	time.sleep(0.1)
	CFCWS.Init()
	time.sleep(0.1)
	CFCWS.run_process()
	time.sleep(0.1)

except KeyboardInterrupt:
	time.sleep(1)
	#HW_CTRL.SyringePump_Off(1)
	HW_CTRL.SPP_Stop()
	time.sleep(0.1)
	HW_CTRL.BPP_stop()
	time.sleep(0.1)
	HW_CTRL.Disconnect_hw()
except :
	pass
print("System Halt")

time.sleep(0.1)

print('STAT:END')
