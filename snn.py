# This python file is a way to process raw data through LIF

import sys
import os
import struct
import math
import cv2
import numpy as np


def getDVSeventsDavis(file, numEvents=1e10, startTime=0):
    """ DESCRIPTION: This function reads a given aedat file and converts it into four lists indicating 
                     timestamps, x-coordinates, y-coordinates and polarities of the event stream. 
    
    Args:
        file: the path of the file to be read, including extension (str).
        numEvents: the maximum number of events allowed to be read (int, default value=1e10).
        startTime: the start event timestamp (in microseconds) where the conversion process begins (int, default value=0).

    Return:
        ts: list of timestamps in microseconds.
        x: list of x-coordinates in pixels.
        y: list of y-coordinates in pixels.`
        pol: list of polarities (0: on -> off, 1: off -> on).       
    """
    print('\ngetDVSeventsDavis function called \n')
    sizeX = 346
    sizeY = 260
    x0 = 0
    y0 = 0
    x1 = sizeX
    y1 = sizeY
   
    print('Reading in at most', str(numEvents))

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
                         

class SNN():
    """Spiking Neural Network.

    ts: timestamp list of the event stream.
    x: x-coordinate list of the event stream.
    y: y-coordinate list of the event stream.
    pol: polarity list of the event stream.  
    threshold: threshold of neuron firing.
    decay: decay of MP with time.
    margin: margin for lateral inhibition.
    spikeVal: MP increment for each event.
    network: MP of each neuron.
    timenet: firing timestamp for each neuron.
    firing: firing numbers for each neuron.
    image: converted output grayscale image.
    """                    
    def __init__(self): 
        self.ts = []
        self.x = []
        self.y = []
        self.pol = []
        self.threshold = 1.2                                          
        self.decay     = 0.02                                          
        self.margin    = 3                                             
        self.spikeVal  = 1
        self.network   = np.zeros((260, 346), dtype = np.float64)
        self.timenet   = np.zeros((260, 346), dtype = np.int64)    
        self.firing = np.zeros((260, 346), dtype = np.int64)
        self.image = np.zeros((260, 346), dtype = np.int64)
    
    def init_timenet(self, t):
        """initialize the timenet with timestamp of the first event"""
        self.timenet[:] = t

    def spiking(self, data):
        """"main process"""
        count = 0
        img_count = 0   
        startindex = 0

        for line in data:
            self.ts.insert(count, int(line[0]))
            self.x.insert(count, int(line[1]))
            self.y.insert(count, int(line[2]))
            self.pol.insert(count, int(line[3]))

            if count == 0:
                self.init_timenet(self.ts[0])
                starttime = self.ts[0]
               
            self.neuron_update(count, self.spikeVal)
            
            if self.ts[count] - starttime > 20000:
                self.show_image(img_count)
                img_count += 1
                starttime = self.ts[count]
                self.image *= 0
                self.firing *= 0

            count += 1

        print('done')
        
    def clear_neuron(self, position):
        """reset MP value of the fired neuron"""             
        for i in range((-1)*self.margin, self.margin):
            for j in range((-1)*self.margin, self.margin):
                if position[0]+i<0 or position[0]+i>=180 or position[1]+j<0 or position[1]+j>=180:
                    continue
                else:
                    self.network[ position[0]+i ][ position[1]+j ] = 0.0

    def neuron_update(self, i, spike_value):
        """update the MP values in the network"""
        x = self.x[i]
        y = self.y[i]
        escape_time = (self.ts[i]-self.timenet[y][x])/1000.0
        residual = max(self.network[y][x]-self.decay*escape_time, 0)
        self.network[y][x] = residual + spike_value
        self.timenet[y][x] = self.ts[i]
        if self.network[y][x] > self.threshold:
            self.firing[y][x] += 1      # countor + 1
            self.clear_neuron([x,y])

    def show_image(self, img_count):
        """convert to and save grayscale images"""
        self.image = np.flip(255*2*(1/(1+np.exp(-self.firing))-0.5),0)
        outputfile = 'D:/ms/' + str(img_count) + '.png'
        cv2.imshow('img', self.image)
        cv2.waitKey(5)
        cv2.imwrite(outputfile, self.image)

    
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

