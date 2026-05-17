from itertools import combinations
import logging
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
import os
# Project file
from config import NUM_AREA, NUM_VEHICLE, NUM_PARAMETER_SETS, NUM_REPLICATIONS, SIMULATION_TIME, NUM_SAMPLES
from policies import MeanRT, LBR, Percentil_95
from models import Vehicle, PrecomputedTimes, ArrivalMode
from policies import DispatchPolicy
from simulation import Simulation
from globals import globs
from wining_scores import  get_win_score_percentage, get_statistique_score
from analysis import save_summarize_results
from experiment import BaseExperimentMode
from analyzeKoubia import analyze_result_simulation, fusion_policies_analyze #analyze


# Configure logging
logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("project")


def start_project(interval_range, service_range, response_range, mode:BaseExperimentMode):
    logger.info("Starting full policy comparison simulation...")

    # Get result of the Set
    sets_results = get_results_of_sets(interval_range, service_range, response_range, mode)

    final = {}
    for result in sets_results:
        for comparison_name, set_result in result.items():
            final.setdefault(comparison_name, [])
            final[comparison_name].append(set_result)

    final_dfs = {comparison_name: pd.DataFrame(list_set) for comparison_name, list_set in final.items()}
    return final_dfs 

def get_results_of_sets(interval_range, service_range, response_range, mode:BaseExperimentMode) -> list:
    sets_results = []
    for index_set in range(NUM_PARAMETER_SETS):
        globs.set_index += 1

        if mode.arrival_mode == ArrivalMode.REGULAR:
            # Initiliaze parameter
            time_parameter_set = mode.generate_time_parameters(interval_range, service_range, response_range) 
            # Create Vehicle + generate Servie & Response time
            vehicles = mode.generate_vehicles(time_parameter_set)
              
        else:
            vehicles = None
            time_parameter_set = None

        # Run Replications
        replications_result = run_replications(vehicles, time_parameter_set, mode)
        
        sets_results.append(replications_result)
    return sets_results


def run_replications(vehicles: list, time_parameter_set, mode:BaseExperimentMode):
    globs.replication_index = 0

    # Policy
    our_policy = mode.our_policy
    other_policies = mode.other_policies
    all_policies = other_policies + [our_policy]
    policy_rep_results = {type(p).__name__: [] for p in all_policies}
    rep_analyze_result = {type(p).__name__: [] for p in all_policies}

    for rep in range(NUM_REPLICATIONS):
        globs.replication_index += 1
        precomputed = mode.generate_precomputed_times(time_parameter_set)
        if  mode.arrival_mode == ArrivalMode.EMPIRICAL:
            vehicles = mode.generate_vehicles(precomputed)
        results, analyze_result = run_simulation_with_policies(vehicles, precomputed, all_policies, mode)
        for policy, result in zip(all_policies, results):
            policy_rep_results[type(policy).__name__].append(result) #dict 2 key : name_polici and result_polici
            policy_name = type(policy).__name__
            if analyze_result is not None: #analyze
                rep_analyze_result[policy_name].append(analyze_result[policy_name])
        
    fusion_policies_analyze(rep_analyze_result, all_policies) #analyze

    summarized_results = {} #dict name_vs_policy and result all kind scores data
    for p1, p2 in combinations(all_policies, 2):
        p1_name = type(p1).__name__
        p2_name = type(p2).__name__
        p1_results = policy_rep_results[p1_name]
        p2_results = policy_rep_results[p2_name]
        name = f"{p1_name} vs {p2_name}"
        summarized_results[name] = summarize_replication_results(p1_results, p2_results, name)

    return summarized_results


def run_simulation_with_policies(vehicles: List[Vehicle], precomputed_times: PrecomputedTimes, policies: List[DispatchPolicy], mode:BaseExperimentMode ) -> List[Dict[str, Any]]:
    """
    Run simulations with multiple policies using the same random numbers.  
    Returns:
        List of dictionaries containing results for each policy
    """
    simulation_time = SIMULATION_TIME
    results = []
    arrival_mode = mode.arrival_mode
    analyze_result = {}

    for policy in policies:
        policy_name = type(policy).__name__
        logger.info(f"Policy : {policy_name} || Y: {globs.interval_index}, X: {globs.total_services_index}")
        logger.info(f"SET {globs.set_index} || REP {globs.replication_index}")

        sim = Simulation(vehicles, policy, precomputed_times, arrival_mode=arrival_mode)
        sim.run(simulation_time)
        
        # Extract key metrics
        if sim.response_times: 
            analyze_result[policy_name] = analyze_result_simulation(sim.response_times, policy_name)#analyze
            percentile_90 = np.percentile(sim.response_times, 90)
            mean_RT = np.mean(sim.response_times)
        else:
            percentile_90 = np.inf
            mean_RT = np.inf

        system_load = sim.total_service_time / (len(vehicles) * simulation_time)
        
        results.append({
            'policy': policy_name,
            'percentile_90': percentile_90,
            'mean_RT' : mean_RT,
            'avg_queue': sim.avg_queue, 
            'max_queue': sim.max_queue_size,
            'total_queue_size' : sim.delayed_event,
            'system_load': system_load,
            'total_services': sim.total_services
        })
        #if not analyze :
        #analyze_result = None
    return results, analyze_result

