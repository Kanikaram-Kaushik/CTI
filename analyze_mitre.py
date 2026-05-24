#!/usr/bin/env python3
"""
Analyze MITRE ATT&CK Enterprise JSON file and extract key information
"""
import json
from collections import defaultdict

# Load the JSON file
with open('data/enterprise-attack.json', 'r') as f:
    data = json.load(f)

# Initialize collections
techniques = {}  # {id: {name, x_mitre_id}}
tactic_objects = {}
groups = {}
malware = {}
tools = {}
tactics_list = set()

# Process all objects
for obj in data['objects']:
    obj_type = obj.get('type')
    obj_id = obj.get('id')
    
    # Attack patterns (techniques)
    if obj_type == 'attack-pattern':
        x_mitre_id = obj.get('x_mitre_id')
        name = obj.get('name')
        kill_chain_phases = obj.get('kill_chain_phases', [])
        
        if x_mitre_id:  # Only include if it has the MITRE ID
            techniques[x_mitre_id] = {
                'name': name,
                'id': obj_id,
                'tactics': [phase.get('phase_name') for phase in kill_chain_phases]
            }
            # Collect tactics
            for phase in kill_chain_phases:
                tactics_list.add(phase.get('phase_name'))
    
    # Intrusion sets (threat groups)
    elif obj_type == 'intrusion-set':
        name = obj.get('name')
        aliases = obj.get('aliases', [])
        groups[obj_id] = {
            'name': name,
            'aliases': aliases
        }
    
    # Malware
    elif obj_type == 'malware':
        name = obj.get('name')
        aliases = obj.get('aliases', [])
        malware[obj_id] = {
            'name': name,
            'aliases': aliases,
            'labels': obj.get('labels', [])
        }
    
    # Tools
    elif obj_type == 'tool':
        name = obj.get('name')
        aliases = obj.get('aliases', [])
        tools[obj_id] = {
            'name': name,
            'aliases': aliases,
            'labels': obj.get('labels', [])
        }

# Sort techniques by ID
sorted_techniques = sorted(techniques.items(), key=lambda x: (
    int(x[0].split('.')[0][1:]) if '.' in x[0] else int(x[0][1:]),
    int(x[0].split('.')[1]) if '.' in x[0] else 0
))

print("=" * 80)
print("MITRE ATT&CK ENTERPRISE KNOWLEDGE BASE ANALYSIS")
print("=" * 80)
print()

# Summary Statistics
print("SUMMARY STATISTICS")
print("-" * 80)
print(f"Total Techniques: {len(techniques)}")
print(f"Total Threat Groups: {len(groups)}")
print(f"Total Malware: {len(malware)}")
print(f"Total Tools: {len(tools)}")
print(f"Total Tactics: {len(tactics_list)}")
print()

# Tactics
print("TACTICS/KILL CHAIN PHASES")
print("-" * 80)
for tactic in sorted(tactics_list):
    count = sum(1 for t in techniques.values() if tactic in t['tactics'])
    print(f"  {tactic:.<40} {count} techniques")
print()

# Sample Techniques
print("ATTACK TECHNIQUES (Sample - First 30)")
print("-" * 80)
for i, (tech_id, tech_data) in enumerate(sorted_techniques[:30]):
    tactics_str = ", ".join(tech_data['tactics']) if tech_data['tactics'] else "N/A"
    print(f"  {tech_id:.<15} {tech_data['name'][:50]:.<50} [{tactics_str}]")
print(f"  ... and {len(techniques) - 30} more techniques")
print()

# Threat Groups
print("THREAT GROUPS / INTRUSION SETS (First 30)")
print("-" * 80)
for i, (group_id, group_data) in enumerate(sorted(groups.items(), key=lambda x: x[1]['name'])[:30]):
    aliases_str = ", ".join(group_data['aliases'][:2]) if group_data['aliases'] else "No aliases"
    print(f"  {group_data['name'][:40]:.<40} ({aliases_str})")
print(f"  ... and {len(groups) - 30} more groups")
print()

