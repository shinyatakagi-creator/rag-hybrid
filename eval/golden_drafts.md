# Golden-set drafts for review

`source_doc` is only a suggestion for `expected_doc_ids`: the drafting model saw one passage. Pick the final pages from your own reading. Flagged = high word overlap with the source passage (the draft may flatter BM25).

## d001 · conceptual  **FLAGGED**
- **Q:** When I query the control plane's readiness URL and want one particular subsystem check skipped while still getting a per-check breakdown, how do I do that and how does the skipped item appear in the results?
- **Reference answer:** Combine the detailed-output parameter with an exclusion parameter naming the check in the request URL. The skipped check is still listed but is labeled as excluded, followed by ok, while the other checks report normally.
- source_doc (suggested expected): `reference/using-api/health-checks` · https://kubernetes.io/docs/reference/using-api/health-checks/
- section: Kubernetes API health endpoints > API endpoints for health
- overlap: ratio 0.28, distinctive shared ['query', 'readiness'], copied phrases []
- flags: distinctive_terms:query,readiness

## d002 · conceptual  **FLAGGED**
- **Q:** How can a cluster admin make sure that requests for disk space in a particular project area are neither too tiny nor too huge, and what happens to a request outside those bounds?
- **Reference answer:** Add a LimitRange to the namespace setting minimum and maximum storage sizes. The admission controller rejects any PersistentVolumeClaim whose requested size is above the max or below the min, e.g., 10Gi is refused when the max is 2Gi.
- source_doc (suggested expected): `tasks/administer-cluster/limit-storage-consumption` · https://kubernetes.io/docs/tasks/administer-cluster/limit-storage-consumption/
- section: Limit Storage Consumption > LimitRange to limit requests for storage
- overlap: ratio 0.28, distinctive shared ['admin', 'project'], copied phrases []
- flags: distinctive_terms:admin,project

## d003 · conceptual
- **Q:** I reserved some large memory blocks on a machine while it was already running, but the cluster still doesn't show them for that machine. What do I need to do?
- **Reference answer:** For pages allocated after the node has booted, the node agent (Kubelet) must be restarted so the new allocations are reflected in the node's reported resources.
- source_doc (suggested expected): `tasks/manage-hugepages/scheduling-hugepages` · https://kubernetes.io/docs/tasks/manage-hugepages/scheduling-hugepages/
- section: Manage HugePages > Before you begin
- overlap: ratio 0.15, distinctive shared [], copied phrases []

