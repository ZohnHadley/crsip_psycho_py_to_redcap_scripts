#script version 2.0.1

import math
from unittest import result

from colorama import init, Back, Fore
init(autoreset=True) # Automatically resets style after every print
import re
import threading as th
import os
import sys
import re
import pandas as pd
import traceback
from datetime import date, datetime


if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.getcwd()


#region script configurables
project_name = "BADE IMAGES MRI"
script_name = "{} BADE IMAGE MRI to Redcap".format(project_name)
script_config = {
    "debug": False,   # when True, also export a per-trial CSV (match / degree_change / responses) for spot-checking
    "google_sheet_url": "",
    "redcap_api_url": "",
    "redcap_api_key": "",
    "red_cap_variables" : {
            "date":"", 
            "task_version":"",

            "percent_trials_considered":"",
            "acc_confirm":"",
            "acc_disconfirm":"",
            "total_acc":"",
            "ratingchg_correctC":"",
            "ratingchg_correctD":"",
            
            "ratingchg_incorrectC":"",
            "ratingchg_incorrectD":"",
            
            "total_ratingchg":"",
            
            "rt_correctC":"",
            "rt_correctD":"",
            "rt_incorrectC":"",
            "rt_incorrectD":"",
            
            "total_rt":""
    },
    
    "dir_paths":{
        "project_folder_path": os.path.join(base_path, 'bade-images_MRIpract-v2'),
        "data_folder_path": os.path.join(base_path, 'bade-images_MRIpract-v2','data'),
        "data_frame_exports": os.path.join(base_path, 'bade_images_MRI_red_cap_exports')
    }
} 

#region script variables
user_input = None 

### Menu options
mainmenu_options = {
    # "export redcap data for 1 saved participant": 1,
    "export redcap data from all participants": 1,
    "change source csv data folder": 2,
    "change export folder": 3,
    "toggle debug output (per-trial csv)": 4,
    "exit": 5
}
export_redcap_data_from_all_participants_submenu_options = {
    "export data for all saved participants in seperate files": 1,
    "export data for all saved participants in 1 combined file": 2,
    "back to main menu": 3
}
#endregion

def log(log_type="",message=""):
    
    prefix_bg_color = Back.BLACK 
    prifix_text_color = Fore.WHITE

    bg_color = Back.RESET
    text_color = Fore.RESET

    prefix = ""
    match log_type.lower():
        case "w":
            prefix_bg_color = Back.YELLOW
            prifix_text_color = Fore.WHITE
            bg_color = Back.RESET
            text_color = Fore.YELLOW

            prefix = "Warn : "
        case "e":
            prefix_bg_color = Back.RED 
            prifix_text_color = Fore.WHITE
            bg_color = Back.RESET
            text_color = Fore.RED

            prefix = "Error : "
        case "l":
            prefix_bg_color = Back.LIGHTBLUE_EX 
            prifix_text_color = Fore.WHITE
            bg_color = Back.RESET
            text_color = Fore.LIGHTBLUE_EX

            prefix = "Info : "
        case "t":
            prefix_bg_color = Back.GREEN
            prifix_text_color = Fore.WHITE
            bg_color = Back.RESET
            text_color = Fore.GREEN
        case "":
            prefix_bg_color = Back.RESET 
            prifix_text_color = Fore.LIGHTGREEN_EX
            bg_color = Back.RESET
            text_color = Fore.RESET

            prefix = ""

    print(prefix_bg_color+prifix_text_color+ f"{prefix}" +Back.RESET+Fore.RESET+bg_color+text_color+ f"{message}"+Back.RESET+Fore.RESET)

def print_instructions(message):
    wrapped_message = re.sub(r'(.{1,80})(\s|$)', r'\1\n', message)  # Wrap text at 80 characters
    border_length = max(len(line) for line in wrapped_message.split('\n')) + 4  # Calculate border length based on longest line
    border = '-' * border_length
    print(Back.LIGHTYELLOW_EX + Fore.BLACK + border)
    for line in wrapped_message.split('\n'):
        print(Back.LIGHTYELLOW_EX + Fore.BLACK + f"| {line.ljust(border_length - 4)} |")  # Left-align text within the border
    print(Back.LIGHTYELLOW_EX + Fore.BLACK + border)

