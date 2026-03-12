#!/usr/bin/env python3
"""
Azure Resource Monitor - Python Automation with Claude AI Analysis
Monitors Azure resources, detects anomalies and generates AI-powered reports
"""

import os
import json
import datetime
import anthropic
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from tabulate import tabulate
from colorama import init, Fore, Style

init(autoreset=True)
load_dotenv()

SUBSCRIPTION_ID  = os.getenv("AZURE_SUBSCRIPTION_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def get_credentials():
    print(Fore.CYAN + "Connecting to Azure...")
    return AzureCliCredential()

def list_resource_groups(credential):
    print(Fore.CYAN + "\nScanning Resource Groups...")
    client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
    groups = list(client.resource_groups.list())
    data = [[g.name, g.location, g.properties.provisioning_state] for g in groups]
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
    for vm in vms:
        rg   = vm.id.split("/")[4]
        size = vm.hardware_profile.vm_size if vm.hardware_profile else "N/A"
        data.append([vm.name, rg, vm.location, size, "Running"])
    print(Fore.GREEN + f"Found {len(vms)} virtual machine(s):\n")
    print(tabulate(data, headers=["Name", "Resource Group", "Location", "Size", "Status"], tablefmt="rounded_outline"))
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
    if data:
        print(tabulate(data, headers=["Resource Type", "Count"], tablefmt="rounded_outline"))
    return resources

def analyze_with_claude(groups, vms, resources):
    print(Fore.CYAN + "\nRunning Claude AI analysis...")

    summary = {
        "resource_groups": len(groups),
        "resource_groups_details": [{"name": g.name, "location": g.location, "status": g.properties.provisioning_state} for g in groups],
        "virtual_machines": len(vms),
        "virtual_machines_details": [{"name": v.name, "size": v.hardware_profile.vm_size if v.hardware_profile else "N/A", "location": v.location} for v in vms],
        "total_resources": len(resources),
        "resource_types": {}
    }
    for r in resources:
        rtype = r.type.split("/")[-1]
        summary["resource_types"][rtype] = summary["resource_types"].get(rtype, 0) + 1

    prompt = f"""You are an Azure cloud infrastructure expert and DevOps engineer.

Analyze the following Azure subscription data and provide:
1. A brief assessment of the infrastructure state (2-3 sentences)
2. Top 5 specific actionable recommendations for cost optimization, security and best practices
3. A risk level: LOW, MEDIUM or HIGH with justification

Azure Infrastructure Data:
{json.dumps(summary, indent=2)}

Respond in French. Be specific and technical. Format your response as:

ASSESSMENT:
[your assessment]

RECOMMENDATIONS:
1. [recommendation]
2. [recommendation]
3. [recommendation]
4. [recommendation]
5. [recommendation]

RISK LEVEL: [LOW/MEDIUM/HIGH]
JUSTIFICATION: [justification]
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    ai_response = message.content[0].text
    print(Fore.YELLOW + "\n" + "=" * 60)
    print(Fore.YELLOW + "   CLAUDE AI ANALYSIS")
    print(Fore.YELLOW + "=" * 60)
    print(Fore.WHITE + ai_response)
    print(Fore.YELLOW + "=" * 60)

    return summary, ai_response

def generate_report(summary, ai_response):
    timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"reports/azure_report_{timestamp}.json"
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "subscription_id": SUBSCRIPTION_ID,
        "summary": summary,
        "ai_analysis": ai_response,
        "status": "completed"
    }
    os.makedirs("reports", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(Fore.GREEN + f"\nReport saved: {report_path}")
    return report_path

def main():
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    print(Fore.BLUE + Style.BRIGHT + "   AZURE RESOURCE MONITOR - Powered by Claude AI")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    print(Fore.WHITE + f"   Subscription : {SUBSCRIPTION_ID}")
    print(Fore.WHITE + f"   Time         : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)

    credential = get_credentials()
    groups     = list_resource_groups(credential)
    vms        = list_virtual_machines(credential)
    resources  = list_all_resources(credential)

    summary, ai_response = analyze_with_claude(groups, vms, resources)
    report_path = generate_report(summary, ai_response)

    print(Fore.BLUE + Style.BRIGHT + "\n" + "=" * 60)
    print(Fore.GREEN + Style.BRIGHT + "   MONITORING COMPLETE")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)
    print(Fore.WHITE + f"   Resource Groups  : {summary['resource_groups']}")
    print(Fore.WHITE + f"   Virtual Machines : {summary['virtual_machines']}")
    print(Fore.WHITE + f"   Total Resources  : {summary['total_resources']}")
    print(Fore.WHITE + f"   Report           : {report_path}")
    print(Fore.BLUE + Style.BRIGHT + "=" * 60)

if __name__ == "__main__":
    main()
