#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import glob
import argparse
import io
import json
import os
import os.path
import re
import csv
import subprocess
from PIL import Image
from math import sqrt, exp, log
from matplotlib import cm
from matplotlib import pyplot as plt
from itertools import izip_longest

import numpy as np
import cv2 as cv
import pandas as pd


class FlirImageExtractor:

    def __init__(self, exiftool_path="exiftool", is_debug=False):
        self.exiftool_path = exiftool_path
        self.is_debug = is_debug
        self.is_debug_number_of_images = 0
        self.is_debug_number_of_images_with_metadata = 0
        self.flir_img_filename = ""
        self.subfolder_name = ""
        self.image_suffix = "_rgb_image.jpg"
        self.thumbnail_suffix = "_rgb_thumb.jpg"
        self.downscaled_image_suffix = "_rgb_image_downscaled.jpg"
        self.cropped_image_suffix = "_rgb_image_cropped.jpg"
        self.thermal_suffix = "_thermal.png"
        self.csv_suffix = "_thermal_values.csv"
        
        # valid for PNG thermal images
        self.use_thumbnail = False
        self.fix_endian = True

        self.rgb_image_np = None
        self.downscaled_rgb_image_np = None
        self.thermal_image_np = None
        self.weather_df = None
        self.emissivity = 0.98
        self.rt = 30.00
        self.default_distance = 15.24
        self.at = None
        self.rh = None
        self.metadata_in_file = False

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

        if self.get_image_type().upper().strip() == "TIFF":
            # valid for tiff images from Zenmuse XTR
            self.use_thumbnail = True
            self.fix_endian = False

        self.rgb_image_np = self.extract_embedded_image()
        self.thermal_image_np = self.extract_thermal_image()

    def get_image_type(self):
        """
        Get the embedded thermal image type, generally can be TIFF or PNG
        :return:
        """
        meta_json = subprocess.check_output(
            [self.exiftool_path, '-RawThermalImageType', '-j', self.flir_img_filename], shell=True)
        meta = json.loads(meta_json.decode())[0]

        return meta['RawThermalImageType']

    def get_rgb_np(self):
        """
        Return the last extracted rgb image
        :return:
        """
        return self.rgb_image_np

    def get_thermal_np(self):
        """
        Return the last extracted thermal image
        :return:
        """
        return self.thermal_image_np

    def extract_embedded_image(self):
        """
        extracts the visual image as 2D numpy array of RGB values
        """
        image_tag = "-EmbeddedImage"
        if self.use_thumbnail:
            image_tag = "-ThumbnailImage"

        visual_img_bytes = subprocess.check_output([self.exiftool_path, image_tag, "-b", self.flir_img_filename], shell=True)
        visual_img_stream = io.BytesIO(visual_img_bytes)

        visual_img = Image.open(visual_img_stream)
        visual_np = np.array(visual_img)

        return visual_np

    def extract_thermal_image(self):
        """
        extracts the thermal image as 2D numpy array with temperatures in oC
        """

        # read image metadata needed for conversion of the raw sensor values
        # E=1,SD=1,RTemp=20,ATemp=RTemp,IRWTemp=RTemp,IRT=1,RH=50,PR1=21106.77,PB=1501,PF=1,PO=-7340,PR2=0.012545258
        meta_json = subprocess.check_output(
            [self.exiftool_path, self.flir_img_filename, '-Emissivity', '-SubjectDistance', '-AtmosphericTemperature',
             '-ReflectedApparentTemperature', '-IRWindowTemperature', '-IRWindowTransmission', '-RelativeHumidity',
             '-PlanckR1', '-PlanckB', '-PlanckF', '-PlanckO', '-PlanckR2', '-j'], shell=True)
        meta = json.loads(meta_json.decode())[0]
        
        # exifread can't extract the embedded thermal image, use exiftool instead
        thermal_img_bytes = subprocess.check_output([self.exiftool_path, "-RawThermalImage", "-b", self.flir_img_filename], shell=True)
        thermal_img_stream = io.BytesIO(thermal_img_bytes)

        thermal_img = Image.open(thermal_img_stream)
        thermal_np = np.array(thermal_img)

        # raw values -> temperature
        subject_distance = self.default_distance
        
        # Distance is wrong in our metadata, uncomment lines below when it is fixed
        #if 'SubjectDistance' in meta:
            #subject_distance = FlirImageExtractor.extract_float(meta['SubjectDistance'])

        if self.fix_endian:
            # fix endianness, the bytes in the embedded png are in the wrong order
            thermal_np = np.vectorize(lambda x: (x >> 8) + ((x & 0x00ff) << 8))(thermal_np)

        # Check if the image is present in the xlsx data
        if self.metadata_in_file:
            # Use the metadata found in file
            raw2tempfunc = np.vectorize(lambda x: FlirImageExtractor.raw2temp(x, 
                                                                    E=self.emissivity, OD=subject_distance,
                                                                    RTemp=self.rt,
                                                                    ATemp=self.at,
                                                                    IRWTemp=FlirImageExtractor.extract_float(
                                                                        meta['IRWindowTemperature']),
                                                                    IRT=meta['IRWindowTransmission'],
                                                                    RH=self.rh,
                                                                    PR1=meta['PlanckR1'], PB=meta['PlanckB'],
                                                                    PF=meta['PlanckF'],
                                                                    PO=meta['PlanckO'], PR2=meta['PlanckR2']))
        
        else:
            # Use the metadata attached to the image
            raw2tempfunc = np.vectorize(lambda x: FlirImageExtractor.raw2temp(x, 
                                                                    E=meta['Emissivity'],               OD=subject_distance,
                                                                    RTemp=FlirImageExtractor.extract_float(
                                                                        meta['ReflectedApparentTemperature']),
                                                                    ATemp=FlirImageExtractor.extract_float(
                                                                        meta['AtmosphericTemperature']),
                                                                    IRWTemp=FlirImageExtractor.extract_float(
                                                                        meta['IRWindowTemperature']),
                                                                    IRT=meta['IRWindowTransmission'],
                                                                    RH=FlirImageExtractor.extract_float(
                                                                        meta['RelativeHumidity']),
                                                                    PR1=meta['PlanckR1'], PB=meta['PlanckB'],
                                                                    PF=meta['PlanckF'],
                                                                    PO=meta['PlanckO'], PR2=meta['PlanckR2']))
        thermal_np = raw2tempfunc(thermal_np)
        return thermal_np

    @staticmethod
    def raw2temp(raw, E=0.98, OD=15.24, RTemp=30, ATemp=20, IRWTemp=20, IRT=1, RH=50, PR1=21106.77, PB=1501, PF=1, PO=-7340,
                 PR2=0.012545258):
        """
        convert raw values from the flir sensor to temperatures in C
        # this calculation has been ported to python from
        # https://github.com/gtatters/Thermimage/blob/master/R/raw2temp.R
        # a detailed explanation of what is going on here can be found there
        """

        # constants
        ATA1 = 0.006569
        ATA2 = 0.01262
        ATB1 = -0.002276
        ATB2 = -0.00667
        ATX = 1.9

        # transmission through window (calibrated)
        emiss_wind = 1 - IRT
        refl_wind = 0

        # transmission through the air
        h2o = (RH / 100) * exp(1.5587 + 0.06939 * (ATemp) - 0.00027816 * (ATemp) ** 2 + 0.00000068455 * (ATemp) ** 3)
        tau1 = ATX * exp(-sqrt(OD / 2) * (ATA1 + ATB1 * sqrt(h2o))) + (1 - ATX) * exp(
            -sqrt(OD / 2) * (ATA2 + ATB2 * sqrt(h2o)))
        tau2 = ATX * exp(-sqrt(OD / 2) * (ATA1 + ATB1 * sqrt(h2o))) + (1 - ATX) * exp(
            -sqrt(OD / 2) * (ATA2 + ATB2 * sqrt(h2o)))

        # radiance from the environment
        raw_refl1 = PR1 / (PR2 * (exp(PB / (RTemp + 273.15)) - PF)) - PO
        raw_refl1_attn = (1 - E) / E * raw_refl1
        raw_atm1 = PR1 / (PR2 * (exp(PB / (ATemp + 273.15)) - PF)) - PO
        raw_atm1_attn = (1 - tau1) / E / tau1 * raw_atm1
        raw_wind = PR1 / (PR2 * (exp(PB / (IRWTemp + 273.15)) - PF)) - PO
        raw_wind_attn = emiss_wind / E / tau1 / IRT * raw_wind
        raw_refl2 = PR1 / (PR2 * (exp(PB / (RTemp + 273.15)) - PF)) - PO
        raw_refl2_attn = refl_wind / E / tau1 / IRT * raw_refl2
        raw_atm2 = PR1 / (PR2 * (exp(PB / (ATemp + 273.15)) - PF)) - PO
        raw_atm2_attn = (1 - tau2) / E / tau1 / IRT / tau2 * raw_atm2
        raw_obj = (raw / E / tau1 / IRT / tau2 - raw_atm1_attn -
                   raw_atm2_attn - raw_wind_attn - raw_refl1_attn - raw_refl2_attn)

        # temperature from radiance
        temp_celcius = PB / log(PR1 / (PR2 * (raw_obj + PO)) + PF) - 273.15
        return temp_celcius

    @staticmethod
    def extract_float(dirtystr):
        """
        Extract the float value of a string, helpful for parsing the exiftool data
        :return:
        """
        digits = re.findall(r"[-+]?\d*\.\d+|\d+", dirtystr)
        return float(digits[0])

    def plot(self):
        """
        Plot the rgb + thermal image (easy to see the pixel values)
        :return:
        """
        rgb_np = self.get_rgb_np()
        thermal_np = self.get_thermal_np()

        plt.subplot(1, 2, 1)
        plt.imshow(thermal_np, cmap='hot')
        plt.subplot(1, 2, 2)
        plt.imshow(rgb_np)
        plt.show()

    def save_images(self):
        """
        Save the extracted images
        :return:
        """
        rgb_np = self.get_rgb_np()
        thermal_np = self.extract_thermal_image()

        img_visual = Image.fromarray(rgb_np)
        thermal_normalized = (thermal_np - np.amin(thermal_np)) / (np.amax(thermal_np) - np.amin(thermal_np))
        img_thermal = Image.fromarray(np.uint8(cm.inferno(thermal_normalized) * 255))

        fn_prefix, _ = os.path.splitext(self.flir_img_filename)
        
        thermal_filename = os.path.join(fn_prefix + '/' + fn_prefix.split('\\')[3] + self.thermal_suffix)
        image_filename = os.path.join(fn_prefix + '/' + fn_prefix.split('\\')[3] + self.image_suffix)
        
        if self.use_thumbnail:
            image_filename = fn_prefix + self.thumbnail_suffix

        if self.is_debug:
            print("DEBUG Saving RGB image to:{}".format(image_filename))
            print("DEBUG Saving Thermal image to:{}".format(thermal_filename))

        img_visual.save(image_filename)
        img_thermal.save(thermal_filename)

    def export_data_to_csv(self):
        """
        Export thermal data, along with rgb information 
        of the downscaled image to a csv file
        :return:
        """
        
        fn_prefix, _ = os.path.splitext(self.flir_img_filename)
        path = os.path.join(fn_prefix + '/' + fn_prefix.split('\\')[3] + self.csv_suffix)


        # list of pixel coordinates and thermal values
        coords_and_thermal_values = []
        for e in np.ndenumerate(self.thermal_image_np):
            x, y = e[0]
            c = e[1]
            coords_and_thermal_values.append([x, y, c])
    
        # list of rgb values of the downscaled 60x80 image
        rgb_values = []
        for i in range(self.downscaled_rgb_image_np.shape[0]):
            for j in range(self.downscaled_rgb_image_np.shape[1]):
                R = self.downscaled_rgb_image_np[i,j,0]
                G = self.downscaled_rgb_image_np[i,j,1]
                B = self.downscaled_rgb_image_np[i,j,2]
                rgb_values.append([R, G, B])
        
        # List of lists of lists [[[x,y,temp],[R,G,B]]]
        merged_list = list(map(list,zip(coords_and_thermal_values, rgb_values)))
        
        # List of lists [[x,y,temp],[R,G,B]]
        flat_list = [item for sublist in merged_list for item in sublist]

        # Combination of consecutive sublists [x,y,temp,R,G,B] -> format needed for csv writer
        x = iter(flat_list)
        formatted_flat_list = [a+b for a, b in izip_longest(x, x, fillvalue=[])]
        
        with open(path, 'w') as fh:
            writer = csv.writer(fh, delimiter=',')
            writer.writerow(['x', 'y', 'Temp(c)', 'R', 'G', 'B'])
            writer.writerows(formatted_flat_list)
            

    def crop_center(self, img, cropx, cropy):
        """
        Crop the image to the given dimensions
        :return:
        """
        y, x, z = img.shape
        startx = x // 2 - (cropx // 2)
        starty = y // 2 - (cropy // 2)
        return img[starty:starty + cropy, startx:startx + cropx]

    def image_downscale(self):
        """
        Downscale the rgb image to 60x80 resolution
        to match the thermal image's resolution
        and save it
        :return:
        """

        # crop the rgb image
        cropped_img = self.crop_center(self.rgb_image_np, 494, 335)

        width = 80
        height = 60
        dim = (width, height)

        # resize the rgb image
        resized = cv.resize(cropped_img, dim, interpolation=cv.INTER_AREA)

        fn_prefix, _ = os.path.splitext(self.flir_img_filename)
        downscaled_image_filename = os.path.join(fn_prefix + '/' + fn_prefix.split('\\')[3] + self.downscaled_image_suffix)
        cropped_image_filename = os.path.join(fn_prefix + '/' + fn_prefix.split('\\')[3] + self.cropped_image_suffix)

        downscaled_img_visual = Image.fromarray(resized)
        self.downscaled_rgb_image_np = np.array(downscaled_img_visual)
        
        cropped_img_visual = Image.fromarray(cropped_img)
        
        downscaled_img_visual.save(downscaled_image_filename)
        cropped_img_visual.save(cropped_image_filename)
        
        if self.is_debug:
            #print('DEBUG Original Dimensions : ', self.rgb_image_np.shape)
            #print('DEBUG Removed black surrounding box')
            #print('DEBUG Cropped RGB image dimensions: ', cropped_img.shape)
            #print('DEBUG Downscaled RGB image dimensions : ', resized.shape)
            #print("DEBUG Saving downscaled RGB image to:{}".format(downscaled_image_filename))
            print("DEBUG Saving cropped 494x335 RGB image to:{}".format(cropped_image_filename))

    def create_subfolder(self):
        """
        Create a subfolder inside the original image
        folder in order to save generated files
        :return:
        """
        # define the name of the directory to be created
        fn_prefix, _ = os.path.splitext(self.flir_img_filename)
        path = fn_prefix

        try:
            os.mkdir(path)
        except OSError:
            if self.is_debug:
                print("DEBUG Creation of the directory %s failed" % path)
        else:
            if self.is_debug:
                print("DEBUG Successfully created the directory %s " % path)

        return path
    
    def parse_weather_data(self):
        file_name = 'images/weather_data.xlsx'
        xl_file = pd.ExcelFile(file_name)
        dfs = pd.read_excel(file_name, header=None, skiprows=1, keep_default_na=False)
        
        # Dataframe keys
        dfs.columns = ['DateTime_1', 'Temp_1', 'RH_1', 'DateTime_2', 'Temp_2', 'RH_2', 'DateTime_3',
                       'Temp_3', 'RH_3']
        
        self.weather_df = dfs
        #print(self.weather_df)

    def check_if_metadata_present(self, file_name):
        self.metadata_in_file = False
        img_name = os.path.split(file_name)[1]
        img_time = img_name.split("_")[2]
        
        # Date modification so that we get an exact match
        joined_date = ''.join(file_name.split("\\")[1] + " " + img_time[:2] + ":15:00" )
     
        for i, j in self.weather_df.iterrows():
            if str(j[0]) == joined_date:
                self.metadata_in_file = True
                self.at = FlirImageExtractor.extract_float(str(j[1]))
                self.rh = FlirImageExtractor.extract_float(str(j[2]))
            elif str(j[3]) == joined_date:
                self.metadata_in_file = True
                self.at = FlirImageExtractor.extract_float(str(j[4]))
                self.rh = FlirImageExtractor.extract_float(str(j[5]))
            elif str(j[6]) == joined_date:
                self.metadata_in_file = True
                self.at = FlirImageExtractor.extract_float(str(j[7]))
                self.rh = FlirImageExtractor.extract_float(str(j[8]))
        
        if self.metadata_in_file:
            self.is_debug_number_of_images_with_metadata+=1
        else:
            print("Weather data not found for: ", file_name)

