-- Daily stow volume by station.
SELECT
    DATE(event_time) AS event_date,
    station_id,
    COUNT(*) AS stow_events,
    SUM(quantity) AS units
FROM fact_warehouse_event
WHERE event_type = 'stowed'
GROUP BY 1, 2
ORDER BY 1, 2;

-- Containers whose latest state is an exception-related location can be inspected separately.
SELECT container_id, location, sku, quantity, latest_event_time
FROM current_container_state
ORDER BY latest_event_time DESC;
