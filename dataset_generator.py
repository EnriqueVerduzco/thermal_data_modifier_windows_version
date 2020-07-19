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



class Preprocessor:

    def __init__(self, is_debug=False):
        self.is_debug = is_debug
        self.is_debug_number_of_images = 0
        self.flir_img_filename = ""

        self.list_of_dirs = ['Dataset_crop/train'] * 80 + ['Dataset_crop/val'] * 15 + ['Dataset_crop/test'] * 5

        
        self.vpl = None
        self.lpl = None

        self.visual_image_names = []
        self.label_image_names = []

    pass


    def initImageLists(self, visual_path_list, label_path_list):

        self.vpl = visual_path_list
        self.lpl = label_path_list

        for path in visual_path_list:
            m = re.search(r'^.*\\([^.]*)..*$', path, re.M)
            self.visual_image_names.append(m.group(1))

        # print(self.visual_image_names)
        
        for path in label_path_list:
            m = re.search(r'^.*\\([^.]*)..*$', path, re.M)
            self.label_image_names.append(m.group(1)[:-2])

        # print(self.label_image_names)
        

        visual_spectrum_missing_counter = 0
        label_with_no_vs_image_path_list = []
        for label in self.label_image_names:
            
            if label not in self.visual_image_names:
                    label_with_no_vs_image_path = glob.glob("Labels/*/"+label+"_L.png")
                    label_with_no_vs_image_path_list.append(label_with_no_vs_image_path)
                    # print("{} exists in the labels folder, but not in the visual spectrum images".format(label))
                    visual_spectrum_missing_counter+=1
            else:
                pass
        
        if visual_spectrum_missing_counter == 0:
            print("\nAll labels correspond to visual spectrum images")
        else:
            print("\n{} labels were not found in the visual spectrum images.\n".format(visual_spectrum_missing_counter))
            print("\n Please generate Visual spectrum images for the following labels: \n")
            for path in label_with_no_vs_image_path_list:
                print(path[0])


        label_missing_counter = 0
        vs_images_with_no_label_path_list = []
        for vs_image in self.visual_image_names:

            vs_img_path = glob.glob("Visual_Spectrum_images_cropped/*/"+vs_image+".jpg")
            
            if vs_image not in self.label_image_names:
                   
                    vs_images_with_no_label_path_list.append(vs_img_path)
                    # print("{} exists in the visual spectrum folder, but not in the labels".format(vs_image))
                    label_missing_counter+=1
            else:
                # Label for the image exists
                label_path = glob.glob("Labels/*/"+vs_image+"_L.png")
                dest = random.choice(self.list_of_dirs)
                
                # print("Directory selected: ", dest)
                # print("Copying {}, {} \n".format(vs_img_path[0].replace("\\","/"), label_path[0].replace("\\","/")))
                shutil.copy2(vs_img_path[0].replace("\\","/"), dest)
                shutil.copy2(label_path[0].replace("\\","/"), dest+'_labels')
        
        if label_missing_counter == 0:
            print("\nAll visual spectrum images have labels\n")
        else:
            print("\n{} visual spectrum images have no labels.".format(label_missing_counter))
            print("\nPlease generate Labels for the following images: \n")
            for path in vs_images_with_no_label_path_list:
                print(path[0])


        
        # dir = random.choice(self.list_of_dirs)
        # shutil.copy2(vs_img_path, dir) # target filename is /dst/dir/file.ext
        # shutil.copy2(label_path, dir+'_labels') # target filename is /dst/dir/file.ext

        # print (self.vpl)
        # print (self.lpl)



class SmartFormatter(argparse.HelpFormatter):


    def _split_lines(self, text, width):

        if text.startswith('R|'):

            return text[2:].splitlines()  

        # this is the RawTextHelpFormatter._split_lines

        return argparse.HelpFormatter._split_lines(self, text, width)


def createDir(output_path, debug=True):
    
    if os.path.exists(output_path):
        if debug:
            print("Debug: {} already exists, deleting...".format(output_path))
        shutil.rmtree(output_path)
    
    if debug:
            print("Debug: Creating {}".format(output_path))
    os.makedirs(output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract and visualize Flir Image data', formatter_class=SmartFormatter)
    parser.add_argument('-d', '--debug', help='Set the debug flag', required=False,
                        action='store_true')
    args = parser.parse_args()

    pre = Preprocessor(is_debug=args.debug)

    if not os.path.isdir('./Visual_Spectrum_images'):
        raise Exception('Folder with name "Visual_Spectrum_images" does not exist.')

    if not os.path.isdir('./Labels'):
        raise Exception('Folder with name "Labels" does not exist.')

    output_path = 'Dataset/train'

    createDir('Dataset_crop/train', args.debug)
    createDir('Dataset_crop/train_labels', args.debug)
    createDir('Dataset_crop/val', args.debug)
    createDir('Dataset_crop/val_labels', args.debug)
    createDir('Dataset_crop/test', args.debug)
    createDir('Dataset_crop/test_labels', args.debug)

    visual_path_list = glob.glob("Visual_Spectrum_images_cropped/*/*.jpg")
    label_path_list = glob.glob("Labels/*/*.png")
    
    pre.initImageLists(visual_path_list, label_path_list)
    if args.debug:
        print ("-------------------------------------------------------")
    
    print("\nTotal number of visual spectrum images: ",len(visual_path_list))
    print("Total number of labels: ",len(label_path_list))
        
