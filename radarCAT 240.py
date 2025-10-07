import struct, os,  csv, pandas as pd, matplotlib.pyplot as plt, numpy as np, os, math, time
from math import radians, degrees, sin, cos, asin, atan2
from scapy.all import rdpcap

# -------------------------------
# CONFIGURATION
# -------------------------------
#filename = "cat240"  # Adjust to your file path
pcap_file = r"C:\Users\shakt\PyCharmMiscProject\cat240\cat240.pcapng"
csv_file = "cat_output.csv"  # Adjust to where you want the CSV file saved
print("File exists:", os.path.exists(pcap_file))

# Constants
c = 299792458
RANGE_RES = 7.5
THRESHOLD = 30
EARTH_RADIUS = 6371000
radar_lat = 12.9716
radar_lon = 77.5946
# -------------------------------
# READ FILE
# -------------------------------

if not os.path.exists(pcap_file):
    print(f"Error: File not found at {pcap_file}")
else:
    with open(pcap_file, "rb") as f:
        data = f.read()
        print("File loaded successfully")

# -------------------------------
# PARSE HEADER (simplified)
# -------------------------------
cat, length = struct.unpack(">BH", data[:3])
print("Category:", cat, "Message Length:", length)
offset = 3
sac, sic = struct.unpack(">BB", data[offset:offset + 2])
offset += 2
start_az, end_az = struct.unpack(">HH", data[offset:offset + 4])
offset += 4

# -------------------------------
# BASIC PARAMETERS
# -------------------------------
start_rg = 0
cell_dur_ns = 1000
cell_dur_s = cell_dur_ns * 1e-9

def range_bearing_to_latlon(lat0, lon0, rng_m, bearing_deg):
    lat0r = radians(lat0)
    lon0r = radians(lon0)
    brng = radians(bearing_deg)
    dr = rng_m / EARTH_RADIUS
    lat1 = asin(sin(lat0r) * cos(dr) + cos(lat0r) * sin(dr) * cos(brng))
    lon1 = lon0r + atan2(sin(brng) * sin(dr) * cos(lat0r),
                         cos(dr) - sin(lat0r) * sin(lat1))
    return degrees(lat1), degrees(lon1)

def az_to_deg(raw):
    return raw * 360 / 65536

azimuth_deg = az_to_deg(start_az)

# -----------------------------
# RUN & SAVE OUTPUT
# -----------------------------

def compute_speeds(records):
    """
    Reads a list of records with columns: timestamp (sec), range_m (meters)
    Returns a list of dicts with speed between consecutive measurements.
    """
    results = []
    results.append({
        "start_time": records[0]["timestamp"],
        "end_time": records[0]["timestamp"],
        "distance_change_m": 0.0,
        "speed": 0.0,
    })
    for prev, curr in zip(records, records[1:]):
        dt = curr["timestamp"] - prev["timestamp"]
        if dt <= 0:
            dt = curr["timestamp"] - results[-1]["end_time"]
            if dt <= 0:
                continue
        dd = curr["range_m"] - prev["range_m"]
        speed_mps = dd / dt
        results.append({
            "start_time": prev["timestamp"],
            "end_time": curr["timestamp"],
            "distance_change_m": dd,
            "speed": speed_mps
        })
    return results


# -------------------------------
# AMPLITUDE SAMPLES
# -------------------------------
num_cells = length - offset
amplitude_samples = list(data[offset:offset + num_cells])
print(f"Parsed {len(amplitude_samples)} amplitude samples")

# -------------------------------
# BUILD RECORDS
# -------------------------------
records = []
for i, amp in enumerate(amplitude_samples, start=1):
    rng = cell_dur_s * (start_rg + i - 1) * c / 2
    lat, lon = range_bearing_to_latlon(radar_lat, radar_lon, rng, azimuth_deg)
    records.append({
        "timestamp": time.time(),
        "msg_index": i,
        "sac": sac,
        "sic": sic,
        "azimuth_deg": azimuth_deg,
        "range_m": rng,
        "amplitude": amp,
        "latitude": lat,
        "longitude": lon,
        "positions": [lat, lon]
    })


speeds = compute_speeds(records)
for i, record in enumerate(records):
    if i < len(speeds):
        record.update({
            "speed": speeds[i]["speed"]
        })
    else:
        record.update({
            "speed": 0.0
        })


# -------------------------------
# FILTER: REMOVE ECHO VALUES
# -------------------------------
non_echo_records = [r for r in records if r["amplitude"] <= THRESHOLD]
print(f"✅ Non-echo records kept: {len(non_echo_records)} of {len(records)} total")

# -------------------------------
# SAVE TO CSV
# -------------------------------
if non_echo_records:
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=non_echo_records[0].keys())
        writer.writeheader()
        writer.writerows(non_echo_records)
    print(f"✅ Non-echo data saved to {csv_file}")
else:
    print("⚠️ No non-echo data below/equal threshold; CSV not written.")

# -------------------------------
# OPTIONAL: VISUALIZE NON-ECHO RADIAL
# -------------------------------
if non_echo_records:
    ranges = [r["range_m"] for r in non_echo_records]
    amps = [r["amplitude"] for r in non_echo_records]
    plt.figure(figsize=(20, 10))
    plt.scatter(ranges, amps)
    plt.title(f"CAT 240 Non-Echo Samples @ {azimuth_deg:.2f}°")
    plt.xlabel("Range (m)")
    plt.ylabel("Amplitude (0–255)")
    plt.grid(True)
    plt.show()
