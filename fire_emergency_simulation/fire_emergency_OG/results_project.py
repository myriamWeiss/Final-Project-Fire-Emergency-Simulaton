import numpy as np
import pandas as pd
from scipy import stats
import math
import pandas as pd
import glob
from typing import Dict, Tuple, List, Any
from sklearn import logger
from config import (NUM_PARAMETER_SETS, MAX_INTERARRIVAL_RANGE , MAX_TOTAL_SERVICE_RANGE , STEP_INNTERVAL, STEP_TOTAL_SERVICE, SERVICE_RT_RATIO)
from project import runProject 
from wining_scores import count_binary_score_for_set, save_summarize_results
import csv
import os
from globals import globs



def get_final_results() -> str:
    for interval_range in generate_interval_ranges():
        globs.interval_index = interval_range

        for total_service_range in generate_service_ranges():
            globs.total_services_index = total_service_range
            logger.info(f"Interval: {interval_range}, Service: {total_service_range}")

            #dict - polici1 vs ourpolicy2 : df of all the 5 set
            result_param = run_simulation_for_cell(interval_range, total_service_range)

            for comparison_name, df_p1_vs_p2 in result_param.items():
                print("Col name : ", df_p1_vs_p2.columns )
                print(df_p1_vs_p2)
                summary = summarize_cell_results(df_p1_vs_p2)
                save_summarize_results(summary, comparison_name, 'result_project.xlsx')
    return 'result_project.xlsx'

def generate_interval_ranges():
    for y in range(math.ceil((MAX_INTERARRIVAL_RANGE[1] - MAX_INTERARRIVAL_RANGE[0]) / STEP_INNTERVAL)):
        low = MAX_INTERARRIVAL_RANGE[0] + y * STEP_INNTERVAL
        yield (low, low + STEP_INNTERVAL)

def generate_service_ranges():
    for x in range(math.ceil((MAX_TOTAL_SERVICE_RANGE[1] - MAX_TOTAL_SERVICE_RANGE[0]) / STEP_TOTAL_SERVICE)):
        low = MAX_TOTAL_SERVICE_RANGE[0] + x * STEP_TOTAL_SERVICE
        yield (low, low + STEP_TOTAL_SERVICE)

def run_simulation_for_cell(interval_range, total_service_range):
    globs.set_index = 0
    service_range = tuple(s * SERVICE_RT_RATIO for s in total_service_range)
    response_range = tuple(s * (1 - SERVICE_RT_RATIO) for s in total_service_range)
    
    return runProject(interval_range, service_range, response_range)

def summarize_cell_results(result_df):
    
    return {
        'RT_0.1_pv_wilc' : count_binary_score_for_set(result_df, 'RT_0.1_pv_wilc' ),
        'RT_0.2_pv_wilc' : count_binary_score_for_set(result_df, 'RT_0.2_pv_wilc' ),
        'RT_0.3_pv_wilc' : count_binary_score_for_set(result_df, 'RT_0.3_pv_wilc' ),
        'RT_0.4_pv_wilc' : count_binary_score_for_set(result_df, 'RT_0.4_pv_wilc' ),
        'Qu_0.1_pv_wilc' : count_binary_score_for_set(result_df, 'Qu_0.1_pv_wilc'),
        'Qu_0.2_pv_wilc' : count_binary_score_for_set(result_df, 'Qu_0.2_pv_wilc'),
        'Qu_0.3_pv_wilc' : count_binary_score_for_set(result_df, 'Qu_0.3_pv_wilc'),
        'Qu_0.4_pv_wilc' : count_binary_score_for_set(result_df, 'Qu_0.4_pv_wilc'),
        'avg_Max_queue_policy1': result_df['avg_policy1_Max_queue'].mean(),
        'avg_Max_queue_policy2': result_df['avg_policy2_Max_queue'].mean(),
        'mean_improvement_perc': result_df['mean_improvement_perc'].mean()
    }


    

