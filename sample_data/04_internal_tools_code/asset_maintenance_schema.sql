-- =============================================================================
-- REFINERY ASSET INTEGRITY & MAINTENANCE RELATIONAL SCHEMA (POSTGRESQL / SQLITE)
-- Purpose: Schema for internal equipment tracking, condition telemetry,
--          ASME/API inspection logs, and maintenance work orders.
-- =============================================================================

CREATE TABLE IF NOT EXISTS plant_units (
    unit_id VARCHAR(16) PRIMARY KEY,
    unit_name VARCHAR(128) NOT NULL,
    refinery_site VARCHAR(64) NOT NULL,
    commissioned_date DATE NOT NULL,
    licensed_capacity_bpd INTEGER,
    process_licensor VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS refinery_assets (
    asset_tag VARCHAR(32) PRIMARY KEY,
    unit_id VARCHAR(16) REFERENCES plant_units(unit_id),
    asset_name VARCHAR(256) NOT NULL,
    equipment_type VARCHAR(64) CHECK (equipment_type IN ('PRESSURE_VESSEL', 'PUMP', 'COMPRESSOR', 'HEAT_EXCHANGER', 'FURNACE', 'PIPING_CIRCUIT', 'STORAGE_TANK')),
    design_code VARCHAR(64) NOT NULL, -- e.g. ASME Sec VIII Div 1, API 610, API 650
    design_pressure_barg NUMERIC(8, 2),
    design_temp_celsius NUMERIC(6, 1),
    material_spec VARCHAR(64) NOT NULL, -- e.g. SA-516 Gr 70, SA-387 Gr 22
    nominal_thickness_mm NUMERIC(6, 2),
    min_required_thickness_mm NUMERIC(6, 2),
    corrosion_allowance_mm NUMERIC(4, 2),
    installation_year INTEGER NOT NULL,
    criticality_ranking VARCHAR(16) CHECK (criticality_ranking IN ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW'))
);

CREATE TABLE IF NOT EXISTS telemetry_sensors (
    sensor_id VARCHAR(32) PRIMARY KEY,
    asset_tag VARCHAR(32) REFERENCES refinery_assets(asset_tag),
    modbus_register_address INTEGER UNIQUE,
    parameter_name VARCHAR(64) NOT NULL,
    engineering_unit VARCHAR(16) NOT NULL,
    warning_threshold_high NUMERIC(10, 3),
    trip_threshold_high NUMERIC(10, 3),
    sampling_interval_sec INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ndt_thickness_inspections (
    inspection_id SERIAL PRIMARY KEY,
    asset_tag VARCHAR(32) REFERENCES refinery_assets(asset_tag),
    inspection_date DATE NOT NULL,
    inspection_technique VARCHAR(32) CHECK (inspection_technique IN ('ULTRASONIC_UT', 'RADIOGRAPHY_RT', 'MAGNETIC_PARTICLE_MPI', 'EDDY_CURRENT_ECT', 'ACOUSTIC_EMISSION_AET')),
    inspector_id VARCHAR(32) NOT NULL,
    measured_thickness_mm NUMERIC(6, 2) NOT NULL,
    corrosion_rate_mm_per_year NUMERIC(6, 3),
    estimated_remaining_life_years NUMERIC(5, 1),
    disposition VARCHAR(32) CHECK (disposition IN ('SATISFACTORY', 'MONITOR_CLOSELY', 'IMMEDIATE_REPAIR_REQUIRED', 'REPLACE_VESSEL')),
    report_reference VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS approval_notes_audit (
    nfa_id VARCHAR(64) PRIMARY KEY,
    asset_tag VARCHAR(32) REFERENCES refinery_assets(asset_tag),
    nfa_date DATE NOT NULL,
    subject TEXT NOT NULL,
    procurement_type VARCHAR(32) CHECK (procurement_type IN ('OPEN_TENDER', 'LIMITED_TENDER', 'SINGLE_PAC_OEM', 'GEM_DIRECT')),
    total_value_inr NUMERIC(14, 2) NOT NULL,
    approving_authority VARCHAR(64) NOT NULL,
    delegation_power_clause VARCHAR(64) NOT NULL,
    status VARCHAR(32) CHECK (status IN ('DRAFT', 'SUBMITTED', 'CONCURRED', 'APPROVED', 'REJECTED'))
);

-- Seed Essential Sample Data for Hydrocracker Unit
INSERT INTO plant_units (unit_id, unit_name, refinery_site, commissioned_date, licensed_capacity_bpd, process_licensor)
VALUES ('HCU-11', 'Hydrocracker Unit', 'Guwahati Refinery', '2012-04-15', 35000, 'Chevron Lummus Global')
ON CONFLICT (unit_id) DO NOTHING;

INSERT INTO refinery_assets (asset_tag, unit_id, asset_name, equipment_type, design_code, design_pressure_barg, design_temp_celsius, material_spec, nominal_thickness_mm, min_required_thickness_mm, corrosion_allowance_mm, installation_year, criticality_ranking)
VALUES 
('11-V-102', 'HCU-11', 'High-Pressure Hydrocracker Separator', 'PRESSURE_VESSEL', 'ASME Sec VIII Div 1', 145.0, 285.0, 'SA-387 Gr 22 Cl 2', 145.0, 138.57, 4.0, 2012, 'VERY_HIGH'),
('11-P-101A', 'HCU-11', 'Hydrocracker Reactor Charge Feed Pump A', 'PUMP', 'API 610 11th Ed', 160.0, 195.0, 'Super Duplex UNS S32750', 35.0, 28.0, 3.0, 2018, 'VERY_HIGH'),
('11-P-101B', 'HCU-11', 'Hydrocracker Reactor Charge Feed Pump B (Standby)', 'PUMP', 'API 610 11th Ed', 160.0, 195.0, 'Super Duplex UNS S32750', 35.0, 28.0, 3.0, 2018, 'VERY_HIGH')
ON CONFLICT (asset_tag) DO NOTHING;