def summarize_replication_results(p1_results, p2_results, name_p1_vs_p2):
    policy1_percentiles, policy2_percentiles = [], []
    policy1_mean_RT, policy2_mean_RT = [], []
    policy1_avg_Q_size, policy2_avg_Q_size = [], []
    policy1_queues, policy2_queues = [], []
    rel_improvements = []
    policy1_loads, policy2_loads = [], []
    
    for p1_result, p2_result in zip(p1_results, p2_results):
        percentile_p1, percentile_p2 = p1_result['percentile_90'], p2_result['percentile_90']
        mean1, mean2 = p1_result['mean_RT'], p2_result['mean_RT']
        avg_queue_size_p1 , avg_queue_size_p2 = p1_result['avg_queue'], p2_result['avg_queue']

        #list of 90_ & mean & scores
        policy1_percentiles.append(float(percentile_p1))
        policy2_percentiles.append(float(percentile_p2))

        policy1_mean_RT.append(mean1)
        policy2_mean_RT.append(mean2)

        policy1_avg_Q_size.append(avg_queue_size_p1)
        policy2_avg_Q_size.append(avg_queue_size_p2)

        rel_improvements.append((percentile_p1 - percentile_p2) / percentile_p1 * 100) #no need
        
        policy1_queues.append(p1_result['max_queue'])
        policy2_queues.append(p2_result['max_queue'])

        policy1_loads.append(p1_result['system_load'])
        policy2_loads.append(p2_result['system_load'])

    #save list parameter of replicatoin : percentile, total queuu size 
    dict_para_repl= {'P1_percentile' : policy1_percentiles,'P2_percentile' : policy2_percentiles, 'P1_Queue_size' : policy1_avg_Q_size, 'P2_Queue_size' : policy2_avg_Q_size }
    save_summarize_results(dict_para_repl, name_p1_vs_p2, 'List_paramater_from_Replication.xlsx')

    #get Test Statistic Score
    statistique_score_RT = get_statistique_score(policy1_percentiles, policy2_percentiles, name_p1_vs_p2, 'Wilcoxon_result_RT.xlsx')
    statistique_score_Queue = get_statistique_score(policy1_avg_Q_size, policy2_avg_Q_size, name_p1_vs_p2, 'Wilcoxon_result_Queue.xlsx') #change

    summarize_results = {
        'RT_0.1_pv_wilc' : statistique_score_RT['alpha = 0.1'],
        'RT_0.2_pv_wilc' : statistique_score_RT['alpha = 0.2'],
        'RT_0.3_pv_wilc' : statistique_score_RT['alpha = 0.3'],
        'RT_0.4_pv_wilc' : statistique_score_RT['alpha = 0.4'],
        'Qu_0.1_pv_wilc' : statistique_score_Queue['alpha = 0.1'],
        'Qu_0.2_pv_wilc' : statistique_score_Queue['alpha = 0.2'],
        'Qu_0.3_pv_wilc' : statistique_score_Queue['alpha = 0.3'],
        'Qu_0.4_pv_wilc' : statistique_score_Queue['alpha = 0.4'],
        'mean_improvement_perc': np.mean(rel_improvements),
        'avg_policy1_load': np.mean(policy1_loads),
        'avg_policy2_load': np.mean(policy2_loads),
        'avg_policy1_Max_queue': np.mean(policy1_queues),
        'avg_policy2_Max_queue': np.mean(policy2_queues),
    }
    save_summarize_results(summarize_results, name_p1_vs_p2, 'parameter_result_for_set.xlsx')
    return summarize_results

# ---------------------------------------------------
# From Emperical file
# ---------------------------------------------------

def check_if_exist_file_result(name_file):
    try:
        if os.path.exists(name_file):
            os.remove(name_file)
            logger.info(f"Deleted previous results file: {name_file}")
    except Exception as e:
        logger.warning(f"Could not delete {name_file} (is it open?): {e}")

# def from_Ofek():
#     RESULTS_XLSX = "replication_results.xlsx"
#     check_if_exist_file_result(RESULTS_XLSX )
#     generate_policy_comparison_plots(
#         xlsx_path=RESULTS_XLSX,
#         sheet="results",
#         output_dir="plots"
#     )