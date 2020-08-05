#!/bin/sh
CLUSTER_HOST=${CLUSTER_NAME}.${MY_NAMESPACE}.svc.cluster.local
CLUSTER_PORT=9443
if python waitfor.py --namespace $MY_NAMESPACE --group app.redislabs.com redisenterpriseclusters $CLUSTER_NAME "$.status.state"  --value "Running" --wait --period 30 --limit 20
then
   python make_request.py saslauthd_ldap_conf /config/saslauthd_ldap_conf > tmp.json
   curl -f -k -u "$CLUSTER_USER:$CLUSTER_PASSWORD" -X PUT -d @tmp.json -H "Content-Type: application/json" https://${CLUSTER_HOST}:${CLUSTER_PORT}/v1/cluster
else
   echo "Cluster is not ready within required period."
   exit 1
fi
