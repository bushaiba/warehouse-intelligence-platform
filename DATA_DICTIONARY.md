# Data dictionary

## Raw and operational tables

### `pipeline_runs`
One row per attempted source batch. Stores checksum, status, row counts and run timestamps.

### `fact_warehouse_event`
Validated immutable event history.

| Column | Purpose |
| --- | --- |
| `event_id` | Synthetic event identifier |
| `event_type` | received, moved, stowed or exception |
| `event_time` | Event timestamp |
| `warehouse_id` | Synthetic warehouse identifier |
| `container_id` | Synthetic container identifier |
| `sku` | Synthetic stock identifier |
| `quantity` | Units attached to the event |
| `location` | Operational location |
| `station_id` | Station when relevant |
| `associate_id` | Synthetic associate identifier when relevant |

### `current_container_state`
Latest reconciled state for each container, rebuilt from event history.

### `quality_results`
Data-quality results attached to a pipeline run.

## Analytics star mart

### `dim_sku`
Surrogate key plus synthetic SKU business key.

### `dim_station`
Surrogate key plus synthetic station business key.

### `dim_associate`
Surrogate key plus synthetic associate business key.

### `fact_stow_activity`
One row per validated stow event with foreign keys to SKU, station and associate dimensions plus event time and units.

### `daily_metrics`
Small API-facing aggregate for event volume, units, exception rate and active containers.
