# Fire Emergency Dispatch Simulation

This project implements a **discrete-event simulation** for a fire emergency dispatch system.  
It compares different vehicle dispatch policies (MinRT, Percentile-95, and LBR – the suggested policy) in order to minimize **Response Time (RT)** and improve system performance.

## Overview

The simulation models a system with multiple service areas and fire trucks.  
It evaluates how different dispatch policies affect key performance metrics such as:
- 90th percentile response time
- Average response time
- Queue sizes
- System utilization
- Win percentage between policies
- Statistical significance (CI and Wilcoxon test)

## Key Components

### Models (`models.py`)
- `Vehicle`: Represents fire trucks with arrival, service, and response rate parameters  
- `Event`: Represents simulation events (arrivals, completions, queue processing)  
- `PrecomputedTimes`: Stores random values for arrivals, services, and responses (for reproducibility)

### Policies (`policies.py`)
- `MeanRT`: Selects the vehicle with the lowest **mean response time**  
- `Percentil_95`: Selects the vehicle with the lowest **95th percentile response time**  
- `LBR`: Selects the vehicle with the largest score  **Laplace-based probability** 

### Simulation Engine (`simulation.py`)
- Core discrete-event simulation loop  
- Event scheduling, queue handling, and vehicle assignment  
- Logging of events and statistics collection  

### Analysis (`analysis.py`)
- Random parameter generation (`generate_random_parameters`)  
- Precomputation of times from correct distributions (`generate_random_times`)  
- Execution of simulation runs under multiple policies  

### Project Runner (`project.py`)
- Runs multiple parameter sets and replications  
- Compares policies pairwise (MeanRT vs LBR, Percentile-95 vs LBR, etc.)  
- Produces summarized metrics  

### Results & Post-Processing
- `results_project.py`: Aggregates results across ranges, saves Excel summaries  
- `wining_scores.py`: Computes win scores, CI analysis, and Wilcoxon test  
- `run_wilconxon.py`: Applies Wilcoxon significance tests on queues and RT  
- `excel_file.py`: Merges multiple Excel outputs into one combined result file  
- `heatMap.py`: Generates heatmaps for win percentages and queues  

### Queue Statistics & Wilcoxon Analysis
- Parses simulation output intervals and assigns them into predefined bins (`y_bins`, `x_bins`) for consistent grouping.  
- Cleans and restructures the dataset to focus on average queue sizes of two compared policies.  
- Applies the **Wilcoxon signed-rank test** on grouped queue data, computing significance levels (`p < 0.1`, `p < 0.2`, etc.).  
- Produces a DataFrame of results and generates a **heatmap** of statistically significant queue differences using [`get_heatmap_for_queu`](heatMap.py).  


## Mathematical Models

- **Interarrival Times**: Exponential distribution (Poisson process)  
- **Service Times**: Lognormal distribution (captures variability in task duration)  
- **Response Times**: Lognormal distribution (captures variability in RT under uncertainty)  

## Simulation Flow

1. **Parameter generation**  
   - Random sets of interarrival, service, and response times are created for each *(area, vehicle)* pair.  
   - Distributions used: exponential (for interarrival), lognormal (for service and response), with variation controlled by coefficients of variation (CVs).  
   - Implemented in [`analysis.generate_random_parameters`](analysis.py) and [`analysis.get_lognormal_params`](analysis.py).

2. **Vehicle initialization**  
   - A fleet of [`Vehicle`](models.py) objects is created, each with its own arrival, service, and response profiles.  
   - Constructed in [`project.generate_vehicles`](project.py).

3. **Precomputation of random times**  
   - All random times are generated **in advance** to guarantee fair policy comparisons.  
   - Stored in [`PrecomputedTimes`](models.py).  
   - Implemented by [`analysis.generate_random_times`](analysis.py).

4. **Simulation setup**  
   - A [`Simulation`](simulation.py) instance is created with the chosen policy and precomputed times.  
   - Event lists are seeded with initial **arrival events** at `t=0`.  
   - State tracking variables include available vehicles, queues, service counts, and response logs.

5. **Discrete-event loop**  
   - Core loop is in [`Simulation.run`](simulation.py).  
   - It repeatedly processes the earliest event from the priority queue:  
     - **Arrival event** → [`Simulation._handle_arrival_event`](simulation.py)  
     - **Completion event** → [`Simulation._handle_completion_event`](simulation.py)  
     - Queue handling → [`Simulation._process_queue`](simulation.py).

6. **Policy decision-making**  
   - Dispatch decisions are delegated to the selected policy class:  
     - [`MeanRT`](policies.py) → lowest average RT  
     - [`Percentil_95`](policies.py) → lowest 95th percentile RT  
     - [`LBR`](policies.py) → Laplace-based score combining call arrivals, service, and response risks.  
   - Policies all inherit from [`DispatchPolicy`](policies.py).

7. **Replication and comparison**  
   - Each parameter set is simulated multiple times in [`project.run_replications`](project.py).  
   - Policy outcomes are compared in [`project.summarize_replication_results`](project.py).  
   - Pairwise metrics include win percentage, confidence intervals (CI), and Wilcoxon tests.

8. **Result aggregation and visualization**  
   - Results across parameter sweeps are produced in [`results_project.get_final_results`](results_project.py).  
   - Summaries and win scores are computed in [`wining_scores.py`](wining_scores.py).  
   - Heatmaps of RT and queue statistics are generated in [`heatMap.py`](heatMap.py).

## Configuration Parameters (`config.py`)

- `NUM_PARAMETER_SETS` → number of parameter sets  
- `NUM_REPLICATIONS` → replications per set  
- `SIMULATION_TIME` → total simulated time  
- `NUM_AREA` → number of service areas  
- `MAX_INTERARRIVAL_RANGE`, `MAX_TOTAL_SERVICE_RANGE` → ranges for parameter sweeps  
- `STEP_INTERVAL`, `STEP_TOTAL_SERVICE` → step size for ranges  
- `SERVICE_RT_RATIO` → ratio of service vs response in total service time  

## Running the Simulation

To run the basic simulation, run the following command
```bash
python main.py
```
This command will create a directory in the following format `YYYY-MM-DD_HH-mm-ss`, containing the execution results

To see queue heat map, run the following command:
```bash
python queue_map.py <output-dir>/result_project.xlsx
```


