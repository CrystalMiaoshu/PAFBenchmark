# -*- coding: UTF-8

import sys
import os
import struct
import math
import cv2
import numpy as np


def getDVSeventsDavis(file, ROI=np.array([]), numEvents=1e10, startEvent=0, startTime=0):#This function converts an aedat file into a quaternary array
    print('\ngetDVSeventsDavis function called \n')
    sizeX = 240
    sizeY = 180
    x0 = 0
    y0 = 0
    x1 = sizeX
    y1 = sizeY
    if len(ROI) != 0:
        if len(ROI) == 4:
            print('Region of interest specified')
            x0 = ROI(0)
            y0 = ROI(1)
            x1 = ROI(2)
            y1 = ROI(3)
        else:
            print('Unknown ROI argument. Call function as: \n getDVSeventsDavis(file, ROI=[x0, y0, x1, y1], numEvents=nE, startEvent=sE) to specify ROI or\n getDVSeventsDavis(file, numEvents=nE, startEvent=sE) to not specify ROI')
            return

    else:
        print('No region of interest specified, reading in entire spatial area of sensor')

    print('Reading in at most', str(numEvents))
    print('Starting reading from event', str(startEvent))

    triggerevent = int('400', 16)
    polmask = int('800', 16)
    xmask = int('003FF000', 16)
    ymask = int('7FC00000', 16)
    typemask = int('80000000', 16)
    typedvs = int('00', 16)
    xshift = 12
    yshift = 22
    polshift = 11
    x = []
    y = []
    ts = []
    pol = []
    numeventsread = 0
    
    length = 0
    aerdatafh = open(file, 'rb')
    k = 0
    p = 0
    statinfo = os.stat(file)
    if length == 0:
        length = statinfo.st_size
    print("file size", length)

    lt = aerdatafh.readline()
    while lt and str(lt)[2] == "#":
        p += len(lt)
        k += 1
        lt = aerdatafh.readline()
        continue

    aerdatafh.seek(p)
    tmp = aerdatafh.read(8)
    p += 8
    while p < length:
        ad, tm = struct.unpack_from('>II', tmp)
        ad = abs(ad)
        if tm >= startTime:
            if (ad & typemask) == typedvs:
                xo = sizeX - 1 - float((ad & xmask) >> xshift)
                yo = float((ad & ymask) >> yshift)
                polo = 1 - float((ad & polmask) >> polshift)
                if xo >= x0 and xo < x1 and yo >= y0 and yo < y1:
                    x.append(xo)
                    y.append(yo)
                    pol.append(polo)
                    ts.append(tm)
        aerdatafh.seek(p)
        tmp = aerdatafh.read(8)
        p += 8
        numeventsread += 1

    print('Total number of events read =', numeventsread)
    print('Total number of DVS events returned =', len(ts))

    return ts, x, y, pol
                         

