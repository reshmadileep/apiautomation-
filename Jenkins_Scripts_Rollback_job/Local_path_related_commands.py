from Generic_functions import convert_to_list, add_to_dictionary, get_key_value
import pandas as pd
import os


def verify_if_file_present_in_location(list_of_file_locations_to_verify, main_folder_path,
                                       file_present_in_folder_status, sheet_name, cr_name, folder_name,
                                       each_folder_dictionary):
    if file_present_in_folder_status:
        for each_file_path in list_of_file_locations_to_verify:
            if not os.path.exists(main_folder_path + each_file_path.replace("/", "\\")):
                file_present_in_folder_status = False
                print("File absent in " + main_folder_path + each_file_path.replace("/", "\\"))
                break
            else:
                try:
                    filename = each_file_path.split("/")[1] if sheet_name != 'APPS' else each_file_path
                except:
                    filename = each_file_path
                add_to_dictionary(cr_name + '/' + sheet_name, folder_name, each_file_path, each_folder_dictionary)
    return file_present_in_folder_status, each_folder_dictionary


def extract_file_names_from_template_file_and_verify_if_files_present(file_present_in_folder_status, list_of_files,
                                                                      path_of_file, sheet_name, cr_name, folder_name,
                                                                      each_folder_dictionary):
    # Do not execute if any previous error
    if not file_present_in_folder_status:
        return file_present_in_folder_status, each_folder_dictionary
    if not pd.isnull(list_of_files) or list_of_files != '':
        list_of_files_present = convert_to_list(list_of_files)
        if len(list_of_files_present) > 0:
            file_present_in_folder_status, each_folder_dictionary = verify_if_file_present_in_location(
                list_of_files_present,
                path_of_file,
                file_present_in_folder_status,
                sheet_name, cr_name, folder_name,
                each_folder_dictionary)
    return file_present_in_folder_status, each_folder_dictionary


def check_if_jenkinsfile_contents_exist(data_in_jenkins_file, svn_cr_folder, svn_trunk_folder, cr_name):
    # Initializing values
    file_present_in_folder_status = True
    db_folder_list = ['TABLES', 'TYPES', 'PACKAGES', 'SEQUENCES', 'FUNCTIONS', 'TRIGGERS', 'SYNONYMS', 'VIEWS',
                      'PACKAGEBODIES', 'SQL']
    # compile_file_folder_list = ['FORMS', 'PROC', 'SCRIPTS', 'SQLDIR']
    compile_files_dictionary = {}
    db_files_dictionary = {}
    db_rollback_dictionary = {}
    # Checking for file existing status and creating dictionaries to rollback
    for sheet_name in data_in_jenkins_file.sheet_names:
        if not file_present_in_folder_status:
            break
        if sheet_name != 'APPS':
            db_rollback_dictionary[cr_name + "/" + sheet_name] = {}
            db_files_dictionary[cr_name + "/" + sheet_name] = {}
        else:
            compile_files_dictionary[cr_name + "/" + sheet_name] = {}
        data_in_each_schema = data_in_jenkins_file.parse(sheet_name)
        for index_value, row_value in data_in_each_schema.iterrows():
            if not file_present_in_folder_status:
                break
            if sheet_name != 'APPS':
                folder_name = get_key_value(row_value['Key_Reference_Value'], db_folder_list)
                # Checking if db folder files are present for each schema
                file_present_in_folder_status, db_files_dictionary = extract_file_names_from_template_file_and_verify_if_files_present(
                    file_present_in_folder_status,
                    row_value['Values'],
                    svn_trunk_folder + "db\\" + sheet_name + "\\", sheet_name, cr_name, folder_name[0],
                    db_files_dictionary)
                # Checking if db folder rollback files are present for each schema
                file_present_in_folder_status, db_rollback_dictionary = extract_file_names_from_template_file_and_verify_if_files_present(
                    file_present_in_folder_status,
                    row_value['Rollback_Details'],
                    svn_cr_folder + "\\db\\" + sheet_name + "\\rollback\\", sheet_name, cr_name, folder_name[0],
                    db_rollback_dictionary)
            else:
                # check if forms are present
                if 'forms' in row_value['Data_to_Fill']:
                    file_present_in_folder_status, compile_files_dictionary = extract_file_names_from_template_file_and_verify_if_files_present(
                        file_present_in_folder_status,
                        row_value['Values'],
                        svn_trunk_folder + "apps\\forms\\", sheet_name, cr_name, 'forms', compile_files_dictionary)
                # check if proc are present
                if 'proc' in row_value['Data_to_Fill']:
                    file_present_in_folder_status, compile_files_dictionary = extract_file_names_from_template_file_and_verify_if_files_present(
                        file_present_in_folder_status,
                        row_value['Values'],
                        svn_trunk_folder + "batch\\proc\\", sheet_name, cr_name, 'proc', compile_files_dictionary)
                # check if sqldir are present
                if 'sqldir' in row_value['Data_to_Fill']:
                    file_present_in_folder_status, compile_files_dictionary = extract_file_names_from_template_file_and_verify_if_files_present(
                        file_present_in_folder_status,
                        row_value['Values'],
                        svn_trunk_folder + "batch\\sqlldr\\", sheet_name, cr_name, 'sqldir', compile_files_dictionary)
                # check if scripts are present
                if 'scripts' in row_value['Data_to_Fill']:
                    file_present_in_folder_status, compile_files_dictionary = extract_file_names_from_template_file_and_verify_if_files_present(
                        file_present_in_folder_status,
                        row_value['Values'],
                        svn_trunk_folder + "batch\\scripts\\", sheet_name, cr_name, 'scripts',
                        compile_files_dictionary)

    return file_present_in_folder_status, compile_files_dictionary, db_files_dictionary, db_rollback_dictionary
