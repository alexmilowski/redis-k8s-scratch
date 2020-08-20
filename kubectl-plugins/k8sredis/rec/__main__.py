import sys
import argparse
import yaml
import base64
import time

from uuid import uuid4

from kubernetes import client
from kubernetes.client.rest import ApiException

from k8sredis.common import bootstrap, get_api, parse_parameters

def rec_command_status(*command_args):

   argparser = argparse.ArgumentParser(description='kubectl-redis-rec')
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
      api_spec = get_api('rec')
      obj = custom_objects.get_namespaced_custom_object(api_spec['group'],api_spec['version'],namespace,api_spec['plural'],args.name)
      status = obj.get('status',{'state':'Unknown'})
      for key in sorted(status.keys()):
         print('{}: {}'.format(key,status.get(key)))
      if args.show_spec:
         spec = obj.get('spec')
         print(yaml.dump({'spec':spec},indent=2))


   except ApiException as e:
      if e.status==404:
         print('Cannot find rec/{} in namespace {}'.format(args.name,namespace),file=sys.stderr)
      else:
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
      exit(e.status)

SCRIPT_JOB = '''
apiVersion: batch/v1
kind: Job
metadata:
  name: {job_name}
spec:
  backoffLimit: 4
  template:
    spec:
      serviceAccountName: {service_account}
      restartPolicy: Never
      volumes:
        - name: scripts
          configMap:
            name: {config_map_name}
      containers:
        - name: script
          image: debian:stable-slim
          env:
            - name: MY_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: SCRIPT
              value: {script_name}
            - name: SOURCE_DB
              value: source
            - name: CLUSTER_SERVICE
              value: .svc.cluster.local
            - name: CLUSTER_NAME
              value: test
            - name: CLUSTER_PORT
              value: "9443"
            - name: CLUSTER_USER
              valueFrom:
               secretKeyRef:
                 name: test
                 key: username
            - name: CLUSTER_PASSWORD
              valueFrom:
               secretKeyRef:
                 name: test
                 key: password
            - name: CLUSTER_HOST
              value: $(CLUSTER_NAME).$(MY_NAMESPACE)$(CLUSTER_SERVICE)
          volumeMounts:
            - mountPath: /opt/scripts/
              name: scripts
          command:
            - /bin/bash
            - -c
            - |
              apt-get update; apt-get install -y curl jq apt-transport-https gnupg2
              apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6A030B21BA07F4FB
              curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
              echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
              apt-get update
              apt-get install -y kubectl
              bash /opt/scripts/$SCRIPT
'''

