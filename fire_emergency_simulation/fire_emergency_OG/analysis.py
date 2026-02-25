import numpy as np
import pandas as pd
from scipy import stats
import time
import logging
from typing import Dict, Tuple, List, Any
from globals import globs
from models import Vehicle, PrecomputedTimes, ArrivalMode
from simulation import Simulation
from policies import DispatchPolicy
from config import (NUM_AREA, CV_SERVICE_RANGE, CV_RESPONSE_RANGE, EPSILON)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("analysis")


def get_lognormal_params(mean: float, cv: float) -> Tuple[float, float]:
    sigma = np.sqrt(np.log(1 + cv ** 2))
    mu = np.log(mean) - 0.5 * sigma ** 2
    return mu, sigma

def save_summarize_results(summary_dict, sheet_name, path) -> pd.DataFrame:
    results_df = pd.DataFrame([summary_dict])
    results_df.insert(0, '(Param, SET)_index', 
                  '({0}, {1})'.format(globs.set_index, globs.replication_index))
    results_df.insert(0, '(Y interval, X service)', 
                  '({0}, {1})'.format(globs.interval_index, globs.total_services_index))

    file_path = os.path.join(globs.folder_path, path)
    if os.path.exists(file_path): 
        with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            try:
                existing_df = pd.read_excel(file_path, sheet_name=sheet_name)
                combined_df = pd.concat([existing_df, results_df], ignore_index=True)
            except ValueError: # creating new Sheet if needed
                combined_df = results_df

            combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        # אם הקובץ לא קיים, צור Sheet ראשון
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            results_df.to_excel(writer, sheet_name=sheet_name, index=False)



def run_simulation_with_policies(vehicles: List[Vehicle], precomputed_times: PrecomputedTimes,
                               simulation_time: float, policies: List[DispatchPolicy],   arrival_mode: ArrivalMode = ArrivalMode.REGULAR ) -> List[Dict[str, Any]]:
    """
    Run simulations with multiple policies using the same random numbers.  
    Returns:
        List of dictionaries containing results for each policy
    """
    results = []
    global set_index, replication_index

    for policy in policies:
        policy_name = type(policy).__name__
        logger.info(f"Policy : {policy_name} || Y: {globs.interval_index}, X: {globs.total_services_index}")
        logger.info(f"SET {globs.set_index} || REP {globs.replication_index}")
        sim = Simulation(vehicles, policy, precomputed_times, arrival_mode=arrival_mode)
        sim.run(simulation_time)
        
        # Extract key metrics
        if sim.response_times:
            percentile_90 = np.percentile(sim.response_times, 90)
            mean_RT = np.mean(sim.response_times)
        else:
            percentile_90 = np.inf
            mean_RT = np.inf

        system_load = sim.total_service_time / (NUM_AREA * simulation_time)
        
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
        
    return results

#go to experiment.py
def generate_random_parameters(interval_range: tuple, service_range: tuple, response_range: tuple) -> Tuple:
    """
    Generate a set of random parameters for the simulation without checking the utilization constraint.
    
    Returns:
        Tuple containing:
        - mean_interarrival_times: Dictionary of interarrival times by area and vehicle.
        - mean_service_times: Dictionary of service times by area and vehicle.
        - mean_response_times: Dictionary of response times by area and vehicle.
        - service_cvs: Dictionary of service time coefficients of variation.
        - response_cvs: Dictionary of response time coefficients of variation.
    """
    # Generate random parameters for interarrival, service, and response times
    mean_interarrival_times = {
        i: {j: np.random.uniform(*interval_range)
            for j in range(NUM_AREA)}
        for i in range(NUM_AREA)
    }
    mean_service_times = {
        i: {j: np.random.uniform(*service_range)
            for j in range(NUM_AREA)}
        for i in range(NUM_AREA)
    }
    mean_response_times = {
        i: {j: np.random.uniform(*response_range)
            for j in range(NUM_AREA)}
        for i in range(NUM_AREA)
    }
    
    # Generate coefficients of variation for service and response times
    service_cvs = {
        i: {j: np.random.uniform(*CV_SERVICE_RANGE)
            for j in range(NUM_AREA)}
        for i in range(NUM_AREA)
    }
    response_cvs = {
        i: {j: np.random.uniform(*CV_RESPONSE_RANGE)
            for j in range(NUM_AREA)}
        for i in range(NUM_AREA)
    }

    utils = 0 #no need for utilization
    
    return (mean_interarrival_times, mean_service_times, mean_response_times, utils,  service_cvs, response_cvs)



def generate_times_simulation(mean_interarrival_times: Dict, mean_service_times: Dict,
                         mean_response_times: Dict, service_cvs: Dict[int, Dict[int, float]],
                        response_cvs: Dict[int, Dict[int, float]],
                         num_events: int) -> PrecomputedTimes:
    """
    Generate all random times upfront for fair comparison.
    
    Args:
        mean_interarrival_times: Dictionary of interarrival times by area and vehicle
        mean_service_times: Dictionary of service times by area and vehicle
        mean_response_times: Dictionary of response times by area and vehicle
        num_events: Number of events to generate
        
    Returns:
        PrecomputedTimes object containing all generated times
    """
    start_time = time.time()
    arrivals = {}
    services = {}
    responses = {}

    for area_id in range(NUM_AREA):
        for vehicle_id in range(NUM_AREA):
            # Generate interarrival times
            lambda_rate = 1 / mean_interarrival_times[area_id][vehicle_id]
            arrivals[(area_id, vehicle_id)] = list(np.random.exponential(
                1 / lambda_rate, num_events))

            # Generate service times
            mean_service = mean_service_times[area_id][vehicle_id]
            cv_service = service_cvs[area_id][vehicle_id]
            mu_s, sigma_s = get_lognormal_params(mean_service, cv_service)
            services[(area_id, vehicle_id)] = np.random.lognormal(mu_s, sigma_s, num_events)

            # Generate response times
            mean_response = mean_response_times[area_id][vehicle_id]
            cv_response = response_cvs[area_id][vehicle_id]
            mu_r, sigma_r = get_lognormal_params(mean_response, cv_response)
            responses[(area_id, vehicle_id)] = list(np.random.lognormal(
                mu_r, sigma_r, num_events))

    logger.info(f"Random times generation took: {time.time() - start_time:.2f} seconds")
    return PrecomputedTimes(arrivals, services, responses)