import os
import datetime
from globals import globs
import pandas as pd
import cProfile, pstats
# Project file :
from excel_file import combine_csv_files
from experiment import RegularMode, EmpiricalMode
from results_project import get_final_results
from project import start_project
from heatMap import  get_heatMap

def main():
   # Chose with the '#' :

   run_simulation_and_heat_map() #run the simulaton

   #run_empirical_project()
   #hrun_heat_map() #run the heatmap
   
 
   
def run_heat_map():
   folder_path = os.path.dirname(os.path.abspath(__file__))
   copies_results__path = os.path.join(folder_path, 'result_project.xlsx')
   while not os.path.exists(copies_results__path):
      print("\n❌ The result file dont exist in fire_emergency_OG folder.❌ \nPllease copy and past the excel result_project.xlsx in the folder project \nfire_emergency_OG - the folder with the codes file\n")
      return 
   ax =get_heatMap(copies_results__path)
   return 

def run_simulation_and_heat_map():
   mode = RegularMode()
   make_new_folder()
   profiler = cProfile.Profile()
   profiler.enable()
   results_file_name = get_final_results(mode) #in the folder created in the run
   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.strip_dirs()
   stats.sort_stats('cumtime').print_stats(20)
   results_file_path = os.path.join(globs.folder_path, results_file_name)
   ax =get_heatMap(results_file_path)

def run_empirical_project():
   mode = EmpiricalMode()
   make_new_folder()
   start_project(mode)
   # results_file_name = get_final_results() #in the folder created in the run
   # results_file_path = os.path.join(globs.folder_path, results_file_name)
   #ax =get_heatMap(results_file_path)


def make_new_folder():
   base_folder = os.getcwd()
   date_folder = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
   full_folder_path = os.path.join(base_folder, date_folder)
   os.makedirs(full_folder_path, exist_ok=True)
   globs.folder_path = full_folder_path
    
   
if __name__ == "__main__":
   print('hey')
   main()
