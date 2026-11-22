import csv
import sys


##############################
##  CLASS WEATHER LOCATION  ##
##############################
# This is the class that will be instantiated for each test data input row

class weather_location:
    __slots__ = ('latitude', 'longitude', 'city', 'state')

    def __init__(self, input_list: list[str]):
        if not input_list:
            raise ValueError("input_list was None")
        if len(input_list) != 4:
            raise ValueError(f"input_list contains {len(input_list)} items but 4 are expected: {input_list}")

        self.latitude = input_list[0].strip()
        self.longitude = input_list[1].strip()
        self.city = input_list[2].strip()
        self.state = input_list[3].strip()


##########################################################################################################
##  FUNCTIONS FOR READING TEST DATA FROM A CSV FILE AND CREATING A LIST OF CLASS OBJECTS FROM DATA ROWS  ##
##########################################################################################################

def get_class(class_name: str):
    return getattr(sys.modules[__name__], class_name)

def load_csv_and_return_list_of_class_objects(class_name: str, csv_file_name: str, has_header_row: bool =False) -> list:
    skip_first_row = has_header_row
    data_list = []
    with open(csv_file_name, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if (skip_first_row):
                skip_first_row = False
                continue
            if (len(row) > 0 and len(row[0].strip()) > 0):
                cls = get_class(class_name)
                data_list.append(cls(row))

    return data_list