def rec_command_cluster_script(*command_args):
   argparser = argparse.ArgumentParser(description='kubectl-redis-rec')
   argparser.add_argument('--use-config',help='Use the .kubeconfig file.',action='store_true',default=False)
   argparser.add_argument('--show-spec',help='Display the spec details.',action='store_true',default=False)
   argparser.add_argument('--verbose',help='Verbose output',action='store_true',default=False)
   argparser.add_argument('--namespace',help='The namespace; defaults to the context.')
   argparser.add_argument('--service-account',help='The service account',default='redis-enterprise-operator')
   argparser.add_argument('--job-name',help='The job name')
   argparser.add_argument('--config-map',help='The name of the configmap containing the scripts')
   argparser.add_argument('--image',help='The name of the base image to use for the job.')
   argparser.add_argument('--create-config-map',help='Create the config map from the script source.',action='store_true',default=False)
   argparser.add_argument('--wait',help='Wait for the job to complete.',action='store_true',default=False)
   argparser.add_argument('name',help='The cluster name')
   argparser.add_argument('script',help='The script name')
   argparser.add_argument('parameters',help='a list of name/value pairs',nargs='*')

   args = argparser.parse_args(command_args)

   namespace = bootstrap(use_config=args.use_config,namespace=args.namespace)

   if namespace is None:
      print('Cannot determine current namespace.',file=sys.stderr)

   parameters = parse_parameters(args.parameters,{},{})

   job_name = args.job_name

   if job_name is None:
      job_name = 'script-' + str(uuid4())

   create_config_map = args.config_map is None or args.create_config_map
   delete_config_map = args.config_map is None and not args.create_config_map
   config_map_name = args.config_map if args.config_map is not None else job_name

   core_api = client.CoreV1Api()


   if create_config_map:

      if args.verbose:
         print('Creating configmap/{} ...'.format(config_map_name))
      config_map = {
         'apiVersion' : 'v1',
         'kind' : 'ConfigMap',
         'metadata': {
            'name' : config_map_name
         },
         'data' : {}
      }
      with open(args.script,'r') as data:
         config_map['data'][args.script] = data.read()

      try:

         resp = core_api.create_namespaced_config_map(namespace,config_map)

      except ApiException as e:
         if e.status==409:
            print('configmap/{} already exists in in namespace {}'.format(config_map_name,namespace),file=sys.stderr)
         else:
            print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
         exit(e.status)

   job = yaml.load(
      SCRIPT_JOB.format(
         job_name = job_name,
         service_account = args.service_account,
         config_map_name = config_map_name,
         script_name = args.script
      ),
      Loader=yaml.Loader
   )
   env = job['spec']['template']['spec']['containers'][0]['env']
   for pname in parameters.keys():
      env.append({'name': pname, 'value' : parameters[pname]})

   if args.image is not None:
      job['spec']['template']['spec']['containers'][0]['image'] = args.image
      job['spec']['template']['spec']['containers'][0]['command'] = ['/bin/bash','-c','bash /opt/scripts/$SCRIPT']

   if args.verbose:
      print(yaml.dump(job,indent=2))

   batch_api = client.BatchV1Api()

   if args.verbose:
      print('Submitting job {}'.format(job_name))
   try:
      batch_api.create_namespaced_job(namespace,job)
   except ApiException as e:
      print('Cannot submit job {} '.format(job_name),file=sys.stderr)
      print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
      print(e.body,file=sys.stderr)
      exit(e.status)

   if args.wait:
      not_done = True
      succeeded = None
      interval = 1
      while not_done:
         time.sleep(interval)
         try:
            resp = batch_api.read_namespaced_job_status(job_name,namespace)
            not_done = resp.status.active is not None
            succeeded = resp.status.succeeded
         except ApiException as e:
            print('Cannot get status of job {} '.format(job_name),file=sys.stderr)
            print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
            print(e.body,file=sys.stderr)
            exit(e.status)
      if args.verbose and succeeded is not None:
         print("Job completed successfully.")


   if args.wait and delete_config_map:
      if args.verbose:
         print('Deleting configmap/{} ...'.format(config_map_name))
      try:
         resp = core_api.delete_namespaced_config_map(config_map_name,namespace)
      except ApiException as e:
         print('Cannot delete configmap/{}'.format(config_map_name),file=sys.stderr)
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
         exit(e.status)


def rec_command_source_url(*command_args):
   argparser = argparse.ArgumentParser(description='kubectl-redis-rec')
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

      core_api = client.CoreV1Api()
      secret = core_api.read_namespaced_secret(args.name,namespace)

      username = base64.b64decode(secret.data['username']).decode('utf-8','strict')
      password = base64.b64decode(secret.data['password']).decode('utf-8','strict')
      print(username)
      print(password)

      custom_objects = client.CustomObjectsApi()
      api_spec = get_api('rec')
      obj = custom_objects.get_namespaced_custom_object(api_spec['group'],api_spec['version'],namespace,api_spec['plural'],args.name)
      status = obj.get('status',{'state':'Unknown'})
      for key in sorted(status.keys()):
         print('{}: {}'.format(key,status.get(key)))
      if args.show_spec:
         spec = obj.get('spec')
         print(yaml.dump({'spec':spec},indent=2))


   except ApiException as e:
      if e.status==404:
         print('Cannot find rec/{} in namespace {}'.format(args.name,namespace),file=sys.stderr)
      else:
         print('{}: {}'.format(str(e.status),e.reason),file=sys.stderr)
      exit(e.status)



commands = {
   'status' : (rec_command_status,'Displays the status of the cluster.'),
   'source-url' : (rec_command_source_url,'Retrieves the source url for replica-of'),
   'script' : (rec_command_cluster_script,'Submits a cluster script.')
}

def usage():
   print('kubectl redis rec <command> ...',file=sys.stderr)
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
