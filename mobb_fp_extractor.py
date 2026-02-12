"""
Mobb FP Auto Extraction Tool

This script demonstrates Mobb's False Positive auto extraction capability.
It fetches active reports, extracts project and repository information, 
and generates a CSV report of irrelevant issues (those with non-empty tags).

Author: Mobb.ai
Date: February 11, 2026
"""

import json
import csv
import requests
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import os
import sys


class MobbFPExtractor:
    """Main class for extracting false positive data from Mobb API."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the extractor with configuration."""
        self.config = self._load_config(config_path)
        self.api_token = self.config.get("mobb_api_token")
        self.tenant = self.config.get("tenant", "api")
        self.days_of_data = self.config.get("daysOfData", 7)
        self.base_url = f"https://{self.tenant}.mobb.ai"
        
        # Setup logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"log_{timestamp}.txt"
        self.csv_filename = f"irrelevant_issues_output_{timestamp}.csv"
        
        self._setup_logging()
        
        # Setup session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'x-mobb-key': self.api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Initialize CSV file with headers
        self._initialize_csv()
        
        logging.info(f"Initialized MobbFPExtractor for tenant: {self.tenant}")
        logging.info(f"Days of data to process: {self.days_of_data}")
        logging.info(f"CSV output file: {self.csv_filename}")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
                
            if not config.get("mobb_api_token") or config.get("mobb_api_token") == "YOUR_MOBB_API_TOKEN_HERE":
                raise ValueError("Please set your Mobb API token in config.json")
                
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {config_path} not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file {config_path}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_filename, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Mobb API with error handling."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            logging.info(f"Making request to: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logging.error(f"Timeout occurred for request to {endpoint}")
            return None
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error for {endpoint}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error for {endpoint}: {e}")
            return None
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON response from {endpoint}")
            return None
    
    def get_active_reports(self) -> List[str]:
        """Get list of active fix report IDs within the configured date range."""
        logging.info(f"Fetching active reports from the last {self.days_of_data} days...")
        
        response = self._make_request("/api/rest/active-reports")
        if not response:
            logging.error("Failed to fetch active reports")
            return []
        
        fix_reports = response.get("fixReport", [])
        
        # Calculate the cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.days_of_data)
        logging.info(f"Filtering reports created after: {cutoff_date.isoformat()}")
        
        filtered_report_ids = []
        
        for report in fix_reports:
            report_id = report.get("id")
            created_on_str = report.get("createdOn")
            
            if not report_id or not created_on_str:
                continue
            
            try:
                # Parse the createdOn date
                created_on = datetime.fromisoformat(created_on_str.replace('Z', '+00:00'))
                
                # Check if the report is within the date range
                if created_on >= cutoff_date:
                    filtered_report_ids.append(report_id)
                    logging.info(f"Including report {report_id} created on {created_on.isoformat()}")
                else:
                    logging.debug(f"Excluding report {report_id} created on {created_on.isoformat()} (too old)")
                    
            except Exception as e:
                logging.error(f"Error parsing date for report {report_id}: {e}")
                continue
        
        logging.info(f"Found {len(filtered_report_ids)} active reports within the last {self.days_of_data} days (total: {len(fix_reports)})")
        return filtered_report_ids
    
    def get_fix_report_details(self, fix_report_id: str) -> Optional[Dict]:
        """Get fix report details including project and repo information."""
        logging.info(f"Fetching details for fix report: {fix_report_id}")
        
        response = self._make_request(f"/api/rest/fix-reports/{fix_report_id}")
        if not response:
            logging.error(f"Failed to fetch details for fix report: {fix_report_id}")
            return None
        
        fix_reports = response.get("fixReport", [])
        if not fix_reports:
            logging.warning(f"No fix report data found for ID: {fix_report_id}")
            return None
        
        fix_report = fix_reports[0]
        
        # Extract project name and repo name
        project_name = None
        repo_name = None
        
        vulnerability_report = fix_report.get("vulnerabilityReport", {})
        project = vulnerability_report.get("project", {})
        if project:
            project_name = project.get("name")
        
        repo = fix_report.get("repo", {})
        if repo:
            repo_name = repo.get("name")
        
        return {
            "project_name": project_name,
            "repo_name": repo_name,
            "fix_report_id": fix_report_id
        }
    
    def get_issues_for_fix_report(self, fix_report_id: str) -> List[Dict]:
        """Get issues for a specific fix report."""
        logging.info(f"Fetching issues for fix report: {fix_report_id}")
        
        params = {"fixReportId": fix_report_id}
        response = self._make_request("/api/rest/v5/issues", params=params)
        
        if not response:
            logging.error(f"Failed to fetch issues for fix report: {fix_report_id}")
            return []
        
        # Handle the correct API response structure
        # The response wraps the issues in getIssuesApiV5 object
        issues_data = response.get("getIssuesApiV5", {})
        issues = issues_data.get("vulnerability_report_issue", [])
        
        logging.info(f"Found {len(issues)} total issues for fix report: {fix_report_id}")
        
        return issues
    
    def filter_irrelevant_issues(self, issues: List[Dict]) -> List[Dict]:
        """Filter issues to only include those with non-empty tags (irrelevant issues)."""
        irrelevant_issues = []
        
        for issue in issues:
            tags = issue.get("vulnerabilityReportIssueTags", [])
            
            # Check if tags list is not empty
            if tags:
                # Extract tag values and concatenate them
                tag_values = []
                for tag in tags:
                    tag_value = tag.get("vulnerability_report_issue_tag_value")
                    if tag_value:
                        tag_values.append(tag_value)
                
                if tag_values:
                    issue["concatenated_tags"] = " | ".join(tag_values)
                    irrelevant_issues.append(issue)
        
        logging.info(f"Filtered to {len(irrelevant_issues)} irrelevant issues")
        return irrelevant_issues
    
    def process_all_reports(self) -> int:
        """Process all active reports and extract irrelevant issues. Returns count of issues found."""
        logging.info("Starting to process all active reports...")
        
        # Get active reports
        report_ids = self.get_active_reports()
        if not report_ids:
            logging.warning("No active reports found")
            return 0
        
        total_irrelevant_issues = 0
        
        for report_id in report_ids:
            try:
                # Get fix report details
                fix_report_details = self.get_fix_report_details(report_id)
                if not fix_report_details:
                    continue
                
                # Get issues for this report
                issues = self.get_issues_for_fix_report(report_id)
                if not issues:
                    continue
                
                # Filter to irrelevant issues only
                irrelevant_issues = self.filter_irrelevant_issues(issues)
                
                # Process each irrelevant issue immediately
                for issue in irrelevant_issues:
                    issue_data = {
                        "project_name": fix_report_details.get("project_name", ""),
                        "repo_name": fix_report_details.get("repo_name", ""),
                        "vendorInstanceId": issue.get("vendorInstanceId") if issue.get("vendorInstanceId") is not None else "null",
                        "state": issue.get("concatenated_tags", ""),
                        "FPDescription": issue.get("fpDescription", "")
                    }
                    
                    # Append to CSV immediately
                    self._append_to_csv(issue_data)
                    total_irrelevant_issues += 1
                
                logging.info(f"Processed report {report_id}: found {len(irrelevant_issues)} irrelevant issues")
                
            except Exception as e:
                logging.error(f"Error processing report {report_id}: {e}")
                continue
        
        logging.info(f"Total irrelevant issues found across all reports: {total_irrelevant_issues}")
        return total_irrelevant_issues
    
    def write_csv_report(self, irrelevant_issues: List[Dict]):
        """Write the irrelevant issues data to a CSV file."""
        if not irrelevant_issues:
            logging.warning("No irrelevant issues to write to CSV")
            return
        
        logging.info(f"Writing {len(irrelevant_issues)} issues to CSV: {self.csv_filename}")
        
        fieldnames = ["project_name", "repo_name", "vendorInstanceId", "state", "FPDescription"]
        
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(irrelevant_issues)
            
            logging.info(f"Successfully wrote CSV report: {self.csv_filename}")
            print(f"\n✅ CSV report generated: {self.csv_filename}")
            print(f"📊 Total irrelevant issues exported: {len(irrelevant_issues)}")
            
        except Exception as e:
            logging.error(f"Error writing CSV file: {e}")
            raise
    
    def _initialize_csv(self):
        """Initialize CSV file with headers."""
        try:
            fieldnames = ["project_name", "repo_name", "vendorInstanceId", "state", "FPDescription"]
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            logging.info(f"Initialized CSV file: {self.csv_filename}")
            print(f"📄 CSV file created: {self.csv_filename}")
        except Exception as e:
            logging.error(f"Error initializing CSV file: {e}")
            raise
    
    def _append_to_csv(self, issue_data: Dict):
        """Append a single issue to the CSV file."""
        try:
            fieldnames = ["project_name", "repo_name", "vendorInstanceId", "state", "FPDescription"]
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(issue_data)
            print(f"📝 Added: {issue_data['project_name']} | {issue_data['repo_name']} | {issue_data['state']}")
        except Exception as e:
            logging.error(f"Error appending to CSV file: {e}")
    
    def run(self):
        """Main execution method."""
        try:
            print("🚀 Starting Mobb FP Auto Extraction...")
            print(f"📋 Configuration: Tenant={self.tenant}, Days of data={self.days_of_data}")
            print(f"📝 Log file: {self.log_filename}")
            print(f"📄 Output CSV: {self.csv_filename}")
            print()
            
            logging.info("="*50)
            logging.info("Starting Mobb FP Auto Extraction")
            logging.info(f"Tenant: {self.tenant}")
            logging.info(f"Base URL: {self.base_url}")
            logging.info("="*50)
            
            # Process all reports and write irrelevant issues to CSV in real-time
            total_issues_count = self.process_all_reports()
            
            logging.info("="*50)
            logging.info("Mobb FP Auto Extraction completed successfully")
            logging.info(f"Total issues exported: {total_issues_count}")
            logging.info("="*50)
            
            print(f"\n✅ Extraction completed successfully!")
            print(f"📊 Total irrelevant issues exported: {total_issues_count}")
            print(f"📄 CSV file: {self.csv_filename}")
            
        except Exception as e:
            logging.error(f"Fatal error during extraction: {e}")
            print(f"❌ Error: {e}")
            raise


def main():
    """Main entry point."""
    try:
        extractor = MobbFPExtractor()
        extractor.run()
    except KeyboardInterrupt:
        print("\n🛑 Extraction cancelled by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()