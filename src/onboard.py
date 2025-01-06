import argparse
import logging
import sys
import subprocess
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException
import yaml
import base64
import time
import os
import requests
requests.packages.urllib3.disable_warnings() 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def tpk8sAttach(cluster,cg,kubeconfig):
    attachyml = {'fullName': {'managementClusterName': 'attached',
              'name': f'{cluster}',
              'provisionerName': 'attached'},
 'meta': {'description': 'Attaching cluster using tanzu cli'},
 'spec': {'clusterGroupName': f'{cg}'}}
    with open('/tmp/attach.yml', 'w') as yaml_file:
        yaml.dump(attachyml, yaml_file, default_flow_style=False)
    try:
        logging.info(f"attaching cluster to tpk8s {cluster}")
        attach = subprocess.check_output(["tanzu", "ops","cluster","attach","-n", cluster,"-f","/tmp/attach.yml","-k",kubeconfig], text=True)
        logging.info(attach)
    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)

def tzStdKeep(kubeconfig,cluster_type):
    config.load_kube_config(config_file=kubeconfig)
    logging.info("removing tmc annotations from pkgr")
    namespace = "tanzu-package-repo-global"
    if cluster_type == "tkgm":
        namespace = "tkg-system"
    api = client.CustomObjectsApi()
    try:
        pkgr = api.get_namespaced_custom_object(namespace=namespace,group="packaging.carvel.dev",version="v1alpha1",plural="packagerepositories",name="tanzu-standard")
    except ApiException as e:
        logging.error(f"failed to get pkgr {e}")
        sys.exit(1)

    annot = ["tanzu.vmware.com/owner","tmc.cloud.vmware.com/managed-tanzu-package-repository"]
    for x in annot:
        if x in pkgr["metadata"]["annotations"]:
            del pkgr["metadata"]["annotations"][x]
    try:
        logging.info("removing annotations for tmc form the pkgr")
        api.patch_namespaced_custom_object(namespace=namespace,group="packaging.carvel.dev",version="v1alpha1",plural="packagerepositories",name="tanzu-standard",body=pkgr)
    except:
        logging.error(f"failed to get pkgr {e}")
        sys.exit(1)

def tzStdremove(kubeconfig,cluster_type):
    logging.info("removing pkgr")
    config.load_kube_config(config_file=kubeconfig)
    namespace = "tanzu-package-repo-global"
    if cluster_type == "tkgm":
        namespace = "tkg-system"
    api = client.CustomObjectsApi()
    try:
        api.delete_namespaced_custom_object(namespace=namespace,group="packaging.carvel.dev",version="v1alpha1",plural="packagerepositories",name="tanzu-standard")
    except ApiException as e:
        logging.error(f"failed to delete pkgr {e}")
        sys.exit(1)
def detachWait(kubeconfig):
    timeout=300
    config.load_kube_config(config_file=kubeconfig)
    v1 = client.CoreV1Api()
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            logging.info("checking if ns still exists")
            v1.read_namespace("vmware-system-tmc")
        except ApiException as e:
            if e.status == 404:
                print(f"TMC namespace deleted successfully.")
                return
            else:
                logging.error(f"failed get namespace {e}")
                sys.exit(1)
        time.sleep(1)  

    raise TimeoutError(f"Timeout waiting for tmc namespace to be deleted.")

def tmcDetach(agentName,cluster_type,mgmt_cluster,provisioner):
    try:
        logging.info(f"getting cluster details for {agentName}")
        cluster_details_str = subprocess.check_output(["tanzu", "tmc","cluster","get", agentName,"-p",provisioner,"-m",mgmt_cluster], text=True)
        cluster_details = yaml.safe_load(cluster_details_str)
        if cluster_type not in ["tkgm","tkgs"]:
            infra_id = cluster_details['meta']['annotations']['infrastructureRID']
        cg = cluster_details['spec']['clusterGroupName']
    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)
    try:
        match cluster_type:
            case "eks":
                logging.info(f"detaching eks cluster {agentName}")
                infra_pieces = infra_id.split(":")
                cred = infra_pieces[3]
                region = infra_pieces[4]
                name = infra_pieces[5]
                result = subprocess.check_output(["tanzu", "tmc","provider-eks-cluster","unmanage", name,"-c",cred,"-r",region,"-g",cg], text=True)
                logging.info(result)
            case "aks":
                logging.info(f"detaching aks cluster {agentName}")
                infra_pieces = infra_id.split(":")
                cred = infra_pieces[3]
                sub = infra_pieces[4]
                rg = infra_pieces[5]
                name = infra_pieces[6]
                result = subprocess.check_output(["tanzu", "tmc","provider-aks-cluster","unmanage", name,"-c",cred,"-s",sub,"-r",rg,"-g",cg], text=True)
                logging.info(result)
            case "tkgs" | "tkgm":
                name = agentName
                logging.info(f"detaching tkg cluster {agentName}")
                result = subprocess.check_output(["tanzu", "tmc","management-cluster","workload-cluster","unmanage", agentName,"-m",mgmt_cluster,"-p",provisioner], text=True)
                logging.info(result)
    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)
    return name
