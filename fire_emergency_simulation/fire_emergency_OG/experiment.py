from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Tuple, List, Dict
import numpy as np
import pandas as pd
from scipy import stats
import time
import logging
import os

# Project file
from models import Vehicle, PrecomputedTimes, ArrivalMode
from config import NUM_SAMPLES, NUM_SAMPLES, NUM_VEHICLE, NUM_AREA, CV_SERVICE_RANGE, CV_RESPONSE_RANGE, EPSILON
from analysis import get_lognormal_params
from generate_empirical_time import (generate_empirical_times, generate_empirical_vehicles)
from globals import globs
from simulation import Simulation
from empirical_policies import LBR_EMP, EmpiricalDispatch, MinP95_EMP
from policies import LBR, MeanRT, Percentil_95



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("experiment")

class BaseExperimentMode(ABC):
    """
    Common interface for all experiment modes.
    Regular mode or empirical mode. It will only call the same methods.
    """

    @property
    @abstractmethod
    def arrival_mode(self) -> ArrivalMode:
        """Return the arrival mode used by Simulation."""
        pass

    @property
    @abstractmethod
    def our_policy(self):
        pass

    @property
    @abstractmethod
    def other_policies(self):
        pass

    @abstractmethod
    def generate_time_parameters(
        self,
        interval_range: tuple | None = None,
        service_range: tuple | None = None,
        response_range: tuple | None = None,
    ) -> Any:
        """
        Build the raw parameters needed by this mode.
        The internal structure can be different between modes.
        """
        pass

    @abstractmethod
    def generate_vehicles(self, time_parameters):
        """Build the vehicles for this mode."""
        pass

    @abstractmethod
    def generate_precomputed_times(self, time_parameters: Any):
        """Build the precomputed times for this mode."""
        pass



class RegularMode(BaseExperimentMode):
    
    """
    Regular mode:
    - generates random parameters from known distributions
    - generates regular vehicles
    - generates regular precomputed arrivals / service / response times
    """

    @property
    def arrival_mode(self) -> ArrivalMode:
        return ArrivalMode.REGULAR
    
    @property
    def our_policy(self):
        return LBR()
    
    @property
    def other_policies(self):
        return [Percentil_95(), MeanRT()]
    
        

    def generate_time_parameters(self, interval_range: tuple, service_range: tuple, response_range: tuple) :
        """
        Generate a set of random parameters for the simulation with known distibution.
        
        Returns:
            Tuple containing:
            - mean_interarrival_times: Dictionary of interarrival times by area and vehicle.
            - mean_service_times: Dictionary of service times by area and vehicle.
            - mean_response_times: Dictionary of response times by area and vehicle.
            - service_cvs: Dictionary of service time coefficients of variation.
            - response_cvs: Dictionary of response time coefficients of variation.
        """
        if interval_range is None or service_range is None or response_range is None:
            raise ValueError(
                "RegularMode requires interval_range, service_range, and response_range"
            )

        # i=area_id | j=vehicle_id 
        # Generate random parameters for interarrival, service, and response times
        mean_interarrival_times = {
            i: {j: np.random.uniform(*interval_range)
                for j in range(NUM_VEHICLE)}
            for i in range(NUM_AREA)
        }
        mean_service_times = {
            i: {j: np.random.uniform(*service_range)
                for j in range(NUM_VEHICLE)}
            for i in range(NUM_AREA)
        }
        mean_response_times = {
            i: {j: np.random.uniform(*response_range)
                for j in range(NUM_VEHICLE)}
            for i in range(NUM_AREA)
        }
        
        # Generate coefficients of variation for service and response times
        service_cvs = {
            i: {j: np.random.uniform(*CV_SERVICE_RANGE)
                for j in range(NUM_VEHICLE)}
            for i in range(NUM_AREA)
        }
        response_cvs = {
            i: {j: np.random.uniform(*CV_RESPONSE_RANGE)
                for j in range(NUM_VEHICLE)}
            for i in range(NUM_AREA)
        }

        utils = 0 #no need for utilization
        
        return (mean_interarrival_times, mean_service_times, mean_response_times, utils,  service_cvs, response_cvs)

    def generate_vehicles(self, time_parameters):
        (
            mean_interarrival_times,
            mean_service_times,
            mean_response_times,
            utils,
            service_cvs,
            response_cvs,
        ) = time_parameters
                
        vehicles = [
        Vehicle(j,
                {i: 1 / mean_interarrival_times[i][j] for i in range(NUM_AREA)},
                {i: 1 / mean_service_times[i][j] for i in range(NUM_AREA)},
                {i: 1 / mean_response_times[i][j] for i in range(NUM_AREA)},
                {i: service_cvs[i][j] for i in range(NUM_AREA)},
                {i: response_cvs[i][j] for i in range(NUM_AREA)})
        for j in range(NUM_VEHICLE)
        ]
        return vehicles
    

    def generate_precomputed_times(self, time_parameters):
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
        (
            mean_interarrival_times,
            mean_service_times,
            mean_response_times,
            utils,
            service_cvs,
            response_cvs,
        ) = time_parameters

        start_time = time.time()
        arrivals = {}
        services = {}
        responses = {}

        for area_id in range(NUM_AREA):
            for vehicle_id in range(NUM_VEHICLE):
                # Generate interarrival times
                lambda_rate = 1 / mean_interarrival_times[area_id][vehicle_id]
                arrivals[(area_id, vehicle_id)] = list(np.random.exponential(
                    1 / lambda_rate, NUM_SAMPLES))

                # Generate service times
                mean_service = mean_service_times[area_id][vehicle_id]
                cv_service = service_cvs[area_id][vehicle_id]
                mu_s, sigma_s = get_lognormal_params(mean_service, cv_service)
                services[(area_id, vehicle_id)] = np.random.lognormal(mu_s, sigma_s, NUM_SAMPLES)

                # Generate response times
                mean_response = mean_response_times[area_id][vehicle_id]
                cv_response = response_cvs[area_id][vehicle_id]
                mu_r, sigma_r = get_lognormal_params(mean_response, cv_response)
                responses[(area_id, vehicle_id)] = list(np.random.lognormal(
                    mu_r, sigma_r, NUM_SAMPLES))

        logger.info(f"Random times generation took: {time.time() - start_time:.2f} seconds")
        return PrecomputedTimes(arrivals, services, responses)
        

     


class EmpiricalMode(BaseExperimentMode):
    """
    Empirical mode:
    - no synthetic parameter generation is needed
    - precomputed times come from empirical PMF / real-data distributions
    - vehicles are derived from the empirical precomputed times
    """

    @property
    def arrival_mode(self) -> ArrivalMode:
        return ArrivalMode.EMPIRICAL
    
    @property
    def our_policy(self):
        return LBR_EMP()
    
    @property
    def other_policies(self):
        return [EmpiricalDispatch(), MinP95_EMP()]

    def generate_time_parameters(
        self,
        interval_range: tuple | None = None,
        service_range: tuple | None = None,
        response_range: tuple | None = None,
    ) -> Any:
        # No random parameter generation is needed for empirical mode.
        return None

    def generate_vehicles(self, time_parameters: Any) :
        return generate_empirical_vehicles(time_parameters)

    def generate_precomputed_times(self, time_parameters: Any):
        return generate_empirical_times(NUM_SAMPLES)

