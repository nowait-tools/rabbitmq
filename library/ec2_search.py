#!/usr/bin/python
# This file is part of NoWait

DOCUMENTATION = '''
---
module: ec2_search
short_description: ask EC2 for information about other instances.
description:
    - Only supports search for hostname by tags currently. Looking to add more later.
version_added: "1.9"
options:
  key:
    description:
      - instance tag key in EC2
    required: false
    default: Name
    aliases: []
  value:
    description:
      - instance tag value in EC2 (prefix)
    required: false
    default: null
    aliases: []
  lookup:
    description:
      - What type of lookup to use when searching EC2 instance info.
    required: false
    default: tags
    aliases: []
  region:
    description:
      - EC2 region that it should look for tags in
    required: false
    default: All Regions
    aliases: []
  ignore_state:
    description:
      - instance state that should be ignored such as terminated.
    required: false
    default: terminated
    aliases: []
author:
    - "Michael Schuett (@michaeljs1990)"
extends_documentation_fragment: aws
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.

# Basic provisioning example
- ec2_search:
    key: mykey
    value: myvalue

'''
try:
    import boto
    import boto.ec2
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        # This Class causes a recursive loop and at this time is not worth
        # debugging. If it's useful later I'll look into it.
        if not isinstance(obj, boto.ec2.blockdevicemapping.BlockDeviceType):
            data = dict([(key, todict(value, classkey))
                        for key, value in obj.__dict__.iteritems()
                        if not callable(value) and not key.startswith('_')])
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data
    else:
        return obj


def get_all_ec2_regions(module):
    try:
        regions = boto.ec2.regions()
    except Exception as e:
        module.fail_json('Boto authentication issue: %s' % e)
    return regions


# Connect to ec2 region
def connect_to_region(region, module):
    try:
        conn = boto.ec2.connect_to_region(region)
        if conn is None:
            raise Exception("Unable to get connection from boto")
        return conn
    except Exception as e:
        module.fail_json(msg='error connecting to region %s: %s' % (region, e))


def main():
    module = AnsibleModule(
        argument_spec = dict(
            key = dict(default='Name'),
            value = dict(),
            lookup = dict(default='tags'),
            ignore_state = dict(default='terminated'),
            region = dict(default='all'),
        )
    )

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')

    ec2_key = module.params.get('key')
    ec2_value = module.params.get('value')

    server_info = list()

    all_regions = [r.name for r in get_all_ec2_regions(module)]
    passed_region = module.params.get('region')

    # Check if passed region is correct
    if passed_region != 'all' and passed_region in all_regions:
        regions = [passed_region]
    else:
        regions = all_regions

    for region in regions:
        conn = connect_to_region(region, module)
        try:
            # Run when looking up by tag names, only returning hostname currently
            if module.params.get('lookup') == 'tags':
                for instance in conn.get_only_instances():
                    nameTag = instance.tags.get(ec2_key)
                    if nameTag is not None and nameTag.startswith(ec2_value):
                        if instance.private_ip_address is not None:
                            instance.hostname = 'ip-' + instance.private_ip_address.replace('.', '-')
                        if instance._state.name not in module.params.get('ignore_state'):
                            server_info.append(todict(instance))
        except Exception as e:
            module.fail_json(msg='error getting instances from: %s %s' % (region, e))

    ec2_facts_result = dict(changed=True, info=server_info)

    module.exit_json(**ec2_facts_result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

main()
