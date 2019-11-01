import argparse
import sys
import os
import glob

import csv
import numpy as np
import cv2 as cv
import pandas as pd


# -*- coding: utf-8 -*-

class ThermalDataModifier:

    def __init__(self, is_debug=False):
        self.is_debug = is_debug
        self.unmodified_data_suffix = '_thermal_values.csv'
        self.metadata_in_file = False
        self.at = 0.00
        self.sub = 0
        self.add = 0

    def process_thermal_data(self, directory):
        """
        Maps the extracted mask to the thermal data
        :return:
        """

        if self.is_debug:
            if os.path.exists(directory):
                print("DEBUG Working directory exists " + directory)
            else:
                print("DEBUG Error! Provided directory does not exist!")

        unmodified_data_suffix = '_thermal_values.csv'
        loaded_csv_files = glob.glob(directory + '/*{}'.format(unmodified_data_suffix))

        if loaded_csv_files.__len__() > 1:
            print('Multiple themal values csv files found inside the folder: ' + directory)
            print(loaded_csv_files)
            print('Please remove the extra file(s)')
            print('Exiting..')
            return
        elif loaded_csv_files.__len__() < 1:
            print('No themal values csv file found inside the folder: ' + directory)
            print('Please add a file')
            print('Exiting..')
            return

        if self.is_debug:
            print("DEBUG Using csv file: " + loaded_csv_files[0])

        thresh_low = self.at - self.sub
        thresh_high = self.at + self.add

        if self.is_debug:
            print("DEBUG Threshold low: %.2f, Threshold high %.2f" % (thresh_low, thresh_high))

        data = pd.read_csv(loaded_csv_files[0], sep=',', parse_dates=False)

        # Create a new column that has rounded temperatures
        data['Temp_rounded(c)'] = data['Temp(c)'].map(lambda tempc: round(tempc))

        # Filter out dataframe rows that contain temperatures that do not abide by the threshold
        filtered_df = data[(data['Temp(c)'] > thresh_low) & (data['Temp(c)']<thresh_high)]
        # print(filtered_df)

        # Count the absolute number of occurrences for each rounded temperature
        observations = filtered_df['Temp_rounded(c)'].value_counts()

        # Calculate the relative frequency for each temperature
        observations_percent = filtered_df['Temp_rounded(c)'].value_counts(normalize=True)

        # Round the relative frequency on second decimal digit
        observations_percent = observations_percent.map(lambda temp: round(temp*100,2))

        # Create a new dictionary with 3 columns
        frame = {'Temp_rounded(c)': observations.index.astype('int64'), 'Observations': observations.values, 'Frequency(%)' : observations_percent.values }

        # Convert it to a Dataframe
        temps_freq_df = pd.DataFrame(frame)

        # Reorder the columns
        temps_freq_df = temps_freq_df[['Temp_rounded(c)', 'Observations', 'Frequency(%)']]

        # Export to csv
        temps_freq_df.to_csv(os.path.join(directory, 'canopy_empirical.csv'), header=True, index=False)

        if self.is_debug:
            print('DEBUG canopy_empirical.csv created')

    def parse_weather_data(self):
        file_name = 'images/weather_data.xlsx'
        dfs = pd.read_excel(file_name, header=None, skiprows=1, keep_default_na=False)

        # Dataframe keys
        dfs.columns = ['DateTime_1', 'Temp_1', 'RH_1', 'DateTime_2', 'Temp_2', 'RH_2', 'DateTime_3',
                       'Temp_3', 'RH_3']

        self.weather_df = dfs

    def check_if_metadata_present(self, folder_name):
        self.metadata_in_file = False
        img_name = folder_name.split('\\')[3]
        img_time = img_name.split("_")[2]

        # Date modification so that we get an exact match
        joined_date = ''.join(folder_name.split("\\")[1] + " " + img_time[:2] + ":15:00" )

        for i, j in self.weather_df.iterrows():
            if str(j[0]) == joined_date:
                self.metadata_in_file = True
                self.at = j[1]
            elif str(j[3]) == joined_date:
                self.metadata_in_file = True
                self.at = j[4]
            elif str(j[6]) == joined_date:
                self.metadata_in_file = True
                self.at = j[7]

        if self.metadata_in_file:
            pass
        else:
            print("Atmospheric temerature not found for: ", folder_name)
            return

    def set_add_sub(self, list):
        self.sub = list[0]
        self.add = list[1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Modifies the thermal data and generates metrics')
    parser.add_argument('-dir', '--directory', type=str, help='Path to directory. Ex. images/test2/', required=False)
    parser.add_argument('-act', '--actions', help='Performs the action for all images inside folders with .csv and mask.txt files', required=False,  action='store_true')
    parser.add_argument('-val', '--values', type=int, nargs=2, help='Number to subtract from Tair and number to add to Tair', required=True)
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False, action='store_true')
    parsed_args = parser.parse_args()

    tdm = ThermalDataModifier(is_debug=parsed_args.debug)
    tdm.parse_weather_data()
    tdm.set_add_sub(parsed_args.values)

    if parsed_args.actions:
        folder_path_list = glob.glob("images/*-*-*/Camera_*/*/")
        for folder_path in folder_path_list:
            tdm.check_if_metadata_present(folder_path)
            tdm.process_thermal_data(folder_path)
            if parsed_args.debug:
                print("-------------------------------------------------------")
    else:
        tdm.check_if_metadata_present(parsed_args.directory)
        tdm.process_thermal_data(parsed_args.directory)