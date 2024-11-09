import json
import datetime
import os
import logging
import subprocess

# Set up logger for the script
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def check_dates_in_json(json_file):
    """Check if the JSON file contains today's date and log the findings."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    topics_found_today = False
    all_dates_past = True  # Flag to track if all dates are in the past

    try:
        with open(json_file, "r") as file:
            data = json.load(file)

        logger.info(f"Checking '{json_file}' for today's date ({today})...")

        # Check each entry in the JSON file
        for entry in data:
            # If today's date is found, log the file and topic details
            if entry.get("Date") == today:
                logger.info(
                    f"Found today's date ({today}) in {json_file}. Proceeding with course content creation..."
                )
                # Call course_content_creator.py with the found JSON file
                subprocess.run(["python3", "course_content_creator.py", json_file])
                topics_found_today = True
                break  # Stop once we find today's date

            # Check if any date is in the future
            if entry.get("Date") > today:
                all_dates_past = False

        # If all dates are in the past, log a warning
        if all_dates_past:
            logger.warning(
                f"WARNING: All dates in '{json_file}' are in the past. Consider moving this file to 'completed'."
            )

        if not topics_found_today:
            logger.info(f"No topics found for today's date in {json_file}.")
            return None  # No match found for today's date

        return json_file

    except Exception as e:
        logger.error(f"Error processing {json_file}: {e}")
        return None


def process_json_files():
    """Process all JSON files with today's date or provide warnings for outdated ones."""
    # Get the list of JSON files in the current directory
    json_files = [
        f
        for f in os.listdir()
        if f.startswith("topics_and_prompts_") and f.endswith(".json")
    ]

    files_with_topics_today = []

    # Check each file
    for json_file in json_files:
        result = check_dates_in_json(json_file)
        if result:
            files_with_topics_today.append(result)

    # After processing all files, check if any topics were found for today
    if not files_with_topics_today:
        logger.warning("No topics found for today's date across any JSON files.")


def main():
    """Main function to process JSON files based on today's date."""
    process_json_files()


if __name__ == "__main__":
    main()