class SNN():                    # Class of SNN for line detection        
    #ts  = []                # Timestamps of events
    #x   = []                # X-coordinates of events
    #y   = []                # Y-coordinates of events
    #pol = []                # Polarities of events

    def __init__(self):      # Initialize SNN Class
        self.ts = []
        self.x = []
        self.y = []
        self.pol = []
        self.threshold = 1.2                                             # Threshold of neuron firing
        self.decay     = 0.02                                            # Decay of MP with time
        self.margin    = 3                                              # Margin for lateral inhibition
        self.spikeVal  = 1
        self.network   = np.zeros((260, 346), dtype = np.float64) # MP of each neuron
        self.timenet   = np.zeros((260, 346), dtype = np.int64)   # Firing timestamp of each neuron
        self.image     = np.zeros((260, 346), dtype = np.uint8)  # Image with lines
        #self.countor   = np.zeros((180, 240), dtype = np.uint8)   # count when exceed the threchold
        self.output = []
    
    def init_timenet(self, t):
        self.timenet[:] = t



    def spiking(self, data):  # Main process
        count = 0
        imgcount = 0   
        startindex = 0
        self.image[:] = 0

        for line in data:
            self.ts.insert(count, int(line[0]))
            self.x.insert(count, int(line[1]))
            self.y.insert(count, int(line[2]))
            self.pol.insert(count, int(line[3]))

            if count == 0:
                self.init_timenet(self.ts[0])
                starttime = self.ts[0]
                # starttime = 479714566     

            #if self.ts[count] - starttime > access:
            #    imgcount += 1
            #    imgcount = self.showimage(starttime, starttime + access, imgcount, lum, access, cycle)
            #    starttime += stepsize
            #    self.image[:] = 0

            #if self.ts[count] >= starttime: #and self.pol[count] == 0:
            self.neuron_update(count, self.spikeVal)

            count += 1

        print('done')
        
    def clear_neuron(self, position):                
        for i in range((-1)*self.margin, self.margin):
            for j in range((-1)*self.margin, self.margin):
                if position[0]+i<0 or position[0]+i>=180 or position[1]+j<0 or position[1]+j>=180:
                    continue
                else:
                    self.network[ position[0]+i ][ position[1]+j ] = 0.0

    def neuron_update(self, i, spike_value):
        x = self.x[i]
        y = self.y[i]
        escape_time = (self.ts[i]-self.timenet[y][x])/1000.0
        residual = max(self.network[y][x]-self.decay*escape_time, 0)
        self.network[y][x] = residual + spike_value
        self.timenet[y][x] = self.ts[i]
        if self.network[y][x] > self.threshold:
            self.spike_output(i)       # countor + 1
            self.clear_neuron([x,y])
        
    def spike_output(self, i):
        #self.countor[y][x] += 1
        outputline = []
        outputline.append(self.ts[i])
        outputline.append(self.x[i])
        outputline.append(self.y[i])
        outputline.append(self.pol[i])
        self.output.append(outputline)
    
    def showimage(self, starttime, endtime, imgcount, lum, access, cycle):
        #maxofcountor = self.countor.max()
        #if maxofcountor == 0:
            #imgcount -= 1
        #else:
        for i in range(0, 240):
            for j in range(0, 180):
                grayscale = (int(255 * (1.0 / (1 + np.exp(-int(self.countor[j][i]) / 2.0)))) - 127) * 2    # the result isnot good
                # print(grayscale)
                # grayscale = int(255 * self.countor[j][i] / maxofcountor)
                self.image[j][i] = (grayscale)
        #self.image = cv2.flip(self.image, 0)
        #cv2.imshow('image', self.image)
        #cv2.waitKey(1)
        if lum == 1:
            filepath = 'cue1/light/'
        else:
            filepath = 'cue1/dark/'
        directory = filepath + str(int(access/1000)) + 'ms/' + str(cycle)
        if not os.path.exists(directory):
            os.makedirs(directory)
        file = directory + '/pcd' + str(imgcount - 1).zfill(4) + 'r.png'
        cv2.imwrite(file, self.image)
        #print('%d   %d  %d' % (starttime, endtime, imgcount))
        self.countor = np.zeros((180, 240), dtype=np.uint8)
        return imgcount
        
if __name__ == '__main__':
    inputfile = 'D:/data_report/5.aedat'
    T, X, Y, Pol = getDVSeventsDavis(inputfile)
    T = np.array(T).reshape((-1, 1))
    X = np.array(X).reshape((-1, 1))
    Y = np.array(Y).reshape((-1, 1))
    Pol = np.array(Pol).reshape((-1, 1))
    data = np.hstack((T, X, Y, Pol))
    print(np.shape(data))
    dvs_snn = SNN()
    dvs_snn.spiking(data)
    np.savetxt('D:/output5.txt', np.array(dvs_snn.output), fmt='%.0f', delimiter='\t', newline='\n')

