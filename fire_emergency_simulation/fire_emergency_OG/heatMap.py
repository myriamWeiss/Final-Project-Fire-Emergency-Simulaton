import numpy as np
import pandas as pd
from scipy import stats
import logging
from typing import Dict, Tuple, List, Any
#from project import runProject 
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import Normalize
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import ast



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("heatMap")


class MultiSlopeNorm(Normalize):
    def __init__(self, breakpoints, clip=False):
        """
        breakpoints: list of sorted values [vmin, p1, p2, ..., vmax]
        """
        if len(breakpoints) < 2:
            raise ValueError("Need at least two breakpoints")
        self.breakpoints = np.array(breakpoints, dtype=float)
        self.num_segments = len(self.breakpoints) - 1
        super().__init__(vmin=self.breakpoints[0], vmax=self.breakpoints[-1], clip=clip)

    def __call__(self, value, clip=None):
        val = np.ma.masked_array(np.asarray(value))
        result = np.empty_like(val, dtype=float)

        for i in range(self.num_segments):
            left = self.breakpoints[i]
            right = self.breakpoints[i + 1]
            mask = (val >= left) & (val <= right)
            proportion = (val[mask] - left) / (right - left)
            result[mask] = (i + proportion) / self.num_segments

        if self.clip or clip:
            result = np.clip(result, 0, 1)
        else:
            result[val < self.vmin] = np.nan
            result[val > self.vmax] = np.nan

        return result

    def inverse(self, value):
        val = np.asarray(value)
        result = np.empty_like(val, dtype=float)

        # Rescale from [0, 1] to piecewise intervals
        segment = (val * self.num_segments).astype(int)
        segment = np.clip(segment, 0, self.num_segments - 1)  

        for i in range(self.num_segments):
            left = self.breakpoints[i]
            right = self.breakpoints[i + 1]
            mask = segment == i
            local_val = (val[mask] * self.num_segments) - i
            result[mask] = left + local_val * (right - left)

        return result

#------------------------#
sheet_names = ['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']
heatmap_type = ['Response Time', 'Queue', 'Both']
alpha_type = [0.1, 0.2, 0.3, 0.4]
column_RT = ['RT_0.1_pv_wilc', 'RT_0.2_pv_wilc', 'RT_0.3_pv_wilc','RT_0.4_pv_wilc']
column_Queue = ['Qu_0.1_pv_wilc', 'Qu_0.2_pv_wilc', 'Qu_0.3_pv_wilc','Qu_0.4_pv_wilc']

def get_heatMap(results_file_path):
    user_response = get_from_user()
    #sheet name
    data  = pd.read_excel(results_file_path, sheet_name =sheet_names[user_response['Policies']])
    #Column Name by Alpha Type
    column_name_Rt = column_RT[user_response["Significance level"]]
    column_name_Qu = column_Queue[user_response["Significance level"]]

    RT_title = 'Win Rate on 90th-Percentile Response Time'
    Queue_title = 'Win Rate on Average Queue Size'

    if user_response["Heat Map Type"] == len(heatmap_type)-1: #if chosen both
        make_heatmap(data, column_name_Rt, cmap_name="autumn", title = RT_title, title_color_bar ="Win Percentage")
        make_heatmap(data, column_name_Qu, cmap_name="YlGn_r", title = Queue_title, title_color_bar ="Win Percentage")
    elif user_response["Heat Map Type"] == 0: #if chosen RT
        make_heatmap(data, column_name_Rt, cmap_name="autumn", title = RT_title, title_color_bar ="Win Percentage")
    else :#if chosen Qu
        make_heatmap(data, column_name_Qu, cmap_name="YlGn_r", title = Queue_title, title_color_bar ="Win Percentage")



def get_from_user():
    user_response = {}
    options = {
        "Policies" : sheet_names,
        "Heat Map Type" : heatmap_type,
        "Significance level" : alpha_type
    }
    for question, values in options.items() :
        print(f"\nChose the {question}:")
        for i, val in enumerate(values, start =1):
            print(f"{i} - {val}")
        while True:
            answer = int(input("\nEnter a valid number : "))
            if  1 <=int(answer) <= len(values):
                user_response[question] = int(answer) -1
                break
            else:
                print("\nInvalid input. Please enter a valid response between 1 and", len(values))
    return user_response


def make_heatmap(data, score_string, cmap_name="autumn", title = "Win Percentage Heatmap", title_color_bar ="Win Percentage"):
    norm = Normalize(vmin=0, vmax=100)
    return build_heatmap_from_csv_win(data, norm, score_string, cmap_name, title, title_color_bar,truncate_range=(0.1, 0.9))


def build_heatmap_from_csv_win(df, norm, score_string, cmap_name, title, title_color_bar,truncate_range):
    cmap = create_colormap(cmap_name, truncate_range) 
    fig, ax = create_figure_and_axes()
    
    for _, row in df.iterrows():
        interval_low, interval_hight, service_low, service_hight = get_param_from_excel(row)
        x = service_low
        y = interval_low
        width = service_hight - service_low
        height = interval_hight - interval_low
        score = row[score_string]

        draw_colored_rectangle(ax, x, y, width, height, score, cmap, norm)
        #annotate_rectangle(ax, x, y, width, height, score) no need to write the score

    set_plot_labels(ax, title)
    add_colorbar(fig, ax, cmap, norm, title_color_bar)
    save_and_show_figure(fig, title)
    return ax

def create_figure_and_axes(figsize=(10, 8)):
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def create_colormap(cmap_name, truncate_range):
    base_cmap = cm.get_cmap(cmap_name)
    cmap = truncate_colormap(base_cmap, *truncate_range)
    return cmap

def truncate_colormap(cmap, minval, maxval, n=100):
    new_cmap = LinearSegmentedColormap.from_list(
        f"trunc({cmap.name},{minval:.2f},{maxval:.2f})",
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap


def get_param_from_excel(row): 
    value_from_excel = row["(Y interval, X service)"]
    parsed_value = ast.literal_eval(value_from_excel)
    range_interval = parsed_value[0]
    range_service = parsed_value[1]
    y_low, y_hight = range_interval
    x_low, x_high = range_service
    return y_low, y_hight, x_low, x_high

def draw_colored_rectangle(ax, x, y, width, height, score, cmap, norm):
    color = cmap(norm(score))
    rect = patches.Rectangle((x, y), width, height, facecolor=color, edgecolor="black", linewidth=0.3)
    ax.add_patch(rect)

def annotate_rectangle(ax, x, y, width, height, score):
    ax.text(x + width / 2, y + height / 2, f"{int(score)}", ha="center", va="center", color="black", fontsize=5)


def set_plot_labels(ax, title, xlim=(10, 500), ylim=(500, 10100), xlabel="Time Service Range (min)", ylabel="Inter-arrival Times Range (min)"):
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=16)
    #ax.tick_params(axis='both', labelsize=12)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

def add_colorbar(fig, ax, cmap, norm, label):
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    #fig.colorbar(sm, ax=ax, label=label)
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label(label, fontsize=14)

def save_and_show_figure(fig, title):
    output_image_path= title + ".png"
    plt.tight_layout()
    plt.savefig(output_image_path)
    plt.show()



if __name__ == "__main__":
    user_response = get_from_user()
    print( column_RT[user_response["Significance level"]])