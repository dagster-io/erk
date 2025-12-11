---
columns:
  - BACKFILL_RUN_CREATED_COUNT (NUMBER(13,0))
  - DAEMON_ALIVE_COUNT (NUMBER(13,0))
  - DAGSTER_VERSION_PARSED (VARCHAR(16777216))
  - DAGSTER_VERSION_RAW (VARCHAR(16777216))
  - GQL_QUERY_COMPLETED_COUNT (NUMBER(13,0))
  - INSTANCE_ID (VARCHAR(16777216))
  - INSTANCE_PRIORITY (NUMBER(38,0))
  - INSTANCE_TYPE (VARCHAR(16777216))
  - REPORTING_DATE (DATE)
  - RUN_LAUNCHED_FROM_WEBSERVER_COUNT (NUMBER(13,0))
  - SCHEDULED_RUN_CREATED_COUNT (NUMBER(13,0))
  - SENSOR_RUN_CREATED_COUNT (NUMBER(13,0))
  - STEP_STARTED_COUNT (NUMBER(13,0))
  - WEBSERVER_STARTED_COUNT (NUMBER(13,0))
schema_hash: 969eed1c6db692b0aac7b26997f44eb1f1bf87dc9fb1dee7833196fb3f7305da
---

# Dataset Summary: OSS_INSTANCES_BY_DAY

## Overall Dataset Characteristics

- **Total Rows**: 5,539,068 records
- **Data Quality**: High-quality dataset with minimal null values (only DAGSTER_VERSION_PARSED has 2.91% nulls)
- **Time Span**: Data spans from 2022 through 2025, covering 1,248 unique reporting dates
- **Scope**: Daily telemetry metrics for 4,277,341 unique Dagster instances
- **Table Purpose**: Tracks open source Dagster usage patterns and activity levels across different instance types

## Column Details

### Temporal Dimension

- **REPORTING_DATE**: Complete date coverage with no nulls, spanning ~3.5 years of daily data

### Instance Classification

- **INSTANCE_TYPE**: Categorical with 4 values (SERVER, CI, LOCAL, UNKNOWN)
- **INSTANCE_PRIORITY**: Numeric priority ranking (1-4) corresponding to instance types
- **INSTANCE_ID**: Unique identifier with over 4M distinct instances (high cardinality)

### Version Information

- **DAGSTER_VERSION_RAW**: 245 distinct version strings, including development versions
- **DAGSTER_VERSION_PARSED**: Simplified major.minor format (17 versions), with some parsing failures (2.91% nulls)

### Activity Metrics (All Non-Null Counters)

- **STEP_STARTED_COUNT**: Job execution activity (0-170,344 range, 12,034 unique values)
- **SENSOR_RUN_CREATED_COUNT**: Sensor-triggered runs (0-130,752 range, 7,883 unique values)
- **SCHEDULED_RUN_CREATED_COUNT**: Scheduled runs (0-108,283 range, 7,439 unique values)
- **BACKFILL_RUN_CREATED_COUNT**: Historical data processing (0-70,866 range, 1,329 unique values)
- **DAEMON_ALIVE_COUNT**: System health indicator (0-65,262 range, 1,729 unique values)
- **WEBSERVER_STARTED_COUNT**: UI activity (0-13,548 range, 472 unique values)
- **GQL_QUERY_COMPLETED_COUNT**: API usage (0-130,096 range, 2,500 unique values)
- **RUN_LAUNCHED_FROM_WEBSERVER_COUNT**: Manual job launches (0-5,737 range, 683 unique values)

## Query Considerations

### Optimal Filtering Columns

- **REPORTING_DATE**: Excellent for time-based queries and trending analysis
- **INSTANCE_TYPE**: Good for segmenting by deployment patterns
- **DAGSTER_VERSION_PARSED**: Useful for version adoption analysis
- **INSTANCE_PRIORITY**: Efficient for filtering by instance importance

### Grouping/Aggregation Opportunities

- **REPORTING_DATE**: Time series analysis, daily/monthly/yearly trends
- **INSTANCE_TYPE**: Usage pattern comparison across deployment types
- **DAGSTER_VERSION_PARSED**: Version adoption and migration tracking
- **INSTANCE_PRIORITY**: Activity analysis by instance importance

### Potential Join Keys

- **INSTANCE_ID**: Primary key for joining with other instance-related tables
- **REPORTING_DATE**: Time-based joins with other daily metrics tables

### Data Quality Considerations

- **Version Parsing**: 2.91% of records have unparseable versions (consider NULL handling)
- **Zero Values**: Many activity counters have significant zero values (inactive instances)
- **High Cardinality**: INSTANCE_ID has very high cardinality (4M+ values) - consider performance implications
- **Outliers**: Some metrics show extreme high values that may need investigation or filtering

## Keywords

Dagster, OSS, open source, telemetry, instances, daily metrics, activity tracking, version adoption, deployment types, job execution, sensors, scheduling, backfills, daemon health, webserver usage, GraphQL queries, time series data, usage analytics, software telemetry

## Table and Column Documentation

### Table Comment

Daily OSS instance telemetry metrics aggregated by instance, providing insights into open source Dagster usage patterns and activity levels

### Column Comments

- **REPORTING_DATE**: Date for which the metrics are reported
- **INSTANCE_TYPE**: Type of instance (SERVER, CI, LOCAL, UNKNOWN)
- **INSTANCE_PRIORITY**: Priority level of the instance based on instance type
- **INSTANCE_ID**: Unique identifier for the Dagster instance
- **DAGSTER_VERSION_RAW**: Raw Dagster version string
- **DAGSTER_VERSION_PARSED**: Parsed Dagster version (major.minor format)
- **STEP_STARTED_COUNT**: Count of step start events for this instance on this day
- **SENSOR_RUN_CREATED_COUNT**: Count of sensor run created events for this instance on this day
- **SCHEDULED_RUN_CREATED_COUNT**: Count of scheduled run created events for this instance on this day
- **BACKFILL_RUN_CREATED_COUNT**: Count of backfill run created events for this instance on this day
- **DAEMON_ALIVE_COUNT**: Count of daemon alive events for this instance on this day
- **WEBSERVER_STARTED_COUNT**: Count of webserver started events for this instance on this day
- **GQL_QUERY_COMPLETED_COUNT**: Count of GraphQL query completed events for this instance on this day
- **RUN_LAUNCHED_FROM_WEBSERVER_COUNT**: Count of runs launched from webserver for this instance on this day
