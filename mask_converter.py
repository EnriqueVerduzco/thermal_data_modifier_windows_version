#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function

import re
import glob
import argparse
import io
import json
import os
import os.path

import shutil

import random

from PIL import Image
import numpy as np


class SmartFormatter(argparse.HelpFormatter):


    def _split_lines(self, text, width):

        if text.startswith('R|'):

            return text[2:].splitlines()  

        # this is the RawTextHelpFormatter._split_lines

        return argparse.HelpFormatter._split_lines(self, text, width)



def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def crop_image(img,tol=0):
    # img is 2D or 3D image data
    # tol  is tolerance
    mask = img>tol
    if img.ndim==3:
        mask = mask.all(2)
    mask0,mask1 = mask.any(0),mask.any(1)
    return img[np.ix_(mask0,mask1)]

def crop_image_only_outside(img,tol=0):
    # img is 2D or 3D image data
    # tol  is tolerance
    mask = img>tol
    if img.ndim==3:
        mask = mask.all(2)
    m,n = mask.shape
    mask0,mask1 = mask.any(0),mask.any(1)
    col_start,col_end = mask0.argmax(),n-mask0[::-1].argmax()
    row_start,row_end = mask1.argmax(),m-mask1[::-1].argmax()
    return img[row_start:row_end,col_start:col_end]

def detect_bounding_box(imagepath):

    img = Image.open(imagepath)
    # summarize some details about the image
    print(img.format)
    print(img.size)
    print(img.mode)
    img.show()

    image = np.asarray(img)


    #tolerance 30
    cropped = crop_image_only_outside(image, 30)

    img_new = Image.fromarray(cropped, 'RGB')
    widthDiff = img.size[0] - img_new.size[0]
    heightDiff = img.size[1] - img_new.size[1]
    print("DIff: {} x {}".format(widthDiff,heightDiff))
    img_new.show()


    img_new.save(imagepath.replace(".jpg","_cropped.jpg"))


def convert_to_transparent_orange(originalMask):
    im = Image.open(originalMask)
    x, y = im.size
    pixels = im.load()

    new_im = Image.new('RGBA', (x, y), (0,0,0,0))
    pixels_new = new_im.load()

    for i in range(0,x):
        for j in range (0, y):
            if pixels[i, j] == (0, 255, 0):
                pixels_new[i, j] = (255, 162, 0,255)
    
    new_im.save(originalMask, 'PNG')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract and visualize Flir Image data', formatter_class=SmartFormatter)
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False,
                        action='store_true')
    parser.add_argument('-i', '--input', type=str, help='Input image. Ex. img.jpg', required=True)
    parser.add_argument("--convert", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Make mask transparent except for leaves, which are painted oragne.")
    parser.add_argument("--crop", type=str2bool, nargs='?',
                        const=True, default=False, required=True,
                        help="Auto remove black bounding box.")


    
    args = parser.parse_args()

    
    if(args.crop):
        detect_bounding_box(args.input)
    elif (args.convert):
        convert_to_transparent_orange(args.input)
       