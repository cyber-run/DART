from threading import Thread, Event
from queue import Queue, Empty
import time
from utils.perf_timer import perf_counter_ns
import random
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Tuple

class DataHandler:
    def __init__(self, queue: Queue, batch_size: int = 1000, output_dir: str = "output", start_time = None):
        """
        Initializes the DataHandler with a queue, batch size, and output directory.
        """
        self.queue = queue
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.batch_number = 0
        self.thread = None
        self.stop_event = Event()
        self.start_time_ms = start_time  # Renamed for consistency
        self.merged_file_path = None

    def start(self, output_file: str = "merged_data.parquet"):
        """
        Starts the data handling thread.
        """
        self.merged_file_path = output_file

        self.stop_event.clear()

        if self.start_time_ms is None:
            self.start_time_ms = perf_counter_ns() * 1e-6  # Start time in milliseconds

        self.thread = Thread(target=self._handle_data)
        self.thread.start()

    def stop(self):
        """
        Signals the data handling thread to stop and waits for it to finish.
        """
        self.stop_event.set()
        self.thread.join()
        self.merge_parquet_files()

    def _handle_data(self):
        """
        Captures and writes data to Parquet files in batches.
        """
        data_batch = []
        while not self.stop_event.is_set():
            try:
                data = self.queue.get(timeout=0.1)
                if data == 'DONE':
                    break
                data_batch.append(data)

                if len(data_batch) >= self.batch_size:
                    self._write_to_parquet_batch(data_batch)
                    data_batch = []
            except Empty:
                continue

        if data_batch:
            self._write_to_parquet_batch(data_batch)

    def _write_to_parquet_batch(self, data_batch: List[Tuple]):
        """
        Writes a batch of data to an individual Parquet file, adjusting timestamps.
        """
        if not data_batch:
            return

        filename = self.output_dir / f"data_batch_{self.batch_number}.parquet"
        columns = ['target position', 'desired_pan', 'desired_tilt', 'encoder_pan', 'encoder_tilt', 'time_stamp_ms']
        df = pd.DataFrame(data_batch, columns=columns)

        # Adjust the timestamp for the whole column
        df['time_stamp_ms'] = df['time_stamp_ms'] - self.start_time_ms

        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, filename)
        self.batch_number += 1

    def merge_parquet_files(self):
        """
        Merges individual batch Parquet files into a larger Parquet file.
        """
        parquet_files = list(self.output_dir.glob("data_batch_*.parquet"))

        if not parquet_files:
            print("No batch files found to merge.")
            return

        tables = [pq.read_table(file) for file in parquet_files]
        combined_table = pa.concat_tables(tables)
        pq.write_table(combined_table, self.merged_file_path)

        print(f"Merged {len(parquet_files)} files into {self.merged_file_path}.")

        for file in parquet_files:
            file.unlink()

def add_test_data(queue: Queue, control_event: Event):
    """
    Function to generate and queue test data.
    """
    while control_event.is_set():
        data = (random.randint(1, 100), random.randint(1, 100),
                random.randint(1, 100), random.randint(1, 100),
                perf_counter_ns() * 1e-6)
        queue.put(data)
        # time.sleep(0.0001)

# Example usage
if __name__ == "__main__":
    queue = Queue()
    control_event = Event()  # Controls whether data is generated
    control_event.set()  # Start with data generation enabled

    # Start data generation in a background thread
    data_gen_thread = Thread(target=add_test_data, args=(queue, control_event))
    data_gen_thread.start()

    # Create and manage the DataHandler to process and write the data
    data_handler = DataHandler(queue, batch_size=1000, output_dir="dev\data")
    data_handler.start()

    # Example: run for 10 seconds, then stop
    time.sleep(5)
    control_event.clear()  # Stop data generation
    data_handler.stop()  # Stop the DataHandler
    data_handler.merge_parquet_files("final_merged_data.parquet")

    data_gen_thread.join()  # Ensure the data generation thread is also stopped