def saClient(token,old_kube,url):
    with open(old_kube) as f:
        kubeconfig = yaml.safe_load(f)
    logging.info("generating a kubeconfig ")
    del kubeconfig['users'][0]['user']['exec']
    kubeconfig['users'][0]['user']['token'] = token
    kubeconfig['clusters'][0]['cluster']['server'] = url
    del kubeconfig['clusters'][0]['cluster']['certificate-authority-data']
    kubeconfig['clusters'][0]['cluster']['insecure-skip-tls-verify'] = True
    filename = "/tmp/sakube.yml"
    with open(filename, 'w') as yaml_file:
        yaml.dump(kubeconfig, yaml_file, default_flow_style=False)
    return filename

def setContext(contextName):
    try:
        result = subprocess.check_output(["tanzu", "context","use",contextName], text=True)
        logging.info(result)
    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)

def setProject(project):
    try:
        result = subprocess.check_output(["tanzu", "project","use",project], text=True)
        logging.info(result)
    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)


def getKubeconfig(cluster,management,provisioner):
    try:
        result = subprocess.check_output(["tanzu", "tmc","cluster","kubeconfig","get",cluster,"-m",management,"-p",provisioner], text=True)
        logging.info("writing kubeconfig to /tmp/tmckube.yml")
        file='/tmp/tmckube.yml' 
        with open(file, 'w') as filetowrite:
            filetowrite.write(result)

    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)

def getApiUrl(kubeconfig):
    with open(kubeconfig) as f:
        kubeconfig = yaml.safe_load(f)
    return kubeconfig['clusters'][0]['cluster']['server']

def createNewUser(kubeconfig):
    config.load_kube_config(config_file=kubeconfig)
    v1 = client.CoreV1Api()
    sa_name = "tp-onboarding"
    service_account = client.V1ServiceAccount(
        metadata=client.V1ObjectMeta(name=sa_name, namespace="default")
    )
    logging.info("creating temporary serrvice account for k8s access")
    try:
        v1.create_namespaced_service_account("default", service_account)
    except ApiException as e:
        logging.error(f"failed to create service account")
        sys.exit(1)
   
    sec  = client.V1Secret( 
        metadata=client.V1ObjectMeta(name=sa_name, namespace="default",annotations={"kubernetes.io/service-account.name": sa_name}),
        type="kubernetes.io/service-account-token"
    )

    logging.info("creating secret for serrvice account for k8s access")
    try:
        v1.create_namespaced_secret(namespace="default", body=sec)
    except ApiException as e:
        logging.error(f"failed to create service account token secret")
        sys.exit(1)
    
    try:
        secret = v1.read_namespaced_secret(
            name=sa_name,
            namespace="default"
        )
    except ApiException as e:
        logging.error(f"failed to get service account secret")
        sys.exit(1)


    role_binding = client.V1ClusterRoleBinding(
        metadata=client.V1ObjectMeta(name="tp-onboarding-rb"),
        subjects=[client.RbacV1Subject(name=sa_name, kind="ServiceAccount", namespace="default")],
        role_ref=client.V1RoleRef(kind="ClusterRole", api_group="rbac.authorization.k8s.io",name="cluster-admin")
    )

    rbac = client.RbacAuthorizationV1Api()
    try:
        rbac.create_cluster_role_binding(body=role_binding)
    except ApiException as e:
        logging.error(e)
        logging.error(f"failed to create clusrterrolebindng for service account")
        sys.exit(1)

    decoded_bytes = base64.b64decode(secret.data["token"])
    token = decoded_bytes.decode('utf-8')
    return token

