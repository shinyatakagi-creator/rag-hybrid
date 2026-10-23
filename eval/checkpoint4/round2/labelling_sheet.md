# Checkpoint 4, round 2: label 30 citation pairs

Rubric: split each sentence into its claims, then judge every claim against the excerpt alone (not against what you know about Kubernetes).

- **supported** = every claim is in the excerpt or directly implied by it (paraphrase counts).
- **partial** = some claims are present in the excerpt and none is contradicted.
- **unsupported** = the excerpt contradicts the sentence, or the sentence's main claim is absent from the excerpt.

Write one label per row in `eval/checkpoint4/round2/my_labels.csv` (columns `id,label,note`; labels `supported`, `partial`, `unsupported`). Do not open the key file until all 30 labels are saved.

## M01

**Sentence:** Each incoming request is assigned to a single priority level.

**Cited excerpt:**

````text
Without APF enabled, overall concurrency in the API server is limited by the
`kube-apiserver` flags `--max-requests-inflight` and
`--max-mutating-requests-inflight`. With APF enabled, the concurrency limits
defined by these flags are summed and then the sum is divided up among a
configurable set of _priority levels_. Each incoming request is assigned to a
single priority level, and each priority level will only dispatch as many
concurrent requests as its particular limit allows.  
The default configuration, for example, includes separate priority levels for
leader-election requests, requests from built-in controllers, and requests from
Pods. This means that an ill-behaved Pod that floods the API server with
requests cannot prevent leader election or actions by the built-in controllers
from succeeding.  
The concurrency limits of the priority levels are periodically
adjusted, allowing under-utilized priority levels to temporarily lend
concurrency to heavily-utilized levels. These limits are based on
nominal limits and bounds on how much concurrency a priority level may
lend and how much it may borrow, all derived from the configuration
objects mentioned below.
````

## M02

**Sentence:** Some long-running requests, such as remote command execution or log tailing, are always subject to this limit.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.29 [stable]  
Controlling the behavior of the Kubernetes API server in an overload situation
is a key task for cluster administrators. The kube-apiserver has some controls available
(i.e. the `--max-requests-inflight` and `--max-mutating-requests-inflight`
command-line flags) to limit the amount of outstanding work that will be
accepted, preventing a flood of inbound requests from overloading and
potentially crashing the API server, but these flags are not enough to ensure
that the most important requests get through in a period of high traffic.  
The API Priority and Fairness feature (APF) is an alternative that improves upon
aforementioned max-inflight limitations. APF classifies
and isolates requests in a more fine-grained way. It also introduces
a limited amount of queuing, so that no requests are rejected in cases
of very brief bursts. Requests are dispatched from queues using a
fair queuing technique so that, for example, a poorly-behaved
controller need not
starve others (even at the same priority level).  
This feature is designed to work well with standard controllers, which
use informers and react to failures of API requests with exponential
back-off, and other clients that also work this way.  
Caution:
Some requests classified as "long-running"&mdash;such as remote
command execution or log tailing&mdash;are not subject to the API
Priority and Fairness filter. This is also true for the
`--max-requests-inflight` flag without the API Priority and Fairness
feature enabled. API Priority and Fairness _does_ apply to **watch**
requests. When API Priority and Fairness is disabled, **watch** requests
are not subject to the `--max-requests-inflight` limit.
````

## M03

**Sentence:** Whether the Pod then runs depends on whether any Node has enough allocatable memory to accommodate the 1 GiB request.

**Cited excerpt:**

````text
Here's a manifest for a Pod that has one container. The container does not
specify a memory request, and it does not specify a memory limit.  
```yaml
apiVersion: v1
kind: Pod
metadata:
name: constraints-mem-demo-4
spec:
containers:
- name: constraints-mem-demo-4-ctr
image: nginx
```  
Create the Pod:  
```shell
kubectl apply -f https://k8s.io/examples/admin/resource/memory-constraints-pod-4.yaml --namespace=constraints-mem-example
```  
View detailed information about the Pod:  
```shell
kubectl get pod constraints-mem-demo-4 --namespace=constraints-mem-example --output=yaml
```  
The output shows that the Pod's only container has a memory request of 1 GiB and a memory limit of 1 GiB.
How did that container get those values?  
```
resources:
limits:
memory: 1Gi
requests:
memory: 1Gi
```  
Because your Pod did not define any memory request and limit for that container, the cluster
applied a
[default memory request and limit](/docs/tasks/administer-cluster/manage-resources/memory-default-namespace/)
from the LimitRange.  
This means that the definition of that Pod shows those values. You can check it using
`kubectl describe`:  
```shell
# Look for the "Requests:" section of the output
kubectl describe pod constraints-mem-demo-4 --namespace=constraints-mem-example
```  
At this point, your Pod might be running or it might not be running. Recall that a prerequisite
for this task is that your Nodes have at least 1 GiB of memory. If each of your Nodes has only
1 GiB of memory, then there is not enough allocatable memory on any Node to accommodate a memory
request of 1 GiB. If you happen to be using Nodes with 2 GiB of memory, then you probably have
enough space to accommodate the 1 GiB request.  
Delete your Pod:  
```shell
kubectl delete pod constraints-mem-demo-4 --namespace=constraints-mem-example
```
````

## M04

**Sentence:** Kubernetes lets you limit the number of process IDs (PIDs) that a Pod can use, which prevents a single Pod from exhausting the node's PIDs.

**Cited excerpt:**

