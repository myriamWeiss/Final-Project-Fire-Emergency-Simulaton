import numpy as np
import pandas as pd
import os
from globals import globs
from scipy.stats import wilcoxon
from heatMap import  get_heatmap_for_queu, get_heatmap_for_wins_percentage


def heatmap_for_queu_result():
    sheet_names = ['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']
    list_of_column = ["PV < 0.1" , "PV < 0.2" , "PV < 0.3", "PV < 0.4" ]
    df =  pd.read_excel( ".\Simulation_05042025_updated\yossi_result\Queu_statistic_wilcoxon.xlsx" ,sheet_name= sheet_names[1])
    pv_signif_col = list_of_column[2]
    ax = get_heatmap_for_queu(df, pv_signif_col )


#1
def queu_statistic_test(path_data, cols_to_drop):
    result ={}
    list_sheet_name = ["Percentil_95 vs MeanRT", "Percentil_95 vs LBR", "MeanRT vs LBR" ]
    for sheet_name in list_sheet_name :
        df = get_data(sheet_name, path_data, cols_to_drop)
        stats_df = get_df_wilcoxon_stats(df)
        result[sheet_name] = stats_df
    save_result_dict_to_excel(result, ".\Simulation_05042025_updated\yossi_result\Queu_statistic_wilcoxon.xlsx")


#2
def get_df_wilcoxon_stats(df : pd.DataFrame) -> pd.DataFrame:
    result = []
    grouped = df.groupby('(Y interval, X service)')[['avg_policy1_queue', 'avg_policy2_queue']]

    for group_key, group_df in grouped:
        avg_queue_list1 = group_df['avg_policy1_queue'].tolist()
        avg_queue_list2 = group_df['avg_policy2_queue'].tolist()
        try:
            stat, pval = wilcoxon_one_sided(avg_queue_list1, avg_queue_list2)
        except ValueError as e:
            stat, pval = None, None  # In case data is insufficient or equal
         
        result.append({
        '(Y interval, X service)': group_key,
        'statistic': stat,
        'p_value': pval,
        'PV < 0.1' : int(pval is not None and pval < 0.1),
        'PV < 0.2' : int(pval is not None and pval < 0.2),
        'PV < 0.3' : int(pval is not None and pval < 0.3),
        'PV < 0.4' : int(pval is not None and pval < 0.4),
        })
    return pd.DataFrame(result)
  
#3
def wilcoxon_one_sided(policy1_values, policy2_values):
    if len(policy1_values) != len(policy2_values):
        raise ValueError("Lists are not in same lenght")

    differences = np.array(policy1_values) - np.array(policy2_values)

    if np.all(differences == 0):
        return None, 1.0
  
    stat, p_value = wilcoxon(differences, alternative='greater')
    return stat, p_value
   
            
def heatmap_for_wilcoxon_result():
    sheet_names = ['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']
    list_of_column = ["PV < 0.1" , "PV < 0.2" , "PV < 0.3", "PV < 0.4" ]
    df =  pd.read_excel( ".\Simulation_05042025_updated\yossi_result\wining_score_wilcoxon.xlsx" ,sheet_name= sheet_names[1])
    pv_signif_col = list_of_column[2]
    ax = get_heatmap_for_wins_percentage(df, pv_signif_col )


#1
def pvalue_signifiicance_on_RT():
    path_data = "./folder_outputs/Test_Statistic.xlsx"
    cols_to_drop = ["mean_difference", "reject_null", "source_run"]
    get_statistic_score(path_data, cols_to_drop)

#2
def get_statistic_score(path_data, cols_to_drop):
    statis_significance_result ={}
    result ={}
    list_sheet_name = ["Percentil_95 vs MeanRT", "Percentil_95 vs LBR", "MeanRT vs LBR" ]
    for sheet_name in list_sheet_name :
        df = get_data(sheet_name, path_data, cols_to_drop)
        df = check_if_pv_is_statistical_significance(df)
        statis_significance_result[sheet_name] = df
        result_df = get_wining_per_set(df)
        result[sheet_name] = result_df
    save_result_dict_to_excel( statis_significance_result, ".\Simulation_05042025_updated\yossi_result\pv_significance.xlsx")  
    save_result_dict_to_excel( result, ".\Simulation_05042025_updated\yossi_result\wining_score_wilcoxon.xlsx")
    
#3
def get_data(sheet_name, path_data, cols_to_drop) -> pd.DataFrame :
    df = pd.read_excel(path_data, sheet_name = sheet_name)
    if cols_to_drop is not None : 
        df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    return df

#4
def check_if_pv_is_statistical_significance(df : pd.DataFrame) -> pd.DataFrame :
    alpha_list= [0.1, 0.2, 0.3, 0.4]
    for alph in alpha_list :
        df[f"PV < {alph}"] = df["p_value"] < alph
    return df

#5
def get_wining_per_set(df : pd.DataFrame) -> pd.DataFrame :
    df= df.drop(columns= ["(Param, SET)_index", "statistic", "p_value"] )

    group_col = '(Y interval, X service)'
    value_columns = [col for col in df.columns if col != group_col]

    result_df = df.groupby(group_col)[value_columns].sum().reset_index() 
    
    cols_to_divide = [col for col in result_df.columns if col != group_col]
    result_df[cols_to_divide] = (result_df[cols_to_divide] / 5)*100

    return result_df

#6
def save_result_dict_to_excel(results_dict: dict, path: str):
    file_path = os.path.join(globs.folder_path, path)
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
        for sheet_name, df in results_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def run_me():
    path_data = "./avg_queu.xlsx"
    cols_to_drop = ["mean_improvement", "win_by_CI", "win_by_Mean", "win_by_Test_statistique", "win_percantage", "win_score"]
    queu_statistic_test (path_data, cols_to_drop)

#run_me()
heatmap_for_queu_result()
#heatmap_for_wilcoxon_result()
