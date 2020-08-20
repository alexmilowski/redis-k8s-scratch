import os

from kubernetes import client, config
import yaml

apis = {
   'rec' : {
      'group' : 'app.redislabs.com',
      'version' : 'v1',
      'kind' : 'RedisEnterpriseCluster',
      'plural' : 'redisenterpriseclusters'
   },
   'redb' : {
      'group' : 'app.redislabs.com',
      'version' : 'v1alpha1',
      'kind' : 'RedisEnterpriseDatabase',
      'plural' : 'redisenterprisedatabases'
   }
}

def get_api(name):
   return apis.get(name).copy()

def _current_namespace_from_kubeconfig():
   location = os.path.expanduser(os.environ.get('KUBECONFIG', '~/.kube/config'))
   with open(location,'r') as config_data:
      kconfig = yaml.load(config_data,Loader=yaml.Loader)
      current_context = kconfig.get('current-context')
      if current_context is not None:
         for context in kconfig.get('contexts',[]):
            if current_context==context.get('name'):
               cluster = context.get('context',{})
               return cluster.get('namespace')
   return None

NAMESPACE_LOCATION='/var/run/secrets/kubernetes.io/serviceaccount/namespace'

def bootstrap(use_config=False,namespace=None):
   if use_config or os.getenv('KUBERNETES_SERVICE_HOST') is None:
      config.load_kube_config()
      return namespace if namespace is not None else _current_namespace_from_kubeconfig()
   else:
      config.load_incluster_config()

      if os.path.isfile(NAMESPACE_LOCATION):
         with open(NAMESPACE_LOCATION,'r') as data:
            ns = data.read().strip()
            return ns
      else:
         return None

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
