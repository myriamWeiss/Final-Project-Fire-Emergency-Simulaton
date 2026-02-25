from itertools import combinations
import logging
import pandas as pd
import numpy as np
import os
from typing import Set, Dict, Optional, List, Tuple,Any
from models import Vehicle
from config import NUM_AREA, NUM_PARAMETER_SETS, NUM_REPLICATIONS, SIMULATION_TIME, NUM_SAMPLES
from globals import globs
from wining_scores import count_binary_score_for_set, save_summarize_results
#from plots import generate_policy_comparison_plots
from wining_scores import get_statistique_score
from project import summarize_replication_results
from generate_empirical_time import generate_empirical_times, generate_empirical_vehicles
from empirical_policies import LBR_EMP, MinP95_EMP, EmpiricalDispatch
from analysis import run_simulation_with_policies


# Configure logging
logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("runProject")

# ---------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------
def empirical_project():
    logger.info("Starting full policy comparison simulation...")

    RESULTS_XLSX = "replication_results.xlsx"
    check_if_exist_file_result(RESULTS_XLSX )
 
    results_parm = []
    for param_set in range(NUM_PARAMETER_SETS):
        globs.set_index = param_set + 1  # keep context in the output rows
        result = run_empirical_replications()
        results_parm.append(result)

    # If you still need a returned object for further Python processing:
    final = {}
    for result_param in results_parm:
        for comparison_name, set_result in result_param.items():
            final.setdefault(comparison_name, [])
            final[comparison_name].append(set_result)

    final_dfs = {comparison_name: pd.DataFrame(list_set) for comparison_name, list_set in final.items()}

    #from OFek
    # generate_policy_comparison_plots(
    #     xlsx_path=RESULTS_XLSX,
    #     sheet="results",
    #     output_dir="plots"
    # )

    return final_dfs


def check_if_exist_file_result(name_file):
    try:
        if os.path.exists(name_file):
            os.remove(name_file)
            logger.info(f"Deleted previous results file: {name_file}")
    except Exception as e:
        logger.warning(f"Could not delete {name_file} (is it open?): {e}")



# ---------------------------------------------------
# Replications runner
# ---------------------------------------------------
def run_empirical_replications():
    globs.replication_index = 0
    our_policy = LBR_EMP() 
    other_policies = [EmpiricalDispatch(), MinP95_EMP()] 
    all_policies = other_policies + [our_policy]
    policy_rep_results = {type(p).__name__: [] for p in all_policies}

    for rep in range(NUM_REPLICATIONS):
        globs.replication_index += 1
        precomputed = generate_empirical_times(NUM_SAMPLES)  #from Ofek
        vehicles = generate_empirical_vehicles(precomputed) #from Ofek
        results = run_simulation_with_policies(vehicles, precomputed, SIMULATION_TIME, all_policies) #same 
        for policy, result in zip(all_policies, results):
            policy_rep_results[type(policy).__name__].append(result)

    summarized_results = {}
    for p1, p2 in combinations(all_policies, 2):
        p1_name = type(p1).__name__
        p2_name = type(p2).__name__
        p1_results = policy_rep_results[p1_name]
        p2_results = policy_rep_results[p2_name]
        name = f"{p1_name} vs {p2_name}"
        summarized_results[name] = summarize_replication_results(p1_results, p2_results, name)

    return summarized_results


