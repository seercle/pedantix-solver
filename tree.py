from datasets import load_dataset
import string
import json
from multiprocessing import Pool
# Load the dataset
ds = load_dataset("wikimedia/wikipedia", "20231101.fr")
dataset = ds['train']

# Define the dataset features names
feature_title = 'title'
feature_text = 'text'

output_file = 'processed_data.json' # Define the output file name
lock_file = 'processed_data.lock' # Define the lock file name
max_depth = 20 # Define the max tree depth
num_workers = 16 # Define the number of workers
batch_size = 10000 # Define the worker batch size

# Split a number into n chunks
def split_range(number, chunks_count):
    chunk_size = number // chunks_count
    chunk_ranges = [(i * chunk_size, (i + 1) * chunk_size) for i in range(chunks_count)]
    # Handle the last chunk to include any remaining data
    chunk_ranges[-1] = (chunk_ranges[-1][0], number)
    return chunk_ranges

"""
def split_dataset(dataset, num_chunks):
    return [dataset.shard(num_chunks=num_chunks, index=i) for i in range(num_chunks)]
"""

def process_title(title):
    # Replace punctuation with spaces and split the title into words
    text = title.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    return text.split()

def merge_dicts(dict1, dict2):
    # Merge two dictionaries
    for key, value in dict2.items():
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(value, dict):
                dict1[key] = merge_dicts(dict1[key], value)
            elif isinstance(dict1[key], list) and isinstance(value, list):
                dict1[key] = dict1[key] + value
            else:
                dict1[key] = value
        else:
            dict1[key] = value
    return dict1

# Process the text by returning the length of the first {max_depth} words
def process_text(text):
    text = text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    return [len(word) for word in (text.split()[:max_depth])] # Return the length of the first {max_depth} characters

# Convert the processed data to a json format
def processed_data_to_dict(title, text):
    # Convert the processed data to a json format
    if len(text) == 0:
        return {"titles": [title]}
    return {text[0]: processed_data_to_dict(title, text[1:])}

# Write the processed data to a json file
def write_to_json(shared_data, filename):
    with open(filename, 'w') as f:
        json.dump(shared_data, f, indent=2)
        print(f"Final JSON written with {len(shared_data)} top-level keys")

# Worker function to process the dataset
def worker_process(dataset, chunk_range):
    local_data = {}
    begin, end = chunk_range
    # Process the dataset into a list of dictionaries
    for i in range(begin, end, batch_size):
        print(f"Processing chunk {i} to {min(i + batch_size, end)}")
        batch_end = min(i + batch_size, end)
        batch = dataset.select(range(i, batch_end))  # Use `select` to handle IterableDataset
        titles = batch[feature_title]
        texts = batch[feature_text]
        # Process the titles and texts
        processed_titles = [process_title(title) for title in titles]
        processed_texts = [process_text(text) for text in texts]
        for title, text in zip(processed_titles, processed_texts):
            processed_dict = processed_data_to_dict(title, text)
            merge_dicts(local_data, processed_dict)
    return local_data

def parallel_process(dataset, dataset_chunks):
    with Pool(processes=num_workers) as pool:
        results = pool.starmap(worker_process, [(dataset, chunk) for chunk in dataset_chunks])
    # Merge all results
    final_data = {}
    for result in results:
        merge_dicts(final_data, result)
    return final_data

# Split the dataset for each worker
dataset_chunks = split_range(len(dataset), num_workers)
print("Dataset chunks:", dataset_chunks)

write_to_json(parallel_process(dataset, dataset_chunks), output_file)