def format_time(time_string):
        valid_date = datetime.strptime(time_string, "%Y-%m-%d_%Hh%M.%S.%f").strftime("%m/%d/%Y %H:%M:%S")
        formatted_date = valid_date if not pd.isna(valid_date) else ""
        return formatted_date
 
 
def get_path_base_name(path):
    return os.path.basename(path)

def check_folders_exist():
    for key, path in script_config["dir_paths"].items():
        if not os.path.isdir(path):
            if key :
                log("e",f"Folder not found at '{path}'. Please make sure the \'{get_path_base_name(path)}\\\' folder exists.")
                if key == "data_frame_exports":
                    log("l",f"making directory the \'{get_path_base_name(path)}\\\' folder")
                    os.makedirs(path, exist_ok=True)
                continue

def read_data_frame_from_csv(file_path):
    if os.path.isfile(file_path):
        try:
            data_frame = pd.read_csv(file_path)
            data_frame = data_frame.fillna('')
            return data_frame
        except Exception as error:
            log("e", f"Could not parse '{get_path_base_name(file_path)}'. Skipping it. CAUSED BY : {error}")
            return None
    log("e", f"File '{get_path_base_name(file_path)}' not found.")
    return None

def has_required_columns(session_data_frame, required_columns):

        missing_required = [
            col for col in required_columns
            if col not in session_data_frame.columns
        ]

        if missing_required: 
            return {"val":True, "columns":missing_required}
        return {"val":False, "columns":missing_required}

def get_column_list(data_frame, column_name):
    if column_name in data_frame.columns:
        return data_frame[column_name].tolist()
    else:
        log("e",f"Column '{column_name}' not found in the data frame.")
        return []

