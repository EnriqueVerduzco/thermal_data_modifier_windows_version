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




class SmartFormatter(argparse.HelpFormatter):


    def _split_lines(self, text, width):

        if text.startswith('R|'):

            return text[2:].splitlines()  

        # this is the RawTextHelpFormatter._split_lines

        return argparse.HelpFormatter._split_lines(self, text, width)


def make_square(im, width, height, color, debug):

    fill_color=(0, 0, 0)
    if color == 'black':
        fill_color=(0, 0, 0)
    elif color == 'brown':
        fill_color=(165,42,42)
    elif color == 'green':
        fill_color=(0,255,0)
    
    x, y = im.size
    new_im = Image.new('RGB', (width, height), fill_color)
    new_im.paste(im, (int((width - x) / 2), int((height - y) / 2)))
    return new_im

def createDir(output_path, debug=True):
    
    list_of_dirs = [x[0] for x in os.walk("Labels/")]
    list_of_dirs.pop(0)

    for directory in list_of_dirs:
        subdir = directory.split("/")[1]

        if os.path.exists(output_path+"/"+subdir):
            if debug:
                print("Debug: {} already exists, deleting...".format(output_path+"/"+subdir))
            shutil.rmtree(output_path+"/"+subdir)
        
        if debug:
                print("Debug: Creating {}".format(output_path+"/"+subdir))
        os.makedirs(output_path+"/"+subdir)

   

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract and visualize Flir Image data', formatter_class=SmartFormatter)
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False,
                        action='store_true')
    parser.add_argument('-i', '--input', type=str, help='Input image. Ex. img.jpg', required=False)
    parser.add_argument('--color', type=str, help='Color to be filled, options are black, brown, green. If sth else is given, it defaults to black', required=False)
    parser.add_argument('--extension', type=str, help='jpg or png', required=False)
    parser.add_argument('--width', type=int, help='Set the width', required=False, default=640)
    parser.add_argument('--height', type=int, help='Set the height', required=False, default=480)

    
    args = parser.parse_args()

    if (args.input and args.color and args.extension and args.width and args.height):
        test_image = Image.open(args.input)
        new_image = make_square(test_image, args.width, args.height, args.color, args.debug)
        new_image.show()

        if args.extension == 'jpg':
            new_image = new_image.save("test.jpg")
        elif args.extension == 'png':
            new_image = new_image.save("test.png")
        else:
            print("Debug: You didn't specify an extension for the file to be saved. Aborting save...")
    
    else:
        createDir('Labels_640x480', debug=args.debug)
        labels = glob.glob("Labels/*/*_L.png")
    
        for label in labels:
            test_image = Image.open(label)
            new_image = make_square(test_image, 640, 480, "brown", args.debug)
            parts = label.split("\\")
            folder = parts[1]
            name = parts[2]
            new_image = new_image.save("Labels_640x480/"+folder+"/"+name)
            if args.debug:
                print ("-------------------------------------------------------")

   