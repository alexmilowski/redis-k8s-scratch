FROM debian:stable-slim

RUN apt-get update; apt-get install -y curl jq apt-transport-https gnupg2
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6A030B21BA07F4FB
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update
RUN apt-get install -y kubectl
