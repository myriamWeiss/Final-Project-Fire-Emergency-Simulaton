import pandas as pd
import numpy as np
import os
from scipy import stats
from globals import globs
from scipy.stats import wilcoxon
import openpyxl
from config import NUM_REPLICATIONS, NUM_PARAMETER_SETS
import openpyxl
from analysis import save_summarize_results




# Win Score and Test Score
def count_binary_score_for_set(result_df, col_name):
    return (result_df[col_name].sum() / NUM_PARAMETER_SETS)*100

# Win score percentage
def get_win_score_percentage(rel_improvements) : 
    count_win = sum(i > 0 for i in rel_improvements) 
    percentage_win = (count_win / NUM_REPLICATIONS )* 100
    if count_win > (NUM_REPLICATIONS/2) :
        return 1, percentage_win
    return 0, percentage_win



#Test Statistic Score
def get_statistique_score(policy1_percentiles, policy2_percentiles, name_p1_vs_p2, path):
    win_p_value,  lose_p_value = wilcoxon_two_sided(policy1_percentiles, policy2_percentiles)
    significant_result = {
        'win_p_value': win_p_value,
        'lose_p_value': lose_p_value,
        'alpha = 0.1' : check_significant_result(win_p_value,  lose_p_value, 0.1),
        'alpha = 0.2' : check_significant_result(win_p_value,  lose_p_value, 0.2),
        'alpha = 0.3' : check_significant_result(win_p_value,  lose_p_value, 0.3),
        'alpha = 0.4' : check_significant_result(win_p_value,  lose_p_value, 0.4),
    }
    save_summarize_results( significant_result, name_p1_vs_p2, path)
    return significant_result

def wilcoxon_two_sided(policy1_values, policy2_values):
    if len(policy1_values) != len(policy2_values):
        raise ValueError("Lists are not in same lenght")

    differences = np.array(policy1_values) - np.array(policy2_values)

    if np.all(differences == 0):
        return  1.0, 1.0
    
    if_win_stat, if_win_p_value = wilcoxon(differences, alternative='greater')
    if_lose_stat, if_lose_p_value = wilcoxon(differences, alternative='less')
    return  if_win_p_value,  if_lose_p_value

def check_significant_result(win_p_value,  lose_p_value, alpha):
    if(win_p_value > alpha ) and ( lose_p_value > alpha):
        return 1 #tekko = win
    if(win_p_value < alpha):
        return 1 #win
    elif(lose_p_value < alpha):
        return 0
    else :
        return None



#5
def get_wining_per_set(df : pd.DataFrame) -> pd.DataFrame :
    df= df.drop(columns= ["(Param, SET)_index", "statistic", "p_value"] )

    group_col = '(Y interval, X service)'
    value_columns = [col for col in df.columns if col != group_col]

    result_df = df.groupby(group_col)[value_columns].sum().reset_index() 
    
    cols_to_divide = [col for col in result_df.columns if col != group_col]
    result_df[cols_to_divide] = (result_df[cols_to_divide] / 5)*100

    return result_df

