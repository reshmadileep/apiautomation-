
from Remote_location_related_commands import execute_ssh_commands, \
    copy_file_from_local_to_remote, execute_ssh_command, check_if_file_exists_in_remote


def get_schema_credentials(schema, config):
    switcher = {
        'DJ_RMS': [config.DJ_RMS['username'], config.DJ_RMS['password']],
        'ORACLE_RMS': [config.ORACLE_RMS['username'], config.ORACLE_RMS['password']],
        'DJ_SIM': [config.DJ_SIM['username'], config.DJ_SIM['password']],
        'DJ_AIT': [config.DJ_AIT['username'], config.DJ_AIT['password']]
    }
    credentials = switcher.get(schema, [])
    user_name = credentials[0]
    password = credentials[1]
    return user_name, password


def execute_db_commands(client, username, password, remote_path_of_execution, db_query):
    output, error = execute_ssh_commands(client, '''
            chgenv -g djpre rms ds
            cd {path_of_execution}
            echo @{db_query} | sqlplus {username}/{password}@$ORACLE_SID
            exit
            '''.format(path_of_execution=remote_path_of_execution, db_query=db_query, username=username,
                       password=password))
    output = [i.decode() for i in output]
    output = " ".join(output)
    return output, error


def rollback_execution(scripts_execution_path, rollback_script, rollback_success, client, username, password):
    if not rollback_success:
        return rollback_success
    out, error = execute_db_commands(client, username, password, scripts_execution_path, rollback_script)
    if "error" in out or 'ERROR' in out:
        print(
            "Recovery failed with file " + rollback_script + ". Recovery step ended.")
        rollback_success = False
    else:
        print("Recovery of file " + rollback_script + " successful.")
    return rollback_success


def db_scripts_rollback(executed_commands_dictionary, rollback_dictionary, client, cr_db_folder_path, svn_trunk_folder,
                        svn_cr_folder,
                        previous_exec_status, config_details, timestamp):
    if previous_exec_status:
        rollback_success = True
        queries_to_execute = list(executed_commands_dictionary.keys())
        queries_to_execute.reverse()
        for key in queries_to_execute:
            schema_name = key.split("/")[1]
            if rollback_success:
                print("Rollback started for db commands in " + schema_name + ".")
                execution_path = cr_db_folder_path + schema_name
                rollback_success = rollback_performed_in_each_schema(schema_name,
                                                                     executed_commands_dictionary[key],
                                                                     rollback_dictionary[key],
                                                                     execution_path, rollback_success, client,
                                                                     svn_trunk_folder, svn_cr_folder, timestamp,
                                                                     config_details)
            else:
                break


def rollback_performed_in_each_schema(schema, executed_commands_dictionary, rollback_dictionary, execution_path,
                                      rollback_success, client, svn_trunk_folder, svn_cr_folder, timestamp,
                                      config_details):
    username, password = get_schema_credentials(schema, config_details)
    # Rollback mechanism : Check if rollback scripts available, else execute from trunk for each sheet
    queries_to_execute = list(executed_commands_dictionary.keys())
    queries_to_execute.reverse()
    for key in queries_to_execute:
        # Check if rollback failed at any point
        if not rollback_success:
            break
        if key in rollback_dictionary:
            print(
                "Rollback scripts available for " + key + " in rollback folder. Execution of rollback scripts started.")
            scripts_execution_path = execution_path + "/rollback"
            for rollback_script in rollback_dictionary[key]:
                if rollback_success:
                    file_exists = check_if_file_exists_in_remote(client,
                                                                 scripts_execution_path + "/" + rollback_script)
                    if file_exists:
                        copy_file_from_local_to_remote(client,
                                                       svn_cr_folder + "\\db\\" + schema + "\\rollback\\" + rollback_script,
                                                       scripts_execution_path + "/" + rollback_script)
                        rollback_success = rollback_execution(scripts_execution_path, rollback_script, rollback_success,
                                                              client, username, password)
                    else:
                        print(
                            "File " + scripts_execution_path + "/" + rollback_script + "does not exist. Hence skipping this rollback.")
                else:
                    break
        else:
            print(
                "Fetching back up files from SVN-> Trunk as no back up available for " + key + " in excel input file.")
            executed_commands_dictionary[key].reverse()
            for fail_query in executed_commands_dictionary[key]:
                if rollback_success:
                    local_path = svn_trunk_folder + "db\\" + schema + "\\" + fail_query.replace("/", "\\")
                    file_exists = check_if_file_exists_in_remote(client,
                                                                 execution_path + "/" + fail_query)
                    if file_exists:
                        # execute_ssh_command(client, "mv "+execution_path + "/" + schema + "/" + fail_query +" "+ execution_path + "/" + schema + "/" + fail_query+"."+timestamp)
                        copy_file_from_local_to_remote(client, local_path,
                                                       execution_path + "/" + fail_query)
                        rollback_success = rollback_execution(execution_path, fail_query, rollback_success, client,
                                                              username, password)
                    else:
                        print(
                            "File " + execution_path + "/" + fail_query + " does not exist. Hence skipping this file.")
                else:
                    break
    return rollback_success
