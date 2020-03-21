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


def copy_file_from_local_to_remote(client, local_path, remote_path):
    try:
        print("copying " + local_path + " to " + remote_path)
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print("copied")
    except Exception as e:
        print("Error message while copying = " + str(e))


def delete_existing_remote_folder(client, path):
    sftp = client.open_sftp()
    try:
        sftp.stat(path)
        execute_ssh_command(client, 'rm -r ' + path)
    except Exception as e:
        print(path + " not previously existing.")
    sftp.close()


def compile_sqldir(client, compile_file_folder, file_name):
    out, std_error = execute_ssh_commands(client, '''
                cd {compile_file_folder}
                dos2unix {file_name}
                chmod 775 {file_name}
                exit
                '''.format(compile_file_folder=compile_file_folder, file_name=file_name))
    out = [i.decode() for i in out]
    out = '\n'.join(out)
    print(out)
    return out


def compile_form(client, compile_file_folder, file_name, compile_file_type):
    compile_command = 'compfrm' if compile_file_type == 'forms' else 'ccomp'
    environment = 'as' if compile_file_type == 'forms' else 'ds'
    out, std_error = execute_ssh_commands(client, '''
            cd {compile_file_folder}
            chgenv -g djpre rms {environment}
            {compile_command} -b {file_name}
            exit
            '''.format(compile_file_folder=compile_file_folder, file_name=file_name, environment=environment,
                       compile_command=compile_command))
    out = [i.decode() for i in out]
    out = '\n'.join(out)
    print(out)
    return out


def check_if_file_exists_in_remote(client, path_to_file):
    file_exists = True
    sftp = client.open_sftp()
    try:
        sftp.stat(path_to_file)
    except Exception as e:
        print(path_to_file + " not previously existing.")
        file_exists = False
    finally:
        sftp.close()
    return file_exists
