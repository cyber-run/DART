from threading import Thread, Event
from queue import Queue, Empty
import time
from utils.perf_timings import perf_counter_ns
import random
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Tuple
import numpy as np
import logging

class DataHandler:
    def __init__(self, queue: Queue, batch_size: int = 1000, output_dir: str = "output", start_time = None):
        """
        Initializes the DataHandler with a queue, batch size, and output directory.
        """
        self.logger = logging.getLogger("DataHandler")
        self.queue = queue
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.batch_number = 0
        self.thread = None
        self.stop_event = Event()
        self.start_time_ms = start_time
        self.merged_file_path = None
        self.frame_timestamps = []
        self.collecting = True

    def start(self, output_file: str = "merged_data.parquet"):
        """
        Starts the data handling thread.
        """
        self.merged_file_path = output_file

        self.stop_event.clear()

        if self.start_time_ms is None:
            self.start_time_ms = perf_counter_ns() * 1e-6

        self.thread = Thread(target=self._handle_data)
        self.thread.start()

    def stop_collecting(self):
        """Stop collecting new data but don't stop the handler"""
        self.collecting = False
        self.logger.info("Stopped collecting new data")
        
    def stop(self):
        """Stop the handler and process collected data"""
        self.collecting = False
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
                if not self.collecting:
                    time.sleep(0.1)
                    continue
                    
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
        """Simple batch writing without synchronization calculations"""
        if not data_batch:
            return

        # Just write the raw data
        df = pd.DataFrame(data_batch, columns=['target_position', 'desired_pan', 'desired_tilt', 
                                             'encoder_pan', 'encoder_tilt', 'time_stamp_ms'])
        
        table = pa.Table.from_pandas(df)
        filename = self.output_dir / f"data_batch_{self.batch_number}.parquet"
        pq.write_table(table, filename)
        self.batch_number += 1

    def merge_parquet_files(self):
        """Merge files and perform post-processing"""
        self.logger.info("Starting post-processing...")
        
        # Merge all batch files
        parquet_files = list(self.output_dir.glob("data_batch_*.parquet"))
        if not parquet_files:
            self.logger.warning("No batch files found to merge.")
            return

        # Read and concatenate all data
        tables = [pq.read_table(file) for file in parquet_files]
        df = pa.concat_tables(tables).to_pandas()
        
        # Post-processing steps
        self.logger.info("Performing synchronization calculations...")
        
        # 1. Calculate relative timestamps
        df['relative_time_ms'] = df['time_stamp_ms'] - self.start_time_ms
        
        # 2. Add frame correlation
        if self.frame_timestamps:
            timestamps = np.array(self.frame_timestamps)
            df['frame_number'] = df['relative_time_ms'].apply(
                lambda t: np.searchsorted(timestamps, t, side='left') - 1
            )
            
            # 3. Calculate sync errors
            df['sync_error_ms'] = df.apply(
                lambda row: self._calculate_sync_error(row['relative_time_ms'], 
                                                     row['frame_number']) 
                if row['frame_number'] >= 0 else float('nan'),
                axis=1
            )
            
            # Log synchronization statistics
            mean_error = df['sync_error_ms'].mean()
            max_error = df['sync_error_ms'].max()
            self.logger.info(f"Synchronization stats:")
            self.logger.info(f"- Mean error: {mean_error:.2f}ms")
            self.logger.info(f"- Max error: {max_error:.2f}ms")
        else:
            self.logger.warning("No frame timestamps available for synchronization")
        
        # Save processed data
        self.logger.info(f"Saving processed data to {self.merged_file_path}")
        table = pa.Table.from_pandas(df)
        pq.write_table(table, self.merged_file_path)
        
        # Cleanup batch files
        for file in parquet_files:
            file.unlink()
        
        self.logger.info("Post-processing complete")

    def _calculate_sync_error(self, timestamp_ms: float, frame_number: int) -> float:
        """Calculate the synchronization error between data and frame timestamps"""
        if not isinstance(frame_number, (int, np.integer)) or frame_number >= len(self.frame_timestamps) or frame_number < 0:
            return float('nan')
        
        frame_time = self.frame_timestamps[frame_number]
        sync_error = abs(timestamp_ms - frame_time)
        
        # Calculate jitter from expected frame interval
        if frame_number > 0:
            actual_interval = self.frame_timestamps[frame_number] - self.frame_timestamps[frame_number - 1]
            expected_interval = 1000.0 / 200.0  # Expected interval for 200Hz
            jitter = abs(actual_interval - expected_interval)
            
            if jitter > 0.5:  # Log significant jitter (>0.5ms)
                self.logger.debug(f"Frame interval jitter: {jitter:.3f}ms at frame {frame_number}")
        
        # Log large sync errors for debugging
        if sync_error > 2.0:  # Lowered threshold to 2ms
            self.logger.debug(f"Sync error: {sync_error:.3f}ms at frame {frame_number}")
            self.logger.debug(f"Data time: {timestamp_ms:.3f}ms, Frame time: {frame_time:.3f}ms")
        
        return sync_error

    def validate_synchronization(self):
        """Validate the synchronization quality of the recording"""
        sync_errors = pd.Series(self.sync_errors)
        max_error = sync_errors.max()
        mean_error = sync_errors.mean()
        
        self.logger.info(f"Synchronization Quality:")
        self.logger.info(f"Mean sync error: {mean_error:.3f}ms")
        self.logger.info(f"Max sync error: {max_error:.3f}ms")
        
        return max_error < self.sync_tolerance_ms

    def _find_nearest_frame(self, timestamp_ms: float) -> int:
        """
        Find the frame number closest to the given timestamp.
        
        Args:
            timestamp_ms: Timestamp in milliseconds relative to recording start
        
        Returns:
            int: The closest frame number, or -1 if no frames available
        """
        if not self.frame_timestamps:
            return -1
        
        timestamps = np.array(self.frame_timestamps)
        idx = np.searchsorted(timestamps, timestamp_ms)
        
        if idx == 0:
            return 0
        elif idx == len(timestamps):
            return len(timestamps) - 1
        
        # Find the closest frame by comparing distances
        if abs(timestamps[idx] - timestamp_ms) < abs(timestamps[idx-1] - timestamp_ms):
            return idx
        else:
            return idx - 1

    def set_frame_timestamps(self, timestamps: List[float]):
        """
        Set the frame timestamps from the camera manager.
        
        Args:
            timestamps: List of frame timestamps in milliseconds
        """
        self.frame_timestamps = timestamps
        self.logger.info(f"Received {len(timestamps)} frame timestamps")

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