````text
Because Pods represent processes running on nodes in the cluster, it is important to
allow those processes to gracefully terminate when they are no longer needed (rather
than being abruptly stopped with a `KILL` signal and having no chance to clean up).  
The design aim is for you to be able to request deletion and know when processes
terminate, but also be able to ensure that deletes eventually complete.
When you request deletion of a Pod, the cluster records and tracks the intended grace period
before the Pod is allowed to be forcefully killed. With that forceful shutdown tracking in
place, the kubelet attempts graceful
shutdown.  
Typically, with this graceful termination of the pod, kubelet makes requests to the container runtime
to attempt to stop the containers in the pod by first sending a TERM (aka. SIGTERM) signal,
with a grace period timeout, to the main process in each container.
The requests to stop the containers are processed by the container runtime asynchronously.
There is no guarantee to the order of processing for these requests.
Many container runtimes respect the `STOPSIGNAL` value defined in the container image and,
if different, send the container image configured STOPSIGNAL instead of TERM.
Once the grace period has expired, the KILL signal is sent to any remaining
processes, and the Pod is then deleted from the
API Server. If the kubelet or the
container runtime's management service is restarted while waiting for processes to terminate, the
cluster retries from the start including the full original grace period.
````

## M05

**Sentence:** The stated reason is flexibility: unique names let you switch between dedicated and shared clusters in the future, or use multi-cluster tooling such as service meshes.

**Cited excerpt:**

````text
As previously mentioned, you should consider isolating each workload in its own namespace, even if
you are using dedicated clusters or virtualized control planes. This ensures that each workload
only has access to its own resources, such as ConfigMaps and Secrets, and allows you to tailor
dedicated security policies for each workload. In addition, it is a best practice to give each
namespace names that are unique across your entire fleet (that is, even if they are in separate
clusters), as this gives you the flexibility to switch between dedicated and shared clusters in
the future, or to use multi-cluster tooling such as service meshes.  
Conversely, there are also advantages to assigning namespaces at the tenant level, not just the
workload level, since there are often policies that apply to all workloads owned by a single
tenant. However, this raises its own problems. Firstly, this makes it difficult or impossible to
customize policies to individual workloads, and secondly, it may be challenging to come up with a
single level of "tenancy" that should be given a namespace. For example, an organization may have
divisions, teams, and subteams - which should be assigned a namespace?  
One possible approach is to organize your namespaces into hierarchies, and share certain policies and
resources between them. This could include managing namespace labels, namespace lifecycles,
delegated access, and shared resource quotas across related namespaces. These capabilities can
be useful in both multi-team and multi-customer scenarios.
````

## M06

**Sentence:** To prevent a particular role or rolebinding from being autoupdated, set that annotation to "false".

**Cited excerpt:**

````text
Type: Annotation  
Example: `rbac.authorization.kubernetes.io/autoupdate: "false"`  
Used on: ClusterRole, ClusterRoleBinding, Role, RoleBinding  
When this annotation is set to `"true"` on default RBAC objects created by the API server,
they are automatically updated at server start to add missing permissions and subjects
(extra permissions and subjects are left in place).
To prevent autoupdating a particular role or rolebinding, set this annotation to `"false"`.
If you create your own RBAC objects and set this annotation to `"false"`, `kubectl auth reconcile`
(which allows reconciling arbitrary RBAC objects in a manifest)
respects this annotation and does not automatically add missing permissions and subjects.
````

## M07

**Sentence:** Before the kubelet terminates end-user pods, it attempts to reclaim node-level resources.

**Cited excerpt:**

