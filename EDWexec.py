import re
import pandas as pd
from paramiko import *
import os
from datetime import datetime
import config_EDW_PRE as config

# Importing the config based on environment to run
if os.getenv("ENV_TO_DEPLOY") == 'SIT':
    import config_EDW_SIT as config
elif os.getenv("ENV_TO_DEPLOY") == 'PRE':
    import config_EDW_PRE as config
elif os.getenv("ENV_TO_DEPLOY") == 'UAT':
    import config_EDW_UAT as config


def execute_ssh_command(client, command):
    print("command : " + command)
    stdin, stdout, stderr = client.exec_command(command)
    print("stdout : ")
    print(stdout.readlines())
    print("stderr : ")
    print(stderr.readlines())
    return stdout, stderr


def execute_ssh_commands(client, commands):
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdout = channel.makefile('rb')
    stderr = channel.makefile('rb')
    stdin.write(commands)
    std_output = stdout.readlines()
    std_error = stderr.readlines()
    print(std_output)
    stdout.close()
    stderr.close()
    stdin.close()
    return std_output, std_error


def compile_file(client, compile_file_folder, file_name):
    out, std_error = execute_ssh_commands(client, '''
            cd {compile_file_folder} 
            tr -d '\\r' < {file_name} > {file_name}.new
            chmod 770 {file_name}.new
            ./{file_name}.new
            exit
            '''.format(compile_file_folder=compile_file_folder, file_name=file_name))
    out = [i.decode() for i in out]
    out = '\n'.join(out)
    print(out)
    return out


def copy_file_from_local_to_remote(client, local_path, remote_path):
    print("copying " + local_path + " to " + remote_path)
    sftp = ssh.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    print("copied")


def delete_existing_remote_folder(path):
    sftp = ssh.open_sftp()
    try:
        sftp.stat(path)
        execute_ssh_command(ssh, 'rm -r ' + path)
    except Exception as e:
        print("CR folder not previously existing.")
    sftp.close()


def check_if_file_exists_in_remote(path):
    sftp = ssh.open_sftp()
    try:
        sftp.stat(path)
    except Exception as e:
        print(path + " does not exist.")
    sftp.close()


def convert_to_list(row_item):
    list_items = row_item.split('\n')
    while "" in list_items:
        list_items.remove("")
    return list_items


def create_cr_folder_in_remote_and_assign_permissions(client, change_request_name, path_in_remote):
    cr_folder_path = path_in_remote + change_request_name
    delete_existing_remote_folder(cr_folder_path)
    out, std_error = execute_ssh_commands(client, '''
                cd {deployment_folder}
                mkdir {cr_name}
                chgrp batch {cr_name}
                chmod 770 {cr_name}
                exit
                '''.format(deployment_folder=path_in_remote, cr_name=change_request_name))
    out = [i.decode() for i in out]
    out = '\n'.join(out)
    print(out)
    return out


def assign_permissions_to_files(client, path_of_files):
    out, std_error = execute_ssh_commands(client, '''
                    cd {path_of_files}
                    chgrp -R batch ./*
                    chmod -R 770 ./*
                    exit
                    '''.format(path_of_files=path_of_files))
    out = [i.decode() for i in out]
    out = '\n'.join(out)
    print(out)
    return out


def check_if_jenkinsfile_contents_exists(data_in_file):
    file_present_in_folder_status = True
    files_to_install = []
    files_to_rollback = []
    data_to_compile_as_dataframe = pd.DataFrame(data_in_file, columns=['Values', 'Rollback_Details'])
    for index, row in data_to_compile_as_dataframe.iterrows():
        if not pd.isnull(row['Values']) or row['Values'] == '':
            files_to_install = convert_to_list(row['Values'])
            if len(files_to_install) == 0:
                continue
            if os.path.exists(svn_cr_folder + '\\deployment\\' + row['Values']):
                continue
            else:
                file_present_in_folder_status = False
                print("File: " + row['Values'] + " not present in the deployment folder.")
                break
        if not pd.isnull(row['Rollback_Details']) or row['Rollback_Details'] == '':
            files_to_rollback = convert_to_list(row['Values'])
            if len(files_to_rollback) == 0:
                continue
            if os.path.exists(svn_cr_folder + '\\deployment\\rollback' + row['Rollback_Details']):
                continue
            else:
                file_present_in_folder_status = False
                print("File: " + row['Rollback_Details'] + " not present in the rollback folder.")
                break
    return file_present_in_folder_status, files_to_install, files_to_rollback


