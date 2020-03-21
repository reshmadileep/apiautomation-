
def add_to_dictionary(main_key, inner_key, value, dictionary):
    if main_key in dictionary:
        if inner_key in dictionary[main_key]:
            dictionary[main_key][inner_key].append(value)
        else:
            dictionary[main_key][inner_key] = [value]
    else:
        dictionary[main_key] = {inner_key: [value]}


def get_key_value(string_containing_key, list_containing_key):
    # Get dictionary key value
    dict_key = [key for key in list_containing_key if (key in string_containing_key)]
    return dict_key


def convert_to_list(row_item):
    try:
        list_item = row_item.split('\n')
        while "" in list_item:
            list_item.remove("")
    except:
        # print("Skipping converting to list as no value to convert.")
        list_item = []
    return list_item
