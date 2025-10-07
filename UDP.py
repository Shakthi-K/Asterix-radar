import struct
import os
import csv
import time
import matplotlib.pyplot as plt
from math import radians, degrees, sin, cos, asin, atan2

# -------------------------------
# CONFIGURATION
# -------------------------------
pcap_file = r"C:\Users\shakt\PyCharmMiscProject\cat240\cat240.pcapng"
csv_file = r"C:\Users\shakt\PyCharmMiscProject\cat240\cat_output_new.csv"
print("File exists:", os.path.exists(pcap_file))

# Constants
c = 299792458         # speed of light in m/s
RANGE_RES = 7.5       # meters
THRESHOLD = 30        # amplitude threshold for echo filtering
EARTH_RADIUS = 6371000
radar_lat = 12.9716
radar_lon = 77.5946

# -------------------------------
# READ FILE
# -------------------------------
if not os.path.exists(pcap_file):
    print(f"Error: File not found at {pcap_file}")
    exit()
else:
    with open(pcap_file, "rb") as f:
        data = f.read()
        print("File loaded successfully")

# -------------------------------
# PARSE HEADER (simplified)
# -------------------------------
cat, length = struct.unpack(">BH", data[:3])
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

# -------------------------------
# AMPLITUDE SAMPLES
# -------------------------------
num_cells = length - offset
amplitude_samples = list(data[offset:offset + num_cells])
print(f"Parsed {len(amplitude_samples)} amplitude samples")

# -------------------------------
# BUILD RECORDS WITH NEW FIELDS
# -------------------------------
records = []
for i, amp in enumerate(amplitude_samples, start=1):
    rng = cell_dur_s * (start_rg + i - 1) * c / 2
    lat, lon = range_bearing_to_latlon(radar_lat, radar_lon, rng, azimuth_deg)

    # Filter out echoes
    if amp > THRESHOLD:
        continue

    records.append({
        "No": i,
        "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "Source": f"Radar_{sac}",
        "Destination": "Unknown",
        "Protocol": "CAT240",
        "Length": 1,
        "Info": f"Az:{azimuth_deg:.2f}, Range:{rng:.2f}m, Amp:{amp}"
    })

print(f"✅ Non-echo records kept: {len(records)}")

# -------------------------------
# SAVE TO CSV
# -------------------------------
if records:
    with open(csv_file, mode="w", newline="") as f:
        fieldnames = ["No", "Time", "Source", "Destination", "Protocol", "Length", "Info"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"✅ Data saved to {csv_file}")
else:
    print("⚠️ No non-echo records; CSV not written.")

# -------------------------------
# OPTIONAL: VISUALIZE NON-ECHO RADIAL
# -------------------------------
if records:
    ranges = [float(r["Info"].split("Range:")[1].split("m")[0]) for r in records]
    amps = [int(r["Info"].split("Amp:")[1]) for r in records]
    plt.figure(figsize=(20, 10))
    plt.scatter(ranges, amps)
    plt.title(f"CAT 240 Non-Echo Samples @ {azimuth_deg:.2f}°")
    plt.xlabel("Range (m)")
    plt.ylabel("Amplitude (0–255)")
    plt.grid(True)
    plt.show()
