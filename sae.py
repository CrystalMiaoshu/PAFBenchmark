import sys
import os
import struct
import math
import cv2
import numpy as np
import argparse


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
        y: list of y-coordinates in pixels.
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


if __name__ == '__main__':
     # parse the command line argument
    parser = argparse.ArgumentParser(description='SAE for encoding.')
    parser.add_argument('file_path', 
                    help='The .aedat file path.')
    args = parser.parse_args()

    inputfile = args.file_path
    
    T, X, Y, Pol = getDVSeventsDavis(inputfile)#Read the quaternion array
    T = np.array(T).reshape((-1, 1))

    X = np.array(X).reshape((-1, 1))
    Y = np.array(Y).reshape((-1, 1))
    Pol = np.array(Pol).reshape((-1, 1))
    step_time = 10000 #The cumulative time of a frame
    start_idx = 0
    end_idx = 0
    start_time = T[0]
    print(start_time)
    end_time = start_time + step_time
    img_count = 0
    
    while end_time <= T[-1]:
        
 
        while T[end_idx] < end_time:
            end_idx = end_idx + 1
        
        data_x = np.array(X[start_idx:end_idx]).reshape((-1, 1))
        data_y = np.array(Y[start_idx:end_idx]).reshape((-1, 1))
        data_T = np.array(T[start_idx:end_idx]).reshape((-1, 1))
        data = np.column_stack((data_x, data_y)).astype(np.int32)
        
        timestamp=start_time*np.ones((260,346))
        
        for i in range(0, data.shape[0]):
            timestamp[data[i,1], data[i,0]]=data_T[i]
           
        grayscale = np.flip(255*(timestamp-start_time)/step_time, 0).astype(np.uint8)#The normalization formula
        
        cv2.imshow('img',grayscale)
       
        cv2.waitKey(5)
        wfile='D:/ms1/' + str(img_count) + '.png'
        cv2.imwrite(wfile,grayscale)

        start_time = end_time
        end_time += step_time
        start_idx = end_idx
        img_count += 1