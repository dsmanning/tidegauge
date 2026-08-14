# Tide Gauge

A small site for `tidegauge.dsmanning.com`. It subscribes to a tide-height MQTT
topic, caches the current value, samples it into SQLite every five minutes, and
serves a current reading and historic chart. It does not expose the MQTT broker
or credentials to the browser.

## Network and firewall

The only new cross-zone flow is an MQTT connection initiated by the application.
The Home Assistant broker is currently reachable at `192.168.1.68:1883` and is
the default in `.env.example`. The preferred final configuration is:

| Source | Destination | Protocol | Port | Purpose |
| --- | --- | --- | --- | --- |
| `tethys-webserver` (DMZ) | Home Assistant MQTT broker (trusted) | TCP | 8883 | MQTT over TLS |

In IPFire, permit the specific source and destination hosts rather than their
whole networks. Return traffic is covered by connection tracking. Do not expose
8883 on the WAN interface. If the broker does not support TLS, TCP 1883 works,
but sends the MQTT username, password, and tide data without transport
encryption and is not recommended across security zones.

Use a dedicated broker account with subscribe-only access to the configured
topic. For a Mosquitto ACL, the relevant grant is:

```text
user tidegauge
topic read home/tide/current_height
```

The TLS certificate must contain the hostname used in `MQTT_URL`. Put the CA
certificate that signed the broker certificate at `certs/mqtt-ca.pem` and
uncomment the certificate volume in `compose.yaml`. A public CA does not
normally require `MQTT_CA_FILE`; remove that setting in that case. Do not disable
certificate validation.

The existing web proxy still accepts public HTTPS on TCP 443. The container
binds its HTTP port only to `127.0.0.1`, so port 3000 does not need a firewall
opening.

## Configure and run

```sh
cp .env.example .env
chmod 600 .env
docker compose up -d --build
```

Edit `.env` first. At minimum, set the broker hostname or IP, topic, credentials,
payload format, and unit. Supported payloads are either a plain number:

```text
4.27
```

or JSON, selected with `MQTT_PAYLOAD_FORMAT=json` and a dot-separated value
path such as `MQTT_VALUE_PATH=state.height`:

```json
{"state":{"height":4.27}}
```

`MQTT_VALUE_SCALE` can convert the reported number (for example, set it to
`3.28084` to convert meters to feet). History starts accumulating when this
service first receives readings. SQLite data lives in the `tidegauge-data`
Docker volume. Raw readings and tide events are retained for 30 days by
default. Expired data is removed on startup and daily thereafter. Long chart
ranges are downsampled to at most roughly 1,500 plotted averages without
deleting the retained raw data.

`TIDE_HEIGHT_OFFSET_METERS` applies a fixed vertical calibration offset to
incoming tide-height readings. Existing stored readings must be migrated once
when this value is introduced.

`TIDE_LOCATION` controls the location label returned by the API and displayed
on the dashboard. It defaults to `Church Creek`.

`MQTT_BATTERY_TOPIC` supplies a plain battery voltage. The dashboard reports a
clamped percentage using 3.0 V as 0% and 4.2 V as 100%, so readings outside
that range never display below 0% or above 100%.

MQTT is push-based rather than polled. The service subscribes continuously and
stores its newest cached value every `SAMPLE_INTERVAL_SECONDS` (300 by default).
The publisher should set the topic's retained flag so a newly started service
immediately receives the current height.

The read-only HTTP APIs are:

```text
GET /api/current
GET /api/history?hours=24
GET /api/export.csv
GET /api/status
```

`/api/current` returns source values in meters and Celsius plus converted
`heightFeet` and `temperatureFahrenheit` fields, along with a millisecond Unix
timestamp. Historic readings use the same fields. The dashboard requests 24
hours of history by default.

`/api/export.csv` downloads all retained raw samples by default. Pass
`?hours=24` (up to the retention period) to export a shorter interval.

## Reverse proxy

Point `tidegauge.dsmanning.com` at `http://127.0.0.1:3000`. For Caddy:

```caddyfile
tidegauge.dsmanning.com {
    reverse_proxy 127.0.0.1:3000
}
```

Temperature uses the analogous `MQTT_TEMPERATURE_PAYLOAD_FORMAT` and
`MQTT_TEMPERATURE_VALUE_PATH` settings. The TTN tide gauge publishes its
retained Celsius value as a plain number at `home/tide/water_temperature`.

For nginx inside the TLS-enabled server block:

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

The complete production virtual host is provided at
`deploy/nginx/tidegauge.dsmanning.com`. Install it in `sites-available`, enable
it with a symlink in `sites-enabled`, obtain the Let's Encrypt certificate, and
reload nginx after validating the configuration.

Then create or update the public DNS A/AAAA record for
`tidegauge.dsmanning.com` to match the other sites hosted on this machine.

## Operations

```sh
docker compose logs -f tidegauge
docker compose ps
curl http://127.0.0.1:3000/health
```

`/health` returns HTTP 200 only while connected to MQTT. The dashboard API is
read-only. MQTT credentials stay server-side in the mode-600 `.env` file.