def createContext(token,org,endpoint,contextName,type):
    try:
        logging.info(f"creating {type} context {contextName} ")
        my_env = os.environ.copy()
        my_env["TANZU_API_TOKEN"] = token
        my_env["TANZU_CLI_CLOUD_SERVICES_ORGANIZATION_ID"] = org
        result = subprocess.check_output(["tanzu", "context","create",contextName,"--endpoint",endpoint,"--type",type], text=True,env=my_env)
        logging.info(result)
        return contextName
    except subprocess.CalledProcessError as e:
        logging.fatal(e.output)
        sys.exit(1)


def main():
    cluster_type = "tkg"
    parser = argparse.ArgumentParser(description="cli app for onboarding clusters from TMC into TPK8s")
    parser.add_argument('-t',"--csp-token", help="the token to be used when creating contexts,only used if tmc-context and tpk8s conmtext are not provided")
    parser.add_argument('-o',"--org-id", help="the org to be used when creating contexts, only used if tmc-context and tp conmtext are not provided")
    parser.add_argument('-c',"--cluster", help="the cluster name, use full agent name")
    parser.add_argument('-m',"--management-cluster", help="the management cluster name")
    parser.add_argument('-p',"--provisioner", help="the provisioner name")
    parser.add_argument("--project", help="the tp project that will be used for attaching the cluster, only needed when context not provided directly")
    parser.add_argument('-r',"--remove-tz-std", default=False, help="optionally remove the tanzu-standard repo",action=argparse.BooleanOptionalAction)
    parser.add_argument("--tkgm", default=False, help="is this a tkgm cluster",action=argparse.BooleanOptionalAction)
    parser.add_argument("--cg", default="run", help="the tpk8s cluster group")
    parser.add_argument("--api-url", help="the url of the api server(not pinniped backed), this is needed to connect after tmc is detached. This is not need for TKG")
    parser.add_argument("--tmc-host", help="the hostname of the tmc instance, not including the protocol. needed when not providing contexts directly")
    args = parser.parse_args()

    if args.csp_token != None and args.org_id != None and args.tmc_host != None and args.project != None:
        logging.info("csp token and org provided, creating contexts on demand")
        tmc_context = createContext(args.csp_token,args.org_id,args.tmc_host,"tp-onboarding-tmc","tmc")
        tp_context = createContext(args.csp_token,args.org_id,"https://platform.tanzu.broadcom.com","tp-onboarding-tp","tanzu")
    else:
        logging.fatal("no context or org details specified please use either --tmc-context and --tp-context or --org-id and --csp-token")
        sys.exit(1)

    if cluster_type in ["aks","eks"] and args.api_url == None:
        logging.error("no api url provided, this is needed for aks and eks")
        sys.exit(1)

    match args.management_cluster:
        case "eks":
            logging.info("management cluster provided and is EKS")
            cluster_type = "eks"
            api_url = args.api_url
        case "aks":
            logging.info("management cluster provided and is AKS")
            cluster_type = "aks"
            api_url = args.api_url
        case None:
            logging.fatal("management cluster name is required")
            sys.exit(1)            
        case _:
            if args.tkgm:
                cluster_type = "tkgm"
            else:
                cluster_type = "tkgs"
            logging.info("management cluster provided and is TKG")

    if cluster_type in ["aks","eks"] and args.api_url == None:
        logging.error("no api url provided, this is needed for aks and eks")
        sys.exit(1)



    setContext(tmc_context)
    getKubeconfig(args.cluster, args.management_cluster,args.provisioner)
    if cluster_type == "tkgm" or cluster_type == "tkgs":
        api_url = getApiUrl("/tmp/tmckube.yml")
    logging.info(f"non pinniped api url is {api_url}")
    token = createNewUser("/tmp/tmckube.yml")
    sakubeconfig = saClient(token,'/tmp/tmckube.yml',api_url)
    cluster_name = tmcDetach(args.cluster,cluster_type,args.management_cluster,args.provisioner)
    detachWait(sakubeconfig)
    if args.remove_tz_std:
        logging.info("removing tanzu standard repo")
        tzStdremove(sakubeconfig,cluster_type)

    else:
        logging.info("keeping tanzu standard repo")
        tzStdKeep(sakubeconfig,cluster_type)
    setContext(tp_context)
    setProject(args.project)
    tpk8sAttach(cluster_name,args.cg,"/tmp/sakube.yml")




if __name__ == "__main__":
    main()