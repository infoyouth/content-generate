import datetime
import requests
import json
import sys
import os
import logging


# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def initialise_url_endpoint():
    """Initialise the API URL endpoint based on the environment (local or GitHub Actions)."""
    # Check if running in GitHub Actions or locally
    if os.getenv("GITHUB_ACTIONS"):
        # In GitHub Actions, read from the GitHub secrets
        API_KEY = os.getenv("GEMINI_API_KEY")
    else:
        # Running locally, read from environment variable
        API_KEY = os.getenv("API_KEY")

    # If an API key is found, create the API URL
    if API_KEY:
        API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"
        logger.info(f"API_URL is: {API_URL}")
        return API_URL
    else:
        logger.error("Error: API key not found.")
        return None  # Return None if API_KEY is not found


def load_prompts_from_json(filename):
    """Load JSON file containing topic, date, prompts, and header info."""
    try:
        with open(filename, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.error(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Error: File '{filename}' is not a valid JSON.")
        sys.exit(1)

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Look for a topic that matches today's date
    for entry in data:
        if entry["Date"] == today:
            header_info = entry.get("Header", {})
            if not isinstance(header_info, dict):
                logger.warning(f"Unexpected format for Header: {header_info}")
                header_info = {}
            return entry["Topic"], entry["Prompts"], header_info

    # If no matching date found, log a message and return None
    logger.warning(f"No matching topic found for today's date: {today}.")
    return None, None, None


def format_header(header_info):
    # Format the header in markdown with YAML front matter
    header = f"""---
title: {header_info.get("title", "Untitled")}
description: {header_info.get("description", "")}
author: {header_info.get("author", "unknown")}
date: {header_info.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))}
categories: {header_info.get("categories", [])}
tags: {header_info.get("tags", [])}
pin: {header_info.get("pin", False)}
math: {header_info.get("math", False)}
mermaid: {header_info.get("mermaid", False)}
---\n\n"""
    return header


def generate_content(prompts, topic, header_info, API_URL):
    style_it = (
        'Please generate visually appealing content using Markdown and "use relevant emojis in headings", '
        "incorporating diverse text styles such as bold, italic, inline code, and headers. "
        "For the headings, please use the following color scheme: Main Heading (H1): Use "
        '# <span style="color:#e67e22">Main Heading</span> Subheading (H2): Use '
        '## <span style="color:#2980b9">Subheading</span> Sub-subheading (H3): Use '
        '### <span style="color:#8e44ad">Sub-subheading</span> Additionally, add '
        "Mermaid diagrams or flowcharts where relevant, and organize the content into visually "
        "distinct sections to highlight key points, using bullet points and clear formatting for clarity."
    )

    content = ""
    headers = {"Content-Type": "application/json"}

    # Add "What we will learn in this post?" section with styled bullets
    content += '# <span style="color:#e67e22; font-size: 24px;">What we will learn in this post?</span>\n'
    content += "<ul style='list-style-type: none; padding-left: 0;'>\n"
    for prompt in prompts:
        content += (
            f"<li style='margin: 6px 0;'>"
            f"<span style='color: #2980b9; font-size: 20px; font-weight: bold;'>👉</span> "
            f"<span style='color: #2ecc71; font-size: 18px; font-weight: bold;'>{prompt['title']}</span>"
            f"</li>\n"
        )  # Color bullets and titles
    content += "</ul>\n\n"

    for prompt in prompts:
        logger.info(
            f"Processing prompt: {prompt['title']}"
        )  # Debug statement to log prompts

        # Check if the title is "Conclusion!" to exclude `style_it`
        if prompt["title"].strip() == "Conclusion!":
            prompt_text = prompt["prompt"]
        else:
            prompt_text = f"{prompt['prompt']} 'in easy english.' {style_it}"

        # Prepare the data for the API request
        data = {
            "contents": [
                {"parts": [{"text": prompt_text}]}  # Use formatted prompt text
            ]
        }

        # Send request to Gemini API
        try:
            response = requests.post(API_URL, headers=headers, json=data)
            response.raise_for_status()  # Raise an exception for bad HTTP responses

            if response.status_code == 200:
                result = response.json()

                # Log the entire response for debugging
                logger.debug(f"API response for '{prompt['title']}': {result}")

                # Check if 'candidates' and 'content' keys exist in the response
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate:
                        generated_text = candidate["content"]["parts"][0]["text"]
                        title_html = (
                            f'# <span style="color:#e67e22">{prompt["title"]}</span>'
                        )
                        content += f"{generated_text}\n\n"
                    else:
                        logger.error(
                            f"Error: 'content' field missing in response for '{prompt['title']}'."
                        )
                        content += f"Error: 'content' field missing in response for '{prompt['title']}'.\n\n"
                else:
                    logger.error(
                        f"Error: 'candidates' field missing or empty in response for '{prompt['title']}'."
                    )
                    content += f"Error: 'candidates' field missing or empty in response for '{prompt['title']}'.\n\n"
            else:
                logger.error(
                    f"API request failed with status code {response.status_code} for '{prompt['title']}'."
                )
                content += f"Error: API request failed with status code {response.status_code} for '{prompt['title']}'.\n\n"

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making API request for '{prompt['title']}': {e}")
            content += f"Error making API request for '{prompt['title']}': {e}\n\n"

    return content


def save_to_markdown(content, topic, header_info):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}-{topic.lower().replace(' ', '-')}.md"

    try:
        # Write header and content to the markdown file
        with open(filename, "w", encoding="utf-8") as file:
            file.write(
                format_header(header_info)
            )  # Assuming format_header is defined elsewhere
            file.write(content)

        logger.info(f"Content successfully saved to {filename}")

    except Exception as e:
        logger.error(f"Failed to save content to {filename}: {e}")


def main():
    # Check for command-line arguments
    if len(sys.argv) < 2:
        logger.error("Usage: python3 script.py <filename>.json")
        sys.exit(1)

    filename = sys.argv[1]

    API_URL = initialise_url_endpoint()
    if API_URL:
        # Proceed with the logic that uses the API_URL
        logger.info(f"Successfully initialized API_URL: {API_URL}")
    else:
        # Handle the case where API_URL could not be initialized
        logger.error("Failed to initialize API_URL.")

    # Load topic, prompts, and header info from JSON file based on today's date
    topic, prompts, header_info = load_prompts_from_json(filename)

    if topic and prompts:
        logger.info(f"Generating content for topic: {topic}")
        content = generate_content(prompts, topic, header_info, API_URL)
        save_to_markdown(content, topic, header_info)
    else:
        logger.warning("No matching topic found for today's date.")


if __name__ == "__main__":
    main()
