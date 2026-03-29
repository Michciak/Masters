import os
import re
import r5py

def patch():
    init_file = r5py.__file__
    target_file = os.path.join(os.path.dirname(init_file), 'r5', 'transport_network.py')

    if not os.path.exists(target_file):
        print(f"Error: Could not find {target_file}")
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if "writableTempFileFromGtfs" in content and "findPatterns" in content:
        print("r5py is already patched on this machine!")
        return

    pattern = r'gtfs_feed\s*=\s*com\.conveyal\.gtfs\.GTFSFeed\.readOnlyTempFileFromGtfs\(\s*f"\{gtfs_file\}"\s*\)'
    replacement = """gtfs_feed = com.conveyal.gtfs.GTFSFeed.writableTempFileFromGtfs(f"{gtfs_file}")
                if gtfs_feed.patternForTrip.size() == 0:
                    print("Applying on-the-fly GTFS validation bypass for empty pattern maps...")
                    gtfs_feed.findPatterns()"""

    new_content, count = re.subn(pattern, replacement, content)

    if count > 0:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully patched r5py at {target_file}!")
    else:
        print("Failed to patch: Could not find the expected code in r5py. You might be using a newer version where this is fixed.")

if __name__ == "__main__":
    patch()