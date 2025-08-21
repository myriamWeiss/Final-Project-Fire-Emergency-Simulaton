from heatMap import  get_heatmap_for_queu, get_heatmap_for_wins_percentage
from results_project import get_final_results
import os
import datetime
from globals import globs
import pandas as pd
from excel_file import combine_csv_files

def main():
   # ------------ Run Simulation ------------ 
   make_new_folder()
   get_final_results()

   # ------------ Choose HeatMAp parmater -------------
   #1. choose the pairs of policies
   
   sheet_names = ['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']
   list_of_column = "win_percentage", "avg_queue_policy2", "avg_queue_policy1", "avg_ratio_2/1", "mean_improvement"

  


   # ------------ Combin CSV result --------------
   #combine_csv_files()
   combined_df = pd.read_excel('./merged_output.xlsx',sheet_name= sheet_names[1])

   # ------------ Build HeatMap -------------
   percentage_score_str = "win_by_Test_statistique"
   #ax = get_heatmap_for_wins_percentage(combined_df, percentage_score_str )

   queue_size_str = list_of_column[3]
   ax = get_heatmap_for_queu(combined_df, queue_size_str)




def make_new_folder():
   base_folder = os.getcwd()
   date_folder = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
   full_folder_path = os.path.join(base_folder, date_folder)
   os.makedirs(full_folder_path, exist_ok=True)
   globs.folder_path = full_folder_path
    
   
if __name__ == "__main__":
    main()
