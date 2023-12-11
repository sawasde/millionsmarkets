from src.utils.utils import divide_list_chunks, discord_webhook_send, integrate_area_below, date_y_m_d, date_now, timestamp_to_date, round_float_num, get_timestamp, date_oper_timestamp_and_date, date_ago_timestmp, text_to_printable, num_in_text, hand_file, hand_json, logger_path, logger
import pytest
import pytz
import json
import os
import datetime as dt
import pandas as pd
from freezegun import freeze_time
from unittest.mock import patch, MagicMock

@pytest.fixture
def temp_dir(tmpdir):
    dir_path = tmpdir.mkdir("test_dir")
    return str(dir_path)

@pytest.fixture
def temp_file(tmpdir):
    file_path = tmpdir.join("test_file.txt")
    return str(file_path)

@pytest.fixture
def temp_json_file(tmpdir):
    file_path = tmpdir.join("test_file.json")
    return str(file_path)

@pytest.fixture
def mock_requests():
    with patch('requests.post') as mock_post:
        yield mock_post

# --- divide_list_chunks ---
def test_divide_list_chunks():
    # Test case 1
    input_list_1 = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    chunks_1 = 3
    expected_output_1 = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert list(divide_list_chunks(input_list_1, chunks_1)) == expected_output_1

    # Test case 2
    input_list_2 = [10, 20, 30, 40, 50, 60]
    chunks_2 = 2
    expected_output_2 = [[10, 20], [30, 40], [50, 60]]
    assert list(divide_list_chunks(input_list_2, chunks_2)) == expected_output_2

    # Test case 3
    input_list_3 = [100, 200, 300, 400]
    chunks_3 = 4
    expected_output_3 = [[100, 200, 300, 400]]
    assert list(divide_list_chunks(input_list_3, chunks_3)) == expected_output_3

    # Test case 4: Empty list
    input_list_4 = []
    chunks_4 = 2
    expected_output_4 = []
    assert list(divide_list_chunks(input_list_4, chunks_4)) == expected_output_4

# --- discord_webhook_send ---
def test_discord_webhook_send_success(mock_requests):
    # Mocking a successful response
    mock_requests.return_value.status_code = 200

    url = "https://example.com/webhook"
    username = "TestUser"
    msg = "Hello, World!"
    embed = {"description": "desc", "title": "embed title"}
    attempts = 5

    results = discord_webhook_send(url, username, msg, embed, attempts)

    assert len(results) == 1
    assert results[0].status_code == 200
    mock_requests.assert_called_once_with(
        url,
        json={
            'content': msg,
            'username': username,
            'embeds': [embed],
        },
        headers={'Content-Type': 'application/json'},
        timeout=24
    )

# --- discord_webhook_send fail ---
def test_discord_webhook_send_retry_on_failure(mock_requests):
    # Mocking a failed response with a retry
    mock_requests.side_effect = [MagicMock(status_code=500), MagicMock(status_code=200)]

    url = "https://example.com/webhook"
    username = "TestUser"
    msg = "Hello, World!"
    embed = {"description": "desc", "title": "embed title"}
    attempts = 2  # Two attempts, the first one fails, and the second one succeeds

    results = discord_webhook_send(url, username, msg, embed, attempts)

    assert len(results) == 2
    assert results[0].status_code == 500
    assert results[1].status_code == 200
    assert mock_requests.call_count == 2

# --- integrate_area_below ---
def test_integrate_area_below():

    # Create a sample DataFrame for testing
    data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]}
    df = pd.DataFrame(data)

    # Call the function
    result_df = integrate_area_below(df, yaxis='y', dx_portion=1.0)

    # Assertions
    assert 'area' in result_df.columns
    assert len(result_df) == len(df)

# --- date_y_m_d ---
@freeze_time("2023, 1, 15")
def test_date_y_m_d():

    # Call the function
    formatted_date = date_y_m_d()

    # Assertions
    assert formatted_date == '20230115'

