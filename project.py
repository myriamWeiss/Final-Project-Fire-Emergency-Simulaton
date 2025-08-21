from itertools import combinations
import logging
import pandas as pd
import numpy as np

from analysis import run_simulation_with_policies, generate_random_parameters, generate_random_times
from policies import MeanRT, LBR, Percentil_95
from models import Vehicle
from config import NUM_AREA, NUM_PARAMETER_SETS, NUM_REPLICATIONS, SIMULATION_TIME, NUM_SAMPLES
from globals import globs
from wining_scores import  get_win_score_percentage, get_score_and_save_CI, get_statistique_score, save_summarize_results



# Configure logging
logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("runProject")



def runProject(interval_range, service_range, response_range):
    logger.info("Starting full policy comparison simulation...")
    results_parm = []
    for param_set in range(NUM_PARAMETER_SETS):
        globs.set_index += 1
        params = generate_random_parameters(interval_range, service_range, response_range) #no need O.G 
        result = evaluate_parameter_set(param_set, params)
        results_parm.append(result)
    

    final = {}
    for result_param in results_parm:
        for comparison_name, set_result in result_param.items():
            final.setdefault(comparison_name, [])
            final[comparison_name].append(set_result)

    final_dfs = {comparison_name: pd.DataFrame(list_set) for comparison_name, list_set in final.items()}

    results_df = pd.DataFrame(results_parm)
    save_results(results_df, "comprehensive_policy_comparison.xlsx")
    return final_dfs 


def evaluate_parameter_set(param_set, params):
    mean_interarrival_times, mean_service_times, mean_response_times, utils, service_cvs, response_cvs = params

    vehicles = generate_vehicles(mean_interarrival_times, mean_service_times, mean_response_times, service_cvs, response_cvs)
    pre_results = init_param_results(param_set, mean_interarrival_times, mean_service_times, mean_response_times, utils)

    stats = run_replications(vehicles, mean_interarrival_times, mean_service_times, mean_response_times, service_cvs, response_cvs)

    pre_results.update(stats)
    return stats


def generate_vehicles(mean_interarrival_times, mean_service_times, mean_response_times, service_cvs, response_cvs):
    vehicles = [
        Vehicle(j,
                {i: 1 / mean_interarrival_times[i][j] for i in range(NUM_AREA)},
                {i: 1 / mean_service_times[i][j] for i in range(NUM_AREA)},
                {i: 1 / mean_response_times[i][j] for i in range(NUM_AREA)},
                {i: service_cvs[i][j] for i in range(NUM_AREA)},
                {i: response_cvs[i][j] for i in range(NUM_AREA)})
        for j in range(NUM_AREA)
    ]
    return vehicles


def init_param_results(param_set, mean_interarrival, mean_service, mean_response, utils):
    result = {'param_set': param_set + 1, 'utilizations': utils}
    for i in range(NUM_AREA):
        for j in range(NUM_AREA):
            result[f'interarrival_{i}_{j}'] = mean_interarrival[i][j]
            result[f'service_{i}_{j}'] = mean_service[i][j]
            result[f'response_{i}_{j}'] = mean_response[i][j]
    return result


def run_replications(vehicles, mean_interarrival, mean_service, mean_response, service_cvs, response_cvs):
    globs.replication_index = 0
    our_policy = LBR()
    other_policies = [Percentil_95(), MeanRT()]
    all_policies = other_policies + [our_policy]
    policy_rep_results = {type(p).__name__: [] for p in all_policies}

    for rep in range(NUM_REPLICATIONS):
        globs.replication_index += 1
        precomputed = generate_random_times(mean_interarrival, mean_service, mean_response, service_cvs, response_cvs, NUM_SAMPLES)
        results = run_simulation_with_policies(vehicles, precomputed, SIMULATION_TIME, all_policies)
        for policy, result in zip(all_policies, results):
            policy_rep_results[type(policy).__name__].append(result) #dict 2 key : name_polici and result_polici
    
    summarized_results = {} #dict name_vs_policy and result all kind scores data
    for p1, p2 in combinations(all_policies, 2):
        p1_name = type(p1).__name__
        p2_name = type(p2).__name__
        p1_results = policy_rep_results[p1_name]
        p2_results = policy_rep_results[p2_name]
        name = f"{p1_name} vs {p2_name}"
        summarized_results[name] = summarize_replication_results(p1_results, p2_results, name)

    return summarized_results

def summarize_replication_results(p1_results, p2_results, name_p1_vs_p2):
    policy1_percentiles, policy2_percentiles = [], []
    policy1_mean_RT, policy2_mean_RT = [], []
    policy1_queues, policy2_queues = [], []
    rel_improvements = []
    policy1_loads, policy2_loads = [], []
    
    for p1_result, p2_result in zip(p1_results, p2_results):
        percentile_p1, percentile_p2 = p1_result['percentile_90'], p2_result['percentile_90']
        mean1, mean2 = p1_result['mean_RT'], p2_result['mean_RT']

        #list of 90_ & mean & scores
        policy1_percentiles.append(float(percentile_p1))
        policy2_percentiles.append(float(percentile_p2))

        policy1_mean_RT.append(mean1)
        policy2_mean_RT.append(mean2)
        
        rel_improvements.append((percentile_p1 - percentile_p2) / percentile_p1 * 100)
        
        policy1_queues.append(p1_result['max_queue'])
        policy2_queues.append(p2_result['max_queue'])

        policy1_loads.append(p1_result['system_load'])
        policy2_loads.append(p2_result['system_load'])

    #save list 90th 
    dict_percentile = {'P1_percentile' : policy1_percentiles,'P2_percentile' : policy2_percentiles }
    save_summarize_results(dict_percentile, name_p1_vs_p2, 'List_90.xlsx')

    #win by improvement
    win_score , win_percantage = get_win_score_percentage(rel_improvements)

    #get Confidence Interval Score
    CI_90_score_and_teko = get_score_and_save_CI(policy1_percentiles,policy2_percentiles,name_p1_vs_p2, 'CI_result.xlsx')
    CI_mean_score_and_teko = get_score_and_save_CI(policy1_mean_RT, policy2_mean_RT, name_p1_vs_p2, 'Mean_result.xlsx')

    #get Test Statistic Score
    statistique_score = get_statistique_score(policy1_percentiles, policy2_percentiles, name_p1_vs_p2, 'Test_Statistic.xlsx')


    summarize_results = {
        'avg_policy1_load': np.mean(policy1_loads),
        'avg_policy2_load': np.mean(policy2_loads),
        'avg_policy1_queue': np.mean(policy1_queues),
        'avg_policy2_queue': np.mean(policy2_queues),
        'mean_improvement': np.mean(rel_improvements),
        'win_percentage': win_percantage,
        'win_score' : win_score,
        'CI_score_90' : CI_90_score_and_teko[0],
        'CI_teko_score_90' : CI_90_score_and_teko[1],
        'CI_score_mean' : CI_mean_score_and_teko[0],
        'CI_teko_score_mean' : CI_mean_score_and_teko[1],
        'Test_statistique_score' : statistique_score 
    }
    save_summarize_results(summarize_results, name_p1_vs_p2, 'parameter_result.xlsx')
    return summarize_results



def save_results(results_df, path):
    results_df.to_excel(path, index=False)
    logger.info(f"Results saved to: {path}")


  
