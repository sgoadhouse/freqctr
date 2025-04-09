#!/usr/bin/env python
#
#
#!/usr/bin/python

#-------------------------------------------------------------------------------
#  Get a data from Agilent/KeySight 53230A Universal Frequency Counter and output to screen
#
# Originally from Tektronix: http://www.tek.com/support/faqs/programing-how-do-i-get-screen-capture-dpo4000-scope-using-python
#
# python 2.7 (http://www.python.org/)
# pyvisa 1.4 (http://pyvisa.sourceforge.net/)
# pyvisa-py 0.2 (https://pyvisa-py.readthedocs.io/en/latest/)
#
# NOTE: pyvisa-py replaces the need to install NI VISA libraries
# (which are crappily written and buggy!) Wohoo!
#-------------------------------------------------------------------------------

# For future Python3 compatibility:
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import random
import time
import math
import sys

import argparse
parser = argparse.ArgumentParser(description='Perform Time Interval measurement on Agilent/KeySight 53230A Freq. Counter. b/w ch. 1 and ch. 2')
parser.add_argument('ofile', nargs='?', help='Output file name for hardcopy')
parser.add_argument('-a', action='store_true', help='Gather Frequency stats including Allan Deviation')
parser.add_argument('-g', action='store_true', help='Create histogram of Frequency instead of TI stats')
parser.add_argument('-f', action='store_true', help='Monitor Frequency and voltage instead of TI stats')
parser.add_argument('-j', action='store_true', help='Create histogram of time interval with source (ch. 2)')
parser.add_argument('-o', action='store_true', help='Take time interval stats of ch. 1 vs. itself')
parser.add_argument('-d', action='store_true', help='Compute Positive Duty Cycle of ch. 1')
parser.add_argument('-q', action='store_true', help='Query VISA resources')
args = parser.parse_args()

if (args.g or args.f or args.j) and not args.ofile:
    print('ERROR: If use -g or -f or -j, must supply ofile')
    sys.exit()
    
# If given a hardcopy filename, process it
if args.ofile:    
    fn_ext = ".png"
    pn = os.environ['HOME'] + "/Downloads"
    fn = pn + "/" + args.ofile

    while os.path.isfile(fn + fn_ext):
        fn += "-" + random.choice("abcdefghjkmnpqrstuvwxyz")

    fn += fn_ext

import pyvisa as visa

rm = visa.ResourceManager('@py')

if args.q:
    print(rm.list_resources())
    sys.exit()

    
## IEEE Block handlers copied from python IVI: https://github.com/python-ivi/python-ivi/blob/master/ivi/ivi.py

def build_ieee_block(data):
    "Build IEEE block"
    # IEEE block binary data is prefixed with #lnnnnnnnn
    # where l is length of n and n is the
    # length of the data
    # ex: #800002000 prefixes 2000 data bytes
    return str('#8%08d' % len(data)).encode('utf-8') + data

    
def decode_ieee_block(data):
    "Decode IEEE block"
    # IEEE block binary data is prefixed with #lnnnnnnnn
    # where l is length of n and n is the
    # length of the data
    # ex: #800002000 prefixes 2000 data bytes
    if len(data) == 0:
        return b''
    
    ind = 0
    c = '#'.encode('utf-8')
    while data[ind:ind+1] != c:
        ind += 1
    
    ind += 1
    l = int(data[ind:ind+1])
    ind += 1
    
    if (l > 0):
        num = int(data[ind:ind+l].decode('utf-8'))
        ind += l
        
        return data[ind:ind+num]
    else:
        return data[ind:]

# From: http://stackoverflow.com/questions/17973278/python-decimal-engineering-notation-for-mili-10e-3-and-micro-10e-6
def eng_string( x, format='%s', si=False):
    '''
    Returns float/int value <x> formatted in a simplified engineering format -
    using an exponent that is a multiple of 3.

    format: printf-style string used to format the value before the exponent.

    si: if true, use SI suffix for exponent, e.g. k instead of e3, n instead of
    e-9 etc.

    E.g. with format='%.2f':
        1.23e-08 => 12.30e-9
             123 => 123.00
          1230.0 => 1.23e3
      -1230000.0 => -1.23e6

    and with si=True:
          1230.0 => 1.23k
      -1230000.0 => -1.23M
    '''
    sign = False
    if x < 0:
        x = -x
        sign = True
    exp = int( math.floor( math.log10( x)))
    exp3 = exp - ( exp % 3)
    x3 = x / ( 10 ** exp3)

    if si and exp3 >= -24 and exp3 <= 24 and exp3 != 0:
        exp3_text = 'yzafpnum kMGTPEZY'[ ( exp3 - (-24)) / 3]
    elif exp3 == 0:
        exp3_text = ''
    else:
        exp3_text = 'e%s' % exp3

    if (sign):
        x3 = -1 * x3
        
    return ( format+'%s') % ( x3, exp3_text)


