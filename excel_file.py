import numpy as np
import pandas as pd
import glob
import os



def combine_csv_files():
    # Path to the folder containing Excel files
    folder_path = './combined result'
    output_file = 'merged_output.xlsx'

    # Find all .xlsx files in the folder, sorted
    excel_files = sorted(glob.glob(os.path.join(folder_path, '*.xlsx')))

    # Sheets you want to combine
    sheet_names = ['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']

    # Dictionary to store dataframes by sheet name
    combined_sheets = {sheet: [] for sheet in sheet_names}

    # Read and combine data
    for file in excel_files:
        try:
            xls = pd.ExcelFile(file)
            for sheet in sheet_names:
                if sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    if not df.empty: # Only append if the dataframe is not empty
                        combined_sheets[sheet].append(df)
        except Exception as e:
            print(f"Error reading file {file}: {e}")
            continue # Skip to the next file if there's an error

    # Flag to check if any data was written
    written_any = False

    # Write to output file
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet, dfs in combined_sheets.items():
            if dfs: # Check if there are any dataframes to concatenate for this sheet
                print(f"Writing sheet: {sheet}")
                pd.concat(dfs, ignore_index=True).to_excel(writer, sheet_name=sheet, index=False)
                written_any = True # Set to True if at least one sheet is written

        if not written_any:
            # If no data was written to any sheet, raise an error to prevent
            # the IndexError from openpyxl
            raise ValueError("No non-empty sheets to write. Aborting to avoid invisible Excel file error.")

    if written_any:
        print(f"Successfully combined data into {output_file}")
    else:
        print(f"No data was written to {output_file}. The file might be empty.")




def merge_simulation_outputs(root_folder: str, output_folder: str, sheet_names: list):
    """
    מאחדת קבצי אקסל מכל תיקיות-המשנה לפי שם קובץ וזהות גיליונות.
    נשמר מבנה של שלושה גיליונות בכל קובץ.

    :param root_folder: תיקיה המכילה את כל תיקיות ההרצות (run_01, run_02 וכו')
    :param output_folder: תיקיה לשמירת קבצי האקסל המאוחדים
    :param sheet_names: רשימת שמות הגיליונות שמופיעים בכל קובץ (למשל ['Sheet1', 'Sheet2', 'Sheet3'])
    """
    os.makedirs(output_folder, exist_ok=True)
    all_excel_files = sorted(glob.glob(os.path.join(root_folder, '*', '*.xlsx')), key=lambda p: int(os.path.basename(os.path.dirname(p)).split(' ')[0]))
    merged_files = {}

    for path in all_excel_files:
        print(path)
        file_name = os.path.basename(path)
        folder_name = os.path.basename(os.path.dirname(path))

        if file_name not in merged_files:
            merged_files[file_name] = {sheet: [] for sheet in sheet_names}

        try:
            xls = pd.ExcelFile(path)
            for sheet in sheet_names:
                if sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    if not df.empty:
                        df['source_run'] = folder_name
                        merged_files[file_name][sheet].append(df)
                        print("adding to pd")
                    else:
                        print(f"⚠️ empty sheet {sheet} in file {file_name} in folder {folder_name}")
                else:
                    print(f"❌ empty sheet  {sheet} in file{file_name}")
        except Exception as e:
            print(f"🚨 error reading {path}: {e}")

    for file_name, sheet_data in merged_files.items():
        output_path = os.path.join(output_folder, file_name)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet in sheet_names:
                print(sheet)
                dfs = sheet_data[sheet]
                if dfs:
                    merged_df = pd.concat(dfs, ignore_index=True)
                    merged_df.to_excel(writer, sheet_name=sheet, index=False)
                    print(f"✅ write to  {output_path} | in sheet: {sheet} ({len(merged_df)} ligne)")
                else:
                    print(f"⚠️ didnt write to {sheet} in file {file_name}")

    print("\n🎉 all files have been combined")

merge_simulation_outputs(
    root_folder='./Simulation_05042025_updated/all folder',
    output_folder='./folder_outputs',
    sheet_names=['Percentil_95 vs MeanRT', 'Percentil_95 vs LBR', 'MeanRT vs LBR']
)