#this is basically the only section that should change
def map_data_frame_to_red_cap_variable(session_data_frame):
    try:
        if session_data_frame is None or session_data_frame.empty:
            log("e", "~~~~~~~~~~~~~~~~~~~~")
            log("e", " [mapping data frame]")
            log("e", " cvs found with no data = empty data frame")
            log("e", " ... skipping empty data frame")
            log("e", "~~~~~~~~~~~~~~~~~~~~")
            return None
            # raise Exception("[mapping data frame] data frame is empty")
        
        required_columns = has_required_columns(session_data_frame, ['date', 'participant'])

        if required_columns["val"]:
            raise Exception(f"Missing required columns: {required_columns["columns"]}")

        # ---- Helpers ----
        def _mean(series):
                series = pd.to_numeric(series, errors='coerce')
                result = series.mean()
                if pd.isna(result):
                    # empty subset (e.g. a participant with no incorrect confirm trials) -> blank cell
                    return ''
                return round(float(result), 4)
                 
        
        # valid_date = datetime.strptime(session_data_frame["date"].iloc[0], "%Y-%m-%d_%Hh%M.%S.%f").strftime("%m/%d/%Y %H:%M:%S")
        # formatted_date = valid_date if not pd.isna(valid_date) else ""
        # ---- Counts ----
 
        trial_rows = session_data_frame[session_data_frame['trialType'] == 'trial']
        nb_trials_ran_in_session = len(trial_rows) # number of trials 

        data_frame = pd.DataFrame([script_config["red_cap_variables"]])
        # data_frame["percent_trials_considered"]= (nb_trials_ran_in_session and nb_answered_trials / nb_trials_ran_in_session * 100) or 0
        # ---- Build the analysis frame: answered trials only (mirrors percent_trials_considered) ----
        answered = trial_rows.copy()
        answered['condition2'] = answered['condition2'].astype(str).str.strip()
        for _col in ['tSlider.response', 'tSlider.response1', 'tSlider.response2', 'tSlider.rt']:
            answered[_col] = pd.to_numeric(answered[_col], errors='coerce')
        # A trial is "answered" if the slider was actually moved (0 / blank = not answered)
        answered = answered[(answered['tSlider.response'].notna()) & (answered['tSlider.response'] != 0)]
        nb_answered_trials = len(answered)

        # Correct final answer comes from the 2nd letter of condition4 (Y -> +100, N -> -100)
        correct_answer = answered['condition4'].astype(str).str.strip().str[1].map({'Y': 100, 'N': -100})
        # match = 1 when the participant's final response has the same sign as the correct answer
        answered['match'] = (answered['tSlider.response'] * correct_answer > 0).astype(int)
        # "rating change between img1 and img2" = rating after img2 minus rating after img1
        # (signed; wrap in .abs() below if your analysis wants magnitude of change)
        answered['degree_change'] = answered['tSlider.response2'] - answered['tSlider.response1']

        confirm = answered[answered['condition2'] == 'confirm']
        disconfirm = answered[answered['condition2'] == 'disconfirm']

        data_frame["task_version"] = session_data_frame["psychopyVersion"].iloc[0] if "psychopyVersion" in session_data_frame.columns else ""
        data_frame["percent_trials_considered"] = round(nb_answered_trials / nb_trials_ran_in_session * 100, 2) if nb_trials_ran_in_session else 0

        # ---- Accuracy: mean of the 0/1 match indicator over the answered trials of each condition ----
        data_frame["acc_confirm"]    = _mean(confirm['match'])
        data_frame["acc_disconfirm"] = _mean(disconfirm['match'])
        data_frame["total_acc"]      = _mean(answered['match'])

        # ---- Rating change: averaged over only the matched / non-matched trials of each condition ----
        data_frame["ratingchg_correctC"]   = _mean(confirm[confirm['match'] == 1]['degree_change'])
        data_frame["ratingchg_correctD"]   = _mean(disconfirm[disconfirm['match'] == 1]['degree_change'])
        data_frame["ratingchg_incorrectC"] = _mean(confirm[confirm['match'] == 0]['degree_change'])
        data_frame["ratingchg_incorrectD"] = _mean(disconfirm[disconfirm['match'] == 0]['degree_change'])
        data_frame["total_ratingchg"]      = _mean(answered['degree_change'])

        # ---- Response time: same matched / non-matched subsets, averaged over tSlider.rt ----
        data_frame["rt_correctC"]   = _mean(confirm[confirm['match'] == 1]['tSlider.rt'])
        data_frame["rt_correctD"]   = _mean(disconfirm[disconfirm['match'] == 1]['tSlider.rt'])
        data_frame["rt_incorrectC"] = _mean(confirm[confirm['match'] == 0]['tSlider.rt'])
        data_frame["rt_incorrectD"] = _mean(disconfirm[disconfirm['match'] == 0]['tSlider.rt'])
        data_frame["total_rt"]      = _mean(answered['tSlider.rt'])

        # ---- Optional per-trial debug export (toggle via script_config["debug"]) ----
        if script_config.get("debug"):
            debug_cols = ['index', 'block', 'condition2', 'condition4', 'trialType',
                          'tSlider.response1', 'tSlider.response2', 'tSlider.response',
                          'degree_change', 'match', 'tSlider.rt']
            debug_view = answered[[c for c in debug_cols if c in answered.columns]].copy()
            save_debug_frame(
                debug_view,
                session_data_frame["participant"].iloc[0],
                format_time(session_data_frame["date"].iloc[0]),
            )
        # # data_frame["acc_disconfirm"]=            _mean(series = disconf_rows, filter = conf_rows['tSlider.response'] == -100)
        data_frame["participant"]=               session_data_frame["participant"].iloc[0]
        data_frame["date"]=                      format_time(session_data_frame["date"].iloc[0])
         
        #if dataframe is empty raise an error
        if data_frame.empty: 
            raise Exception("Data frame is empty. Cannot compute scores.")
        return data_frame
    except Exception as e:
        log("e", f"Error while computing scores: {e}") 
        return None


def save_debug_frame(answered_frame, participant, experiment_date):
    try:
        debug_dir = os.path.join(script_config["dir_paths"]["data_frame_exports"], "debug")
        os.makedirs(debug_dir, exist_ok=True)
        safe_date = re.sub(r'[\\/:*?"<>|]', '-', str(experiment_date))
        file_name = f"{participant}_DEBUG_per-trial_bade-images_MRIpract_{safe_date}.csv"
        answered_frame.to_csv(os.path.join(debug_dir, file_name), index=False)
        log("l", f"[debug] per-trial data written: {file_name}")
    except Exception as error:
        log("e", f"[debug] could not write per-trial debug file. CAUSED BY : {error}")


