import cx_Oracle
import platform
import os

LOCATION = r"C:\oracle\instantclient_19_5"

#print("ARCH:", platform.architecture())
#print("FILES AT LOCATION:")
for name in os.listdir(LOCATION):
#	print(name)
	os.environ["PATH"] = LOCATION + ";" + os.environ["PATH"]

def connect_to_db(db_host_name, db_port, service_name, username, password):
    dsn_tns = cx_Oracle.makedsn(db_host_name, db_port, service_name=service_name)
    conn = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)
    return conn


def disconnect_from_db(conn):
    conn.close()


def create_temp_file_with_query(local_path_to_create_file, query, filename):
    f = open(local_path_to_create_file + "\\" + filename, "a+")
    f.write(query)
    f.close()


def db_objects_create_backup(local_path_to_create_file, conn):
    main_cur = conn.cursor()
    inner_cur = conn.cursor()
    for row in main_cur.execute("select * from dba_objects where object_name='MV_REP_UNMATCHED_INVOICES'"):
        try:
            inner_cur.execute("select dbms_metadata.get_ddl('" + row[5] + "','MV_REP_UNMATCHED_INVOICES') from dual")
            for result in inner_cur:
                create_temp_file_with_query(local_path_to_create_file, result[0].read(), 'Object_Type_' + row[5] + ".sql")
        except Exception as e:
            create_temp_file_with_query(local_path_to_create_file, "Error in sql execution " + str(e), "Error_log.txt")
    main_cur.close()
    inner_cur.close()


