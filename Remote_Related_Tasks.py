

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


def compile_reports(client, compile_file_folder, file_name):
    out, std_error = execute_ssh_commands(client, '''
                cd {compile_file_folder}
                chgenv -g djpre sim as
                comprep -b {file_name}
                exit
                '''.format(compile_file_folder=compile_file_folder, file_name=file_name))
    out = [i.decode() for i in out]
    out = '\n'.join(out)
    print(out)
    return out


def get_file_type_to_compile(file_extension):
    switcher = {
        'fmx': 'forms',
        'rep': 'reports'
    }
    return switcher.get(file_extension, "proc")


def get_bin_file_name(file_type, compile_file_name):
    switcher = {
        'forms': compile_file_name.split('.')[0] + ".fmx",
        'reports': compile_file_name.split('.')[0] + ".rep",
        'proc': compile_file_name.split('.')[0]
    }
    return switcher.get(file_type, "Invalid file type")


def check_if_file_exist(path, client):
    file_present_status = True
    sftp = client.open_sftp()
    try:
        sftp.stat(path)
    except Exception as e:
        print(path + " not previously existing.")
        file_present_status = False
    finally:
        sftp.close()
        return file_present_status