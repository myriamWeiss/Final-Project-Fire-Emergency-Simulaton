import pandas as pd
import numpy as np
from config import NUM_SAMPLES, NUM_AREA, NUM_VEHICLE
from config import EMPERICAL_FILE
import numpy as np
import pandas as pd
from scipy import stats
import time
from globals import globs
from models import Vehicle, PrecomputedTimes
from config import (NUM_AREA, CV_SERVICE_RANGE, CV_RESPONSE_RANGE, EPSILON)

# ---------------------------------------------------
# Generate Time
# ---------------------------------------------------

def generate_empirical_times(num_of_events) -> PrecomputedTimes: #need change O.G
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

def generate_interarrival_samples_by_fdcall(path_file: str):
    """
    Given a CSV of empirical PMFs aggregated by FD_call
    (columns: FD_call, Parameter, Value, Probability),
    return: { parameter: { fd_call_idx: [N samples] } }
    """
    num_event = NUM_SAMPLES
    df = pd.read_csv(path_file)

    # Map FD_call to 0-based indices
    call_ids = {area: i for i, area in enumerate(sorted(df["FD_call"].unique()))}
    df["FD_call"] = df["FD_call"].map(call_ids)

    out = {}
    for parameter in df["Parameter"].unique():
        d = {}
        sub = df[df["Parameter"] == parameter]
        for fd_call, g in sub.groupby("FD_call"):
            values = g["Value"].values
            probs = g["Probability"].values
            probs = probs / probs.sum()
            samples = np.random.choice(values, size=num_event, replace=True, p=probs)
            d[fd_call] = list(samples)
        out[parameter] = d
    return out

def generate_empirical_samples_from_pmf(path_file):
    """
    Given a CSV of empirical PMFs (columns: FD_call, FD_response, Parameter, Value, Probability),
    returns a dictionary for each parameter with keys (fd_call_idx, fd_response_idx) as 0-based indices,
    and values as lists of N sampled values according to the empirical probabilities.

    Args:
        pmf_file (str): Path to CSV file.
        N (int): Number of samples to generate per (fd_call, fd_response) combo.

    Returns:
        dict: parameter_dicts[parameter][(fd_call_idx, fd_response_idx)] = [sampled values]
    """
    N = NUM_SAMPLES            # Number of samples you wish to generate (should be defined)

    pmf_df = pd.read_csv(path_file)  # Load PMF data from CSV

    # === Create mappings from FD_call and FD_response values to 0-based indices ===
    call_ids = {v: i for i, v in enumerate(sorted(pmf_df["FD_call"].unique()))}
    resp_ids = {v: i for i, v in enumerate(sorted(pmf_df["FD_response"].unique()))}

    # === Replace FD_call and FD_response values in DataFrame with their new indices ===
    pmf_df["FD_call"] = pmf_df["FD_call"].map(call_ids)
    pmf_df["FD_response"] = pmf_df["FD_response"].map(resp_ids)

    parameter_dicts = {}  # Main output: dict of parameter -> {(fd_call_idx, fd_response_idx): [samples]}

    # === For each parameter (e.g., RESPONSE_TIME_MIN), build the sampling dictionary ===
    for parameter in pmf_df["Parameter"].unique():
        d = {}
        sub_df = pmf_df[pmf_df["Parameter"] == parameter]  # Filter for this parameter
        grouped = sub_df.groupby(["FD_call", "FD_response"])  # Group by each (call, response) pair
        for (fd_call, fd_response), group in grouped:
            values = group["Value"].values                # All possible observed values for this combo
            probs = group["Probability"].values           # Their associated probabilities
            probs = probs / probs.sum()                   # Normalize to ensure they sum to 1
            # === Draw N samples according to the empirical probabilities (replace = True -> the same value can appear multiple times ) ===
            samples = np.random.choice(values, size=N, replace=True, p=probs)
            d[(fd_call, fd_response)] = list(samples)     # Store the samples in the dict with index-based key
        parameter_dicts[parameter] = d  # Store the dict for this parameter

    return parameter_dicts  # The top-level dictionary: parameter -> {(fd_call_idx, fd_response_idx): [samples]}


# ---------------------------------------------------
# Generate Vehicles
# ---------------------------------------------------

def generate_empirical_vehicles(precomputed: PrecomputedTimes):
    """
    Build Vehicle objects and compute a sensible total_rate per vehicle:
    total_rate = 1 / mean(service + response) aggregated across areas for this vehicle.
    This avoids touching models.py even if Vehicle(total_rate) is required.
    """
    EPS = 1e-4
    vehicles = []

    # infer counts from precomputed (more robust than assuming NUM_AREA)
    num_vehicles = max(v for (_, v) in precomputed.services.keys()) + 1
    num_areas = max(a for (a, _) in precomputed.services.keys()) + 1

    for vid in range(num_vehicles):
        totals = []
        for area_id in range(num_areas):
            s = precomputed.services[(area_id, vid)]
            r = precomputed.responses[(area_id, vid)]
            n = min(len(s), len(r))
            if n > 0:
                totals.extend([s[i] + r[i] for i in range(n)])

        if totals:
            mean_total = float(np.mean(totals))
            total_rate = (1.0 / mean_total) if mean_total > 0 else EPS
        else:
            total_rate = EPS

        vehicles.append(Vehicle(vid, None, None, None, None, None, total_rate))
    return vehicles
