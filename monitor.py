#!/usr/bin/env python3
"""
Azure Resource Monitor - Python Automation with AI Analysis
Monitors Azure resources, detects anomalies and generates reports
"""

import os
import json
import datetime
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from tabulate import tabulate
from colorama import init, Fore, Style

init(autoreset=True)
load_dotenv()

SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP  = os.getenv("RESOURCE_GROUP", "rg-monitor-demo")

def get_credentials():
    print(Fore.CYAN + "Connecting to Azure...")
    return AzureCliCredential()

def list_resource_groups(credential):
    print(Fore.CYAN + "\nScanning Resource Groups...")
    client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
    groups = list(client.resource_groups.list())
    
    data = []
    for g in groups:
        data.append([g.name, g.location, g.properties.provisioning_state])
    
    print(Fore.GREEN + f"Found {len(groups)} resource group(s):\n")
    print(tabulate(data, headers=["Name", "Location", "Status"], tablefmt="rounded_outline"))
    return groups

def list_virtual_machines(credential):
    print(Fore.CYAN + "\nScanning Virtual Machines...")
    client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
    vms = list(client.virtual_machines.list_all())
    
    if not vms:
        print(Fore.YELLOW + "No virtual machines found.")
        return []
    
    data = []
    alerts = []
    for vm in vms:
        status = "Running"
        rg = vm.id.split("/")[4]
        size = vm.hardware_profile.vm_size if vm.hardware_profile else "N/A"
        location = vm.location
        data.append([vm.name, rg, location, size, status])
        
        if "stopped" in status.lower():
            alerts.append(f"VM '{vm.name}' is stopped - consider deallocating to save costs")
    
    print(Fore.GREEN + f"Found {len(vms)} virtual machine(s):\n")
    print(tabulate(data, headers=["Name", "Resource Group", "Location", "Size", "Status"], tablefmt="rounded_outline"))
    
    if alerts:
        print(Fore.RED + "\nALERTS:")
        for alert in alerts:
            print(Fore.RED + f"  - {alert}")
    
    return vms

def list_all_resources(credential):
    print(Fore.CYAN + "\nScanning all Azure resources...")
    client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
    resources = list(client.resources.list())
    
    type_count = {}
    for r in resources:
        rtype = r.type.split("/")[-1]
        type_count[rtype] = type_count.get(rtype, 0) + 1
    
    data = [[k, v] for k, v in sorted(type_count.items(), key=lambda x: x[1], reverse=True)]
    print(Fore.GREEN + f"Found {len(resources)} total resource(s):\n")
    print(tabulate(data, headers=["Resource Type", "Count"], tablefmt="rounded_outline"))
    return resources

def analyze_with_ai(groups, vms, resources):
    print(Fore.CYAN + "\nRunning AI analysis...")
    
    summary = {
        "resource_groups": len(groups),
        "virtual_machines": len(vms),
        "total_resources": len(resources),
        "resource_types": {}
    }
    
    for r in resources:
        rtype = r.type.split("/")[-1]
        summary["resource_types"][rtype] = summary["resource_types"].get(rtype, 0) + 1
    
    recommendations = []
    
    if summary["virtual_machines"] == 0:
        recommendations.append("No VMs detected - infrastructure is fully containerized (good practice)")
    
    if summary["resource_groups"] > 5:
        recommendations.append("Many resource groups detected - consider consolidating for better governance")
    
    if summary["total_resources"] < 5:
        recommendations.append("Low resource count - subscription may be under-utilized")
    
    dominant_types = sorted(summary["resource_types"].items(), key=lambda x: x[1], reverse=True)[:3]
    if dominant_types:
        top = dominant_types[0][0]
        recommendations.append(f"Most used resource type: {top} - ensure proper tagging and cost allocation")
    
    recommendations.append("Enable Azure Cost Management alerts to monitor spending")
    recommendations.append("Use Terraform to manage all resources as Infrastructure as Code")
    recommendations.append("Enable Azure Monitor and set up alerts for critical resources")
    
    print(Fore.GREEN + "\nAI Recommendations:\n")
    for i, rec in enumerate(recommendations, 1):
        print(Fore.YELLOW + f"  {i}. {rec}")
    
    return summary, recommendations

def generate_report(summary, recommendations):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"reports/azure_report_{timestamp}.json"
    
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "subscription_id": SUBSCRIPTION_ID,
        "summary": summary,
        "recommendations": recommendations,
        "status": "completed"
    }
    
    os.makedirs("reports", exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(Fore.GREEN + f"\nReport saved: {report_path}")
    return report_path

def main():
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    print(Fore.BLUE + Style.BRIGHT + "   AZURE RESOURCE MONITOR - Python Automation with AI")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    print(Fore.WHITE + f"   Subscription: {SUBSCRIPTION_ID}")
    print(Fore.WHITE + f"   Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    
    credential = get_credentials()
    
    groups    = list_resource_groups(credential)
    vms       = list_virtual_machines(credential)
    resources = list_all_resources(credential)
    
    summary, recommendations = analyze_with_ai(groups, vms, resources)
    
    report_path = generate_report(summary, recommendations)
    
    print(Fore.BLUE + Style.BRIGHT + "\n" + "=" * 60)
    print(Fore.GREEN + Style.BRIGHT + "   MONITORING COMPLETE")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    print(Fore.WHITE + f"   Resource Groups : {summary['resource_groups']}")
    print(Fore.WHITE + f"   Virtual Machines : {summary['virtual_machines']}")
    print(Fore.WHITE + f"   Total Resources  : {summary['total_resources']}")
    print(Fore.WHITE + f"   Report           : {report_path}")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)

if __name__ == "__main__":
    main()
