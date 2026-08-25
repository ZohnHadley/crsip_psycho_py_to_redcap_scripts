#script version 2.0.2

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
project_name = "ER40"
script_name = "{} ER40 to Redcap".format(project_name)
script_config = {
    "debug": False,   # when True, also export a per-trial CSV (trial correctness) for spot-checking
    "google_sheet_url": "",
    "redcap_api_url": "",
    "redcap_api_key": "",
    "red_cap_variables" : {
            "record_id":"",
            "redcap_event_name":"",
            ###### keys that will change
            # "er_40_":"", -- this one will be generated
            "er_40_total":"",
            "er_40_zscore":""
    },
    "dir_paths":{
        "project_folder_path": os.path.join(base_path, 'ER-40'),
        "data_folder_path": os.path.join(base_path, 'ER-40','data'),
        "data_frame_exports": os.path.join(base_path, 'ER-40_red_cap_exports')
    }
}

session_types = {
    "_m2":"m2_arm_1", 
    "_pre":"pre_arm_1", 
    "_post":"post_arm_1", 
    "_base":"base_arm_1", 
    "":"all_arm_1",
    "_":"unknown",
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
    log_type = log_type.lower()
    if log_type == "w":
        prefix_bg_color = Back.YELLOW
        prifix_text_color = Fore.WHITE
        bg_color = Back.RESET
        text_color = Fore.YELLOW

        prefix = "Warn : "
    elif log_type == "e":
        prefix_bg_color = Back.RED 
        prifix_text_color = Fore.WHITE
        bg_color = Back.RESET
        text_color = Fore.RED

        prefix = "Error : "
    elif log_type == "l":
        prefix_bg_color = Back.LIGHTBLUE_EX 
        prifix_text_color = Fore.WHITE
        bg_color = Back.RESET
        text_color = Fore.LIGHTBLUE_EX

        prefix = "Info : "
    elif log_type == "t":
        prefix_bg_color = Back.GREEN
        prifix_text_color = Fore.WHITE
        bg_color = Back.RESET
        text_color = Fore.GREEN
    elif log_type == "":
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

###updated
def check_folders_exist():
    for key, path in script_config["dir_paths"].items():
        if not os.path.isdir(path):
            if key :
                log("e",f"Folder not found at '{path}'. Please make sure the \'{get_path_base_name(path)}\\\' folder exists.")
                if key == "data_frame_exports":
                    log("l",f"making directory the \'{get_path_base_name(path)}\\\' folder")
                    os.makedirs(path, exist_ok=True)
                continue
###updated

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
    global session_types
    try:
        if session_data_frame is None or session_data_frame.empty:
            log("e", "~~~~~~~~~~~~~~~~~~~~")
            log("e", " [mapping data frame]")
            log("e", " cvs found with no data = empty data frame")
            log("e", " ... skipping empty data frame")
            log("e", "~~~~~~~~~~~~~~~~~~~~")
            return None

        required_columns = has_required_columns(session_data_frame, ['date', 'participant', 'timepoints', 'score', 'scoreZ', 'trialCorrectAns'])

        if required_columns["val"]:
            raise Exception(f"Missing required columns: {required_columns['columns']}")

        #print(session_data_frame.columns.tolist()) 
        
        redcap_event_name = session_types.get(session_data_frame['timepoints'].iloc[0])
        data_frame = pd.DataFrame([script_config["red_cap_variables"]])
        data_frame = data_frame.fillna('')
  
        responses = get_column_list(session_data_frame, 'trialCorrectAns')
        if not responses:
            log("e",f"No valid responses found in the data frame for participant {session_data_frame['participant']}.")
            return None
        responses = [response for response in responses if response != '' and not pd.isna(response)]
        for i in range(len(responses)):
            response = responses[i]
            if response != None and response != '' and not pd.isna(response):
                if response == 1:
                    data_frame[f'er_40_{i+1}'] = 1
                elif response == 0:
                    data_frame[f'er_40_{i+1}'] = 0
            else:
                log("e",f"Invalid response value '{response}' found for participant {session_data_frame['participant']} at index {i}. Expected 0 or 1.")
                return None
        # script_config["red_cap_variables"]["record_id"] = session_data_frame['participant']
        #go throut list and get first instance of date and format 
        dates = get_column_list(session_data_frame, 'date')
        dates = [date for date in dates if date != '' and not pd.isna(date)]

        data_frame['record_id'] = session_data_frame['participant']
        data_frame['date'] = format_time(dates[0])
        data_frame['redcap_event_name'] = redcap_event_name
        data_frame['er_40_total'] = session_data_frame['score'].iloc[-1]
        data_frame['er_40_zscore'] = session_data_frame['scoreZ'].iloc[-1]
        log("", f"extracted data : participant[{data_frame['record_id'].iloc[0]}], event name [{data_frame['redcap_event_name'].iloc[0]}]")

        # ---- Optional per-trial debug export (toggle via script_config["debug"]) ----
        # writes the scored trials with the er_40_N variable each one was mapped to,
        # so a row in the redcap export can be traced back to its source trial.
        if script_config.get("debug"):
            scored_trials = session_data_frame[
                session_data_frame['trialCorrectAns'].apply(lambda value: value != '' and not pd.isna(value))
            ].copy()
            scored_trials.insert(0, 'er_40_variable', [f"er_40_{i+1}" for i in range(len(scored_trials))])
            save_debug_frame(
                scored_trials,
                data_frame['record_id'].iloc[0],
                data_frame['date'].iloc[0],
            )
        # for key, value in session_types.items():
        #     if session_data_frame['timepoints'].iloc[0] == key:
        #         print(f"{key} is equal to {value}")
                
    
        #if dataframe is empty raise an error
        if data_frame.empty:
            raise Exception("Data frame is empty. Cannot compute scores.")

        return data_frame
    except Exception as e:
        log("e",f"Error while computing scores: {e}")
        if script_config.get("debug"):
            traceback.print_exc()
        return None


def save_debug_frame(scored_trials_frame, participant, experiment_date):
    try:
        debug_dir = os.path.join(script_config["dir_paths"]["data_frame_exports"], "debug")
        os.makedirs(debug_dir, exist_ok=True)
        safe_date = re.sub(r'[\\/:*?"<>|]', '-', str(experiment_date))
        file_name = f"{participant}_DEBUG_per-trial_ER-40_{safe_date}.csv"
        scored_trials_frame.to_csv(os.path.join(debug_dir, file_name), index=False)
        log("l", f"[debug] per-trial data written: {file_name}")
    except Exception as error:
        log("e", f"[debug] could not write per-trial debug file. CAUSED BY : {error}")


def save_data_frame_to_redcap_csv(data_frame):
    try:
        # FIXED: use OR instead of AND
        if data_frame is None or data_frame.empty:
            return None
        if data_frame['record_id'].iloc[0] == None:
            raise Exception("[ saving data ] : record_id value is None")
        if data_frame['date'].iloc[0] == None:
            raise Exception("[ saving data ] : date value is None")

        participant = data_frame['record_id'].iloc[0]
        experiment_date = data_frame['date'].iloc[0]

        # Replace invalid filename characters
        safe_date = re.sub(r'[\\/:*?"<>|]', '-', str(experiment_date))

        exported_file_name = f"{participant}_redcap_ER-40_{safe_date}.csv"
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
        log("e",f"An exception occurred. Error while saving data frames to Redcap CSV. {error}")

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
 