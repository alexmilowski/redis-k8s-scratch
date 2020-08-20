#!/bin/bash

JQ='.[] | select(.name=="'
JQ+="${SOURCE_DB}"
JQ+='") | ("redis://admin:" +  .authentication_admin_pass + "@"+.endpoints[0].dns_name+":"+(.endpoints[0].port|tostring))'
URL=`curl -sf -k -u "$CLUSTER_USER:$CLUSTER_PASSWORD" "https://${CLUSTER_HOST}:${CLUSTER_PORT}/v1/bdbs?fields=uid,name,endpoints,authentication_admin_pass" | jq "$JQ" | sed 's/"//g'`
echo "URL: ${URL}"
cat << EOF > /tmp/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ${SOURCE_DB}-url
stringData:
  url: ${URL}
EOF
cat /tmp/secret.yaml
kubectl -n ${MY_NAMESPACE} apply -f /tmp/secret.yaml
