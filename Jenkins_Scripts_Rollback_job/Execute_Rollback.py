import pandas as pd
from paramiko import *
import os
from datetime import datetime

# import config_PRE as config

from DB_related_commands import db_scripts_rollback
from Local_path_related_commands import check_if_jenkinsfile_contents_exist
from Remote_location_related_commands import execute_ssh_command, \
    copy_file_from_local_to_remote, compile_sqldir, compile_form, check_if_file_exists_in_remote

# Importing the config based on environment to run
if os.getenv("ENV_TO_DEPLOY") == 'SIT':
    import config_SIT as config
elif os.getenv("ENV_TO_DEPLOY") == 'PRE':
    import config_PRE as config
elif os.getenv("ENV_TO_DEPLOY") == 'UAT':
    import config_UAT as config

cr_name_list = os.getenv("RMS_CR_IDENTIFIER").split(',')
# cr_name_list = 'CHG0012345'.split(',')
svn_folder = "..\\svn\\RMS\\"
svn_trunk_folder = svn_folder + "Trunk\\"
timestamp = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
ssh = SSHClient()
ssh.load_system_host_keys()
ssh.set_missing_host_key_policy(AutoAddPolicy())
ssh.connect(config.server['host'], username=config.server['username'], password=config.server['password'])
db_exec_success_status = True
remote_server_compile_files_path_main_folder = "/app/retek/rms/9.0"

for cr_name in cr_name_list:
    cr_remote_folder_path = '/deployment/' + cr_name
    cr_db_folder_path = cr_remote_folder_path + '/db/'
    svn_cr_folder = svn_folder + "tags\\" + cr_name
    excel_file = svn_folder + "tags\\" + cr_name + '\\JenkinsTemplateFile.xlsx'
    data = pd.ExcelFile(excel_file)
    # Check if files exist as in Jenkins File, if yes create dictionary of corresponding files
    db_exec_success_status, compile_files_dictionary, db_files_dictionary, db_rollback_dictionary = check_if_jenkinsfile_contents_exist(
        data, svn_cr_folder, svn_trunk_folder, cr_name)
    if db_exec_success_status:
        print("All files in Jenkins Template file are present in the required folders.")
        # Starting rollback of compile files first
        print("Execution of rollback for compile files started ---------")
        dict_keys = list(compile_files_dictionary[cr_name + '/APPS'].keys())
        dict_keys.reverse()
        for key in dict_keys:
            if not db_exec_success_status:
                break
            compile_files_dictionary[cr_name + '/APPS'][key].reverse()
            for file in compile_files_dictionary[cr_name + '/APPS'][key]:
                print("Rollback of file " + file + " started.")
                if key == 'sqldir':
                    file_exists = check_if_file_exists_in_remote(ssh,
                                                                 cr_remote_folder_path + "/batch/sqldir/" + file)
                    if file_exists:
                        copy_file_from_local_to_remote(ssh, svn_trunk_folder + "batch\\sqlldr\\" + file,
                                                       cr_remote_folder_path + "/batch/sqldir/" + file)
                        compile_sqldir(ssh, cr_remote_folder_path + "/batch/sqldir", file)
                    else:
                        print(
                            "File " + cr_remote_folder_path + "/batch/sqldir/" + file + " does not exist. Hence skipping file rollback.")
                elif key == 'scripts':
                    file_exists = check_if_file_exists_in_remote(ssh,
                                                                 cr_remote_folder_path + "/batch/scripts/" + file)
                    if file_exists:
                        copy_file_from_local_to_remote(ssh, svn_trunk_folder + "batch\\scripts\\" + file,
                                                       cr_remote_folder_path + "/batch/scripts/" + file)
                        compile_sqldir(ssh, cr_remote_folder_path + "/batch/scripts", file)
                    else:
                        print(
                            "File " + cr_remote_folder_path + "/batch/scripts/" + file + " does not exist. Hence skipping file rollback.")
                elif key == 'forms':
                    file_exists = check_if_file_exists_in_remote(ssh,
                                                                 cr_remote_folder_path + "/apps/forms/" + file)
                    if file_exists:
                        execute_ssh_command(ssh,
                                            "mv " + cr_remote_folder_path + "/apps/forms/" + file + " " + cr_remote_folder_path + "/apps/forms/" + file + "." + timestamp)
                        copy_file_from_local_to_remote(ssh, svn_trunk_folder + "apps\\forms\\" + file,
                                                       cr_remote_folder_path + "/apps/forms/" + file)
                        output = compile_form(ssh, cr_remote_folder_path + "/apps/forms/", file, 'forms')
                        if "Compile  Success.  Moved executable to $BIN" not in output:
                            print("Compiling of file " + file + " failed. Recovery ended.")
                            db_exec_success_status = False
                            execute_ssh_command(ssh,
                                                "mv " + cr_remote_folder_path + "/apps/forms/" + file + "." + timestamp + " " + cr_remote_folder_path + "/apps/forms/" + file)
                            break
                    else:
                        print(
                            "File " + cr_remote_folder_path + "/apps/forms/" + file + " does not exist. Hence skipping file rollback.")
                elif key == 'proc':
                    file_exists = check_if_file_exists_in_remote(ssh,
                                                                 cr_remote_folder_path + "/batch/proc/" + file)
                    if file_exists:
                        execute_ssh_command(ssh,
                                            "mv " + cr_remote_folder_path + "/batch/proc/" + file + " " + cr_remote_folder_path + "/batch/proc/" + file + "." + timestamp)
                        copy_file_from_local_to_remote(ssh, svn_trunk_folder + "batch\\proc\\" + file,
                                                       cr_remote_folder_path + "/batch/proc/" + file)
                        output = compile_form(ssh, cr_remote_folder_path + "/batch/proc/", file, 'proc')
                        if "Pre-ProCess, Compile, Link. Done. Moved exe to $BIN" not in output:
                            print("Compiling of file " + file + " failed. Recovery ended.")
                            db_exec_success_status = False
                            execute_ssh_command(ssh,
                                                "mv " + cr_remote_folder_path + "/batch/proc/" + file + "." + timestamp + " " + cr_remote_folder_path + "/batch/proc/" + file)
                            break
                    else:
                        print(
                            "File " + cr_remote_folder_path + "/batch/proc/" + file + " does not exist. Hence skipping file rollback.")

    if db_exec_success_status:
        # Starting rollback of db scripts
        db_exec_success_status = db_scripts_rollback(db_files_dictionary, db_rollback_dictionary, ssh,
                                                     cr_db_folder_path, svn_trunk_folder,
                                                     svn_cr_folder,
                                                     db_exec_success_status, config, timestamp)
if db_exec_success_status:
    print("Rollback over successfully.")
else:
    print("Rollback not over successfully.")

ssh.close()