#@@@#freqctr = rm.open_resource('TCPIP0::128.143.100.207::INSTR')
#@@@#freqctr = rm.open_resource('TCPIP0::a-53230a-sdg1.phys.virginia.edu::INSTR')
#@@@#freqctr = rm.open_resource('TCPIP0::A-53230A-SDG1::inst0::INSTR')
freqctr = rm.open_resource('TCPIP0::192.168.153.128::INSTR')
freqctr.timeout = 30000 # set the timeout to 30 seconds

#@@@#freqctr = rm.open_resource("TCPIP0::mx3034a-sdg::inst0::INSTR")

#print freqctr.query('*IDN?')
#print freqctr.query('SENS:FREQ:MODE?')
#print freqctr.query('TINT:GATE:SOUR?')

#The following example captures and returns the front-panel display image in BMP format:
#HCOP:SDUM:DATA:FORM BMP
#HCOP:SDUM:DATA?
#TypicalResponse: Adefinitelengthbinaryblockcontainingtheimage


if args.g:
    # If requesting a histogram, do that
    freqctr.timeout = 120000             # set the timeout to 120 seconds (histograms can take a while)
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    #freqctr.write('CONF:FREQ %e,.001' % (args.freq[0]))      # configure for frequency
    freqctr.write('CONF:FREQ')           # configure for frequency

    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    #freqctr.write('INPUT1:LEV:AUTO ON') # disable auto level for start/stop thresholds       
    #freqctr.write('INPUT1:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    #freqctr.write('INPUT1:LEV1 2.00')    # start threshold at 2.00V
    #freqctr.write('INPUT1:LEV2 2.00')    # stop threshold at 2.00V
    #freqctr.write('INPUT1:SLOP1 POS')    # start on positive (rising) edge                    
    #freqctr.write('INPUT1:SLOP2 NEG')    # stop on negative (falling) edge                    

    ## Sample frequency for a time period to determine how to set up the bins for
    #freqctr.write('SAMP:COUN 500E3')     # set a sample (reading) count
    #freqctr.write('CALC:AVER:STAT ON')   # enable statistics collections
    #freqctr.write('CALC:STAT ON')
    #freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    #freqctr.write('DISP OFF')            # turn off the display to make the process faster
    #freqctr.write('DISP:TEXT "MEASURING..."')
    #freqctr.write('INIT')
    #freqctr.write('*TRG')                # trigger data collection
    #freqctr.write('*WAI')                # wait for all reading to complete

    cnts = 1000
    freqctr.write('SAMP:COUN %d' % (cnts))       # set a sample (reading) count
    
    # Setup the histogram    
    freqctr.write('CALC2:TRAN:HIST:RANG:AUTO ON')
    freqctr.write('CALC2:TRAN:HIST:RANG:AUTO:COUN %d' % (cnts)) # number of samples to use for computing bins (ie. all of them)
    freqctr.write('CALC2:TRAN:HIST:POIN 40')                    # number of bins
    freqctr.write('CALC2:TRAN:HIST:STAT ON')                    # enable histogram
    freqctr.write('DISP:MODE HIST')                             # display histogram
    
    freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    #freqctr.write('DISP OFF')            # turn off the display to make the process faster
    #freqctr.write('DISP:TEXT "Histogramming..."')
    freqctr.write('INIT')
    freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete    
    freqctr.query('*OPC?')               # wait for histogram to be done

    #freqctr.write('DISP:TEXT:CLE')       # clear the text message
    #freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it
    