def save_data_frame_to_redcap_csv(data_frame):
    try:
        # FIXED: use OR instead of AND
        if data_frame is None or data_frame.empty:
            return None
        if data_frame['participant'].iloc[0]== None:
            raise Exception("[ saving data ] : participant value is None")
        if data_frame['date'].iloc[0] == None:
            raise Exception("[ saving data ] : date value is None")

        participant = data_frame['participant'].iloc[0]
        experiment_date = data_frame['date'].iloc[0]


        # Replace invalid filename characters
        safe_date = re.sub(r'[\\/:*?"<>|]', '-', str(experiment_date))

        exported_file_name = f"{participant}_redcap_bade-images_MRIpract_{safe_date}.csv"
        exported_file_path = os.path.join(
            script_config["dir_paths"]["data_frame_exports"],
            exported_file_name
        )

        data_frame.to_csv(exported_file_path, index=False)
        return data_frame

    except Exception as error:
        log("e", f"An exception occurred. Error occurred while exporting data frame. CAUSED BY : {error}")
        


##TODO : FIX THIS : if fixed script is basicaly finishjed
def save_combined_data_frame_to_redcap_csv(data_frames, file_name = "combined_redcap_ER-40_data.csv"):
    try:
        if not data_frames:
            log("e","No valid data frames to combine.")
            return
        count = 0
        for data_frame in data_frames:
            if data_frame is not None and not data_frame.empty:
                count += 1
        
        combined_data_frame = pd.concat(data_frames, ignore_index=True)
        exported_file_path = os.path.join(
            script_config['dir_paths']['data_frame_exports'],
            file_name
        )
        combined_data_frame.to_csv(exported_file_path, index=False)
        log("w",f"Combined data frame saved {count} out of {len(data_frames)} total participants.")
    except Exception as error:
        log("e",f"An exception occurred. Error while saving combined data frame to Redcap CSV. {error}")
        

#
#
# for doing the whole folder of csvs, we will read them all, map them to redcap variables and then save them all to redcap csvs
#
#
def read_data_frames_from__csvs(folder_path):
    try:
        if(not folder_path):
            log("e","invalide source path")

        data_frames = []
        folder_content_list = os.listdir(folder_path)
        
        if not folder_content_list:
            log("e","\ndata folder is empty")
            return []
        
        for file_name in folder_content_list:
            if file_name.endswith('.csv'):
                file_path = os.path.join(folder_path, file_name)
                data_frame = read_data_frame_from_csv(file_path)
                if data_frame is not None:
                    data_frames.append(data_frame)
        return data_frames
    except Exception as error:
        log("e",f"An exception occurred. Error while reading data frames from CSVs. {error}")
        
        return []

def map_data_frames_to_red_cap_variables(data_frames):
    try:
        list = [map_data_frame_to_red_cap_variable(data_frame) for data_frame in data_frames]
        return list
    except Exception:
        log("e","An exception occurred. Error while mapping data frames to Redcap variables.")
        

def save_all_data_frames_to_redcap_csv(data_frames):
    try:
        count = 0
        for data_frame in data_frames:
            dataframe = save_data_frame_to_redcap_csv(data_frame)
            if dataframe is not None:
                count += 1
        if count > 0:
            log("l",f"successfully extracted data from {count} participants out of {len(data_frames)} total participants.")
        else:
            log("w", f"*** {count} data extracted ***")
    except Exception as error:
        log("e","An exception occurred. Error while saving data frames to Redcap CSV. {}", error)
        

