import heapq
import time
import warnings
import pandas as pd
import numpy as np
from typing import List, Dict, Set, Optional, Tuple, Any
import logging
from models import Vehicle, Event, EventLog, PrecomputedTimes, EventType, ArrivalMode
from policies import DispatchPolicy
from config import NUM_AREA, NUM_VEHICLE,  NUM_SAMPLES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simulation")


class Simulation:
    """
    Core simulation engine for emergency dispatch system.
    
    This class handles the discrete event simulation including event scheduling,
    vehicle dispatching, and statistics collection.
    """
    
    def __init__(self, vehicles: List[Vehicle], dispatch_policy: DispatchPolicy,
                 precomputed_times: PrecomputedTimes, arrival_mode: ArrivalMode = ArrivalMode.REGULAR):
        """
        Initialize simulation with entities and configuration.
        Args:
            vehicles: List of Vehicle objects representing available units
            dispatch_policy: Policy to use for vehicle selection
            precomputed_times: Pre-generated random times for reproducibility
            arrival_mode : Parameter is generate from Empirical Distribution or from known Distribution
        """
        self.total_service_time = 0
        self.vehicles = vehicles
        self.dispatch_policy = dispatch_policy
        self.precomputed_times = precomputed_times
        self.available_vehicles = set(range(len(vehicles)))
        self.arrival_mode = arrival_mode
        self.events = []
        self.current_time = 0
        self.response_times = []
        self.waiting_queue = []
        self.max_queue_size = 0
        self.total_services = 0
        self.delayed_event = 0
        self.queue_area = 0.0        # ∫ Q(t) dt
        self.last_q_time = 0.0       # הזמן האחרון שנצבר עד אליו


        # Track usage of precomputed times
        self.time_indices = {(i, j): 0 for i in range(NUM_AREA) for j in range(NUM_VEHICLE)}
        self.max_index_used = 0
        self.start_time = time.time()

        # Initialize parameters for policies
        self.prioritization_parameters = {
            i: {j: 0.0 for j in range(len(vehicles))}
            for i in range(NUM_AREA)
        }
        self.mean_response_times = {
            i: {j: 0.0 for j in range(len(vehicles))}
            for i in range(NUM_AREA)
        }

        # Initialize event logs
        self.event_logs = []

        # Set up parameters needed for policies
        self._compute_policy_parameters()

    def log_event(self, event: Event, available_vehicles_for_log: List[int], 
                 chosen_vehicle_id: int, service_time: float, response_time: float) -> None:
        """
        Record an event to the event log.
        
        Args:
            event: The event to log
            available_vehicles_for_log: Vehicles available at event time
            chosen_vehicle_id: Vehicle that was selected
            service_time: Time required to service the call
            response_time: Time required to respond to the call
        """
        self.event_logs.append(EventLog(
            time_of_event=self.current_time,
            time_of_service=service_time,
            response_time=response_time,
            available_engines=available_vehicles_for_log,
            chosen_engine=chosen_vehicle_id,
            mean_response_times=self.mean_response_times[event.area_id],
            prioritization_parameters=self.prioritization_parameters[event.area_id]
        ))

    def _accumulate_queue_area(self, until_time: float):
        if until_time <= self.last_q_time:
            return
        dt = until_time - self.last_q_time
        self.queue_area += len(self.waiting_queue) * dt
        self.last_q_time = until_time

    def save_logs_to_excel(self, filename: str) -> None:
        """
        Save event logs to an Excel file.
        Args:
            filename: Path to save the Excel file
        """
        df = pd.DataFrame([e.__dict__ for e in self.event_logs])
        df.to_excel(filename, index=False)

    def _compute_policy_parameters(self) -> None:
        """
        Compute parameters required for dispatch policies.
        This method calculates mean response times based on the precomputed random times.
        """
        for area_id in range(NUM_AREA):
            for vehicle_id, vehicle in enumerate(self.vehicles):
                # For Response Time Policy: compute 90th percentile response times
                responses = self.precomputed_times.responses[(area_id, vehicle_id)]
                self.mean_response_times[area_id][vehicle_id] = np.mean(responses)
        
        self.dispatch_policy.compute_parameters(self.precomputed_times, self.vehicles, NUM_AREA, self.mean_response_times)

    def _select_vehicle(self, area_id: int) -> Optional[int]:
        """
        Select a vehicle to dispatch based on the current policy.
        Args:
            area_id: ID of the area requiring service
        Returns:
            ID of the selected vehicle, or None if no vehicle is available
        """
        if not self.available_vehicles:
            return None
        return self.dispatch_policy.select_vehicle(
            area_id, self.available_vehicles)

    def _get_next_time(self, area_id: int, vehicle_id: int, time_type: str) -> float:
        """
        Get next precomputed time of specified type.
        Args:
            area_id: ID of the area
            vehicle_id: ID of the vehicle
            time_type: Type of time ('arrival', 'service', or 'response')
        Returns:
            Next random time value  
        Raises:
            ValueError: If time_type is not recognized
        """

        if time_type == 'arrival':
            key = self._get_arrival_key(area_id, vehicle_id)
            container = self.precomputed_times.arrivals
        elif time_type == 'service':
            key = (area_id, vehicle_id)
            container = self.precomputed_times.services
        elif time_type == 'response':
            key = (area_id, vehicle_id)
            container = self.precomputed_times.responses
        else:
            raise ValueError(f"Unknown time type: {time_type}")

        #Keeping track which precomputed time value should be used next from a specific (area, vehicle) time sequence.
        idx = self.time_indices[key]
        # Track maximum index used
        self.max_index_used = max(self.max_index_used, idx)
        # Check if we're close to running out of samples
        if idx >= len(container[key]) - 100:
            warnings.warn(f"Running low on {time_type} times for key {key}")
        self.time_indices[key] += 1
        
        return container[key][idx]

    def _get_arrival_key(self, area_id: int, vehicle_id: int) -> tuple[int, int]:
        return (area_id,0) if self.arrival_mode == ArrivalMode.EMPIRICAL else (area_id, vehicle_id)

    def _process_queue(self) -> None:
        """
        Process waiting calls from the queue when vehicles become available.
        """
        available_vehicles_log = list(self.available_vehicles)
        while self.waiting_queue and self.available_vehicles:
            self._accumulate_queue_area(self.current_time)#new
            arrival_time, area_id = self.waiting_queue.pop(0)
            chosen_vehicle_id = self._select_vehicle(area_id)

            if chosen_vehicle_id is None:
                self.waiting_queue.insert(0, (arrival_time, area_id))
                break

            self.available_vehicles.remove(chosen_vehicle_id)

            service_time = self._get_next_time(area_id, chosen_vehicle_id, 'service')
            response_time = self._get_next_time(area_id, chosen_vehicle_id, 'response')

            # Log the event
            self.log_event(
                Event(self.current_time, EventType.QUEUE_PROCESSING, area_id),
                available_vehicles_log, 
                chosen_vehicle_id, 
                service_time, 
                response_time
            )

            total_response_time = (self.current_time - arrival_time) + response_time
            self.response_times.append(total_response_time)
            self.total_services += 1

            heapq.heappush(
                self.events,
                Event(self.current_time + service_time, EventType.COMPLETION, 
                      area_id, chosen_vehicle_id)
            )

    def _handle_arrival_event(self, event: Event) -> None:
        """
        Process an arrival event.
        Args:
            event: The arrival event to process
        """

        # Schedule the next arrival from this source
        next_arrival = self.current_time + self._get_next_time(
            event.area_id, event.vehicle_id, 'arrival')
        heapq.heappush(
            self.events,
            Event(next_arrival, EventType.ARRIVAL, event.area_id,
                  event.vehicle_id, next_arrival)
        )

        # Handle the current arrival
        service_time = 0
        response_time = 0
        chosen_vehicle_id = None
        
        if self.available_vehicles:
            available_vehicles_for_log = list(self.available_vehicles)
            chosen_vehicle_id = self._select_vehicle(event.area_id)
            
            if chosen_vehicle_id is not None:
                self.available_vehicles.remove(chosen_vehicle_id)
                service_time = self._get_next_time(event.area_id, chosen_vehicle_id, 'service')
                response_time = self._get_next_time(event.area_id, chosen_vehicle_id, 'response')
                
                self.total_service_time += service_time
                self.response_times.append(response_time)
                self.total_services += 1
                
                heapq.heappush(
                    self.events,
                    Event(self.current_time + service_time, EventType.COMPLETION, 
                          event.area_id, chosen_vehicle_id)
                )
        else:
            available_vehicles_for_log = []
            self._accumulate_queue_area(self.current_time)#new
            self.waiting_queue.append((event.arrival_time, event.area_id))
            self.max_queue_size = max(self.max_queue_size, len(self.waiting_queue))
            self.delayed_event += 1
        
        # Log the event
        self.log_event(
            event, 
            available_vehicles_for_log, 
            chosen_vehicle_id, 
            service_time, 
            response_time
        )

    def _handle_completion_event(self, event: Event) -> None:
        """
        Process a completion event.
        
        Args:
            event: The completion event to process
        """
        self.available_vehicles.add(event.vehicle_id)
        self._process_queue()

    def run(self, end_time: float) -> None:
        """
        Run the simulation until the specified end time.
        Args:
            end_time: Time at which to stop the simulation
        """
        run_start_time = time.time()

        second_loop = 1 if self.arrival_mode == ArrivalMode.EMPIRICAL else NUM_VEHICLE #vehicle Id = 0
        
        # Initialize first arrivals
        for area_id in range(NUM_AREA):
            for vehicle_id in range(second_loop):
                arrival_time = self._get_next_time(area_id, vehicle_id, 'arrival')
                heapq.heappush(
                    self.events,
                    Event(arrival_time, EventType.ARRIVAL, area_id,
                          vehicle_id, arrival_time)
                )

        # Process events until end time
        last_update_time = 0
        
        while self.events and self.current_time < end_time:
            event = heapq.heappop(self.events)
            
            # Update progress bar based on current time
            if event.time - last_update_time > end_time / 100:
                last_update_time = event.time
            
            # צבירה עד זמן האירוע לפי Q(t) הקודם
            self._accumulate_queue_area(event.time)#new

            self.current_time = event.time
            
            # Process event based on type
            if event.event_type == EventType.ARRIVAL:
                self._handle_arrival_event(event)
            elif event.event_type == EventType.COMPLETION:
                self._handle_completion_event(event)

        # אם נעצרנו לפני end_time (נגמרו אירועים) – לצבור עד סוף החלון
        if self.current_time < end_time:
            self._accumulate_queue_area(end_time)

        # ממוצע גודל תור בזמן
        self.avg_queue = self.queue_area / end_time


        logger.info(f"Simulation completed in {time.time() - run_start_time:.2f} seconds")
     
        