# --- date_now ---
@freeze_time(dt.datetime(2023, 1, 15, 12, 34, 56))
def test_date_now_tuple():

    # Call the function
    result_tuple = tuple(date_now())

    # Assertions
    expected_tuple = (2023, 1, 15, 7, 34, 56, 6, 15, 0)
    assert result_tuple == expected_tuple

# --- date_now ---
@freeze_time(dt.datetime(2023, 1, 15, 12, 34, 56))
def test_date_now_datetime():
    # Call the function with use_tuple=False
    result_datetime = date_now(use_tuple=False)

    # Assertions
    assert result_datetime.year == 2023
    assert result_datetime.month == 1
    assert result_datetime.day == 15
    assert result_datetime.hour == 7 # GMT-5
    assert result_datetime.minute ==  34
    assert result_datetime.second ==  56

# --- timestamp_to_date ---
def test_timestamp_to_date():
    # Mock the conversion from timestamp to date

    # Call the function
    result_date = timestamp_to_date(1702316835)  # Use a sample timestamp for testing

    # Assertions
    assert result_date.year == 2023
    assert result_date.month == 12
    assert result_date.day == 11
    assert result_date.hour == 12 # GMT-5
    assert result_date.minute ==  47
    assert result_date.second ==  15

# --- round_float_num ---
def test_round_float_num():
    # Test case 1: Round to 2 digits
    result_1 = round_float_num(3.14159, 2)
    assert result_1 == 3.14

    # Test case 2: Round to 0 digits (integer)
    result_2 = round_float_num(123.456, 0)
    assert result_2 == 123.0

    # Test case 3: Round to 5 digits
    result_3 = round_float_num(7.123456789, 5)
    assert result_3 == 7.12346

    # Test case 4: Round to 3 digits (negative number)
    result_4 = round_float_num(-9.87654321, 3)
    assert result_4 == -9.877

    # Test case 5: Round to more digits than available
    result_5 = round_float_num(42.123, 10)
    assert result_5 == 42.123  # No change since the original number has fewer digits

# ---get_timestamp---
@freeze_time(dt.datetime(2023, 1, 15, 12, 34, 56))
def test_get_timestamp():

    # Call the function with default multiplier (1)
    result_default_multiplier = get_timestamp()

    # Call the function with a custom multiplier (e.g., 1000)
    result_custom_multiplier = get_timestamp(multiplier=1000)

    # Assertions
    expected_default_multiplier = int(dt.datetime(2023, 1, 15, 12, 34, 56).timestamp())
    expected_custom_multiplier = expected_default_multiplier * 1000

    assert result_default_multiplier == expected_default_multiplier
    assert result_custom_multiplier == expected_custom_multiplier

# --- date_oper_timestamp_and_date ---
def test_date_oper_timestamp_and_date_addition():

    # Call the function with addition operation
    result_addition = date_oper_timestamp_and_date(1673786096, oper='+', days=5, hours=3)

    # Assertions
    expected_addition = 1674228896# Result after adding 5 days and 3 hours to the timestamp
    assert result_addition == expected_addition

# --- date_oper_timestamp_and_date ---
def test_date_oper_timestamp_and_date_subtraction():

    # Call the function with subtraction operation
    result_subtraction = date_oper_timestamp_and_date(1673786096, oper='-', days=3, hours=2)

    # Assertions
    expected_subtraction = 1673519696  # Result after subtracting 3 days and 2 hours from the timestamp
    assert result_subtraction == expected_subtraction

# --- date_ago_timestmp ---
@freeze_time(dt.datetime(2023, 1, 15, 12, 34, 56))
def test_date_ago_timestmp():
    # January 13, 2023 7:04:56 AM
    # Call the function with a duration of 2 days, 5 hours, and 30 minutes ago
    result_timestamp = date_ago_timestmp(days=2, hours=5, minutes=30)

    # Assertions
    expected_timestamp = int(dt.datetime(2023, 1, 13, 7, 4, 56).timestamp())
    assert result_timestamp == expected_timestamp

