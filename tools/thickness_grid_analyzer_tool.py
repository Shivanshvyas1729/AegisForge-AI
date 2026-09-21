from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from schemas.thickness_grid import (
    ThicknessGridInput,
    ThicknessGridOutput,
    CriticalPoint,
    LocalizedThinning,
)

def read_thickness_grid(file_path: str) -> np.ndarray:
    """Read a csv file or excel file thickness grid and return as a 
    2d numpy array. of thickness measurements 
    
    The function allows non-numeric row/column labels.
    any complete non-numberic rows or columns are removed
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".csv":
        df = pd.read_csv(path, header= None)

    elif extension in [".xls", ".xlsx"]:
        df = pd.read_excel(path, header= None)

    else:
        raise ValueError(f"Unsupported file format: {extension}")

    # convert everything possible to numbers
    numeric_df = df.apply(pd.to_numeric, errors= "coerce")

    # drop any rows or columns that are completely non-numeric
    numeric_df = numeric_df.dropna(how="all")
    numeric_df = numeric_df.dropna(axis=1, how="all")

    if numeric_df.empty:
        raise ValueError("no numeric data found in the file")

    #convert to numpy array
    grid = numeric_df.to_numpy(dtype= float)

    #check for the nan values in the grid 
    if np.isnan(grid).any():
        raise ValueError("The grid contains NaN values. Please ensure all measurements are numeric.")

    #check for positive thickness values
    if (grid <= 0).any():
        raise ValueError("The Grid contains non-positive thickness values. please ensure all measurements are positive.")

    return grid 

def detect_localized_thinning(grid: np.ndarray, nominal_thickness_mm: float) -> List[LocalizedThinning]:
    """
    Detect points that are significantly thinner than their
    local neighborhood.

    Method:

    1. Calculate the mean of neighboring cells.
    2. Calculate how much thinner the center point is.
    3. Flag the point if it is at least 5% thinner than
       its local neighborhood.

    This is a screening algorithm, NOT an engineering
    acceptance decision.
    """
    rows, columns = grid.shape
    thinning_points = []
    for row in range(rows):
        for col in range(columns):
            current_thickness = grid[row, col]
            neighbors = []

            #check 8 neighboring cells 
            
            for row_offset in [-1, 0, 1]:
                for col_offset in [-1, 0, 1]:
                    if row_offset == 0 and col_offset == 0:
                        continue
                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset

                    #making sure the neighbor is within bounds
                    if 0 <= neighbor_row < rows and 0 <= neighbor_col < columns:
                        neighbors.append(grid[neighbor_row, neighbor_col])

            # a grid with only one point has no neighbours 
            if not neighbors:
                continue 
            local_mean = np.mean(neighbors)

            # calculate loss thining percentage 
            local_loss_percentage = ((local_mean - current_thickness) / local_mean) * 100

            # check if the current point is at least 5% thinner than its local mean
            if local_loss_percentage >= 5.0:
                overall_loss_percentage = ((nominal_thickness_mm - current_thickness) / nominal_thickness_mm) * 100
                thinning_points.append(LocalizedThinning(row= row + 1, col = col + 1, thickness_mm= current_thickness, loss_percentage= max(0.0, float(overall_loss_percentage))))

    return thinning_points

def _estimate_flaw_length(
    thinning_points: List[LocalizedThinning],
    row_spacing_mm: float | None,
    column_spacing_mm: float | None,
) -> float | None:

    """
    Estimate the spatial extent of localized thinning.

    This is NOT a true metallurgical flaw-length measurement.

    It estimates the maximum physical distance between
    detected thinning coordinates.

    Returns None when physical grid spacing is unavailable.
    """

    if not thinning_points:
        return None

    if (
        row_spacing_mm is None
        or column_spacing_mm is None
    ):
        return None

    if len(thinning_points) == 1:
        return 0.0

    maximum_distance = 0.0

    for first_index in range(
        len(thinning_points)
    ):

        first_point = thinning_points[first_index]

        for second_index in range(
            first_index + 1,
            len(thinning_points),
        ):

            second_point = thinning_points[
                second_index
            ]

            row_distance = (
                first_point.row
                - second_point.row
            ) * row_spacing_mm

            column_distance = (
                first_point.column
                - second_point.column
            ) * column_spacing_mm

            distance = float(
                np.sqrt(
                    row_distance ** 2
                    + column_distance ** 2
                )
            )

            maximum_distance = max(
                maximum_distance,
                distance,
            )

    return maximum_distance

def analyze_thickness_grid(
    input_data: ThicknessGridInput,
) -> ThicknessGridOutput:

    """
    Analyze an ultrasonic thickness measurement grid.

    Input:
        ThicknessGridInput

    Output:
        ThicknessGridOutput
    """

    # ========================================================
    # 1. READ CSV / EXCEL
    # ========================================================

    grid = read_thickness_grid(
        input_data.file_path
    )

    # ========================================================
    # 2. GET GRID DIMENSIONS
    # ========================================================

    rows, columns = grid.shape

    grid_points_scanned = rows * columns

    # ========================================================
    # 3. BASIC STATISTICS
    # ========================================================

    mean_thickness = float(
        np.mean(grid)
    )

    minimum_thickness = float(
        np.min(grid)
    )

    maximum_thickness = float(
        np.max(grid)
    )

    # ========================================================
    # 4. FIND CRITICAL / MINIMUM POINT
    # ========================================================

    minimum_position = np.unravel_index(
        np.argmin(grid),
        grid.shape,
    )

    minimum_row = int(
        minimum_position[0]
    )

    minimum_column = int(
        minimum_position[1]
    )

    # ========================================================
    # 5. CALCULATE THICKNESS LOSS
    # ========================================================

    loss_percentages = (
        (
            input_data.nominal_thickness_mm
            - grid
        )
        / input_data.nominal_thickness_mm
    ) * 100

    # We don't want negative "loss" when a measurement
    # happens to be above nominal thickness.

    loss_percentages = np.maximum(
        loss_percentages,
        0,
    )

    mean_loss_percentage = float(
        np.mean(loss_percentages)
    )

    max_loss_percentage = float(
        np.max(loss_percentages)
    )

    # ========================================================
    # 6. CRITICAL POINT OBJECT
    # ========================================================

    critical_point = CriticalPoint(
        row=minimum_row + 1,
        column=minimum_column + 1,
        thickness_mm=minimum_thickness,
        location=None,
    )

    # ========================================================
    # 7. DETECT LOCALIZED THINNING
    # ========================================================

    localized_thinning = (
        detect_localized_thinning(
            grid=grid,
            nominal_thickness_mm=(
                input_data.nominal_thickness_mm
            ),
        )
    )

    # ========================================================
    # 8. ESTIMATE FLAW EXTENT
    # ========================================================

    flaw_length = _estimate_flaw_length(
        thinning_points=localized_thinning,
        row_spacing_mm=input_data.row_spacing_mm,
        column_spacing_mm=input_data.column_spacing_mm,
    )

    # ========================================================
    # 9. ADD LOCATION TO CRITICAL POINT
    # ========================================================

    if input_data.location_name:

        critical_point.location = (
            f"{input_data.location_name} - "
            f"Row {critical_point.row}, "
            f"Column {critical_point.column}"
        )

    # ========================================================
    # 10. RETURN VALIDATED OUTPUT
    # ========================================================

    return ThicknessGridOutput(

        grid_points_scanned=grid_points_scanned,

        rows=rows,

        columns=columns,

        nominal_thickness_mm=(
            input_data.nominal_thickness_mm
        ),

        mean_thickness_mm=mean_thickness,

        min_point_thickness_mm=minimum_thickness,

        max_point_thickness_mm=maximum_thickness,

        mean_loss_percentage=mean_loss_percentage,

        max_loss_percentage=max_loss_percentage,

        critical_point=critical_point,

        localized_thinning=localized_thinning,

        flaw_length_mm=flaw_length,
    )
