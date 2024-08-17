"""
 Authors: Nils Gumpfer, Joshua Prim
 Version: 0.1

 Extractor for MehmetAkif ECGs

 Copyright 2020 The Authors. All Rights Reserved.
"""
import pandas as pd
import PyPDF2
import numpy as np
import math
from extractors.abstract_extractor import AbstractExractor
from utils.data.visualisation import visualiseIndividualfromDF, visualiseIndividualinMPL
from utils.extract_utils.extract_utils import rotate_origin_only, move_along_the_axis, scale_values_based_on_eich_peak, \
    create_measurement_points, adjust_leads_baseline, preprocess_page_content, extract_graphics_string
from utils.misc.datastructure import perform_shape_switch
import logging
from tqdm import tqdm
import os


class MehmetAkifExtractor(AbstractExractor):

    def __init__(self, params):
        super().__init__(params)

        if 'ecg_path_source' not in self.params:
            raise ValueError('ecg_path_source is not set in params')
        else:
            self.path_source = params['ecg_path_source']

        if 'ecg_path_sink' not in self.params:
            raise ValueError('ecg_path_sink is not set in params')
        else:
            self.path_sink = params['ecg_path_sink']

        # reference value for the calibration jag
        self.eich_ref = 1000

        # extracted height for the calibration jag in PDF
        self.eichzacke = 1000
        if 'number_of_points' not in params:
            raise ValueError('number_of_points is not set in params')
        else:
            # number of measuring points in XML
            self.number_of_points = params['number_of_points']

        if 'show_visualisation' in params:
            self.show_visualisation = params['show_visualisation']
        else:
            self.show_visualisation = False

        if 'vis_scale' in params:
            self.vis_scale = params['vis_scale']
        else:
            self.vis_scale = 1

        if 'vis_MPL' in params:
            self.vis_MPL = params['vis_MPL']
        else:
            self.vis_MPL = False

        # factor for scaling
        self.gamma = self.eich_ref / self.eichzacke

        # name of the leads
        self.lead_names = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

    def extract(self):
        for file_name in tqdm(os.listdir(self.path_source)):
            logging.info('Converting "{}"'.format(file_name))
            try:
                lead_list = self.extract_leads_from_pdf(file_name)
                logging.warning('Extracted {} leads'.format(len(lead_list)))

                if lead_list is not None:
                    new_lead_list = []

                    for lead in lead_list:
                        tmp_lead = []

                        # Preprocess extracted vectors
                        for t in lead:
                            x, y = rotate_origin_only(float(t[0]), float(t[1]), math.radians(0))
                            tmp_lead.append([x, y])

                        new_lead = move_along_the_axis(tmp_lead)

                        # Scale values based on eich peak
                        new_lead = scale_values_based_on_eich_peak(new_lead, self.gamma)

                        # Create (e.g. 5000) measurement points based on the unevenly distributed points
                        measurement_points = create_measurement_points(new_lead, self.number_of_points)

                        # Collect converted leads
                        new_lead_list.append(measurement_points)

                    # Convert lead list to dataframe
                    df_leads = pd.DataFrame(perform_shape_switch(new_lead_list), columns=self.lead_names)

                    # Adjust baseline position of each lead
                    df_leads = adjust_leads_baseline(df_leads)

                    # Plot leads of ECG if config is set to do so
                    if self.show_visualisation:
                        if not self.vis_MPL:
                            visualiseIndividualfromDF(df_leads, self.vis_scale)
                        else:
                            visualiseIndividualinMPL(df_leads)
                    df_leads.to_csv(('{}{}.csv'.format(self.path_sink, file_name.replace(".pdf", ""))),
                                    index=False)
                else:
                    logging.error('Lead list is none')
            except Exception as e:
                logging.warning(('Exception: ' + str(e)))
                logging.warning(('Failed to extract ' + str(file_name)))

        return True

    def extract_leads_from_pdf(self, filename):
        reader = PyPDF2.PdfFileReader(open(self.path_source + filename, 'rb'))

        num_pages = reader.getNumPages()
        logging.warning('Number of pages: {}'.format(num_pages))
        if num_pages == 5:
            try:
                pg1 = reader.getPage(2).getContents()._data
                pg2 = reader.getPage(3).getContents()._data      
            except:
                logging.warning('Switching to MUSE(R) format')
                pg1 = reader.getPage(2).getContents()[0].getObject()._data
                pg2 = reader.getPage(3).getContents()[0].getObject()._data          
        else:
            try:
                pg1 = reader.getPage(0).getContents()._data
                pg2 = reader.getPage(1).getContents()._data
            except:
                logging.warning('Switching to MUSE(R) format')
                pg1 = reader.getPage(0).getContents()[0].getObject()._data
                pg2 = reader.getPage(1).getContents()[0].getObject()._data
        pg1 = preprocess_page_content(pg1)
        pg1 = extract_graphics_string(pg1)
        pg1_leads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
        
        pg2 = preprocess_page_content(pg2)
        pg2 = extract_graphics_string(pg2)
        pg2_leads = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']
        
        leads1 = self.collectLeads(pg1, None, None, pg1_leads)
        leads2 = self.collectLeads(pg2, None, None, pg2_leads)

        leads = leads1 + leads2
        


        return leads

    def collectLeads(self, graphicsstring, lower=7, upper=18, leads_str=None):
        leads = []
        leads_raw = []

        for i in range(len(leads_str)):
            split_string = "Td ({})".format(leads_str[i])
            graphicsstring_app = graphicsstring[0].split(split_string)[0]
            leads_raw.append(graphicsstring_app)
            graphicsstring[0] = graphicsstring[0].split(split_string)[1]
        for i in range(len(leads_raw)):
            temp_string = leads_raw[i].split('S')
            for j in range(len(temp_string)):
                if "1050" in temp_string[j] and len(temp_string[j]) > 100:
                    if "Tj ET" in temp_string[j]:
                        temp_string[j] = temp_string[j].split('Tj ET')[1]
                    leads_raw[i] = temp_string[j]
                    leads_raw[i] = leads_raw[i].split('1050 1913')[0].split('\n')
                    break


        
        for tmp in leads_raw:
            lead = []
            for p in tmp:
                coordinates = p.split(' ')
                if len(coordinates) == 2:
                    lead.append(coordinates)

            lead = np.array(lead)
            leads.append(lead)

        return leads


if __name__ == '__main__':
    path_source = '../data/pdf_data/pdf_mehmetakif/original_ecgs/'
    path_sink = '../data/pdf_data/pdf_mehmetakif/extracted_ecgs/'

    params = {
        'ecg_path_sink': path_sink,
        'ecg_path_source': path_source,
        'number_of_points': 5000,
        'show_visualisation': True,
    }

    tmp = MehmetAkifExtractor(params)
    tmp.extract()
