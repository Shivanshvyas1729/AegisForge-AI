import json
import csv
import os

def read_or_write_file(file_path: str, mode: str = 'r', data: any = None, file_type: str = None) -> any:
    """
    Reads from or writes to a file of various types (txt, json, csv).
    
    Args:
        file_path (str): The path to the file.
        mode (str): 'r' for read, 'w' for write, 'a' for append. Defaults to 'r'.
        data (any): The data to write to the file (used in 'w' or 'a' modes).
        file_type (str, optional): The type of file ('txt', 'json', 'csv'). 
                                   If None, infers from file extension.
                                   
    Returns:
        The content of the file if mode is 'r', else True on success.
    """
    if not file_type:
        _, ext = os.path.splitext(file_path)
        file_type = ext.lower().strip('.')
        if not file_type:
            file_type = 'txt'
            
    if mode in ['w', 'a', 'wb', 'ab']:
        if data is None:
            raise ValueError("Data must be provided for write/append modes.")
            
        try:
            if file_type == 'json':
                with open(file_path, 'w' if mode == 'w' else 'a', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            elif file_type == 'csv':
                with open(file_path, 'w' if mode == 'w' else 'a', newline='', encoding='utf-8') as f:
                    if isinstance(data, list) and all(isinstance(i, dict) for i in data):
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        if mode == 'w':
                            writer.writeheader()
                        writer.writerows(data)
                    elif isinstance(data, list) and all(isinstance(i, list) for i in data):
                        writer = csv.writer(f)
                        writer.writerows(data)
                    else:
                        raise ValueError("Data for CSV must be a list of dictionaries or list of lists.")
            else:
                # Default to text
                with open(file_path, mode, encoding='utf-8') as f:
                    f.write(str(data))
            return True
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    elif mode in ['r', 'rb']:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")
            
        try:
            if file_type == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif file_type == 'csv':
                with open(file_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            else:
                # Default to text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    else:
        raise ValueError("Invalid mode. Use 'r', 'w', or 'a'.")
