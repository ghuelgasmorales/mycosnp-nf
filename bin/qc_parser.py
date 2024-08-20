#!/usr/bin/env python3

"""
QC report parser script to evaluate quality control metrics
against specified thresholds.
"""

import os
import sys
import argparse
import pandas as pd


def parse_thresholds(threshold_str):
    """Parse and validate the QC thresholds provided as a string."""
    try:
        parts = threshold_str.split(',')
        if len(parts) != 4:
            raise ValueError(
                "Thresholds must be in the format 'gc_min-gc_max,coverage,depth,qscore'"
            )

        # Parse the GC range
        gc_range_str = parts[0]
        gc_range = list(map(float, gc_range_str.split('-')))
        if len(gc_range) != 2:
            raise ValueError("GC range must have exactly two values separated by a dash ('-').")

        # Parse the other thresholds
        coverage_threshold = float(parts[1])
        depth_threshold = float(parts[2])
        qscore_threshold = float(parts[3])

        return gc_range, coverage_threshold, depth_threshold, qscore_threshold
    except ValueError as value_error:
        print(f"Error parsing thresholds: {value_error}")
        sys.exit(1)


def evaluate_qc(row, gc_range, coverage_threshold, depth_threshold, qscore_threshold):
    """Evaluate QC metrics for a single sample against the specified thresholds."""
    print(f"Evaluating QC for sample {row['Sample Name']}")
    if not gc_range[0] <= row['GC After Trimming'] <= gc_range[1]:
        print(f"GC After Trimming {row['GC After Trimming']} is out of range {gc_range}")
        return 'fail'
    if (
        row['Reference Length Coverage After Trimming'] >= coverage_threshold
        and row['Mean Coverage Depth'] >= depth_threshold
        and row['Average Q Score After Trimming'] >= qscore_threshold
    ):
        return 'pass'

    print(f"Sample {row['Sample Name']} failed on thresholds.")
    return 'fail'


def main():
    """Main function to parse QC report, evaluate samples, and save results."""
    print("Starting the QC parser main script")

    parser = argparse.ArgumentParser(description='QC report parser')
    parser.add_argument(
        'file_path', help='Path to the QC report file'
    )
    parser.add_argument(
        '-qc_thresholds',
        required=True,
        help='QC thresholds in the format "gc_min-gc_max,coverage,depth,qscore"',
    )
    args = parser.parse_args()

    print(f"Received file path: {args.file_path}")
    print(f"Received thresholds: {args.qc_thresholds}")

    # Check if the input file exists and is not empty
    if not os.path.isfile(args.file_path):
        print(f"Error: The file '{args.file_path}' does not exist.")
        sys.exit(1)

    if os.stat(args.file_path).st_size == 0:
        print(f"Error: The file '{args.file_path}' is empty.")
        sys.exit(1)

    # Parse and validate the thresholds
    gc_range, coverage_threshold, depth_threshold, qscore_threshold = parse_thresholds(
        args.qc_thresholds
    )

    try:
        data_frame = pd.read_csv(args.file_path, sep='\t')
        if data_frame.empty:
            raise ValueError("Input file is empty after parsing.")
        print("Successfully read the input file")
    except (ValueError, pd.errors.EmptyDataError) as read_error:
        print(f"Error reading the input file: {read_error}")
        sys.exit(1)

    print(f"DataFrame columns: {list(data_frame.columns)}")

    try:
        data_frame = data_frame.replace('%', '', regex=True).apply(
            pd.to_numeric, errors='ignore'
        )
        print("Successfully converted columns to numeric")
    except (ValueError, TypeError) as conversion_error:
        print(f"Error during data conversion: {conversion_error}")
        sys.exit(1)

    try:
        data_frame['QC_fail_pass'] = data_frame.apply(
            evaluate_qc,
            axis=1,
            gc_range=gc_range,
            coverage_threshold=coverage_threshold,
            depth_threshold=depth_threshold,
            qscore_threshold=qscore_threshold,
        )
        print("Successfully evaluated QC for all rows")
    except (ValueError, TypeError) as eval_error:
        # Using more specific exceptions where possible
        print(f"Error during QC evaluation: {eval_error}")
        sys.exit(1)

    try:
        result = data_frame[['Sample Name', 'QC_fail_pass']]
        result.to_csv('qc_fail_pass.csv', index=False)
        print("QC results saved to 'qc_fail_pass.csv'.")
    except (IOError, OSError) as save_error:
        print(f"Error saving the results: {save_error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