# --- text_to_printable ---
def test_text_to_printable():
    # Test case 1: Text with printable characters only
    result_1 = text_to_printable("Hello, World!")
    assert result_1 == "Hello, World!"

    # Test case 2: Text with non-printable characters
    result_2 = text_to_printable("Non-printable \x01\x02\x03 characters")
    assert result_2 == "Non-printable  characters"

    # Test case 3: Empty text
    result_3 = text_to_printable("")
    assert result_3 == ""

    # Test case 4: Text with only non-printable characters
    result_4 = text_to_printable("\x01\x02\x03")
    assert result_4 == ""

    # Test case 5: Text with a mix of printable and non-printable characters
    result_5 = text_to_printable("Mixed \x01 Text")
    assert result_5 == "Mixed  Text"

# --- num_in_text ---
def test_num_in_text():
    # Test case 1: Text without numbers
    result_1 = num_in_text("Hello, World!")
    assert result_1 is False

    # Test case 2: Text with a number
    result_2 = num_in_text("There is a 123 in this text.")
    assert result_2 is True

    # Test case 3: Text with multiple numbers
    result_3 = num_in_text("Multiple numbers: 42, 7, and 99")
    assert result_3 is True

    # Test case 4: Text with non-numeric characters
    result_4 = num_in_text("No numbers here: @#$%^&*")
    assert result_4 is False

    # Test case 5: Empty text
    result_5 = num_in_text("")
    assert result_5 is False

# --- hand_file ---
def test_hand_file_read(temp_file):
    # Write content to the temporary file
    content_to_write = "Test content"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(content_to_write)

    # Read the content using hand_file
    result_content = hand_file(temp_file, 'r')

    # Assertions
    assert result_content == content_to_write

# --- hand_file ---
def test_hand_file_write(temp_file):
    # Write content to the temporary file using hand_file
    content_to_write = "Test content"
    hand_file(temp_file, 'w', data=content_to_write)

    # Read the content directly from the file
    with open(temp_file, 'r', encoding='utf-8') as f:
        result_content = f.read()

    # Assertions
    assert result_content.strip() == content_to_write


# --- hand_json ---
def test_hand_json_read(temp_json_file):
    # Write JSON content to the temporary file
    json_content = {"key": "value"}
    with open(temp_json_file, 'w', encoding='utf-8') as f:
        json.dump(json_content, f)

    # Read the JSON content using hand_json
    result_json = hand_json(temp_json_file, 'r')

    # Assertions
    assert result_json == json_content

# --- hand_json ---
def test_hand_json_write(temp_json_file):
    # Write JSON content to the temporary file using hand_json
    json_content = {"key": "value"}
    hand_json(temp_json_file, 'w', data=json_content)

    # Read the JSON content directly from the file
    with open(temp_json_file, 'r', encoding='utf-8') as f:
        result_json = json.load(f)

    # Assertions
    assert result_json == json_content

# --- hand_json ---
def test_hand_json_write_empty(temp_json_file):
    # Write an empty JSON object to the temporary file using hand_json
    hand_json(temp_json_file, 'w')

    # Read the JSON content directly from the file
    with open(temp_json_file, 'r', encoding='utf-8') as f:
        result_json = json.load(f)

    # Assertions
    assert result_json == None

# --- logger_path ---
def test_logger_path(temp_dir):
    # Call the function to set the logger path
    log_message = ""
    message = "Test log message"
    logger_path(os.path.join(temp_dir, "test_log.log"))

    logger.info(message)

    # Assertions
    log_file_path = os.path.join(temp_dir, "test_log.log")

    with open(log_file_path, 'r', encoding='utf-8') as f:
        log_message = f.read()

    log_message = log_message.split('-')[-1].strip()

    assert os.path.isfile(log_file_path)
    assert message == log_message
