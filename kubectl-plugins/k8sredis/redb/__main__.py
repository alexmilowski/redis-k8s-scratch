import sys
import argparse
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException

from k8sredis.common import bootstrap, get_api

def redb_command_status(*command_args):

   argparser = argparse.ArgumentParser(description='k8s-waitfor')
   argparser.add_argument('--use-config',help='Use the .kubeconfig file.',action='store_true',default=False)
   argparser.add_argument('--show-spec',help='Display the spec details.',action='store_true',default=False)
   argparser.add_argument('--verbose',help='Verbose output',action='store_true',default=False)
   argparser.add_argument('--namespace',help='The namespace; defaults to the context.')
   argparser.add_argument('name',help='The object name')

   args = argparser.parse_args(command_args)

   namespace = bootstrap(use_config=args.use_config,namespace=args.namespace)

   if namespace is None:
      print('Cannot determine current namespace.',file=sys.stderr)

   try:

      custom_objects = client.CustomObjectsApi()
      api_spec = get_api('redb')
      obj = custom_objects.get_namespaced_custom_object(api_spec['group'],api_spec['version'],namespace,api_spec['plural'],args.name)
      status = obj.get('status',{'state':'Unknown'})
      for key in sorted(status.keys()):
         print('{}: {}'.format(key,status.get(key)))
      if args.show_spec:
         spec = obj.get('spec')
         print(yaml.dump({'spec':spec},indent=2))


   except ApiException as e:
      if e.status==404:
         print('Cannot find redb/{} in namespace {}'.format(args.name,namespace),file=sys.stderr)
      else:
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
      exit(e.status)



commands = {
   'status' : (redb_command_status,'Displays the status of the database.')
}

def usage():
   print('kubectl redis redb <command> ...',file=sys.stderr)
   print('where <command> is one of: ',file=sys.stderr)
   print()
   for name in sorted(commands.keys()):
      print('\t{}\t{}'.format(name,commands[name][1]),file=sys.stderr)
   print()

if __name__.rpartition('.')[-1] == "__main__":
   if len(sys.argv) < 3:
      usage()
      exit(1)

   command_name = sys.argv[2]
   args = sys.argv[3:]

   command = commands.get(command_name)
   if command is None:
      print('Unknown command: '+command_name,file=sys.stderr)
      sys.exit(1)

   command[0](*args)
