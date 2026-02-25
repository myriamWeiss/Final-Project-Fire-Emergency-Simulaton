import sys
import pandas as pd
import ast
import numpy as np
from scipy.stats import wilcoxon

from heatMap import  get_heatmap_for_queu

# Extended bins
y_bins = list(range(500, 10600, 600))   # 500–1100 to 10000–10600
x_bins = list(range(10, 531, 30))       # 10–40 to 500–530

def parse_interval(interval_str):
    try:
        parsed = ast.literal_eval(interval_str)
        (y_min, y_max), (x_min, x_max) = parsed
        return pd.Series([y_min, y_max, x_min, x_max])
    except:
        return pd.Series([np.nan, np.nan, np.nan, np.nan])

# Use only y_min and x_min for binning
def assign_bin_by_start(y_min, x_min):
    for y_start in y_bins[:-1]:
        y_end = y_start + 600
        if y_start <= y_min < y_end:
            for x_start in x_bins[:-1]:
                x_end = x_start + 30
                if x_start <= x_min < x_end:
                    return f"(({y_start},{y_end}),({x_start},{x_end}))"
    return None


def get_queue_interals_df(file_path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    original_row_count = df.shape[0]

    df[['y_min', 'y_max', 'x_min', 'x_max']] = df['(Y interval, X service)'].apply(parse_interval)

    df['group'] = df.apply(lambda row: assign_bin_by_start(row['y_min'], row['x_min']), axis=1)

    dropped_rows = df['group'].isna().sum()

    # Keep only rows that fall into bins (some rows may still be invalid or empty)
    df = df[df['group'].notna()]

    df['(Y interval, X service)'] = df['group']
    df.drop(columns=['y_min', 'y_max', 'x_min', 'x_max', 'group'], inplace=True) 
    return df



#1
def queu_statistic_test(queue_intervals_df: pd.DataFrame, cols_to_drop) -> pd.DataFrame:
    df = queue_intervals_df.drop(columns=[col for col in cols_to_drop if col in queue_intervals_df.columns])
    print(df)
    return get_df_wilcoxon_stats(df)


#2
def get_df_wilcoxon_stats(df : pd.DataFrame) -> pd.DataFrame:
    result = []
    grouped = df.groupby('(Y interval, X service)')[['avg_queue_policy1', 'avg_queue_policy2']]

    for group_key, group_df in grouped:
        avg_queue_list1 = group_df['avg_queue_policy1'].tolist()
        avg_queue_list2 = group_df['avg_queue_policy2'].tolist()
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
   

def main():
    cols_to_drop = ["mean_improvement", "win_by_CI", "win_by_Mean", "win_by_Test_statistique", "win_percantage", "win_score"]
    file_path = sys.argv[1]
    sheet_names = ['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']
    df = get_queue_interals_df(file_path, sheet_name=sheet_names[1])
    wilcoxon_df = queu_statistic_test(df, cols_to_drop)
    list_of_column = ["PV < 0.1" , "PV < 0.2" , "PV < 0.3", "PV < 0.4" ]
    pv_signif_col = list_of_column[0]
    ax = get_heatmap_for_queu(wilcoxon_df, pv_signif_col )

if __name__ == '__main__':
    main()