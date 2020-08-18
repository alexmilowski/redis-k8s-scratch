#!/usr/bin/env bash

BUILDDIR=build
TARGET_NAME=packaged
mkdir -p $BUILDDIR/${TARGET_NAME}
mkdir -p bin
pip3 install . --target ${BUILDDIR}/${TARGET_NAME} --upgrade

cd ${BUILDDIR}

for command in "" ".rec" ".redb"; do
   MODULE="k8sredis${command}"
   PLUGIN_NAME=`echo $command | sed s/\\\\./-/g`
   PLUGIN="kubectl-redis${PLUGIN_NAME}"
   echo "${MODULE} -> bin/${PLUGIN}"
   cat << EOF > ${TARGET_NAME}/__main__.py
import runpy
runpy.run_module('${MODULE}',alter_sys=True)
EOF
   mv ${TARGET_NAME} ${PLUGIN}
   python -m zipapp -p "/usr/bin/env python3" ${PLUGIN}
   cp ${PLUGIN}.pyz ../bin/${PLUGIN}
   mv ${PLUGIN} ${TARGET_NAME}
done
