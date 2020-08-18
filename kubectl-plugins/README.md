# k8sredis

A module containing command line tools for redis and the Redis Enterprise operator

## Install it

### via source

You can use this source directly by:

```
cd kubectl-plugins
export PYTHONPATH=`pwd`
export PATH=`pwd`:$PATH
```

and then you should see the three plugins via:

```
kubectl plugin list
```

### via build

Build the packaging via:

```
cd kubectl-plugins
./build.sh
```

You can copy the three executables (kubectl-redis, kubectl-redis-rec, & kubectl-redis-redb) into your path
or add the `bin` directory to your path via:

```
export PATH=`pwd`/bin:$PATH
```

Note: You don't need to set `PYTHONPATH` because the build process packages all
the dependencies.


You should see the three plugins via:

```
kubectl plugin list
```

## Try it

### Commands

```
kubectl redis create rec name ...
kubectl redis create redb name ...
kubectl redis delete rec name ...
kubectl redis delete redb name ...
kubectl redis rec status name
kubectl redis redb status name
```

Universal options:

 * --use-config - use the kubeconfig file
 * --verbose - verbose output
 * --dry-run - output the actions but commit no changes
 * --namespace - the namespace for the actions
 
