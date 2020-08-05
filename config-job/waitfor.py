from kubernetes import client, config
import argparse
import pprint
from jsonpath_ng import jsonpath, parse as parse_jsonpath
import sys
from time import sleep

if __name__ == '__main__':

   argparser = argparse.ArgumentParser(description='k8s-waitfor')
   argparser.add_argument('--use-config',help='Use the .kubeconfig file.',action='store_true',default=False)
   argparser.add_argument('--wait',help='Wait for success',action='store_true',default=False)
   argparser.add_argument('--limit',help='The limit of interations of waiting',type=int,default=5)
   argparser.add_argument('--period',help='The period of time to wait (seconds)',type=int,default=12)
   argparser.add_argument('--verbose',help='Verbose output',action='store_true',default=False)
   argparser.add_argument('--group',help='The API group',default='app.redislabs.com')
   argparser.add_argument('--version',help='The API version',default='v1')
   argparser.add_argument('--namespace',help='The namespace',default='default')
   argparser.add_argument('--value',help='A value to compare')
   argparser.add_argument('--value-type',help='A value type',default='string',choices=['integer','float','string'])
   argparser.add_argument('--compare',help='A comparison operator',default='eq',choices=['eq','neq','gt','gte','lt','lte'])
   argparser.add_argument('--cluster',help='Check a cluster scoped object',action='store_true',default=False)
   argparser.add_argument('plural',help='The object kind')
   argparser.add_argument('name',help='The object name')
   argparser.add_argument('expr',help='The jsonpath expression')

   args = argparser.parse_args()

   expr = parse_jsonpath(args.expr)

   if args.use_config:
      config.load_kube_config()
   else:
      config.load_incluster_config()

   api = client.CustomObjectsApi()

   pp = pprint.PrettyPrinter(indent=2)


   if not args.wait:
      args.limit = 1

   iteration = 0
   count = 0

   while count==0 and iteration < args.limit:

      if args.cluster:
         # /apis/{group}/{version}/{plural}/{name}
         # group = apiextensions.k8s.io
         # version = v1
         # plural = customresourcedefinitions
         # name = redisenterpriseclusters.app.redislabs.com
         obj = api.get_cluster_custom_object(args.group,args.version,args.plural,args.name)
      else:
         #  /apis/{group}/{version}/namespaces/{namespace}/{plural}/{name}
         # e.g.
         # group = app.redislabs.com
         # version = v1
         # namespace = default
         # plural = redisenterpriseclusters
         # name = test
         obj = api.get_namespaced_custom_object(args.group,args.version,args.namespace,args.plural,args.name)

      if args.value is not None:
         if args.value_type=='integer':
            args.value = int(args.value)
         if args.value_type=='float':
            args.value = float(args.value)
      for match in expr.find(obj):
         if args.verbose:
            pp.pprint(match.value)
         if args.value is not None:
            if (args.compare=='eq' and args.value==match.value) or \
               (args.compare=='neq' and args.value!=match.value) or \
               (args.compare=='gt' and match.value>args.value) or \
               (args.compare=='gte' and match.value>=args.value) or \
               (args.compare=='lt' and match.value<args.value) or \
               (args.compare=='lte' and match.value<=args.value):
               count += 1
         else:
            count += 1
      if args.wait and count==0:
         if args.verbose:
            print('Waiting: {}'.format(iteration))
         sleep(args.period)

      iteration += 1

   sys.exit(0 if count>0 else 1)
