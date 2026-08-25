# ThreadLens ELK Stack

This folder contains a clean local ELK setup for parsing the Django JSON logs from `threadlens`.

The application log file on macOS is:

```text
/Users/arash/Documents/pro/security_orchestrator/backend/var/logs/app.log
```

Logstash mounts that host directory into:

```text
/usr/share/logstash/pipeline/logs/
```

and reads:

```text
/usr/share/logstash/pipeline/logs/app.log
```

## Services

- Elasticsearch `9.4.3`
- Kibana `9.4.3`
- Logstash `9.4.3`

Default image source is the official Elastic registry. You can switch to another registry, including an Arvancloud mirror, with environment variables.

Example:

```bash
export ELASTICSEARCH_IMAGE=docker.arvancloud.ir/elasticsearch:9.4.3
export KIBANA_IMAGE=docker.arvancloud.ir/kibana:9.4.3
export LOGSTASH_IMAGE=docker.arvancloud.ir/logstash:9.4.3
```

If those image names are not available in your mirror, use the official defaults:

```text
docker.elastic.co/elasticsearch/elasticsearch:9.4.3
docker.elastic.co/kibana/kibana:9.4.3
docker.elastic.co/logstash/logstash:9.4.3
```

## Credentials

Default developer credentials:

```text
username: elastic
password: threadlens-dev-password
```

Override them before startup:

```bash
export ELASTIC_PASSWORD='change-this-password'
export KIBANA_SYSTEM_PASSWORD='change-this-kibana-system-password'
```

## Start ELK

From the project root:

```bash
cd elk
docker compose up -d
```

Follow logs:

```bash
docker compose logs -f elasticsearch
docker compose logs -f logstash
docker compose logs -f kibana
```

Open:

```text
Elasticsearch: http://127.0.0.1:9200
Kibana:        http://127.0.0.1:5601
```

Check Elasticsearch:

```bash
curl -u elastic:threadlens-dev-password http://127.0.0.1:9200
```

## Logstash Pipeline

Pipeline file:

```text
elk/logstash/pipeline/logstash.conf
```

Important settings:

```ruby
codec => json
path => "/usr/share/logstash/pipeline/logs/app.log"
start_position => "beginning"
index => "threadlens-logs-%{+YYYY.MM.dd}"
```

The pipeline supports both fields:

- `asctime` with format `yyyy-MM-dd HH:mm:ss,SSS`
- `timestamp` with ISO8601

The `date` filter maps the matched value to `@timestamp`.

## Generate A Test Log

From the backend folder:

```bash
cd /Users/arash/Documents/pro/security_orchestrator/backend
source .venv/bin/activate
python manage.py shell -c "import logging; logging.getLogger('scanner_engine.scan').info('elk test event', extra={'task_id':'elk-test','scanner_name':'gitleaks','status_code':200})"
```

Then check Logstash:

```bash
cd /Users/arash/Documents/pro/security_orchestrator/elk
docker compose logs -f logstash
```

## Create Kibana Data View

1. Open Kibana:

   ```text
   http://127.0.0.1:5601
   ```

2. Log in:

   ```text
   username: elastic
   password: threadlens-dev-password
   ```

3. Go to:

   ```text
   Stack Management -> Data Views -> Create data view
   ```

4. Name:

   ```text
   ThreadLens Logs
   ```

5. Index pattern:

   ```text
   threadlens-logs-*
   ```

6. Timestamp field:

   ```text
   @timestamp
   ```

7. Save the data view.

## Recommended Discover Columns

Add these fields as columns in Kibana Discover:

- `@timestamp`
- `levelname`
- `log_level`
- `name`
- `logger`
- `module`
- `message`
- `task_id`
- `scanner_name`
- `status_code`
- `request`
- `execution_status`
- `duration_ms`
- `metadata.source_file`
- `metadata.line_number`

## Essential KQL Queries

### Authentication Failures

```kql
status_code: (401 or 403) or metadata.status_code: (401 or 403)
```

Useful when checking failed or forbidden API access.

### Django Request And Utility Logs

```kql
name: django.request or logger: django.request or name: django.utils.* or logger: django.utils.*
```

Useful for request warnings, reload messages, and Django internals.

### Error-Level Events

```kql
levelname: ERROR or log_level: ERROR
```

Useful for backend exceptions and failed execution paths.

### Scanner Failures Or Missing Binaries

```kql
execution_status: failed or metadata.execution.status: failed or message: "Executable not found*"
```

Useful when a scanner is missing, crashes, or cannot reach its database.

### Admin User Management Audit Events

```kql
logger: "scanner_engine.audit" and metadata.event_action: user.*
```

Useful for user creation, disable/enable, role changes, and deletions.

## Index Management

The daily index pattern is:

```text
threadlens-logs-YYYY.MM.dd
```

For local development, daily indices are enough. For production, add an Index Lifecycle Management policy to:

- rollover by size or age
- retain hot logs for a short period
- delete old logs after your retention window

## Stop And Clean Up

Stop services:

```bash
docker compose down
```

Delete Elasticsearch and Logstash data:

```bash
docker compose down -v
```

Use `down -v` carefully because it removes persisted Elasticsearch indices.
