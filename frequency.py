import sys
import os
import struct
import math
import cv2
import numpy as np


def getDVSeventsDavis(file, ROI=np.array([]), numEvents=1e10, startEvent=0, startTime=0):#This function converts an aedat file into a quaternary array
    print('\ngetDVSeventsDavis function called \n')
    sizeX = 346
    sizeY = 260
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

    #ts[:] = [x - ts[0] for x in ts]  # absolute time -> relative time
    #x[:] = [int(a) for a in x]
    #y[:] = [int(a) for a in y]
    
    return ts, x, y, pol


if __name__ == '__main__':
    inputfile = 'D:/data_report/5.aedat'
    T, X, Y, Pol = getDVSeventsDavis(inputfile)#Read the quaternion array
    T = np.array(T).reshape((-1, 1))

    X = np.array(X).reshape((-1, 1))
    Y = np.array(Y).reshape((-1, 1))
    Pol = np.array(Pol).reshape((-1, 1))
    #data = np.hstack((T, X, Y, Pol))
    #print(np.shape(data))
    step_time = 10000 #The cumulative time of a frame
    #img = np.zeros((260, 346), dtype=np.uint8)
    start_idx = 0
    end_idx = 0
    start_time = T[0]
    print(start_time)
    end_time = start_time + step_time
    img_count = 0
    
    while end_time <= T[-1]:
        #end_time = start_time + step_time
 
        while T[end_idx] < end_time:
            end_idx = end_idx + 1
        # print(end_idx)
        data_x = np.array(X[start_idx:end_idx]).reshape((-1, 1))
        data_y = np.array(Y[start_idx:end_idx]).reshape((-1, 1))
        data = np.column_stack((data_x, data_y)).astype(np.int32)
        #print(type(data[0,1]))
        counter=np.zeros((260,346))
        
        for i in range(0, data.shape[0]):
            counter[data[i,1], data[i,0]]+=1#Count the number of pixel occurrences
            #for a in range(0,260):
            #    for b in range(0,346):cccccc
        grayscale = np.flip(255*2*(1/(1+np.exp(-counter))-0.5),0)#The normalization formula
        #counter[a][b]=grayscale
                    # print(grayscale)
        cv2.imshow('img',grayscale)
        # print(counter)
        cv2.waitKey(5)
        wfile='D:/ms/' + str(img_count) + '.png'
        cv2.imwrite(wfile,grayscale)

        start_time = end_time
        end_time += step_time
        start_idx = end_idx
        img_count += 1
        
   
        