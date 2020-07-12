#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function

import glob
import argparse
import io
import json
import os
import os.path
import subprocess
from PIL import Image
from math import sqrt, exp, log

import numpy as np

import shutil


class FlirImageExtractor:

    def __init__(self, exiftool_path="exiftool", is_debug=False):
        self.exiftool_path = exiftool_path
        self.is_debug = is_debug
        self.is_debug_number_of_images = 0
        self.flir_img_filename = ""
        self.rgb_image_np = None

    pass


    def process_image(self, flir_img_filename):
        """
        Given a valid image path, process the file: extract real thermal values
        and a thumbnail for comparison (generally thumbnail is on the visible spectre)
        :param flir_img_filename:
        :return:
        """
        if self.is_debug:
            print("INFO Flir image filepath:{}".format(flir_img_filename))

        if not os.path.isfile(flir_img_filename):
            raise ValueError("Input file does not exist or this user don't have permission on this file")

        self.flir_img_filename = flir_img_filename

        self.rgb_image_np = self.extract_embedded_image()


    def get_rgb_np(self):
        """
        Return the last extracted rgb image
        :return:
        """
        return self.rgb_image_np


    def extract_embedded_image(self):
        """
        extracts the visual image as 2D numpy array of RGB values
        """
        image_tag = "-EmbeddedImage"

        visual_img_bytes = subprocess.check_output([self.exiftool_path, image_tag, "-b", self.flir_img_filename], shell=True)
        visual_img_stream = io.BytesIO(visual_img_bytes)

        visual_img = Image.open(visual_img_stream)
        visual_np = np.array(visual_img)

        return visual_np


    def crop_center(self, img, cropx, cropy):
        """
        Crop the image to the given dimensions
        :return:
        """
        y, x, z = img.shape
        startx = x // 2 - (cropx // 2)
        starty = y // 2 - (cropy // 2)
        return img[starty:starty + cropy, startx:startx + cropx]
    

    def save_images(self, path, crop, destination):
        """
        Save the extracted images
        :return:
        """
        visual_np = self.get_rgb_np()

        if crop:
            visual_np = self.crop_center(visual_np, 504, 342)
       
        parts = path.split("\\")
        folder = parts[1]
        name = parts[2]

        destination_path = os.path.join(destination, folder, name)
        img_visual = Image.fromarray(visual_np)
        
        if self.is_debug:
            print("DEBUG Saving cropped RGB image to:{}".format(destination_path))

        img_visual.save(destination_path)



def createDir(output_path, debug=True):
    
    list_of_dirs = [x[0] for x in os.walk("images/")]
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


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

class SmartFormatter(argparse.HelpFormatter):


    def _split_lines(self, text, width):

        if text.startswith('R|'):

            return text[2:].splitlines()  

        # this is the RawTextHelpFormatter._split_lines

        return argparse.HelpFormatter._split_lines(self, text, width)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract and visualize Flir Image data', formatter_class=SmartFormatter)
    parser.add_argument('-exif', '--exiftool', type=str, help='Custom path to exiftool', required=False,
                        default='exiftool')
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False,
                        action='store_true')
    parser.add_argument("--crop", type=str2bool, nargs='?', const=True, default=False, help="Crop the visual spectrum images.")
    args = parser.parse_args()

    fie = FlirImageExtractor(exiftool_path=args.exiftool, is_debug=args.debug)

    if not os.path.isdir('./images'):
        raise Exception('Folder with name "images" does not exist.')

    
    if args.crop:
        output_path = 'Visual_Spectrum_images_cropped'
    else:
        output_path = 'Visual_Spectrum_images'

    createDir(output_path, args.debug)

    image_path_list = glob.glob("images/*/*.jpg")
    
    for image_path in image_path_list:
        fie.process_image(image_path)
        fie.save_images(image_path, args.crop, output_path)
        if args.debug:
            print ("-------------------------------------------------------")
    
    print("Total number of images: ",len(image_path_list))
        
