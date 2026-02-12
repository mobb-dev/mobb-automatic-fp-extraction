# Mobb False Positive Auto Extraction Tool

This Python script demonstrates Mobb's False Positive auto extraction capability. It fetches active reports from the Mobb API, extracts project and repository information, and generates a CSV report of irrelevant issues (those with non-empty vulnerability tags).

## Features

- ✅ Fetches all active fix reports from Mobb API
- ✅ **Date filtering** - Process only reports from the last N days (configurable)
- ✅ Extracts project names and repository names
- ✅ Filters issues to only include irrelevant ones (with non-empty tags)
- ✅ Concatenates multiple tags per issue
- ✅ **Real-time CSV updates** - See results as they're found
- ✅ Exports data to timestamped CSV files
- ✅ Comprehensive logging with timestamps
- ✅ Proper error handling and retry logic
- ✅ Configurable tenant support
- ✅ **Enhanced test validation** with filtered report counts

## Prerequisites

- Python 3.7 or higher
- Mobb API token
- Access to Mobb tenant (api or api-st-finacct)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Edit `config.json` and replace `YOUR_MOBB_API_TOKEN_HERE` with your actual Mobb API token
2. Set the `tenant` field to either `"api"` or `"api-st-finacct"`
3. Set the `daysOfData` field to control how many days back to process reports (default: 7)

Example config.json:
```json
{
  "mobb_api_token": "your-actual-api-token-here",
  "tenant": "api",
  "daysOfData": 7
}
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mobb_api_token` | string | required | Your Mobb API authentication token |
| `tenant` | string | "api" | Tenant subdomain (`"api"` or `"api-st-finacct"`) |
| `daysOfData` | integer | 7 | Number of days to go back for processing reports |

## Usage

Run the script:
```bash
python mobb_fp_extractor.py
```

The script will:
1. Read configuration from `config.json`
2. Fetch active reports from Mobb API (filtered by `daysOfData`)
3. For each report, extract project/repo information and issues
4. Filter to only irrelevant issues (those with non-empty tags)
5. **Write each issue to CSV immediately** as it's found
6. Display real-time progress and final summary

### Real-time Progress

You'll see live updates as the script processes:
```
🚀 Starting Mobb FP Auto Extraction...
📋 Configuration: Tenant=api, Days of data=7
📄 CSV file created: irrelevant_issues_output_20260211_172345.csv
📝 Added: My First Project | git-node-app-test2 | VENDOR_CODE
📝 Added: Project Test | git-node-app-test2 | TEST_CODE | VENDOR_CODE
📝 Added: Another Project | some-repo | FALSE_POSITIVE
✅ Extraction completed successfully!
📊 Total irrelevant issues exported: 15
```

## Output Files

- **CSV Report**: `irrelevant_issues_output_YYYYMMDD_HHMMSS.csv`
  - Contains: project_name, repo_name, vendorInstanceId, state (concatenated tags), FPDescription
- **Log File**: `log_YYYYMMDD_HHMMSS.txt`
  - Contains detailed logging information about the extraction process

## CSV Output Format

| Column | Description |
|--------|-------------|
| project_name | Name of the project from Mobb |
| repo_name | Name of the repository |
| vendorInstanceId | Vendor instance ID (shows "null" if empty) |
| state | Concatenated vulnerability tags (e.g., "FALSE_POSITIVE \| TEST_CODE") |
| FPDescription | Detailed description of why the issue is a false positive |

## API Endpoints Used

1. `/api/rest/active-reports` - Gets list of active fix reports
2. `/api/rest/fix-reports/{fixReportId}` - Gets project/repo details for each report
3. `/api/rest/v5/issues?fixReportId={fixReportId}` - Gets issues for each report

## Error Handling

The script includes comprehensive error handling for:
- Network timeouts and connection errors
- Invalid API responses
- Missing configuration
- File I/O errors
- API authentication failures

## Filtering Logic

The script uses two levels of filtering:

### 1. **Date Filtering** (Active Reports)
- Only processes reports created within the last `daysOfData` days
- Filters based on the `createdOn` field from `/api/rest/active-reports`
- Logs which reports are included/excluded

### 2. **Tag-based Filtering** (Issues)
The script uses a **whitelist approach** and only includes issues that have:
- Non-empty `vulnerabilityReportIssueTags` array
- At least one tag with a non-empty `vulnerability_report_issue_tag_value`

Common tag values include:
- `FALSE_POSITIVE`
- `TEST_CODE`
- `VENDOR_CODE`
- `AUTO_GENERATED_CODE`

### Example Filtering Results
```
Fetching active reports from the last 7 days...
Filtering reports created after: 2026-02-04T17:23:45+00:00
Including report 6300dc09-... created on 2026-02-11T23:42:50+00:00
Excluding report 99e12f6b-... created on 2026-01-30T19:07:09+00:00 (too old)
Found 15 active reports within the last 7 days (total: 86)
```

## Troubleshooting

1. **"Please set your Mobb API token in config.json"**
   - Update the `mobb_api_token` field in config.json with your actual token

2. **HTTP 401 Unauthorized**
   - Verify your API token is correct and has proper permissions

3. **HTTP 403 Forbidden**
   - Check that your account has access to the specified tenant

4. **No active reports found within date range**
   - Increase the `daysOfData` value in config.json
   - Check the test output: "Found 0 reports within 1 day(s) out of 86 total active reports"

5. **No irrelevant issues found**
   - Verify that there are active reports with issues that have non-empty tags
   - Check that the reports are in "Finished" state

6. **CSV file not updating**
   - The script now writes to CSV in real-time - refresh your file viewer
   - Check the console output for "📝 Added:" messages

7. **Network errors**
   - Check your internet connection
   - Verify the tenant URL is accessible

8. **"Invalid daysOfData" error**
   - Ensure `daysOfData` is a positive integer (1, 7, 30, etc.)
   - Run `python test_config.py` to validate your configuration

## Support

For issues or questions, please contact Mobb support at support@mobb.ai