from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np
import time
# Project file
from models import ArrivalMode, Vehicle, PrecomputedTimes
from policies import DispatchPolicy
from config import (NUM_AREA, CV_SERVICE_RANGE, CV_RESPONSE_RANGE, EPSILON, NUM_SAMPLES)
from analysis import get_lognormal_params

@dataclass
class Experiment():
        name : str
        arrival_mode = ArrivalMode
        policies = List[DispatchPolicy]


class RegularExperiment(Experiment):
    """
    Regular (theoretical) experiment:
    - arrival_mode = REGULAR
    - precomputed_times generated from known distributions
    - vehicles ij's service time and RT are generate from known distributions
    """
    def __init__(self, policies:List[DispatchPolicy], vehicles : List[Vehicle]):
        super().__init__(name="regular", arrival_mode = ArrivalMode.REGULAR, policies = policies)
        self.vehicles = vehicles

    # 1- Parameter
    def generate_time_parameters(self, interval_range: tuple, service_range: tuple, response_range: tuple) -> Tuple:
        """
        Generate a set of parameters (miu, lamda..) for the simulation times.
        
        Returns:
            Tuple containing:
            - mean_interarrival_times: Dictionary of interarrival times by area and vehicle.
            - mean_service_times: Dictionary of service times by area and vehicle.
            - mean_response_times: Dictionary of response times by area and vehicle.
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

    # 2- Vehicles
    def generate_vehicles(self, time_parameter_set):
        
        mean_interarrival_times, mean_service_times, mean_response_times, utils, service_cvs, response_cvs = time_parameter_set

        vehicles = [
            Vehicle(j,
                    {i: 1 / mean_interarrival_times[i][j] for i in range(NUM_AREA)},
                    {i: 1 / mean_service_times[i][j] for i in range(NUM_AREA)},
                    {i: 1 / mean_response_times[i][j] for i in range(NUM_AREA)},
                    {i: service_cvs[i][j] for i in range(NUM_AREA)},
                    {i: response_cvs[i][j] for i in range(NUM_AREA)}, 
                    None)
            for j in range(NUM_AREA)
        ]
        return vehicles

    def generate_times_simulation(time_parameter_set) -> PrecomputedTimes:
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
        num_events = NUM_SAMPLES
        mean_interarrival_times, mean_service_times, mean_response_times, utils, service_cvs, response_cvs = time_parameter_set

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
        return PrecomputedTimes(arrivals, services, responses)


class EmpericalExperiment(Experiment):
    """
    Empirical experiment:
    - arrival_mode = EMPIRICAL (arrival stream per area)
    - precomputed_times generated from empirical distributions/CSV
    - vehicles often generated based on empirical data
    """
    def __init__(self, policies:List[DispatchPolicy], vehicles : List[Vehicle]):
        super().__init__(name="emperical", arrival_mode = ArrivalMode.EMPIRICAL, policies = policies)
        self.vehicles = vehicles

    def generate_times_simulation(time_parameter_set):
        """
        Generate  times from distribution.
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
        # times_dict = prepare_empirical_dispatch("empirical_dispatch_distribution.csv")
        times_dict = generate_empirical_samples_from_pmf('./fire_emergency_OG/empirical_pmf.csv')
        inter_by_area = generate_interarrival_samples_by_fdcall("./fire_emergency_OG/empirical_pmf_by_fd_call.csv")

        for area_id in range(NUM_AREA):
            # single arrival stream per area (use vehicle_id == 0 as the stream key)
            arrivals[(area_id, 0)] = inter_by_area["INTER_ARRIVAL_MIN"][area_id]

            for vehicle_id in range(NUM_AREA):

                # Generate service times
                services[(area_id, vehicle_id)] = times_dict["SERVICE_MIN"][(area_id, vehicle_id)] #list - generate num_of_events : service time for [area,vehicle]

                # Generate response times
                responses[(area_id, vehicle_id)] = times_dict["RESPONSE_TIME_MIN"][(area_id, vehicle_id)] #list - generate num_of_events : response time for [area,vehicle]

        return PrecomputedTimes(arrivals, services, responses)