#script execution
#run a console window with mainmenu options
def run():
    while True:
        log("t","\n//////////////")
        log("t","Main Menu:")
        log("t","//////////////")
        log("l",f"current csv data folder: {script_config['dir_paths']['data_folder_path']}")
        log("l",f"debug output: {'ON' if script_config['debug'] else 'OFF'}")
        for option in mainmenu_options:
            print(f"{mainmenu_options[option]}. {option}")
        
        choice = input("Please select an option: ").strip()
        if choice == str(mainmenu_options["export redcap data from all participants"]):
            log("w","Option 1 selected: Export data for all saved participants.")
            # Implement the logic for exporting data for all saved participants
            # You can call the relevant functions here
            # For example, you might want to read all CSV files in a folder and export them to Redcap
            log("t","\n////////////////////////////////////////////////////////")
            log("t","Options for exporting data for all saved participants:")
            log("t","////////////////////////////////////////////////////////")
            for option in export_redcap_data_from_all_participants_submenu_options:
                print(f"{export_redcap_data_from_all_participants_submenu_options[option]}. {option}")
            sub_choice = input("Please select an option: ").strip()
            print("\n")
            if sub_choice == str(export_redcap_data_from_all_participants_submenu_options["export data for all saved participants in seperate files"]):
                log("w","Sub-option 1 selected: Exporting data for all saved participants in separate files.")
                data_frames = read_data_frames_from__csvs(script_config["dir_paths"]["data_folder_path"])
                redcap_mapped_data_frames = map_data_frames_to_red_cap_variables(data_frames)
                save_all_data_frames_to_redcap_csv(redcap_mapped_data_frames)

            elif sub_choice == str(export_redcap_data_from_all_participants_submenu_options["export data for all saved participants in 1 combined file"]):
                log("w","Sub-option 2 selected: Exporting data for all saved participants in 1 combined file.")
                data_frames = read_data_frames_from__csvs(script_config["dir_paths"]["data_folder_path"])
                redcap_mapped_data_frames = map_data_frames_to_red_cap_variables(data_frames)
                save_combined_data_frame_to_redcap_csv(redcap_mapped_data_frames)

            elif sub_choice == str(export_redcap_data_from_all_participants_submenu_options["back to main menu"]):
                log("w","Returning to main menu.")
                continue
            
            else:
                log("e","Invalid option selected. Returning to main menu.")

            
        elif choice == str(mainmenu_options["change source csv data folder"]):
            log("","\nOption 2 selected: Change data folder.")
            # Implement the logic for changing the data folder
            # You can prompt the user to enter a new folder path and update dir_paths accordingly
            print_instructions("Please enter the path to the new data folder where your CSV files are located." \
            "\nexample: C:\\Users\\my_computer_user_name\\Desktop\\PsychoPyExperimentFolder\\data")
            new_folder_path = input("Please enter the new data folder path: ")
            if not os.path.isdir(new_folder_path):
                log("e",f"The provided path '{new_folder_path}' is not a valid directory. Please try again.")
            else:
                script_config["dir_paths"]["data_folder_path"] = new_folder_path

        elif choice == str(mainmenu_options["change export folder"]):
            log("","\nOption 3 selected: Change export folder.")
            # Implement the logic for changing the export folder
            # You can prompt the user to enter a new folder path and update dir_paths accordingly
            print_instructions("Please enter the path to the new export folder where you want your Redcap CSV files to be saved." \
            "\nexample: C:\\Users\\my_computer_user_name\\Desktop\\PsychoPyExperimentFolder\\red_cap_exports")
            new_export_folder_path = input("Please enter the new export folder path: ")
            if not os.path.isdir(new_export_folder_path):
                log("e",f"The provided path '{new_export_folder_path}' is not a valid directory. Please try again.")
            else:
                script_config["dir_paths"]["data_frame_exports"] = new_export_folder_path

        elif choice == str(mainmenu_options["toggle debug output (per-trial csv)"]):
            script_config["debug"] = not script_config["debug"]
            log("l", f"Debug output is now {'ON' if script_config['debug'] else 'OFF'}. Per-trial CSVs are written to the 'debug' subfolder of your export folder.")

        elif choice == str(mainmenu_options["exit"]):
            log("l","Exiting the program. Goodbye!")
            break
        
        else:
            log("e","Invalid option selected. Please try again.")

if __name__ == "__main__":
    check_folders_exist()
    print_instructions(f"Welcome to the {project_name} Redcap Data Extractor!\nThis script allows you to export all data from {get_path_base_name(script_config['dir_paths']['data_folder_path'])} into a csv containing only the Redcap variables." \
    "\n\nPlease make sure this script is in the same folder as your data folder containing the csv files you want to export from.")
    thread = th.Thread(target=run)
    thread.start() 
 