## d004 · conceptual  **FLAGGED**
- **Q:** If I want to pin specific internal IP addresses on an Amazon-managed network load balancer fronting my cluster workload, where do I find out how that annotation is meant to be used and which component reads it?
- **Reference answer:** The annotation is placed on a Service and is read by the AWS load balancer controller. Its details are in the annotations guide within that controller's documentation, which the passage links to.
- source_doc (suggested expected): `reference/labels-annotations-taints/_index` · https://kubernetes.io/docs/reference/labels-annotations-taints/
- section: Well-Known Labels, Annotations and Taints > Labels, annotations and taints used on API objects > service.beta.kubernetes.io/aws-load-balancer-private-ipv4-addresses (beta) {#service-beta-kubernetes-io-aws-load-balancer-private-ipv4-addresses}
- overlap: ratio 0.84, distinctive shared ['amazon', 'balancer', 'front', 'internal'], copied phrases []
- flags: high_overlap(0.84); distinctive_terms:amazon,balancer,front,internal

## d005 · conceptual  **FLAGGED**
- **Q:** What do I need to set up on the control plane so it trusts the identity certificates presented by a new node that is joining, and how do I point it at the signing authority?
- **Reference answer:** The API server must be told which certificate authority bundle holds the signing certificate, so it can accept client certificates. This is done by adding a client CA file option to the API server command, pointing to the CA bundle file, such as /var/lib/kubernetes/ca.pem.
- source_doc (suggested expected): `reference/access-authn-authz/kubelet-tls-bootstrapping` · https://kubernetes.io/docs/reference/access-authn-authz/kubelet-tls-bootstrapping/
- section: TLS bootstrapping > kube-apiserver configuration > Recognizing client certificates
- overlap: ratio 0.79, distinctive shared ['authority', 'certificate', 'sign', 'trust'], copied phrases []
- flags: high_overlap(0.79); distinctive_terms:authority,certificate,sign,trust

## d006 · conceptual  **FLAGGED**
- **Q:** In the node agent's metrics report, how is processor consumption expressed as a running total since something was created, as opposed to an average over a recent sampling interval?
- **Reference answer:** The cumulative figure sums usage across all cores since the object was created. The other figure is total usage across all cores averaged over the sample window, interpreted as core-nanoseconds per second.
- source_doc (suggested expected): `reference/kubelet-api/stats.v1alpha1` · https://kubernetes.io/docs/reference/kubelet-api/stats.v1alpha1/
- section: Kubelet Summary API (v1alpha1) > `CPUStats`     {#CPUStats}
- overlap: ratio 0.44, distinctive shared ['average', 'metric', 'report', 'total'], copied phrases []
- flags: distinctive_terms:average,metric,report,total

## d007 · conceptual  **FLAGGED**
- **Q:** Which kind of workload is supervised and restarted by the node agent itself rather than by the central management layer, and what is it mostly used for?
- **Reference answer:** Static Pods are supervised and restarted directly by the kubelet on one specific node, without the API server observing them. Their main use is running a self-hosted control plane, with the kubelet supervising the control plane components.
- source_doc (suggested expected): `concepts/workloads/pods/_index` · https://kubernetes.io/docs/concepts/workloads/pods/
- section: Pods > Static Pods
- overlap: ratio 0.54, distinctive shared ['rather'], copied phrases []
- flags: high_overlap(0.54)

## d008 · conceptual  **FLAGGED**
- **Q:** If I change a confidential value that my running workload reads from a mounted directory, why might the new value take a while to show up, and what determines the maximum wait?
- **Reference answer:** Updates are eventually consistent. The maximum delay is the kubelet sync period plus the cache propagation delay, which depends on the cache type: watch delay, the configured TTL, or zero when polling the API server directly.
- source_doc (suggested expected): `concepts/configuration/secret` · https://kubernetes.io/docs/concepts/configuration/secret/
- section: Secrets > Working with Secrets > Using Secrets as files from a Pod {#using-secrets-as-files-from-a-pod}
- overlap: ratio 0.81, distinctive shared ['confidential', 'directory', 'mount', 'wait'], copied phrases []
- flags: high_overlap(0.81); distinctive_terms:confidential,directory,mount,wait

## d009 · conceptual  **FLAGGED**
- **Q:** How did people choose which traffic-routing controller should handle their rules before the dedicated object type for this was introduced in version 1.18, and why isn't the modern replacement a perfect one-to-one swap?
- **Reference answer:** Previously an informal, never formally defined annotation on the resource named the controller to implement it. The newer field instead points to a separate class object holding extra configuration, including the controller name, so it isn't a direct equivalent.
- source_doc (suggested expected): `concepts/services-networking/ingress` · https://kubernetes.io/docs/concepts/services-networking/ingress/
- section: Ingress > Ingress class > Deprecated annotation
- overlap: ratio 0.6, distinctive shared ['choose', 'handle', 'replacement', 'rout', 'traffic'], copied phrases []
- flags: high_overlap(0.6); distinctive_terms:choose,handle,replacement,rout,traffic

## d010 · conceptual  **FLAGGED**
- **Q:** How long will the control plane wait on an external hook that vets incoming requests before giving up, and what range of wait times can I set?
- **Reference answer:** The wait defaults to 10 seconds. It can be configured to any value from 1 to 30 seconds, and if it expires the call is either ignored or the request is rejected depending on the failure policy.
- source_doc (suggested expected): `reference/access-authn-authz/extensible-admission-controllers` · https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/
- section: Dynamic Admission Control > Webhook configuration > Timeouts
- overlap: ratio 0.71, distinctive shared ['incom', 'long', 'wait'], copied phrases []
- flags: high_overlap(0.71); distinctive_terms:incom,long,wait

## d011 · conceptual  **FLAGGED**
- **Q:** If I want to guarantee that just one workload in my entire cluster can read from or write to a piece of storage, which setting should I choose, and what does it require from the storage driver?
- **Reference answer:** Choose the single-pod read-write mode, ReadWriteOncePod. It is only supported for CSI volumes on Kubernetes 1.22+, and requires updated CSI sidecars: provisioner v3.0.0+, attacher v3.3.0+, and resizer v1.3.0+.
- source_doc (suggested expected): `concepts/storage/persistent-volumes` · https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- section: Persistent Volumes > Access Modes
- overlap: ratio 0.93, distinctive shared ['choose', 'driver', 'guarantee', 'piece'], copied phrases ['a piece of storage', 'read from or write']
- flags: high_overlap(0.93); distinctive_terms:choose,driver,guarantee,piece; copied_phrase:a piece of storage|read from or write

## d012 · conceptual  **FLAGGED**
- **Q:** If my scaling signal comes from a third-party hosted service and isn't tied to anything inside my cluster, and several data series match what I asked for, how does the autoscaler combine them?
- **Reference answer:** When more than one time series matches the selector for an external metric, the autoscaler adds their values together and uses that sum.
- source_doc (suggested expected): `tasks/run-application/horizontal-pod-autoscale-walkthrough` · https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
- section: HorizontalPodAutoscaler Walkthrough > Autoscaling on multiple metrics and custom metrics > Autoscaling on metrics not related to Kubernetes objects
- overlap: ratio 0.47, distinctive shared ['autoscaler', 'isn', 'scal', 'sery', 'several'], copied phrases []
- flags: distinctive_terms:autoscaler,isn,scal,sery,several

## d013 · conceptual  **FLAGGED**
- **Q:** If I'm splitting a big batch of tasks across many containers, why might creating a separate controller object for every single task become a problem as the number of tasks grows?
- **Reference answer:** Making one Job per work item adds overhead for both the user and the system, since they must manage a large number of Job objects. A single Job covering all work items is better when there are many items.
- source_doc (suggested expected): `concepts/workloads/controllers/job` · https://kubernetes.io/docs/concepts/workloads/controllers/job/
- section: Jobs > Job patterns
- overlap: ratio 0.76, distinctive shared ['batch', 'become', 'separate'], copied phrases []
- flags: high_overlap(0.76); distinctive_terms:batch,become,separate

## d014 · conceptual  **FLAGGED**
- **Q:** What happens to a machine joining my cluster if its software for running containers only speaks an outdated version of the standard communication protocol with the node agent, on newer releases?
- **Reference answer:** For Kubernetes v1.26 and later, the kubelet requires the container runtime to support the v1 CRI API. If the runtime lacks v1 support, the kubelet will not register the node.
- source_doc (suggested expected): `concepts/containers/cri` · https://kubernetes.io/docs/concepts/containers/cri/
- section: Container Runtime Interface (CRI) > The API {#api}
- overlap: ratio 0.47, distinctive shared ['communication', 'protocol', 'standard'], copied phrases []
- flags: distinctive_terms:communication,protocol,standard

## d015 · conceptual  **FLAGGED**
- **Q:** If the node agent restarts in the middle of waiting for a workload's processes to shut down, does the countdown before forced termination pick up where it left off?
- **Reference answer:** No. If the kubelet or the container runtime's management service restarts while waiting for processes to stop, the cluster retries from the beginning, giving the full original grace period again.
- source_doc (suggested expected): `concepts/workloads/pods/pod-lifecycle` · https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- section: Pod Lifecycle > Termination of Pods {#pod-termination}
- overlap: ratio 0.73, distinctive shared ['down', 'forc', 'pick', 'shut', 'termination', 'wait'], copied phrases []
- flags: high_overlap(0.73); distinctive_terms:down,forc,pick,shut,termination,wait

## d016 · conceptual  **FLAGGED**
- **Q:** My workloads on a Windows machine keep getting stuck while starting up or crash-looping; what low-level helper image should I double-check, and where do I configure it if I use containerd?
- **Reference answer:** Verify the pause image matches your Windows OS version. With containerd, the pause image is set in the sandbox_image field under the CRI plugin section of the config.toml file.
- source_doc (suggested expected): `tasks/debug/debug-cluster/windows` · https://kubernetes.io/docs/tasks/debug/debug-cluster/windows/
- section: Windows debugging tips > Node-level troubleshooting {#troubleshooting-node}
- overlap: ratio 0.6, distinctive shared ['containerd', 'gett', 'machine', 'stuck', 'window'], copied phrases []
- flags: high_overlap(0.6); distinctive_terms:containerd,gett,machine,stuck,window

## d017 · conceptual
- **Q:** Why is it recommended that every cluster run a name-resolution server for its services, even though most optional extras aren't mandatory?
- **Reference answer:** Although other addons are not strictly required, every cluster should have cluster DNS because many examples depend on it. It serves DNS records for Kubernetes services, and containers started by Kubernetes automatically use it in their lookups.
- source_doc (suggested expected): `concepts/architecture/_index` · https://kubernetes.io/docs/concepts/architecture/
- section: Cluster Architecture > Addons > DNS
- overlap: ratio 0.38, distinctive shared [], copied phrases []

## d018 · conceptual  **FLAGGED**
- **Q:** On my Debian-based server, how can I tell whether my software sources point at the newer community-run location or at the old one for Kubernetes packages?
- **Reference answer:** Display the contents of the Kubernetes apt source file (its name may differ on your system). If it has a line pointing to the community host with the stable core path, you're using the community-owned repositories; otherwise you should migrate.
- source_doc (suggested expected): `tasks/administer-cluster/kubeadm/change-package-repository` · https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/change-package-repository/
- section: Changing The Kubernetes Package Repository > Before you begin > Verifying if the Kubernetes package repositories are used
- overlap: ratio 0.4, distinctive shared ['community', 'debian', 'package'], copied phrases []
- flags: distinctive_terms:community,debian,package

## d019 · conceptual  **FLAGGED**
- **Q:** Which kinds of login approaches suit a tiny personal setup versus a big installation with many people who need to be organized into teams?
- **Reference answer:** Small, single-user clusters can use a simple certificate or static bearer token. Larger clusters may integrate an existing OIDC or LDAP server, which lets users be divided into groups.
- source_doc (suggested expected): `tasks/administer-cluster/securing-a-cluster` · https://kubernetes.io/docs/tasks/administer-cluster/securing-a-cluster/
- section: Securing a Cluster > Controlling access to the Kubernetes API > API Authentication
- overlap: ratio 0.33, distinctive shared ['installation', 'setup', 'team'], copied phrases []
- flags: distinctive_terms:installation,setup,team

## d020 · conceptual  **FLAGGED**
- **Q:** What cluster-level setup steps do I need to take so that the endpoint serving CPU and memory usage figures can be reached, and what extra component must be running to actually answer those requests?
- **Reference answer:** You need to turn on the API aggregation layer and register an APIService for metrics.k8s.io. You also have to deploy metrics-server or an alternative adapter that serves the Metrics API, otherwise it cannot be accessed.
- source_doc (suggested expected): `tasks/debug/debug-cluster/resource-metrics-pipeline` · https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/
- section: Resource metrics pipeline > Metrics API
- overlap: ratio 0.52, distinctive shared ['figure'], copied phrases ['cpu and memory usage']
- flags: high_overlap(0.52); copied_phrase:cpu and memory usage

## d021 · conceptual  **FLAGGED**
- **Q:** If I put a setting at the front of the list that stores API data without scrambling it, what happens to items that were already scrambled earlier?
- **Reference answer:** With the no-encryption provider listed first, newly written resources are stored as plaintext. Resources that were already encrypted are not automatically rewritten as plaintext.
- source_doc (suggested expected): `tasks/administer-cluster/encrypt-data` · https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/
- section: Encrypting Confidential Data at Rest > Understanding the encryption at rest configuration > Available providers {#providers}
- overlap: ratio 0.69, distinctive shared ['earlier', 'item', 'store'], copied phrases []
- flags: high_overlap(0.69); distinctive_terms:earlier,item,store

## d022 · conceptual  **FLAGGED**
- **Q:** I ran a query to list a certain kind of hardware-descriptor resource in my cluster and the server said it doesn't recognize that resource type. What might be wrong and what should I try first?
- **Reference answer:** The cluster's setup for dynamic device allocation is likely incorrect, for example because the resource.k8s.io API group was disabled. Start by reconfiguring and restarting the kube-apiserver component.
- source_doc (suggested expected): `tasks/configure-pod-container/assign-resources/set-up-dra-cluster` · https://kubernetes.io/docs/tasks/configure-pod-container/assign-resources/set-up-dra-cluster/
- section: Set Up DRA in a Cluster > Verify that DRA is enabled {#verify}
- overlap: ratio 0.53, distinctive shared ['doesn', 'hardware', 'try'], copied phrases []
- flags: high_overlap(0.53); distinctive_terms:doesn,hardware,try

## d023 · mixed  **FLAGGED**
- **Q:** When a new workload is submitted without any registry credentials of its own, what does the API server plugin do regarding imagePullSecrets, and where does it get them?
- **Reference answer:** If the incoming Pod's spec has no imagePullSecrets, the admission controller adds them, copying them from the Pod's ServiceAccount.
- exact term: `imagePullSecrets`
- source_doc (suggested expected): `reference/access-authn-authz/service-accounts-admin` · https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/
- section: Managing Service Accounts > Control plane details > ServiceAccount admission controller
- overlap: ratio 0.73, distinctive shared ['credential'], copied phrases []
- flags: high_overlap(0.73)

## d024 · mixed
- **Q:** How does a group hierarchy get cleaned up automatically, and which metadata field linking it to its creating controller makes that possible, namely ownerReferences?
- **Reference answer:** The group hierarchy is owned by the workload controller that created it through ownerReferences. When the owning workload object is deleted, cascading garbage collection automatically removes the associated hierarchy.
- exact term: `ownerReferences`
- source_doc (suggested expected): `concepts/workloads/compositepodgroup-api/lifecycle` · https://kubernetes.io/docs/concepts/workloads/compositepodgroup-api/lifecycle/
- section: CompositePodGroup Lifecycle > Ownership and garbage collection
- overlap: ratio 0.54, distinctive shared ['hierarchy'], copied phrases []

## d025 · mixed
- **Q:** When turning off this feature, besides restarting the kubelet, what must be true of the `memoryReservationPolicy` setting, and why do leftover per-pod protection values stop having any effect?
- **Reference answer:** memoryReservationPolicy must be unset or set to None. Leftover pod-level and container-level memory.min and memory.low values are ineffective because the kubelet resets the ancestor protection to zero at startup.
- exact term: `memoryReservationPolicy`
- source_doc (suggested expected): `concepts/workloads/pods/pod-qos` · https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/
- section: Pod Quality of Service Classes > Memory QoS with cgroup v2 > Disabling or rolling back Memory QoS
- overlap: ratio 0.5, distinctive shared ['protection'], copied phrases []

## d026 · mixed  **FLAGGED**
- **Q:** If I'm running kube-proxy on a machine that uses systemd, where do its log entries end up, and does the default container output handling apply?
- **Reference answer:** Components that run inside containers, such as kube-proxy, always write to .log files in /var/log, bypassing the default container logging mechanism. The journald behavior applies only to the kubelet and container runtime on systemd machines.
- exact term: `kube-proxy`
- source_doc (suggested expected): `concepts/cluster-administration/observability` · https://kubernetes.io/docs/concepts/cluster-administration/observability/
- section: Observability > Logs
- overlap: ratio 0.83, distinctive shared ['end', 'entry', 'machine', 'systemd'], copied phrases []
- flags: high_overlap(0.83); distinctive_terms:end,entry,machine,systemd

## d027 · mixed  **FLAGGED**
- **Q:** Which file does the kubelet use to keep a record of what the container runtime has accepted for each pod on a node, called actuated_pods_state, and where does that file live?
- **Reference answer:** actuated_pods_state records the resources that have been accepted by the runtime for each pod running on the node. It is located within the kubelet base directory, /var/lib/kubelet by default on Linux.
- exact term: `actuated_pods_state`
- source_doc (suggested expected): `reference/node/kubelet-files` · https://kubernetes.io/docs/reference/node/kubelet-files/
- section: Local Files And Paths Used By The Kubelet > State > Pod resource checkpoints
- overlap: ratio 0.83, distinctive shared ['accept', 'keep', 'record'], copied phrases []
- flags: high_overlap(0.83); distinctive_terms:accept,keep,record

## d028 · mixed  **FLAGGED**
- **Q:** In kubeadm's configuration for mounting host volumes into control plane components, which setting decides where inside the container the host directory shows up, as opposed to the location on the node, when using mountPath?
- **Reference answer:** The mountPath field gives the path inside the Pod where the hostPath will be mounted. It is a required field of type string.
- exact term: `mountPath`
- source_doc (suggested expected): `reference/config-api/kubeadm-config.v1beta4` · https://kubernetes.io/docs/reference/config-api/kubeadm-config.v1beta4/
- section: kubeadm Configuration (v1beta4) > kube-proxy specific options here > `HostPathMount`     {#kubeadm-k8s-io-v1beta4-HostPathMount}
- overlap: ratio 0.83, distinctive shared ['directory', 'inside', 'kubeadm'], copied phrases []
- flags: high_overlap(0.83); distinctive_terms:directory,inside,kubeadm

## d029 · mixed  **FLAGGED**
- **Q:** When kube-proxy uses the Maglev-based scheduler in IPVS mode, is the `mh-port` flag turned on or left off, and what does that flag change about how a backend gets picked?
- **Reference answer:** kube-proxy always sets the mh-port flag when using mh. It adds the source port number to the hash computation, so mh behaves like source hashing but with ports.
- exact term: `mh-port`
- source_doc (suggested expected): `reference/networking/virtual-ips` · https://kubernetes.io/docs/reference/networking/virtual-ips/
- section: Virtual IPs and Service Proxies > Proxy modes > IPVS proxy mode {#proxy-mode-ipvs}
- overlap: ratio 0.93, distinctive shared ['backend', 'ipv', 'maglev', 'pick', 'turn'], copied phrases ['kube proxy uses the']
- flags: high_overlap(0.93); distinctive_terms:backend,ipv,maglev,pick,turn; copied_phrase:kube proxy uses the

## d030 · mixed  **FLAGGED**
- **Q:** When a cluster's network plugin needs it, which setting, `masqueradeAll`, makes the proxy rewrite the source address on every packet headed to a virtual service address, and in which proxy modes does it apply?
- **Reference answer:** masqueradeAll tells kube-proxy to SNAT all traffic sent to Service cluster IPs. It applies when using the iptables or ipvs proxy mode, and may be required with some CNI plugins.
- exact term: `masqueradeAll`
- source_doc (suggested expected): `reference/config-api/kube-proxy-config.v1alpha1` · https://kubernetes.io/docs/reference/config-api/kube-proxy-config.v1alpha1/
- section: kube-proxy Configuration (v1alpha1) > `KubeProxyIPTablesConfiguration`     {#kubeproxy-config-k8s-io-v1alpha1-KubeProxyIPTablesConfiguration}
- overlap: ratio 0.62, distinctive shared ['packet'], copied phrases []
- flags: high_overlap(0.62)

## d031 · mixed  **FLAGGED**
- **Q:** In the older beta apps API, which value did the update strategy type take when left unspecified, as opposed to the current default, and what is that older value called: OnDelete?
- **Reference answer:** In apps/v1beta1 the default update strategy type was OnDelete, whereas in apps/v1 it now defaults to RollingUpdate.
- exact term: `OnDelete`
- source_doc (suggested expected): `reference/using-api/deprecation-guide` · https://kubernetes.io/docs/reference/using-api/deprecation-guide/
- section: Deprecated API Migration Guide > Removed APIs by release > v1.16
- overlap: ratio 0.62, distinctive shared ['older', 'strategy', 'unspecifi'], copied phrases []
- flags: high_overlap(0.62); distinctive_terms:older,strategy,unspecifi

## d032 · mixed  **FLAGGED**
- **Q:** Why might an operator choose the AlwaysAllow setting for budgets protecting workloads, when they want a node to be emptied even though some of the application's replicas are malfunctioning?
- **Reference answer:** Setting AlwaysAllow lets misbehaving application pods be evicted during a node drain. Without it, the default is to wait until the application pods become healthy before the drain can proceed.
- exact term: `AlwaysAllow`
- source_doc (suggested expected): `concepts/workloads/pods/disruptions` · https://kubernetes.io/docs/concepts/workloads/pods/disruptions/
- section: Disruptions > Pod disruption budgets
- overlap: ratio 0.6, distinctive shared ['budget', 'replica'], copied phrases []
- flags: high_overlap(0.6); distinctive_terms:budget,replica

## d033 · mixed  **FLAGGED**
- **Q:** When the scheduler picks victims to make room for a pending Pod, under what circumstances might it skip the lowest-ranked Pods because a PodDisruptionBudget guards them, and move on to more important ones?
- **Reference answer:** Higher-priority Pods are considered for preemption only if removing the lowest priority Pods isn't enough to schedule the preemptor, or if those lowest priority Pods are protected by PodDisruptionBudget.
- exact term: `PodDisruptionBudget`
- source_doc (suggested expected): `concepts/scheduling-eviction/pod-priority-preemption` · https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/
- section: Pod Priority and Preemption > Interactions between Pod priority and quality of service {#interactions-of-pod-priority-and-qos}
- overlap: ratio 0.72, distinctive shared ['lowest', 'pend', 'pick', 'rank', 'room', 'skip', 'under', 'victim'], copied phrases ['to make room for']
- flags: high_overlap(0.72); distinctive_terms:lowest,pend,pick,rank,room,skip,under,victim; copied_phrase:to make room for

## d034 · mixed  **FLAGGED**
- **Q:** When setting up encryption with an external key service, which kube-apiserver option do I use with --encryption-provider-config-automatic-reload turned on so that edits to the file on disk get picked up without a restart?
- **Reference answer:** The --encryption-provider-config-automatic-reload boolean argument controls whether the file named by --encryption-provider-config is reloaded automatically when its disk contents change.
- exact term: `--encryption-provider-config-automatic-reload`
- source_doc (suggested expected): `tasks/administer-cluster/kms-provider` · https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/
- section: Using a KMS provider for data encryption > Encrypting your data with the KMS provider
- overlap: ratio 0.71, distinctive shared ['disk'], copied phrases []
- flags: high_overlap(0.71)

## d035 · mixed  **FLAGGED**
- **Q:** When wiring up my custom API backend, what is the purpose of binding my namespace's service account to the extension-apiserver-authentication-reader role?
- **Reference answer:** The role binding gives the extension api-server permission to read the extension-apiserver-authentication configmap, which it needs to access.
- exact term: `extension-apiserver-authentication-reader`
- source_doc (suggested expected): `tasks/extend-kubernetes/setup-extension-api-server` · https://kubernetes.io/docs/tasks/extend-kubernetes/setup-extension-api-server/
- section: Set up an Extension API Server > Set up an extension api-server to work with the aggregation layer
- overlap: ratio 0.6, distinctive shared ['bind', 'role'], copied phrases []
- flags: high_overlap(0.6); distinctive_terms:bind,role

## d036 · mixed  **FLAGGED**
- **Q:** Why does a rule that loops over a list-type field get rejected at cost estimation, and how does setting maxItems on that field help?
- **Reference answer:** Without a length limit, the cost system assumes the worst case for anything that can be iterated over, so the rule may exceed the budget. Setting maxItems bounds the input size, preventing the cost estimation validation error.
- exact term: `maxItems`
- source_doc (suggested expected): `tasks/extend-kubernetes/custom-resources/custom-resource-definitions` · https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/
- section: Extend the Kubernetes API with CustomResourceDefinitions > Advanced topics > Validation rules
- overlap: ratio 0.83, distinctive shared ['cost', 'estimation', 'reject'], copied phrases []
- flags: high_overlap(0.83); distinctive_terms:cost,estimation,reject

## d037 · mixed  **FLAGGED**
- **Q:** If a node operator wants the kubelet to actually enforce the OS daemon reservation rather than just subtract it from capacity, which value must be added to the enforceNodeAllocatable setting?
- **Reference answer:** To enforce the reservation for OS system daemons, add system-reserved to enforceNodeAllocatable and set the systemReservedCgroup to the parent control group of those daemons.
- exact term: `enforceNodeAllocatable`
- source_doc (suggested expected): `tasks/administer-cluster/reserve-compute-resources` · https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/
- section: Reserve Compute Resources for System Daemons > Node Allocatable > System Reserved
- overlap: ratio 0.73, distinctive shared ['capacity', 'daemon', 'operator', 'reservation'], copied phrases []
- flags: high_overlap(0.73); distinctive_terms:capacity,daemon,operator,reservation

## d038 · mixed  **FLAGGED**
- **Q:** When would a setting of localhostProfile be allowed, and what does the value you give it refer to on the machines running workloads?
- **Reference answer:** localhostProfile may only be set when type is Localhost. It names a pre-configured profile on the node, which must be loaded on all nodes suitable for the Pod since scheduling location is unknown.
- exact term: `localhostProfile`
- source_doc (suggested expected): `tasks/configure-pod-container/security-context` · https://kubernetes.io/docs/tasks/configure-pod-container/security-context/
- section: Configure a Security Context for a Pod or Container > Set the AppArmor Profile for a Container
- overlap: ratio 0.75, distinctive shared ['give'], copied phrases []
- flags: high_overlap(0.75)
