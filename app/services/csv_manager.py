import csv


class CSVManager:
    @staticmethod
    def read(file_path : str, skip_header : bool = False):
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            if skip_header:
                next(reader)
            return list(reader)