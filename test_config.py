"""
Test script to validate Mobb API configuration and connectivity.
Run this before running the main extractor to ensure everything is set up correctly.
"""

import json
import requests
import sys
from datetime import datetime, timezone, timedelta
from mobb_fp_extractor import MobbFPExtractor


def test_configuration():
    """Test if the configuration file is valid."""
    print("🧪 Testing configuration...")
    
    try:
        with open("config.json", "r") as file:
            config = json.load(file)
        
        api_token = config.get("mobb_api_token")
        tenant = config.get("tenant")
        days_of_data = config.get("daysOfData", 7)
        
        if not api_token or api_token == "YOUR_MOBB_API_TOKEN_HERE":
            print("❌ Please set your Mobb API token in config.json")
            return False
        
        if tenant not in ["api", "api-st-finacct"]:
            print(f"❌ Invalid tenant '{tenant}'. Must be 'api' or 'api-st-finacct'")
            return False
        
        if not isinstance(days_of_data, int) or days_of_data < 1:
            print(f"❌ Invalid daysOfData '{days_of_data}'. Must be a positive integer")
            return False
        
        if days_of_data > 365:
            print(f"⚠️  Warning: daysOfData is set to {days_of_data} days (more than 1 year)")
        
        print("✅ Configuration file is valid")
        print(f"   Tenant: {tenant}")
        print(f"   Days of data: {days_of_data}")
        print(f"   Token: {'*' * 20}{api_token[-8:]}")
        return True
        
    except FileNotFoundError:
        print("❌ config.json file not found")
        return False
    except json.JSONDecodeError:
        print("❌ Invalid JSON in config.json")
        return False
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False


def test_api_connectivity():
    """Test API connectivity and authentication."""
    print("\n🌐 Testing API connectivity...")
    
    try:
        extractor = MobbFPExtractor()
        
        # Test with a simple API call to get active reports
        response = extractor._make_request("/api/rest/active-reports")
        
        if response is None:
            print("❌ Failed to connect to Mobb API")
            return False
        
        fix_reports = response.get("fixReport", [])
        total_reports = len(fix_reports)
        
        # Apply the same date filtering as the main script
        days_of_data = extractor.days_of_data
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_of_data)
        
        filtered_count = 0
        for report in fix_reports:
            created_on_str = report.get("createdOn")
            if created_on_str:
                try:
                    created_on = datetime.fromisoformat(created_on_str.replace('Z', '+00:00'))
                    if created_on >= cutoff_date:
                        filtered_count += 1
                except Exception:
                    continue
        
        print(f"✅ Successfully connected to Mobb API")
        print(f"   Found {filtered_count} reports within {days_of_data} day(s) out of {total_reports} total active reports")
        
        if filtered_count == 0 and total_reports > 0:
            print(f"⚠️  Note: No reports found within the last {days_of_data} day(s). Consider increasing daysOfData in config.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API connectivity: {e}")
        return False


def main():
    """Run all tests."""
    print("🔍 Mobb FP Extractor - Configuration Test\n")
    
    # Test configuration
    config_valid = test_configuration()
    
    if not config_valid:
        print("\n❌ Configuration test failed. Please fix the issues above.")
        sys.exit(1)
    
    # Test API connectivity
    api_connected = test_api_connectivity()
    
    if not api_connected:
        print("\n❌ API connectivity test failed. Please check your token and network connection.")
        sys.exit(1)
    
    print("\n✅ All tests passed! You can now run the main extractor:")
    print("   python mobb_fp_extractor.py")


if __name__ == "__main__":
    main()