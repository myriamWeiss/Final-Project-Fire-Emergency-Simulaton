import numpy as np
from itertools import combinations
#files
from analysis import save_summarize_results

def analyze_result_simulation(rt_result_simulation: list, policy_name):
    return {
        "policy_name": policy_name, 
        "num_of_event" : len(rt_result_simulation),
        "Avg_RT" : np.mean(rt_result_simulation),
        "Percentile_RT" : np.percentile(rt_result_simulation,90),
        "Min_RT": np.min(rt_result_simulation),
        "Max_RT" : np.max(rt_result_simulation),
        "Std_RT" : np.std(rt_result_simulation, ddof=1)
        }

def fusion_policies_analyze(rep_analyze_result, all_policies):
    summarized_results = {} #dict name_vs_policy and result all kind scores data
    for p1, p2 in combinations(all_policies, 2):
        p1_name = type(p1).__name__
        p2_name = type(p2).__name__

        p1_results = rep_analyze_result[p1_name]  # list of dicts
        p2_results = rep_analyze_result[p2_name]

        # 🔥 aggregate per policy (THIS is what you add)
        p1_agg = aggregate_results(p1_results)
        p2_agg = aggregate_results(p2_results)

        name = f"{p1_name} vs {p2_name}"

        summarized_results[name] = combined_result(p1_agg, p2_agg, name)


def aggregate_results(results_list):
    keys = results_list[0].keys()
    return {
        k: np.mean([r[k] for r in results_list if k != "policy_name"])
        for k in keys if k != "policy_name"
    }

def combined_result(p1_results, p2_results, name_p1_vs_p2):
    combined = {
    f"{k}_p1": v for k, v in p1_results.items() if k != "policy_name"
    } | {
    f"{k}_p2": v for k, v in p2_results.items() if k != "policy_name"
    }
    save_summarize_results(combined, name_p1_vs_p2, 'Analyze_set.xlsx')
    return combined