class SmartFormatter(argparse.HelpFormatter):



    def _split_lines(self, text, width):

        if text.startswith('R|'):

            return text[2:].splitlines()  

        # this is the RawTextHelpFormatter._split_lines

        return argparse.HelpFormatter._split_lines(self, text, width)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract and visualize Flir Image data', formatter_class=SmartFormatter)
    parser.add_argument('-act', '--actions', help='R|Perform all available actions except for plot() for all images.\nIncludes the generation of 4 images and a csv file.\n'
                        '1. Original thermal image (60x80)\n2. Original rgb image (640x480)\n3. Downscaled rgb image (60x80)\n4. Cropped rgb image (494x335)\n'
                        '5. Thermal data csv file generated by using the attached metadata',required=False,  action='store_true')
    parser.add_argument('-i', '--input', type=str, help='Input image. Ex. img.jpg', required=False)
    parser.add_argument('-p', '--plot', help='Generate a plot using matplotlib', required=False, action='store_true')
    parser.add_argument('-exif', '--exiftool', type=str, help='Custom path to exiftool', required=False,
                        default='exiftool')
    parser.add_argument('-csv', '--extractcsv', help='Export the data per pixel encoded as csv file',
                        required=False, action='store_true')
    parser.add_argument('-s', '--scale', help='Downscale the original image to match the thermal image\'s dimensions',
                        required=False, action='store_true')
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False,
                        action='store_true')
    args = parser.parse_args()
    
    if args.debug:
        print("DEBUG Recommended Python version: > 3.5")
        print("DEBUG Your system's Python version: "+str(sys.version_info[0])+"."+str(sys.version_info[1]))

    fie = FlirImageExtractor(exiftool_path=args.exiftool, is_debug=args.debug)
    
    if args.actions:
        image_path_list = glob.glob("images/*-*-*/Camera_*/*.jpg")
        fie.parse_weather_data()
        
        for image_path in image_path_list:
            fie.check_if_metadata_present(image_path)
            fie.process_image(image_path)
            fie.create_subfolder()
            fie.image_downscale()
            fie.export_data_to_csv()
            fie.save_images()
            if args.debug:
                print ("-------------------------------------------------------")
        
        print("Total number of images: ",len(image_path_list))
        print("Total number of images with metadata present in the xlsx : ",fie.is_debug_number_of_images_with_metadata)
        
    else:
        fie.process_image(args.input)
        fie.create_subfolder()
        if args.plot:
            fie.plot()
        if args.scale:
            fie.image_downscale()
        if args.extractcsv:
            fie.export_data_to_csv()
        fie.save_images()
