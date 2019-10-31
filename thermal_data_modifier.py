import argparse
import sys
import os
import glob

import csv
import numpy as np
import cv2 as cv


# -*- coding: utf-8 -*-

class ThermalDataModifier:

    def __init__(self, is_debug=False, directory=''):
        self.is_debug = is_debug
        self.directory = directory
        self.unmodified_data_suffix = '_thermal_values.csv'

    def process_thermal_data(self):
        """
        Maps the extracted mask to the thermal data
        :return:
        """

        if self.is_debug:
            if os.path.exists(self.directory):
                print("DEBUG Working directory exists " + self.directory)
            else:
                print("DEBUG Error! Provided directory does not exist!")


        path_to_mask = os.path.join(self.directory + '\\' + 'mask.txt')
        
        if os.path.exists(path_to_mask):
            mask = np.loadtxt(path_to_mask)
            new_mask = cv.resize(mask, dsize=(80, 60), interpolation=cv.INTER_CUBIC)
            np.savetxt(os.path.join(self.directory + '\\' + 'mask_60x80.txt'),new_mask, fmt='%d')
            it = np.nditer(new_mask, flags=['multi_index'])
            if self.is_debug:
                print('DEBUG Mask successfully loaded!')
                print('DEBUG Mask was downscaled to 60x80!')
        else:
            print("Mask not found! Please add a mask.txt file to the following folder: "+ self.directory)
            return

        unmodified_data_suffix = '_thermal_values.csv'
        path_to_csv = self.directory + '\\' + '*{}'.format(unmodified_data_suffix)

        # List of csv files with givn suffix inside the folder
        loaded_csv_files = glob.glob(path_to_csv)

        if loaded_csv_files.__len__() > 1:
            print('Multiple themal values csv files found inside the folder: ' + self.directory)
            print(loaded_csv_files)
            print('Please remove the extra file(s)')
            print('Exiting..')
            return
        elif loaded_csv_files.__len__() < 1:
            print('No themal values csv file found inside the folder: ' + self.directory)
            print('Please add a file')
            print('Exiting..')
            return

        if self.is_debug:
            print("DEBUG Using csv file: " + loaded_csv_files[0])

        #Create another csv containing class information
        with open(loaded_csv_files[0], 'r') as csvInput:

            leaves = 0
            reader = csv.reader(csvInput)

            all = []
            row = next(reader)
            row.append('Class')
            all.append(row)

            for row in reader:
                if not it.finished:
                    #check if the csv has been modified before
                    if (len(row)-1) >=6:
                        if self.is_debug:
                            print('DEBUG csv already contains class information and will not be modified')
                        return
                    if it[0] != 0:
                        leaves+=1
                        row.append('Leaf')
                    else:
                        row.append('Noise')
                    it.iternext()
                    all.append(row)

            if leaves == 0:
                if self.is_debug:
                    print("DEBUG: the mask.txt file in the folder does not contain any leaf information")
                return
            with open(loaded_csv_files[0], 'w') as csvOutput:
                writer = csv.writer(csvOutput, lineterminator='\n')
                writer.writerows(all)

        if self.is_debug:
            print('DEBUG csv modified')
            print('DEBUG The file now also contains information regarding which pixels correspond to leaves')

        with open(loaded_csv_files[0], 'r') as csvInput:
            reader = csv.reader(csvInput)
            next(reader)

            total_counter = 0
            leaf_counter = 0
            noise_counter = 0

            total_image_temp = 0
            total_leaf_temp = 0
            total_noise_temp = 0

            lowest_leaf_temp = 9999
            highest_leaf_temp = -9999

            lowest_noise_temp = 9999
            highest_noise_temp = -9999

            for row in reader:
                temp_value = float(row[2])
                total_counter += 1
                total_image_temp += temp_value
                if row[6] == 'Leaf':
                    leaf_counter += 1
                    total_leaf_temp += temp_value
                    if temp_value > highest_leaf_temp:
                        highest_leaf_temp = temp_value
                    if temp_value < lowest_leaf_temp:
                        lowest_leaf_temp = temp_value
                else:
                    noise_counter += 1
                    total_noise_temp += temp_value
                    if temp_value > highest_noise_temp:
                        highest_noise_temp = temp_value
                    if temp_value < lowest_noise_temp:
                        lowest_noise_temp = temp_value

            if leaf_counter > 0:
                average_leaf_temp = total_leaf_temp/leaf_counter
            else:
                print("DEBUG you have provided an empty mask, edit the mask and try again.")
                return()
            average_image_temp = total_image_temp/total_counter
            average_noise_temp = total_noise_temp/noise_counter
            diff = abs(average_leaf_temp - average_noise_temp)

            if self.is_debug:
                print('DEBUG Temperature values that correspond to leaves:', leaf_counter)
                print('DEBUG Filtered out temperature values that do not correspond to leaves:', noise_counter)
                print('Total number of temperature values:', total_counter)
                print('DEBUG Metrics successfully exported into output.csv')

            metric_labels = ['Temp avg', 'Leaf Temp avg', 'Noise Temp avg', 'avg diff',
                             'Leaf Temp peak', 'Leaf Temp Low', 'Noise Temp Peak', 'Noise Temp Low']

            metrics = [average_image_temp, average_leaf_temp, average_noise_temp, diff, highest_leaf_temp,
                       lowest_leaf_temp, highest_noise_temp, lowest_noise_temp]

            with open(os.path.join(self.directory,'output.csv'), 'w') as csvOutput:
                writer = csv.writer(csvOutput, lineterminator='\n')

                all = []
                all.append(metric_labels)
                all.append(metrics)

                writer.writerows(all)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Modifies the thermal data and generates metrics')
    parser.add_argument('-dir', '--directory', type=str, help='Path to directory. Ex. images/test2/', required=False)
    parser.add_argument('-act', '--actions', help='Performs the action for all images inside folders with .csv and mask.txt files',required=False,  action='store_true')
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False, action='store_true')
    parsed_args = parser.parse_args()
    
    if parsed_args.actions:
        folder_path_list = glob.glob("images/*-*-*/Camera_*/*/")

        for folder_path in folder_path_list:
            tdm = ThermalDataModifier(is_debug=parsed_args.debug, directory=folder_path)
            tdm.process_thermal_data()
            if parsed_args.debug:
                print("-------------------------------------------------------")
    else:
        tdm = ThermalDataModifier(is_debug=parsed_args.debug, directory=parsed_args.directory)
        tdm.process_thermal_data()
    
    