elif args.j:
    # If requesting a time interval histogram, do that
    freqctr.timeout = 120000             # set the timeout to 120 seconds (histograms can take a while)
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    freqctr.write('CONF:TINT (@2),(@1)') # configure two-channel time interval measurements from 2 to 1
    freqctr.write('TINT:GATE:SOUR IMM')  # immediate gate source

    # set up input 1
    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    freqctr.write('INPUT1:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    freqctr.write('INPUT1:LEV1 2.00')    # start threshold at 2.00V
    freqctr.write('INPUT1:SLOP1 POS')    # start on positive (rising) edge                    

    # set up input 2
    freqctr.write('INPUT2:RANG 5')       # set Input2 to the 50V range
    freqctr.write('INPUT2:PROB 1')       # set Input2 for 1:1 probe
    freqctr.write('INPUT2:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT2:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    freqctr.write('INPUT2:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    freqctr.write('INPUT2:LEV1 1.15')    # start threshold at 1.15V
    freqctr.write('INPUT2:SLOP1 POS')    # start on positive (rising) edge                    

    cnts = 250000
    trigs = 10000
    freqctr.write('SAMP:COUN %d' % (cnts/trigs))   # set a sample (reading) count
    freqctr.write('TRIG:COUN %d' % (trigs))        # set the number of triggers
    
    # Setup the histogram    
    freqctr.write('CALC2:TRAN:HIST:RANG:AUTO ON')
    #freqctr.write('CALC2:TRAN:HIST:RANG:AUTO:COUN %d' % (cnts/4)) # number of samples to use for computing bins
    freqctr.write('CALC2:TRAN:HIST:RANG:AUTO:COUN MAX')
    freqctr.write('CALC2:TRAN:HIST:POIN 100')                   # number of bins
    freqctr.write('CALC2:TRAN:HIST:STAT ON')                    # enable histogram
    freqctr.write('DISP:MODE HIST')                             # display histogram
    
    freqctr.write('TRIG:SOUR IMM')       # immediate trigger
    #freqctr.write('DISP OFF')            # turn off the display to make the process faster
    #freqctr.write('DISP:TEXT "Histogramming..."')
    freqctr.write('INIT')
    #freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete    
    freqctr.query('*OPC?')               # wait for histogram to be done

    #freqctr.write('DISP:TEXT:CLE')       # clear the text message
    #freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it
    
elif args.f:
    # Else, if want to look at frequency and voltage, do that
    #
    #freqctr.timeout = 120000             # set the timeout to 120 seconds (histograms can take a while)
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    #freqctr.write('CONF:FREQ %e,.001' % (args.freq[0]))      # configure for frequency
    freqctr.write('CONF:FREQ')           # configure for frequency

    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    #freqctr.write('INPUT1:LEV:AUTO ON') # disable auto level for start/stop thresholds       
    #freqctr.write('INPUT1:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    #freqctr.write('INPUT1:LEV1 2.00')    # start threshold at 2.00V
    #freqctr.write('INPUT1:LEV2 2.00')    # stop threshold at 2.00V
    #freqctr.write('INPUT1:SLOP1 POS')    # start on positive (rising) edge                    
    #freqctr.write('INPUT1:SLOP2 NEG')    # stop on negative (falling) edge                    

    ## Sample frequency for a time period to determine how to set up the bins for
    #freqctr.write('SAMP:COUN 500E3')     # set a sample (reading) count
    #freqctr.write('CALC:AVER:STAT ON')   # enable statistics collections
    #freqctr.write('CALC:STAT ON')
    #freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    #freqctr.write('DISP OFF')            # turn off the display to make the process faster
    #freqctr.write('DISP:TEXT "MEASURING..."')
    #freqctr.write('INIT')
    #freqctr.write('*TRG')                # trigger data collection
    #freqctr.write('*WAI')                # wait for all reading to complete

    freqctr.write('AUT')                  # Autoscale input after setting up input
    
    cnts = 1
    freqctr.write('SAMP:COUN %d' % (cnts))       # set a sample (reading) count
    
    #freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    #freqctr.write('DISP OFF')            # turn off the display to make the process faster
    #freqctr.write('DISP:TEXT "Histogramming..."')
    freqctr.write('INIT')
    #freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete    
    freqctr.query('*OPC?')               # wait for histogram to be done

    #freqctr.write('DISP:TEXT:CLE')       # clear the text message
    #freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it
    
elif args.d:
    ## Else, handle duty cycle statistics but of just ch. 1
    #
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    freqctr.write('CONF:PDUT (@1)')      # configure single-channel time interval measurements
    freqctr.write('TINT:GATE:SOUR IMM')  # immediate gate source

    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    freqctr.write('INPUT1:LEV:AUTO ON')  # enable auto level for start/stop thresholds       
    freqctr.write('INPUT1:LEV1:REL 50')  # use 50% threshold levels

    freqctr.write('SAMP:COUN 250E3')     # set a sample (reading) count
    freqctr.write('CALC:AVER:STAT ON')   # enable statistics collections
    freqctr.write('CALC:STAT ON')
    freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    freqctr.write('DISP OFF')            # turn off the display to make the process faster
    freqctr.write('DISP:TEXT "MEASURING Duty Cycle..."')
    freqctr.write('INIT')
    freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete

    #print freqctr.query('*OPC?')         # check if operation is pending
    #print freqctr.query('CALC:AVER:COUN:CURR?') # return number of counts used in statistics

    # This query returns the mathematical mean (average), standard deviation, minimum value, and maximum value
    # of all measurements taken since the last time statistics were cleared. They get cleared with 'CONF:' command.
    #print freqctr.query('CALC:AVER:ALL?') # return statistics
    #print freqctr.query('CALC:AVER:PTP?') # return peak-to-peak value
    stats = freqctr.query_ascii_values('CALC:AVER:ALL?') # return statistics
    ptp = freqctr.query_ascii_values('CALC:AVER:PTP?')   # return peak-to-peak value

    counts = freqctr.query_ascii_values('CALC:AVER:COUN:CURR?') # return number of counts used in statistics
    print ('Ch. 1 Duty Cycle Stats over %d counts:' % counts[0])
    #print 'Average +Duty:  '+ eng_string(stats[0], format='%2.5f', si=True) + 's'
    #print 'StdDev +Duty:   '+ eng_string(stats[1], format='%2.5f', si=True) + 's'
    #print 'Max +Duty:      '+ eng_string(stats[3], format='%2.5f', si=True) + 's'
    #print 'Min +Duty:      '+ eng_string(stats[2], format='%2.5f', si=True) + 's'
    #print 'Pk-to-Pk +Duty: '+ eng_string(ptp[0], format='%2.5f', si=True) + 'Hz'
    print ('Average +Duty:  %6.3f' % (stats[0]*100) + '%')
    print ('StdDev +Duty:   %6.3f' % (stats[1]*100) + '%')
    print ('Max +Duty:      %6.3f' % (stats[3]*100) + '%')
    print ('Min +Duty:      %6.3f' % (stats[2]*100) + '%')
    print ('Pk-to-Pk +Duty: %6.3f' % (ptp[0]*100) + 'Hz')
    #print stats
    #print ptp

    freqctr.write('DISP:TEXT:CLE')       # clear the text message
    freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it

elif args.a:
    ## Else, handle frequency statistics of ch. 1 with allan deviation
    #
    freqctr.timeout = 60000              # set the timeout to 60 seconds (freq. stats can take a while)
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    freqctr.write('CONF:FREQ (@1)')      # configure single-channel time interval measurements
    freqctr.write('SENS:FREQ:MODE CONT') # continuous frequency mode for Allan Deviation 

    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    freqctr.write('INPUT1:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    freqctr.write('INPUT1:LEV1 2.00')    # start threshold at 2.00V
    #freqctr.write('INPUT1:LEV2 2.00')    # stop threshold at 2.00V
    freqctr.write('INPUT1:SLOP1 POS')    # start on positive (rising) edge                    
    #freqctr.write('INPUT1:SLOP2 NEG')    # stop on negative (falling) edge                    

    freqctr.write('SAMP:COUN 250')     # set a sample (reading) count
    freqctr.write('CALC:AVER:STAT ON')   # enable statistics collections
    freqctr.write('CALC:STAT ON')
    freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    #freqctr.write('DISP OFF')            # turn off the display to make the process faster
    #freqctr.write('DISP:TEXT "MEASURING Frequency..."')
    freqctr.write('INIT')
    freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete
    freqctr.query('*OPC?')               # check if operation is pending

    #print freqctr.query('*OPC?')         # check if operation is pending
    #print freqctr.query('CALC:AVER:COUN:CURR?') # return number of counts used in statistics

    # This query returns the mathematical mean (average), standard deviation, minimum value, and maximum value
    # of all measurements taken since the last time statistics were cleared. They get cleared with 'CONF:' command.
    #print freqctr.query('CALC:AVER:ALL?') # return statistics
    #print freqctr.query('CALC:AVER:PTP?') # return peak-to-peak value
    stats = freqctr.query_ascii_values('CALC:AVER:ALL?') # return statistics
    alldev = freqctr.query_ascii_values('CALC:AVER:ADEV?')   # return Allan Deviation value

    counts = freqctr.query_ascii_values('CALC:AVER:COUN:CURR?') # return number of counts used in statistics
    print ('Freq. 1->1 statistics over %d counts:' % counts[0])
    print ('Average Freq: '+ eng_string(stats[0], format='%10.6f', si=True) + 'Hz')
    print ('StdDev Freq:  '+ eng_string(stats[1], format='%10.6f', si=True) + 'Hz')
    print ('Max Freq:     '+ eng_string(stats[3], format='%10.6f', si=True) + 'Hz')
    print ('Min Freq:     '+ eng_string(stats[2], format='%10.6f', si=True) + 'Hz')
    print ('Allan Dev:    '+ eng_string(alldev[0], format='%10.6f', si=True) + '')
    #print stats
    #print ptp

    freqctr.write('DISP:TEXT:CLE')       # clear the text message
    freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it


elif args.o:
    ## Else, handle time interval statistics but of just ch. 1
    ## If want to make sure the configuration is set correctly, but it will change what is already set up
    #
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    freqctr.write('CONF:TINT (@1)')      # configure single-channel time interval measurements
    freqctr.write('TINT:GATE:SOUR IMM')  # immediate gate source

    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    freqctr.write('INPUT1:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    freqctr.write('INPUT1:LEV1 2.00')    # start threshold at 2.00V
    freqctr.write('INPUT1:LEV2 2.00')    # stop threshold at 2.00V
    freqctr.write('INPUT1:SLOP1 POS')    # start on positive (rising) edge                    
    freqctr.write('INPUT1:SLOP2 NEG')    # stop on negative (falling) edge                    

    freqctr.write('SAMP:COUN 500E3')     # set a sample (reading) count
    freqctr.write('CALC:AVER:STAT ON')   # enable statistics collections
    freqctr.write('CALC:STAT ON')
    freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    freqctr.write('DISP OFF')            # turn off the display to make the process faster
    freqctr.write('DISP:TEXT "MEASURING..."')
    freqctr.write('INIT')
    freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete

    #print freqctr.query('*OPC?')         # check if operation is pending
    #print freqctr.query('CALC:AVER:COUN:CURR?') # return number of counts used in statistics

    # This query returns the mathematical mean (average), standard deviation, minimum value, and maximum value
    # of all measurements taken since the last time statistics were cleared. They get cleared with 'CONF:' command.
    #print freqctr.query('CALC:AVER:ALL?') # return statistics
    #print freqctr.query('CALC:AVER:PTP?') # return peak-to-peak value
    stats = freqctr.query_ascii_values('CALC:AVER:ALL?') # return statistics
    ptp = freqctr.query_ascii_values('CALC:AVER:PTP?')   # return peak-to-peak value

    counts = freqctr.query_ascii_values('CALC:AVER:COUN:CURR?') # return number of counts used in statistics
    print ('TI 1->1 statistics over %d counts:' % counts[0])
    print ('Average TI: '+ eng_string(stats[0], format='%2.5f', si=True) + 's')
    print ('StdDev TI:  '+ eng_string(stats[1], format='%2.5f', si=True) + 's')
    print ('Max TI:     '+ eng_string(stats[3], format='%2.5f', si=True) + 's')
    print ('Min TI:     '+ eng_string(stats[2], format='%2.5f', si=True) + 's')
    print ('Pk-to-Pk:   '+ eng_string(ptp[0], format='%2.5f', si=True) + 'Hz')
    #print stats
    #print ptp

    freqctr.write('DISP:TEXT:CLE')       # clear the text message
    freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it

else:
    ## Else, handle time interval statistics between ch. 2 (GLIBv2 CLKOUT) and ch. 1 (MCLK: LVPECL+ to GND)
    ## If want to make sure the configuration is set correctly, but it will change what is already set up
    #
    freqctr.write('*RST')                # start from a known instrument state                
    freqctr.write('DISP:MODE NUM')       # Make sure display mode is Numeric (not impacted by *RST)
    freqctr.write('DISP:DIG:MASK 10')    # disable auto-digit mode; set display to 10 digits   

    freqctr.write('CONF:TINT (@2),(@1)') # configure two-channel time interval measurements from 2 to 1
    freqctr.write('TINT:GATE:SOUR IMM')  # immediate gate source

    # set up input 1 (MCLK from backplane with oscope probe, LVPECL+ to GND)
    freqctr.write('INPUT1:RANG 50')      # set Input1 to the 50V range
    freqctr.write('INPUT1:PROB 10')      # set Input1 for 10:1 probe
    freqctr.write('INPUT1:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT1:IMP 1.0E6')    # set 1.0E6 ohms impedance                              
    freqctr.write('INPUT1:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    freqctr.write('INPUT1:LEV1 1.90')    # start threshold at 1.90V
    freqctr.write('INPUT1:SLOP1 POS')    # start on positive (rising) edge                    

    # set up input 2
    freqctr.write('INPUT2:RANG 5')       # set Input2 to the 50V range
    freqctr.write('INPUT2:PROB 1')       # set Input2 for 1:1 probe
    freqctr.write('INPUT2:COUP DC')      # set DC coupling                                    
    freqctr.write('INPUT2:IMP 50')       # set 50 ohms impedance                              
    freqctr.write('INPUT2:LEV:AUTO OFF') # disable auto level for start/stop thresholds       
    freqctr.write('INPUT2:LEV1 0.60')    # start threshold at 0.60V
    freqctr.write('INPUT2:SLOP1 POS')    # start on positive (rising) edge                    

    freqctr.write('SAMP:COUN 500E3')     # set a sample (reading) count
    freqctr.write('CALC:AVER:STAT ON')   # enable statistics collections
    freqctr.write('CALC:STAT ON')
    freqctr.write('TRIG:SOUR BUS')       # wait until *TRG command is sent to trigger, so can control trigger and hardcopy grab
    freqctr.write('DISP OFF')            # turn off the display to make the process faster
    freqctr.write('DISP:TEXT "MEASURING..."')
    freqctr.write('INIT')
    freqctr.write('*TRG')                # trigger data collection
    freqctr.write('*WAI')                # wait for all reading to complete

    #print freqctr.query('*OPC?')         # check if operation is pending
    #print freqctr.query('CALC:AVER:COUN:CURR?') # return number of counts used in statistics

    # This query returns the mathematical mean (average), standard deviation, minimum value, and maximum value
    # of all measurements taken since the last time statistics were cleared. They get cleared with 'CONF:' command.
    #print freqctr.query('CALC:AVER:ALL?') # return statistics
    #print freqctr.query('CALC:AVER:PTP?') # return peak-to-peak value
    stats = freqctr.query_ascii_values('CALC:AVER:ALL?') # return statistics
    ptp = freqctr.query_ascii_values('CALC:AVER:PTP?')   # return peak-to-peak value

    counts = freqctr.query_ascii_values('CALC:AVER:COUN:CURR?') # return number of counts used in statistics
    print ('TI 2->1 statistics over %d counts:' % counts[0])
    print ('Average TI: '+ eng_string(stats[0], format='%2.5f', si=True) + 's')
    print ('StdDev TI:  '+ eng_string(stats[1], format='%2.5f', si=True) + 's')
    print ('Max TI:     '+ eng_string(stats[3], format='%2.5f', si=True) + 's')
    print ('Min TI:     '+ eng_string(stats[2], format='%2.5f', si=True) + 's')
    print ('Pk-to-Pk:   '+ eng_string(ptp[0], format='%2.5f', si=True) + 'Hz')
    #print stats
    #print ptp

    freqctr.write('DISP:TEXT:CLE')       # clear the text message
    freqctr.write('DISP ON')             # turn on the display so can grab a hardcopy of it

if args.ofile:    
    time.sleep(2)                        # wait a seconds for display to update before grabbing a hardcopy

    #print freqctr.query('HCOP:SDUM:DATA:FORM?')
    freqctr.write('HCOP:SDUM:DATA:FORM PNG')
    #values = freqctr.query_binary_values('HCOP:SDUM:DATA?', datatype='uint8', is_big_endian=False)
    freqctr.write('HCOP:SDUM:DATA?')
    raw_data = freqctr.read_raw()
    dec_data = decode_ieee_block(raw_data)

#freqctr.write('CALC:AVER:STAT OFF')  # disable statistics collections
freqctr.write('SAMP:COUN 1')     # return sample count to its default of 1
freqctr.write('TRIG:SOUR IMM')   # return trigger source to IMMEdiate
freqctr.write('DISP:MODE NUM')   # return display to Numeric

if args.ofile:    
    print ("Screen Hardcopy Output file: %s" % fn )

    fid = open(fn, 'wb')
    fid.write(dec_data)
    fid.close()

#print 'Done'
