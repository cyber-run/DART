from multiprocessing import Process, Queue
import time
import random
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path


def add_test_data(queue: Queue):
    try:
        while True:
            desired_pan = random.randint(1, 100)
            desired_tilt = random.randint(1, 100)
            actual_pan = random.randint(1, 100)
            actual_tilt = random.randint(1, 100)
            timestamp = time.perf_counter_ns()*1e-6  # Convert to milliseconds
            data = (desired_pan, desired_tilt, actual_pan, actual_tilt, timestamp)
            queue.put(data)
            time.sleep(0.001)  # Sleep for 1ms
    except KeyboardInterrupt:
        pass
    finally:
        queue.put('DONE')

def write_to_parquet_batch(data_batch, batch_number):
    """
    Writes a batch of data to an individual Parquet file, excluding the index column.

    Args:
    data_batch (list of tuples): The data batch to write, where each tuple represents a row.
    batch_number (int): Identifier for the batch, used in naming the Parquet file.
    """
    if not data_batch:
        print("No data to write.")
        return

    filename = f"data_batch_{batch_number}.parquet"
    columns = ['desired_pan', 'desired_tilt', 'actual_pan', 'actual_tilt', 'timestamp']
    dtypes = {'desired_pan': 'int32', 'desired_tilt': 'int32', 
              'actual_pan': 'int32', 'actual_tilt': 'int32', 'timestamp': 'float64'}
    df = pd.DataFrame(data_batch, columns=columns).astype(dtypes)
    table = pa.Table.from_pandas(df, preserve_index=False)  # Exclude the index column
    pq.write_table(table, filename)


def merge_parquet_files(output_file):
    """
    Merges individual batch Parquet files into a larger Parquet file.

    Args:
    output_file (str): The name of the output merged Parquet file.
    """
    parquet_files = list(Path(".").glob("data_batch_*.parquet"))
    tables = [pq.read_table(file) for file in parquet_files]
    if tables:
        combined_table = pa.concat_tables(tables)
        pq.write_table(combined_table, output_file)
        print(f"Merged {len(parquet_files)} files into {output_file}.")
        # Optionally, delete the individual batch files after merging
        for file in parquet_files:
            file.unlink()
    else:
        print("No batch files found to merge.")

def main():
    queue = Queue()
    process = Process(target=add_test_data, args=(queue,))
    process.start()
    
    batch_size = 1000
    data_batch = []
    batch_number = 0

    try:
        while True:
            data = queue.get()
            if data == 'DONE':
                break
            data_batch.append(data)
            
            if len(data_batch) >= batch_size:
                write_to_parquet_batch(data_batch, batch_number)
                data_batch = []  # Reset the batch
                batch_number += 1
    except KeyboardInterrupt:
        print("\nTerminating...")
    finally:
        if data_batch:
            write_to_parquet_batch(data_batch, batch_number)
        process.terminate()
        process.join()
        # Optionally, merge all batch files into a larger file
        merge_parquet_files("merged_data.parquet")

if __name__ == "__main__":
    main()
