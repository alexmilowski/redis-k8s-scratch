import sys
import argparse
import json
import yaml

from kubernetes import client
from kubernetes.client.rest import ApiException
from k8sredis.common import bootstrap, get_api

parmaeter_defaults = {
   'redb' : { 'memory' : '100MB', 'redisEnterpriseCluster.name' : 'rec'},
   'rec' : { 'nodes' : 1 }
}

parameter_aliases = {
   'redb' : {
      'cluster' : 'redisEnterpriseCluster.name'
   },
   'rec' : {
      'cpu' : 'redisEnterpriseNodeResources.requests.cpu',
      'memory' : 'redisEnterpriseNodeResources.requests.memory'
   }
}

def parse_parameters(specs, defaults, aliases):
   parameters = defaults.copy()
   for spec in specs if specs is not None else []:
      parts = spec.split('=')
      if len(parts)!=2:
         continue
      pname = parts[0].strip()
      pname = aliases.get(pname,pname)
      value = parts[1].strip()
      try:
         value = int(value)
      except ValueError:
         pass
      parameters[pname] = value
   return parameters


def redis_command_create(*command_args):
   argparser = argparse.ArgumentParser(description='k8s-waitfor')
   argparser.add_argument('--use-config',help='Use the .kubeconfig file.',action='store_true',default=False)
   argparser.add_argument('--verbose',help='Verbose output',action='store_true',default=False)
   argparser.add_argument('--namespace',help='The namespace; defaults to the context.')
   argparser.add_argument('--dry-run',help='Validate the request but do not create.',action='store_true',default=False)
   argparser.add_argument('kind',choices=['redb','rec'],help='The kind of object to create.')
   argparser.add_argument('name',help='The object name')
   argparser.add_argument('parameters',help='a list of name/value pairs',nargs='*')

   args = argparser.parse_args(command_args)

   namespace = bootstrap(use_config=args.use_config,namespace=args.namespace)

   if namespace is None:
      print('Cannot determine current namespace.',file=sys.stderr)

   parameters = parse_parameters(args.parameters,parmaeter_defaults[args.kind],parameter_aliases[args.kind])

   # TODO: generalize
   for target in ['cpu','memory']:
      from_name = 'redisEnterpriseNodeResources.requests.'+target
      to_name = 'redisEnterpriseNodeResources.limits.'+target
      if from_name in parameters and to_name not in parameters:
         parameters[to_name] = parameters[from_name]

   custom_objects = client.CustomObjectsApi()

   api_spec = get_api(args.kind)

   body = {
      'apiVersion' : api_spec['group'] + '/' + api_spec['version'],
      'kind' : api_spec['kind'],
      'metadata' : { 'name' : args.name },
      'spec' : {
      }
   }
   spec = body['spec']
   for pname in parameters.keys():
      pvalue = parameters[pname]
      if type(pvalue)==str and pvalue[0]=='{':
         pvalue = json.loads(pvalue)
      context = spec
      path = pname.split('.')
      for pname in path[0:-1]:
         next = context.get(pname)
         if next is None:
            next = {}
            context[pname ] = next
         context = next
      context[path[-1]] = pvalue
   if args.verbose:
      print(yaml.dump(body,indent=2))

   if args.dry_run:
      print(yaml.dump(body,indent=2))
      return

   try:
      resp = custom_objects.create_namespaced_custom_object(api_spec['group'],api_spec['version'],namespace,api_spec['plural'],body)
      if args.verbose:
         print('---')
         print(yaml.dump(resp,indent=2))
   except ApiException as e:
      if e.status==409:
         print('409: Database with name {} already exists.'.format(args.name),file=sys.stderr)
      else:
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
      exit(e.status)

def redis_command_delete(*command_args):
   argparser = argparse.ArgumentParser(description='k8s-waitfor')
   argparser.add_argument('--use-config',help='Use the .kubeconfig file.',action='store_true',default=False)
   argparser.add_argument('--verbose',help='Verbose output',action='store_true',default=False)
   argparser.add_argument('--namespace',help='The namespace; defaults to the context.')
   argparser.add_argument('--dry-run',help='Validate the request but do not create.',action='store_true',default=False)
   argparser.add_argument('kind',choices=['redb','rec'],help='The kind of object to create.')
   argparser.add_argument('name',help='The object name')

   args = argparser.parse_args(command_args)

   namespace = bootstrap(use_config=args.use_config,namespace=args.namespace)

   if namespace is None:
      print('Cannot determine current namespace.',file=sys.stderr)

   custom_objects = client.CustomObjectsApi()

   # Must delete databases first
   if args.kind=='rec':
      db_api = get_api('redb')
      try:

         list_resp = custom_objects.list_namespaced_custom_object(db_api['group'],db_api['version'],namespace,db_api['plural'])
         for item in list_resp['items']:
            dbname = item['metadata']['name']
            cluster = item['spec']['redisEnterpriseCluster']['name']
            if cluster==args.name:
               if args.verbose:
                  print("Deleting redb/{name}".format(name=dbname))
               response = custom_objects.delete_namespaced_custom_object(db_api['group'],db_api['version'],namespace,db_api['plural'],dbname)

      except ApiException as e:
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
         exit(e.status)

   if args.verbose:
      print("Deleting {kind}/{name}".format(kind=args.kind,name=args.name))

   api_spec = get_api(args.kind)
   response = custom_objects.delete_namespaced_custom_object(api_spec['group'],api_spec['version'],namespace,api_spec['plural'],args.name)


def redis_command_proxy(*command_args):
   pass

commands = {
   'create' : (redis_command_create,'Creates a database or cluster'),
   'delete' : (redis_command_delete,'Delets a database or cluster'),
   'proxy' : (redis_command_proxy,'Establishes a proxy a redis node')
}

def usage():
   print('kubectl redis redb <command> ...',file=sys.stderr)
   print('where <command> is one of: ',file=sys.stderr)
   print()
   for name in sorted(commands.keys()):
      print('\t{}\t{}'.format(name,commands[name][1]),file=sys.stderr)
   print()

if __name__.rpartition('.')[-1] == "__main__":
   if len(sys.argv) < 2:
      usage()
      exit(1)

   command_name = sys.argv[1]
   args = sys.argv[2:]

   command = commands.get(command_name)
   if command is None:
      print('Unknown command: '+command_name,file=sys.stderr)
      sys.exit(1)

   command[0](*args)