def copy_folder_and_files(client, changerequest_name):
    path = '/deployment/' + changerequest_name
    sub_directories = [x[0] for x in os.walk(svn_cr_folder)]
    list_of_folders_with_files = []
    # Creating folders in remote path
    for folder in sub_directories:
        if len(os.listdir(folder)) > 0:
            print(folder)
            folder = folder.replace(svn_cr_folder, "")
            if folder != "":
                list_of_folders_with_files.append(folder)
                execute_ssh_command(client, 'mkdir ' + path + "/" + folder.replace("\\", "/"))
    # Copy files from local to remote
    for directory_with_file in list_of_folders_with_files:
        for file in os.listdir(svn_cr_folder + directory_with_file):
            try:
                copy_file_from_local_to_remote(client, svn_cr_folder + directory_with_file + "\\" + file,
                                               path + "/" + directory_with_file.replace("\\", "/") + "/" + file)
            except Exception as e:
                continue


# cr_name_list = os.getenv("CR_IDENTIFIER").split(',')
cr_name_list = 'CHG0034741'.split(',')
svn_folder = ".\\svn\\EDW\\"
timestamp = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
ssh = SSHClient()
ssh.load_system_host_keys()
ssh.set_missing_host_key_policy(AutoAddPolicy())
ssh.connect(config.server['host'], username=config.server['username'], password=config.server['password'])
build_execution_status = True
rollback_dict = {}
files_executed_dict = {}
remote_shell_scripts_deployment_path = '/djs/pre/bin'

for cr_name in cr_name_list:
    print("Deployment started for CR: " + cr_name)
    cr_remote_deployment_path = '/deployment/'
    cr_deployment_remote_folder_path = cr_remote_deployment_path + cr_name
    svn_cr_folder = svn_folder + "tags\\" + cr_name
    excel_file = svn_folder + "tags\\" + cr_name + '\\JenkinsTemplateFile.xlsx'
    data = pd.ExcelFile(excel_file)
    data_sheet = data.parse('EDW')
    # Checking if files in Jenkins Template file are present in local
    file_present_status, list_to_install, files_to_backup = check_if_jenkinsfile_contents_exists(data_sheet)
    if file_present_status:
        rollback_dict = {cr_name: files_to_backup}
    else:
        build_execution_status = False
    if build_execution_status and len(list_to_install) > 0:
        # Creating CR folder in remote directory, Assign permissions to folder
        print("Creating the CR folder in the server")
        create_cr_folder_in_remote_and_assign_permissions(ssh, cr_name, cr_remote_deployment_path)
        # Copying files from local to remote
        print("Copying the folders from local to server.....")
        copy_folder_and_files(ssh, cr_name)
        # Assign permissions to files
        assign_permissions_to_files(ssh, cr_remote_deployment_path + cr_name)
        # Compile Files
        print("Compiling begins.....")
        for file_to_compile in list_to_install:
            if build_execution_status:
                output = compile_file(ssh, cr_remote_deployment_path + cr_name + "/deployment", file_to_compile)
                if cr_name in files_executed_dict:
                    files_executed_dict[cr_name].append(file_to_compile)
                else:
                    files_executed_dict[cr_name] = [file_to_compile]
                if "Install Failure     : 0" not in output:
                    print("Rollback starting due to some failure in build....")
                    build_execution_status = False
                    for backup_cr_name in rollback_dict.keys():
                        if rollback_dict[backup_cr_name] != "":
                            for backup_file_to_compile in rollback_dict[backup_cr_name]:
                                print("Compiling of back up for " + backup_cr_name + " started.")
                                if backup_file_to_compile != "":
                                    output = compile_file(ssh,
                                                          cr_remote_deployment_path + backup_cr_name + "/deployment",
                                                          backup_cr_name)
                                    if "Install Failure     : 0" not in output:
                                        print("Back up for CR " + backup_cr_name + " failed. Rollback process stopped.")
                                        break
                                else:
                                    print(
                                        "Back up file not available for CR " + backup_cr_name + ". Hence skipping backup for the same.")

        # Check if any shell script to be executed.
    shell_files_list = os.listdir(svn_cr_folder + "\\unix\\shell")
    if len(shell_files_list) > 0 and build_execution_status:
        print("Copying of Shell scripts started....")
        for shell_script in shell_files_list:
            if shell_script.endswith(".sh"):
                execute_ssh_command(ssh,
                                    "cp -p " + remote_shell_scripts_deployment_path + "/" + shell_script + " " + remote_shell_scripts_deployment_path + "/" + shell_script + "." + timestamp)
                print("Copying of file: " + shell_script + " started.")
                copy_file_from_local_to_remote(ssh, svn_cr_folder + "\\unix\\shell\\" + shell_script,
                                               remote_shell_scripts_deployment_path + "/" + shell_script)

if build_execution_status:
    print("Jenkins execution over successfully in Pre.")
else:
    print("Jenkins execution not over successfully in Pre.")
ssh.close()
