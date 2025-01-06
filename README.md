# TPK8s onboarding

This tool automates the TMC detach process along with the attach process to TPK8s. This is a temporary solution that can be used to ease the process of using existing or new TMC created clusters and enabling them in Tanzu PLatform. Long term this will be handled by TMC. 


# What it does
1. handles creating the Tanzu cli contexts(optional)
2. creates a non TMC based kubeconfig for access after the detach
3. detaches the cluster from TMC
4. optionally removed the tanzu standard package repo
5. attached to TPK8s

# Usage

This tool can be run directly as a python script, however the recomended approach is to use prebuilty container image. Jump to the section that fits your use case. There will be a common set of options between the scenarios. Specifically, the option to use an existing context or an ephemeral one. The difference is that using an existing one allows for mounting in and existing tanzu config, the ephemeral option takes in a token and handles the login and context creation on demand in the container. Another common option is whether or not to remove the tanzu standard package repo(`--remove-tz-std`), by default if this flag is not passed it will keep the repo enabled, this is helpful if you are using packages from this repo like fluentbit.

## A note on `api-url`

For EKS and AKS there is a required option for `api-url`, this is the api url for the k8s api server when not using pinniped. This can be foudn in the aks or eks console. We need this becuase after we detach the cluster we need to still connect to it to re-attach. This is not needed for TKG becuase pinniped runs on the same endpoint and we can infer it from the cluster. This info is not available in the eks or aks clusters. 

## General usage
```
usage: onboard.py [-h] [-t CSP_TOKEN] [--tmc-context TMC_CONTEXT] [--tp-context TP_CONTEXT] [-o ORG_ID] [-c CLUSTER] [-m MANAGEMENT_CLUSTER] [-p PROVISIONER]
                  [--project PROJECT] [-r | --remove-tz-std | --no-remove-tz-std] [--tkgm | --no-tkgm] [--cg CG] [--api-url API_URL] [--tmc-host TMC_HOST]

cli app for onboarding clusters from TMC into TPK8s

options:
  -h, --help            show this help message and exit
  -t, --csp-token CSP_TOKEN
                        the token to be used when creating contexts,only used if tmc-context and tpk8s conmtext are not provided
  --tmc-context TMC_CONTEXT
                        the name of the tmc context to be used, only used if token and org are not provided
  --tp-context TP_CONTEXT
                        the name of the tp context to be used, only used if token and org are not provided
  -o, --org-id ORG_ID   the org to be used when creating contexts, only used if tmc-context and tp conmtext are not provided
  -c, --cluster CLUSTER
                        the cluster name, use full agent name
  -m, --management-cluster MANAGEMENT_CLUSTER
                        the management cluster name
  -p, --provisioner PROVISIONER
                        the provisioner name
  --project PROJECT     the tp project that will be used for attaching the cluster, only needed when context not provided directly
  -r, --remove-tz-std, --no-remove-tz-std
                        optionally remove the tanzu-standard repo
  --tkgm, --no-tkgm     is this a tkgm cluster
  --cg CG               the tpk8s cluster group
  --api-url API_URL     the url of the api server(not pinniped backed), this is needed to connect after tmc is detached. This is not need for TKG
  --tmc-host TMC_HOST   the hostname of the tmc instance, not including the protocol. needed when not providing contexts directly
  ```


## TKGs(VKS) clusters

Using a ephemeral context

```bash
docker run ghcr.io/warroyo/tpk8s-attach -c <clustername> -p <provisioner> -m <mgmt-cluster> --csp-token <token> --org-id <org-id> --tmc-host <tmc-hostname> --project <tanzu-platform-project>
```

Using an existing context

```bash
docker run -v -v ~/.config/tanzu/:/root/.config/tanzu/ ghcr.io/warroyo/tpk8s-attach -c <clustername> -p <provisioner> -m <mgmt-cluster> --tmc-context <tmc-context-name> --tp-context <tanzu-platform-context-name> --project <tanzu-platform-project>
```


## TKGm

Using a ephemeral context

```bash
docker run ghcr.io/warroyo/tpk8s-attach --tkgm -c <clustername> -p <provisioner> -m <mgmt-cluster> --csp-token <token> --org-id <org-id> --tmc-host <tmc-hostname> --project <tanzu-platform-project>
```

Using an existing context

```bash
docker run -v -v ~/.config/tanzu/:/root/.config/tanzu/ ghcr.io/warroyo/tpk8s-attach --tkgm -c <clustername> -p <provisioner> -m <mgmt-cluster> --tmc-context <tmc-context-name> --tp-context <tanzu-platform-context-name> --project <tanzu-platform-project>
```


## AKS

Using a ephemeral context

```bash
docker run ghcr.io/warroyo/tpk8s-attach -c <full-agent-name> -p aks -m aks  --api-url <non-pinniped-api-url> --csp-token <token> --org-id <org-id>> --tmc-host <tmc-hostname> --project  <tanzu-platform-project>
```

Using an existing context

```bash
docker run -v -v ~/.config/tanzu/:/root/.config/tanzu/ ghcr.io/warroyo/tpk8s-attach  -c <full-agent-name> -p aks -m aks --api-url <non-pinniped-api-url> --tmc-context <tmc-context-name> --tp-context <tanzu-platform-context-name> --project <tanzu-platform-project>
```

## EKS

Using a ephemeral context

```bash
docker run ghcr.io/warroyo/tpk8s-attach -c <full-agent-name> -p eks -m eks  --api-url <non-pinniped-api-url> --csp-token <token> --org-id <org-id>> --tmc-host <tmc-hostname> --project  <tanzu-platform-project>
```

Using an existing context

```bash
docker run -v -v ~/.config/tanzu/:/root/.config/tanzu/ ghcr.io/warroyo/tpk8s-attach  -c <full-agent-name> -p eks -m eks --api-url <non-pinniped-api-url> --tmc-context <tmc-context-name> --tp-context <tanzu-platform-context-name> --project <tanzu-platform-project>
```