````text
Self healing behavior
The kubelet attempts to [reclaim node-level resources](#reclaim-node-resources)
before it terminates end-user pods. For example, it removes unused container
images when disk resources are starved.  
If the pods are managed by a workload
management object (such as StatefulSet
or Deployment) that
replaces failed pods, the control plane (`kube-controller-manager`) creates new
pods in place of the evicted pods.

If you are running a [static pod](/docs/concepts/workloads/pods/#static-pods)
on a node that is under resource pressure, the kubelet may evict that static
Pod. The kubelet then tries to create a replacement, because static Pods always
represent an intent to run a Pod on that node.  
The kubelet takes the _priority_ of the static pod into account when creating
a replacement. If the static pod manifest specifies a low priority, and there
are higher-priority Pods defined within the cluster's control plane, and the
node is under resource pressure, the kubelet may not be able to make room for
that static pod. The kubelet continues to attempt to run all static pods even
when there is resource pressure on a node.
````

## M08

**Sentence:** Any Pods located on those bypassed nodes do not impact the maxSkew calculation.

**Cited excerpt:**

````text
There are some implicit conventions worth noting here:  
- Only the Pods holding the same namespace as the incoming Pod can be matching candidates.  
- The scheduler only considers nodes that have all `topologySpreadConstraints[*].topologyKey` present at the same time.
Nodes missing any of these `topologyKeys` are bypassed. This implies that:  
1. any Pods located on those bypassed nodes do not impact `maxSkew` calculation - in the
above [example](#example-conflicting-topologyspreadconstraints), suppose the node `node1`
does not have a label "zone", then the 2 Pods will
be disregarded, hence the incoming Pod will be scheduled into zone `A`.
2. the incoming Pod has no chances to be scheduled onto this kind of nodes -
in the above example, suppose a node `node5` has the **mistyped** label `zone-typo: zoneC`
(and no `zone` label set). After node `node5` joins the cluster, it will be bypassed and
Pods for this workload aren't scheduled there.  
- Be aware of what will happen if the incoming Pod's
`topologySpreadConstraints[*].labelSelector` doesn't match its own labels. In the
above example, if you remove the incoming Pod's labels, it can still be placed onto
nodes in zone `B`, since the constraints are still satisfied. However, after that
placement, the degree of imbalance of the cluster remains unchanged - it's still zone `A`
having 2 Pods labeled as `foo: bar`, and zone `B` having 1 Pod labeled as
`foo: bar`. If this is not what you expect, update the workload's
`topologySpreadConstraints[*].labelSelector` to match the labels in the pod template.
````

## M09

**Sentence:** preBind plugins perform any work required before a Pod is bound.

**Cited excerpt:**

````text
PreBind {#pre-bind}
These plugins are used to perform any work required before a Pod is bound. For
example, a pre-bind plugin may provision a network volume and mount it on the
target node before allowing the Pod to run there.  
If any PreBind plugin returns an error, the Pod is [rejected](#reserve) and
returned to the scheduling queue.

These plugins are used to bind a Pod to a Node. Bind plugins will not be called
until all PreBind plugins have completed. Each bind plugin is called in the
configured order. A bind plugin may choose whether or not to handle the given
Pod. If a bind plugin chooses to handle a Pod, **the remaining bind plugins are
skipped**.

PostBind {#post-bind}
This is an informational interface. Post-bind plugins are called after a
Pod is successfully bound. This is the end of a binding cycle, and can be used
to clean up associated resources.
````

## M10

**Sentence:** An administrator can use it to limit the maximum value of a projected service account token's `expirationSeconds`.

**Cited excerpt:**

````text
You can inject the token for the current [service account](/docs/reference/access-authn-authz/authentication/#service-account-tokens)
into a Pod at a specified path. For example:  
```yaml
apiVersion: v1
kind: Pod
metadata:
name: sa-token-test
spec:
containers:
- name: container-test
image: busybox:1.28
command: ["sleep", "3600"]
volumeMounts:
- name: token-vol
mountPath: "/service-account"
readOnly: true
serviceAccountName: default
volumes:
- name: token-vol
projected:
sources:
- serviceAccountToken:
audience: api
expirationSeconds: 3600
path: token
```  
The example Pod has a projected volume containing the injected service account
token. Containers in this Pod can use that token to access the Kubernetes API
server, authenticating with the identity of [the pod's ServiceAccount](/docs/tasks/configure-pod-container/configure-service-account/).
The `audience` field contains the intended audience of the
token. A recipient of the token must identify itself with an identifier specified
in the audience of the token, and otherwise should reject the token. This field
is optional and it defaults to the identifier of the API server.  
The `expirationSeconds` is the expected duration of validity of the service account
token. It defaults to 1 hour and must be at least 10 minutes (600 seconds). An administrator
can also limit its maximum value by specifying the `--service-account-max-token-expiration`
option for the API server. The `path` field specifies a relative path to the mount point
of the projected volume.  
Note:
A container using a projected volume source as a [`subPath`](/docs/concepts/storage/volumes/#using-subpath)
volume mount will not receive updates for those volume sources.
````

## M11

**Sentence:** APF classifies and isolates requests in a more fine-grained way.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.29 [stable]  
Controlling the behavior of the Kubernetes API server in an overload situation
is a key task for cluster administrators. The kube-apiserver has some controls available
(i.e. the `--max-requests-inflight` and `--max-mutating-requests-inflight`
command-line flags) to limit the amount of outstanding work that will be
accepted, preventing a flood of inbound requests from overloading and
potentially crashing the API server, but these flags are not enough to ensure
that the most important requests get through in a period of high traffic.  
The API Priority and Fairness feature (APF) is an alternative that improves upon
aforementioned max-inflight limitations. APF classifies
and isolates requests in a more fine-grained way. It also introduces
a limited amount of queuing, so that no requests are rejected in cases
of very brief bursts. Requests are dispatched from queues using a
fair queuing technique so that, for example, a poorly-behaved
controller need not
starve others (even at the same priority level).  
This feature is designed to work well with standard controllers, which
use informers and react to failures of API requests with exponential
back-off, and other clients that also work this way.  
Caution:
Some requests classified as "long-running"&mdash;such as remote
command execution or log tailing&mdash;are not subject to the API
Priority and Fairness filter. This is also true for the
`--max-requests-inflight` flag without the API Priority and Fairness
feature enabled. API Priority and Fairness _does_ apply to **watch**
requests. When API Priority and Fairness is disabled, **watch** requests
are not subject to the `--max-requests-inflight` limit.
````

## M12

**Sentence:** Cosign 2.0 requires the `--certificate-oidc-issuer` option in addition to `--certificate-identity`.

**Cited excerpt:**

````text
The Kubernetes release process signs all binary artifacts (tarballs, SPDX files,
standalone binaries) by using cosign's keyless signing. To verify a particular
binary, retrieve it together with its signature and certificate:  
```bash
URL=https://dl.k8s.io/release/v/bin/linux/amd64
BINARY=kubectl

FILES=(
"$BINARY"
"$BINARY.sig"
"$BINARY.cert"
)

for FILE in "${FILES[@]}"; do
curl -sSfL --retry 3 --retry-delay 3 "$URL/$FILE" -o "$FILE"
done
```  
Then verify the blob by using `cosign verify-blob`:  
```shell
cosign verify-blob "$BINARY" \
--signature "$BINARY".sig \
--certificate "$BINARY".cert \
--certificate-identity krel-staging@k8s-releng-prod.iam.gserviceaccount.com \
--certificate-oidc-issuer https://accounts.google.com
```  
Note:
Cosign 2.0 requires the `--certificate-identity` and `--certificate-oidc-issuer` options.  
To learn more about keyless signing, please refer to [Keyless Signatures](https://docs.sigstore.dev/cosign/signing/overview/).  
Previous versions of Cosign required that you set `COSIGN_EXPERIMENTAL=1`.  
For additional information, please refer to the [sigstore Blog](https://blog.sigstore.dev/cosign-2-0-released/)
````

## M13

**Sentence:** The taint marks the node as needing a second initialization from an external controller before it can be scheduled work.

**Cited excerpt:**

````text
Successfully running cloud-controller-manager requires some changes to your cluster configuration.  
* `kubelet` and `kube-controller-manager` must be set according to the
user's usage of external CCM. If the user has an external CCM (not the internal cloud
controller loops in the Kubernetes Controller Manager), then `--cloud-provider=external`
must be specified. Otherwise, it should not be specified.  
Keep in mind that setting up your cluster to use cloud controller manager will
change your cluster behaviour in a few ways:  
* Components that specify `--cloud-provider=external` will add a taint
`node.cloudprovider.kubernetes.io/uninitialized` with an effect `NoSchedule`
during initialization. This marks the node as needing a second initialization
from an external controller before it can be scheduled work. Note that in the
event that cloud controller manager is not available, new nodes in the cluster
will be left unschedulable. The taint is important since the scheduler may
require cloud specific information about nodes such as their region or type
(high cpu, gpu, high memory, spot instance, etc).
* cloud information about nodes in the cluster will no longer be retrieved using
local metadata, but instead all API calls to retrieve node information will go
through cloud controller manager. This may mean you can restrict access to your
cloud API on the kubelets for better security. For larger clusters you may want
to consider if cloud controller manager will hit rate limits since it is now
responsible for almost all API calls to your cloud from within the cluster.  
The cloud controller manager can implement:  
* Node controller - responsible for updating kubernetes nodes using cloud APIs
and deleting kubernetes nodes that were deleted on your cloud.
* Service controller - responsible for loadbalancers on your cloud against
services of type LoadBalancer.
* Route controller - responsible for setting up network routes on your cloud
* any other features you would like to implement if you are running an out-of-tree provider.
````

## M14

**Sentence:** A Workload must define either `spec.podGroupTemplates` (flat) or `spec.compositePodGroupTemplates` (hierarchical), but not both.

**Cited excerpt:**

````text
Feature gate: CompositePodGroup  
When the [`CompositePodGroup`](/docs/reference/command-line-tools-reference/feature-gates/#CompositePodGroup)
feature gate and the `scheduling.k8s.io/v1alpha3` API group
are enabled, you can use `CompositePodGroupTemplates` to define multi-level, hierarchical scheduling
requirements in a `Workload`. These requirements can include enforcing nested topology constraints
across different layers of cluster infrastructure (multi-level topology-aware scheduling),
all-or-nothing scheduling across child groups (multi-level gang scheduling), or group-level
disruption policies.  
`CompositePodGroupTemplates` can be defined using the `spec.compositePodGroupTemplates` field in the
`Workload` API. At runtime, workload controllers create [CompositePodGroup](/docs/concepts/workloads/compositepodgroup-api/)
and [PodGroup](/docs/concepts/workloads/podgroup-api/) objects from these templates to maintain the runtime
scheduling state of the hierarchy. While `PodGroup` objects manage groups of Pods at the leaves,
`CompositePodGroup` objects represent non-leaf groups that enforce scheduling policies across child groups.  
Note:
In a `Workload` specification, `spec.compositePodGroupTemplates` and `spec.podGroupTemplates`
fields form a union: a `Workload` must define either `spec.podGroupTemplates` (for flat
workloads) or `spec.compositePodGroupTemplates` (for hierarchical workloads), but cannot
specify both.  
#### Structure and constraints  
The `spec.compositePodGroupTemplates` field defines non-leaf templates in a group-template
hierarchy tree. Each entry represents a template for a `CompositePodGroup` and can contain:  
- **Child templates**: Nested `CompositePodGroupTemplates` (for intermediate non-leaf
groups) or `PodGroupTemplates` (for leaf groups containing Pods).
- **Scheduling policy**: Specifies how child groups within this composite group are
scheduled:
- `basic`: Child groups are admitted and scheduled independently.
- `gang`: Enforces multi-level all-or-nothing scheduling across child groups.
Requires `minGroupCount`, which specifies the minimum number of child groups
that must be schedulable simultaneously for the composite group to be feasible.
- **Scheduling constraints**: Optional
[topology constraints](/docs/concepts/workloads/workload-api/topology-aware-scheduling/)
for multi-level topology-aware scheduling.
- **Priority, preemption policy and disruption mode**: Optional `priorityClassName`,
`disruptionMode` (`Single` or `All`) and `preemptionPolicy` for
[workload-aware preemption](/docs/concepts/workloads/workload-api/disruption-and-priority/).
````

## M15

**Sentence:** The incoming Pod also cannot be scheduled onto such a node.

**Cited excerpt:**

````text
There are some implicit conventions worth noting here:  
- Only the Pods holding the same namespace as the incoming Pod can be matching candidates.  
- The scheduler only considers nodes that have all `topologySpreadConstraints[*].topologyKey` present at the same time.
Nodes missing any of these `topologyKeys` are bypassed. This implies that:  
1. any Pods located on those bypassed nodes do not impact `maxSkew` calculation - in the
above [example](#example-conflicting-topologyspreadconstraints), suppose the node `node1`
does not have a label "zone", then the 2 Pods will
be disregarded, hence the incoming Pod will be scheduled into zone `A`.
2. the incoming Pod has no chances to be scheduled onto this kind of nodes -
in the above example, suppose a node `node5` has the **mistyped** label `zone-typo: zoneC`
(and no `zone` label set). After node `node5` joins the cluster, it will be bypassed and
Pods for this workload aren't scheduled there.  
- Be aware of what will happen if the incoming Pod's
`topologySpreadConstraints[*].labelSelector` doesn't match its own labels. In the
above example, if you remove the incoming Pod's labels, it can still be placed onto
nodes in zone `B`, since the constraints are still satisfied. However, after that
placement, the degree of imbalance of the cluster remains unchanged - it's still zone `A`
having 2 Pods labeled as `foo: bar`, and zone `B` having 1 Pod labeled as
`foo: bar`. If this is not what you expect, update the workload's
`topologySpreadConstraints[*].labelSelector` to match the labels in the pod template.
````

## M16

**Sentence:** It depends on the rbac.authorization.kubernetes.io/autoupdate annotation: when it is "true" on default RBAC objects created by the API server, they are automatically updated at server start to add missing permissions and subjects.

**Cited excerpt:**

````text
Type: Annotation  
Example: `rbac.authorization.kubernetes.io/autoupdate: "false"`  
Used on: ClusterRole, ClusterRoleBinding, Role, RoleBinding  
When this annotation is set to `"true"` on default RBAC objects created by the API server,
they are automatically updated at server start to add missing permissions and subjects
(extra permissions and subjects are left in place).
To prevent autoupdating a particular role or rolebinding, set this annotation to `"false"`.
If you create your own RBAC objects and set this annotation to `"false"`, `kubectl auth reconcile`
(which allows reconciling arbitrary RBAC objects in a manifest)
respects this annotation and does not automatically add missing permissions and subjects.
````

## M17

**Sentence:** At runtime, workload controllers create CompositePodGroup and PodGroup objects from these templates to maintain the runtime scheduling state of the hierarchy.

**Cited excerpt:**

````text
Feature gate: CompositePodGroup  
When the [`CompositePodGroup`](/docs/reference/command-line-tools-reference/feature-gates/#CompositePodGroup)
feature gate and the `scheduling.k8s.io/v1alpha3` API group
are enabled, you can use `CompositePodGroupTemplates` to define multi-level, hierarchical scheduling
requirements in a `Workload`. These requirements can include enforcing nested topology constraints
across different layers of cluster infrastructure (multi-level topology-aware scheduling),
all-or-nothing scheduling across child groups (multi-level gang scheduling), or group-level
disruption policies.  
`CompositePodGroupTemplates` can be defined using the `spec.compositePodGroupTemplates` field in the
`Workload` API. At runtime, workload controllers create [CompositePodGroup](/docs/concepts/workloads/compositepodgroup-api/)
and [PodGroup](/docs/concepts/workloads/podgroup-api/) objects from these templates to maintain the runtime
scheduling state of the hierarchy. While `PodGroup` objects manage groups of Pods at the leaves,
`CompositePodGroup` objects represent non-leaf groups that enforce scheduling policies across child groups.  
Note:
In a `Workload` specification, `spec.compositePodGroupTemplates` and `spec.podGroupTemplates`
fields form a union: a `Workload` must define either `spec.podGroupTemplates` (for flat
workloads) or `spec.compositePodGroupTemplates` (for hierarchical workloads), but cannot
specify both.  
#### Structure and constraints  
The `spec.compositePodGroupTemplates` field defines non-leaf templates in a group-template
hierarchy tree. Each entry represents a template for a `CompositePodGroup` and can contain:  
- **Child templates**: Nested `CompositePodGroupTemplates` (for intermediate non-leaf
groups) or `PodGroupTemplates` (for leaf groups containing Pods).
- **Scheduling policy**: Specifies how child groups within this composite group are
scheduled:
- `basic`: Child groups are admitted and scheduled independently.
- `gang`: Enforces multi-level all-or-nothing scheduling across child groups.
Requires `minGroupCount`, which specifies the minimum number of child groups
that must be schedulable simultaneously for the composite group to be feasible.
- **Scheduling constraints**: Optional
[topology constraints](/docs/concepts/workloads/workload-api/topology-aware-scheduling/)
for multi-level topology-aware scheduling.
- **Priority, preemption policy and disruption mode**: Optional `priorityClassName`,
`disruptionMode` (`Single` or `All`) and `preemptionPolicy` for
[workload-aware preemption](/docs/concepts/workloads/workload-api/disruption-and-priority/).
````

## M18

**Sentence:** Later values in the comma-separated list override earlier ones.

**Cited excerpt:**

````text
This page shows how to enable or disable an API version from your cluster's
control plane.  
Specific API versions can be turned on or off by passing `--runtime-config=api/<version>` as a
command line argument to the API server. The values for this argument are a comma-separated
list of API versions. Later values override earlier values.  
The `runtime-config` command line argument also supports 2 special keys:  
- `api/all`, representing all known APIs
- `api/legacy`, representing only legacy APIs. Legacy APIs are any APIs that have been
explicitly [deprecated](/docs/reference/using-api/deprecation-policy/).  
For example, to turn off all API versions except v1, pass `--runtime-config=api/all=false,api/v1=true`
to the `kube-apiserver`.
````

## M19

**Sentence:** Process IDs (PIDs) are a fundamental resource on nodes.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.20 [stable]  
Kubernetes allow you to limit the number of process IDs (PIDs) that a
Pod can use.
You can also reserve a number of allocatable PIDs for each node
for use by the operating system and daemons (rather than by Pods).  
Process IDs (PIDs) are a fundamental resource on nodes. It is trivial to hit the
task limit without hitting any other resource limits, which can then cause
instability to a host machine.  
Cluster administrators require mechanisms to ensure that Pods running in the
cluster cannot induce PID exhaustion that prevents host daemons (such as the
kubelet or
kube-proxy,
and potentially also the container runtime) from running.
In addition, it is important to ensure that PIDs are limited among Pods in order
to ensure they have limited impact on other workloads on the same node.  
Note:
On certain Linux installations, the operating system sets the PIDs limit to a low default,
such as `32768`. Consider raising the value of `/proc/sys/kernel/pid_max`.  
You can configure a kubelet to limit the number of PIDs a given Pod can consume.
For example, if your node's host OS is set to use a maximum of `262144` PIDs and
expect to host less than `250` Pods, one can give each Pod a budget of `1000`
PIDs to prevent using up that node's overall number of available PIDs. If the
admin wants to overcommit PIDs similar to CPU or memory, they may do so as well
with some additional risks. Either way, a single Pod will not be able to bring
the whole machine down. This kind of resource limiting helps to prevent simple
fork bombs from affecting operation of an entire cluster.  
Per-Pod PID limiting allows administrators to protect one Pod from another, but
does not ensure that all Pods scheduled onto that host are unable to impact the node overall.
Per-Pod limiting also does not protect the node agents themselves from PID exhaustion.  
You can also reserve an amount of PIDs for node overhead, separate from the
allocation to Pods. This is similar to how you can reserve CPU, memory, or other
resources for use by the operating system and other facilities outside of Pods
and their containers.  
PID limiting is an important sibling to [compute
resource](/docs/concepts/configuration/manage-resources-containers/) requests
and limits. However, you specify it in a different way: rather than defining a
Pod's resource limit in the `.spec` for a Pod, you configure the limit as a
setting on the kubelet. Pod-defined PID limits are not currently supported.  
Caution:
This means that the limit that applies to a Pod may be different depending on
````

## M20

**Sentence:** The container runtime (such as containerd or CRI-O) must support that `mount_options` field for the feature to work.

**Cited excerpt:**

````text
Feature gate: VolumeBindMountOptions  
This page shows how to apply security-related bind mount options (`noexec`,
`nodev`, `nosuid`) to volume mounts in a Pod.

You need to have the `VolumeBindMountOptions`
[feature gate](/docs/reference/command-line-tools-reference/feature-gates/) enabled
on the API server **and** the kubelet. The container runtime must also support
the `mount_options` field in the CRI `Mount` message.
````

## M21

**Sentence:** As a further example, you can disable the `v1beta3` version of the API Priority and Fairness API group with `--runtime-config=flowcontrol.apiserver.k8s.io/v1beta3=false`.

**Cited excerpt:**

````text
The API Priority and Fairness feature is controlled by a command-line flag
and is enabled by default. See
[Options](/docs/reference/command-line-tools-reference/kube-apiserver/#options)
for a general explanation of the available kube-apiserver command-line
options and how to enable and disable them. The name of the
command-line option for APF is "--enable-priority-and-fairness". This feature
also involves an API Group
with: (a) a stable `v1` version, introduced in 1.29, and
enabled by default (b) a `v1beta3` version, enabled by default, and
deprecated in v1.29. You can
disable the API group beta version `v1beta3` by adding the
following command-line flags to your `kube-apiserver` invocation:  
```shell
kube-apiserver \
--runtime-config=flowcontrol.apiserver.k8s.io/v1beta3=false \
# …and other flags as usual
```  
The command-line flag `--enable-priority-and-fairness=false` will disable the
API Priority and Fairness feature.
````

## M22

**Sentence:** For example, if the host OS allows a maximum of 524288 PIDs and you expect fewer than 250 Pods, you could give each Pod a budget of 1000 PIDs.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.20 [stable]  
Kubernetes allow you to limit the number of process IDs (PIDs) that a
Pod can use.
You can also reserve a number of allocatable PIDs for each node
for use by the operating system and daemons (rather than by Pods).  
Process IDs (PIDs) are a fundamental resource on nodes. It is trivial to hit the
task limit without hitting any other resource limits, which can then cause
instability to a host machine.  
Cluster administrators require mechanisms to ensure that Pods running in the
cluster cannot induce PID exhaustion that prevents host daemons (such as the
kubelet or
kube-proxy,
and potentially also the container runtime) from running.
In addition, it is important to ensure that PIDs are limited among Pods in order
to ensure they have limited impact on other workloads on the same node.  
Note:
On certain Linux installations, the operating system sets the PIDs limit to a low default,
such as `32768`. Consider raising the value of `/proc/sys/kernel/pid_max`.  
You can configure a kubelet to limit the number of PIDs a given Pod can consume.
For example, if your node's host OS is set to use a maximum of `262144` PIDs and
expect to host less than `250` Pods, one can give each Pod a budget of `1000`
PIDs to prevent using up that node's overall number of available PIDs. If the
admin wants to overcommit PIDs similar to CPU or memory, they may do so as well
with some additional risks. Either way, a single Pod will not be able to bring
the whole machine down. This kind of resource limiting helps to prevent simple
fork bombs from affecting operation of an entire cluster.  
Per-Pod PID limiting allows administrators to protect one Pod from another, but
does not ensure that all Pods scheduled onto that host are unable to impact the node overall.
Per-Pod limiting also does not protect the node agents themselves from PID exhaustion.  
You can also reserve an amount of PIDs for node overhead, separate from the
allocation to Pods. This is similar to how you can reserve CPU, memory, or other
resources for use by the operating system and other facilities outside of Pods
and their containers.  
PID limiting is an important sibling to [compute
resource](/docs/concepts/configuration/manage-resources-containers/) requests
and limits. However, you specify it in a different way: rather than defining a
Pod's resource limit in the `.spec` for a Pod, you configure the limit as a
setting on the kubelet. Pod-defined PID limits are not currently supported.  
Caution:
This means that the limit that applies to a Pod may be different depending on
````

## M23

**Sentence:** The flag applies to bindings, not roles; removing extra permissions from roles is controlled by the separate `--remove-extra-permissions` flag.

**Cited excerpt:**

````text
Creates or updates `rbac.authorization.k8s.io/v1` API objects from a manifest file.  
Missing objects are created, and the containing namespace is created for namespaced objects, if required.  
Existing roles are updated to include the permissions in the input objects,
and remove extra permissions if `--remove-extra-permissions` is specified.  
Existing bindings are updated to include the subjects in the input objects,
and remove extra subjects if `--remove-extra-subjects` is specified.  
Examples:  
* Test applying a manifest file of RBAC objects, displaying changes that would be made:  
```shell
kubectl auth reconcile -f my-rbac-rules.yaml --dry-run=client
```  
* Apply a manifest file of RBAC objects, preserving any extra permissions (in roles) and any extra subjects (in bindings):  
```shell
kubectl auth reconcile -f my-rbac-rules.yaml
```  
* Apply a manifest file of RBAC objects, removing any extra permissions (in roles) and any extra subjects (in bindings):  
```shell
kubectl auth reconcile -f my-rbac-rules.yaml --remove-extra-subjects --remove-extra-permissions
```
````

## M24

**Sentence:** The field can only be initialized when the Pod is created, and afterwards gates can be removed in any order but new gates cannot be added.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.30 [stable]  
Pods were considered ready for scheduling once created. Kubernetes scheduler
does its due diligence to find nodes to place all pending Pods. However, in a
real-world case, some Pods may stay in a "miss-essential-resources" state for a long period.
These Pods actually churn the scheduler (and downstream integrators like Cluster AutoScaler)
in an unnecessary manner.  
By specifying/removing a Pod's `.spec.schedulingGates`, you can control when a Pod is ready
to be considered for scheduling.

Configuring Pod schedulingGates
The `schedulingGates` field contains a list of strings, and each string literal is perceived as a
criteria that Pod should be satisfied before considered schedulable. This field can be initialized
only when a Pod is created (either by the client, or mutated during admission). After creation,
each schedulingGate can be removed in arbitrary order, but addition of a new scheduling gate is disallowed.  
Figure: Figure. Pod SchedulingGates
````

## M25

**Sentence:** Bind plugins will not be called until all PreBind plugins have completed.

**Cited excerpt:**

````text
PreBind {#pre-bind}
These plugins are used to perform any work required before a Pod is bound. For
example, a pre-bind plugin may provision a network volume and mount it on the
target node before allowing the Pod to run there.  
If any PreBind plugin returns an error, the Pod is [rejected](#reserve) and
returned to the scheduling queue.

These plugins are used to bind a Pod to a Node. Bind plugins will not be called
until all PreBind plugins have completed. Each bind plugin is called in the
configured order. A bind plugin may choose whether or not to handle the given
Pod. If a bind plugin chooses to handle a Pod, **the remaining bind plugins are
skipped**.

PostBind {#post-bind}
This is an informational interface. Post-bind plugins are called after a
Pod is successfully bound. This is the end of a binding cycle, and can be used
to clean up associated resources.
````

## M26

**Sentence:** The container that is terminated (OOMKilled) does not clean up the custom packet filtering rules that it added during startup.

**Cited excerpt:**

````text
The `node-local-dns` Pods use memory for storing cache entries and processing queries.
Since they do not watch Kubernetes objects, the cluster size or the number of Services / EndpointSlices do not directly affect memory usage. Memory usage is influenced by the DNS query pattern.
From [CoreDNS docs](https://github.com/coredns/deployment/blob/master/kubernetes/Scaling_CoreDNS.md),
> The default cache size is 10000 entries, which uses about 30 MB when completely filled.  
This would be the memory usage for each server block (if the cache gets completely filled).
Memory usage can be reduced by specifying smaller cache sizes.  
The number of concurrent queries is linked to the memory demand, because each extra
goroutine used for handling a query requires an amount of memory. You can set an upper limit
using the `max_concurrent` option in the forward plugin.  
If a `node-local-dns` Pod attempts to use more memory than is available (because of total system
resources, or because of a configured
[resource limit](/docs/concepts/configuration/manage-resources-containers/)), the operating system
may shut down that pod's container.
If this happens, the container that is terminated (“OOMKilled”) does not clean up the custom
packet filtering rules that it previously added during startup.
The `node-local-dns` container should get restarted (since managed as part of a DaemonSet), but this
will lead to a brief DNS downtime each time that the container fails: the packet filtering rules direct
DNS queries to a local Pod that is unhealthy.  
You can determine a suitable memory limit by running node-local-dns pods without a limit and
measuring the peak usage. You can also set up and use a
[VerticalPodAutoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
in _recommender mode_, and then check its recommendations.
````

## M27

**Sentence:** The taint marks the node as unusable until a controller from the cloud-controller-manager initializes the node and then removes the taint.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.18 [stable]  
The node controller automatically taints a Node when certain conditions
are true. The following taints are built in:  
* `node.kubernetes.io/not-ready`: Node is not ready. This corresponds to
the NodeCondition `Ready` being "`False`".
* `node.kubernetes.io/unreachable`: Node is unreachable from the node
controller. This corresponds to the NodeCondition `Ready` being "`Unknown`".
* `node.kubernetes.io/memory-pressure`: Node has memory pressure.
* `node.kubernetes.io/disk-pressure`: Node has disk pressure.
* `node.kubernetes.io/pid-pressure`: Node has PID pressure.
* `node.kubernetes.io/network-unavailable`: Node's network is unavailable.
* `node.kubernetes.io/unschedulable`: Node is unschedulable.
* `node.cloudprovider.kubernetes.io/uninitialized`: When the kubelet is started
with an "external" cloud provider, this taint is set on a node to mark it
as unusable. After a controller from the cloud-controller-manager initializes
this node, the kubelet removes this taint.  
In case a node is to be drained, the node controller or the kubelet adds relevant taints
with `NoExecute` effect. This effect is added by default for the
`node.kubernetes.io/not-ready` and `node.kubernetes.io/unreachable` taints.
If the fault condition returns to normal, the kubelet or node
controller can remove the relevant taint(s).  
In some cases when the node is unreachable, the API server is unable to communicate
with the kubelet on the node. The decision to delete the pods cannot be communicated to
the kubelet until communication with the API server is re-established. In the meantime,
the pods that are scheduled for deletion may continue to run on the partitioned node.  
Note:
The control plane limits the rate of adding new taints to nodes. This rate limiting
manages the number of evictions that are triggered when many nodes become unreachable at
once (for example: if there is a network disruption).  
You can specify `tolerationSeconds` for a Pod to define how long that Pod stays bound
to a failing or unresponsive Node.  
For example, you might want to keep an application with a lot of local state
bound to node for a long time in the event of network partition, hoping
that the partition will recover and thus the pod eviction can be avoided.
The toleration you set for that Pod might look like:  

```yaml
tolerations:
- key: "node.kubernetes.io/unreachable"
operator: "Exists"
effect: "NoExecute"
tolerationSeconds: 6000
```  
````

## M28

**Sentence:** Where you do not fully trust such a user, you should enforce the Baseline or Restricted Pod Security Standard, for example using Pod Security admission.

**Cited excerpt:**

````text
Permission to create workloads (either Pods, or
[workload resources](/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods. Additionally, since Pods can run as any
[ServiceAccount](/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.  
Users who can run privileged Pods can use that access to gain node access and potentially to
further elevate their privileges. Where you do not fully trust a user or other principal
with the ability to create suitably secure and isolated Pods, you should enforce either the
**Baseline** or **Restricted** Pod Security Standard.
You can use [Pod Security admission](/docs/concepts/security/pod-security-admission/)
or other (third party) mechanisms to implement that enforcement.  
For these reasons, namespaces should be used to separate resources requiring different levels of
trust or tenancy. It is still considered best practice to follow [least privilege](#least-privilege)
principles and assign the minimum set of permissions, but boundaries within a namespace should be
considered weak.
````

## M29

**Sentence:** metrics-server is a lightweight, short-term, in-memory component that exposes these metrics via the `metrics.k8s.io` API.

**Cited excerpt:**

````text
The resource metrics pipeline provides a limited set of metrics related to
cluster components such as the
[Horizontal Pod Autoscaler](/docs/tasks/run-application/horizontal-pod-autoscale/)
controller, as well as the `kubectl top` utility.
These  metrics are collected by the lightweight, short-term, in-memory
[metrics-server](https://github.com/kubernetes-sigs/metrics-server) and
are exposed via the `metrics.k8s.io` API.  
metrics-server discovers all nodes on the cluster and
queries each node's
[kubelet](/docs/reference/command-line-tools-reference/kubelet/) for CPU and
memory usage. The kubelet acts as a bridge between the Kubernetes master and
the nodes, managing the pods and containers running on a machine. The kubelet
translates each pod into its constituent containers and fetches individual
container usage statistics from the container runtime through the container
runtime interface. If you use a container runtime that uses Linux cgroups and
namespaces to implement containers, and the container runtime does not publish
usage statistics, then the kubelet can look up those statistics directly
(using code from [cAdvisor](https://github.com/google/cadvisor)).
No matter how those statistics arrive, the kubelet then exposes the aggregated pod
resource usage statistics through the metrics-server Resource Metrics API.
This API is served at `/metrics/resource` on the kubelet's authenticated and
read-only ports.
````

## M30

**Sentence:** The flag takes comma-separated `<key>[=<value>]` pairs, and if `=<value>` is omitted it is treated as `=true`.

**Cited excerpt:**

````text
Certain resources and API groups are enabled by default. You can enable or
disable them by setting `--runtime-config` on the API server.  The
`--runtime-config` flag accepts comma separated `<key>[=<value>]` pairs
describing the runtime configuration of the API server. If the `=<value>`
part is omitted, it is treated as if `=true` is specified. For example:  
- to disable `batch/v1`, set `--runtime-config=batch/v1=false`
- to enable `batch/v2alpha1`, set `--runtime-config=batch/v2alpha1`
- to enable a specific version of an API, such as `storage.k8s.io/v1beta1/csistoragecapacities`, set `--runtime-config=storage.k8s.io/v1beta1/csistoragecapacities`  
Note:
When you enable or disable groups or resources, you need to restart the API
server and controller manager to pick up the `--runtime-config` changes.
````
