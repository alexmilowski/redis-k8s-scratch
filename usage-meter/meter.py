import sys
import argparse
import signal
import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from common import bootstrap, get_api

def get_rec_specs(namespace):

   try:

      custom_objects = client.CustomObjectsApi()
      api_spec = get_api('rec')
      obj_list = custom_objects.get_namespaced_custom_object(api_spec['group'],api_spec['version'],namespace,api_spec['plural'],'')

      return [(obj_list['items'][0]['metadata']['name'],item['spec']) for item in obj_list['items']]

   except ApiException as e:
      if e.status==404:
         return []
      else:
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
         return []

running = True
def sigterm_handler(signal,frame):
   running = False
   sys.print('SIGTERM received - terminating process.')
signal.signal(signal.SIGTERM, sigterm_handler)

def parse_numberunit(value):
   unit_pos = -1
   for index, digit in enumerate(value):
      if not digit.isdigit():
         unit_pos = index
         break
   if unit_pos < 0:
      return float(value), None
   else:
      return float(value[0:unit_pos]),value[unit_pos:]


def parse_cpu(value):
   scalar, unit = parse_numberunit(value)
   if unit == 'm':
      scalar / 1000.0
   return scalar

memory_units = {
   'K' : 10**3,
   'M' : 10**6,
   'G' : 10**9,
   'T' : 10**12,
   'P' : 10**15,
   'Ki' : 2**10,
   'Mi' : 2**20,
   'Gi' : 2**30,
   'Ti' : 2**40,
   'Pi' : 2**50
}

def parse_memory(value):
   scalar, unit = parse_numberunit(value)
   if unit is not None:
      if unit not in memory_units:
         return None
      multiplier = memory_units[unit]
      scalar = scalar * multiplier
   scalar = scalar / memory_units['Gi']
   return scalar

def requested_value(current,resources,category,item,parser):
   if category in resources:
      if item in resources[category]:
         value = parser(resources[category][item])
         if value > current:
            current = value
   return current

def report_usage(namespace,interval=60):
   while running:
      time.sleep(interval)
      for name, rec in get_rec_specs(namespace):
         cpu = 2.0
         memory = 4.0
         if 'redisEnterpriseNodeResources' in rec:
            resources = rec['redisEnterpriseNodeResources']
            cpu = requested_value(cpu,resources,'requests','cpu',parse_cpu)
            cpu = requested_value(cpu,resources,'limits','cpu',parse_cpu)
            memory = requested_value(memory,resources,'requests','memory',parse_memory)
            memory = requested_value(memory,resources,'limits','memory',parse_memory)
         print((name,cpu,memory,interval),flush=True)


if __name__ == "__main__":

   argparser = argparse.ArgumentParser(description='kubectl-redis-rec')
   argparser.add_argument('--verbose',help='Verbose output',action='store_true',default=False)
   argparser.add_argument('--use-config',help='Use the .kubeconfig',action='store_true',default=False)
   argparser.add_argument('--interval',help='Usage interval (in seconds)',type=int,default=60)
   argparser.add_argument('--namespace',help='The namespace; defaults to the context.')

   args = argparser.parse_args()

   namespace = bootstrap(use_config=args.use_config,namespace=args.namespace)

   if namespace is None:
      print('Cannot determine current namespace.',file=sys.stderr)
      sys.exit(1)

   report_usage(namespace,interval=args.interval)
