FROM python:3.13
WORKDIR /home/app_user
COPY src/requirements.txt ./
COPY src/onboard.py ./
RUN update-ca-certificates && \
curl -kLO  https://github.com/vmware-tanzu/tanzu-cli/releases/download/v1.5.1/tanzu-cli-linux-amd64.tar.gz && \
tar -xf tanzu-cli-linux-amd64.tar.gz && \
mv v1.5.1/tanzu-cli-linux_amd64 /usr/local/bin/tanzu && \
tanzu ceip-participation set false && \
tanzu config eula accept && \
tanzu init && \
tanzu plugin install --group vmware-tanzu/platform-engineer && \
tanzu plugin install --group vmware-tmc/default && \
tanzu plugin install --group vmware-tanzucli/essentials:v1.0.0
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT ["python","onboard.py"]