# Malware
print("MALWARE (First 30)")
print("-" * 80)
for i, (mal_id, mal_data) in enumerate(sorted(malware.items(), key=lambda x: x[1]['name'])[:30]):
    aliases_str = ", ".join(mal_data['aliases'][:1]) if mal_data['aliases'] else "No aliases"
    print(f"  {mal_data['name'][:40]:.<40} ({aliases_str})")
print(f"  ... and {len(malware) - 30} more malware")
print()

# Tools
print("TOOLS (First 30)")
print("-" * 80)
for i, (tool_id, tool_data) in enumerate(sorted(tools.items(), key=lambda x: x[1]['name'])[:30]):
    aliases_str = ", ".join(tool_data['aliases'][:1]) if tool_data['aliases'] else "No aliases"
    print(f"  {tool_data['name'][:40]:.<40} ({aliases_str})")
print(f"  ... and {len(tools) - 30} more tools")
print()

# Full listings (exported to separate sections)
print("=" * 80)
print("COMPLETE TECHNIQUE LISTING")
print("=" * 80)
print()

for tech_id, tech_data in sorted_techniques:
    tactics_str = ", ".join(tech_data['tactics']) if tech_data['tactics'] else "N/A"
    print(f"{tech_id:.<20} {tech_data['name']:<50} [{tactics_str}]")

print()
print("=" * 80)
print("COMPLETE THREAT GROUPS LISTING")
print("=" * 80)
print()

for group_id, group_data in sorted(groups.items(), key=lambda x: x[1]['name']):
    aliases_str = ", ".join(group_data['aliases']) if group_data['aliases'] else ""
    if aliases_str:
        print(f"{group_data['name']:<50} (aka: {aliases_str})")
    else:
        print(f"{group_data['name']:<50}")

print()
print("=" * 80)
print("COMPLETE MALWARE LISTING")
print("=" * 80)
print()

for mal_id, mal_data in sorted(malware.items(), key=lambda x: x[1]['name']):
    aliases_str = ", ".join(mal_data['aliases']) if mal_data['aliases'] else ""
    if aliases_str:
        print(f"{mal_data['name']:<50} (aka: {aliases_str})")
    else:
        print(f"{mal_data['name']:<50}")

print()
print("=" * 80)
print("COMPLETE TOOLS LISTING")
print("=" * 80)
print()

for tool_id, tool_data in sorted(tools.items(), key=lambda x: x[1]['name']):
    aliases_str = ", ".join(tool_data['aliases']) if tool_data['aliases'] else ""
    if aliases_str:
        print(f"{tool_data['name']:<50} (aka: {aliases_str})")
    else:
        print(f"{tool_data['name']:<50}")

print()
print("=" * 80)
print("KNOWLEDGE BASE OVERVIEW: Questions This System Can Answer")
print("=" * 80)
print("""
ABOUT ATTACK TECHNIQUES:
  ✓ What are all MITRE ATT&CK techniques?
  ✓ What tactics does a specific technique belong to?
  ✓ What are all techniques in a specific tactic?
  ✓ What is the description/detail of a specific technique?

ABOUT THREAT ACTORS:
  ✓ What are known APT groups / intrusion sets?
  ✓ What are aliases for threat groups?
  ✓ What techniques does a specific threat group use?
  ✓ What malware and tools does a group use?
  ✓ How active is a particular threat actor?

ABOUT MALWARE:
  ✓ What malware families are in the database?
  ✓ What aliases does a malware have?
  ✓ What are the capabilities of specific malware?
  ✓ What threat groups use a specific malware?

ABOUT TOOLS:
  ✓ What tools/utilities are used in attacks?
  ✓ What tool alternatives exist?
  ✓ What threat groups use specific tools?

CROSS-REFERENCE QUERIES:
  ✓ Given a tactic, what are the techniques and related tools/malware?
  ✓ Given a threat group, what is their full attack chain?
  ✓ What patterns connect specific malware to threat groups to techniques?
  ✓ What is the most commonly used technique across all groups?
  ✓ What techniques are used by multiple threat actors?

CONTEXTUAL ANALYSIS:
  ✓ Threat intelligence for incident response
  ✓ Red team planning and simulation
  ✓ Defense prioritization based on threat prevalence
  ✓ Trend analysis on which tactics/techniques are most active
""")
