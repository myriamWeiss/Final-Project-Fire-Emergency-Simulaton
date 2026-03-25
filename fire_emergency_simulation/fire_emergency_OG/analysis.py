import numpy as np
import pandas as pd
from scipy import stats
import time
import logging
from typing import Dict, Tuple, List, Any
import os
# Project files
from globals import globs



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





